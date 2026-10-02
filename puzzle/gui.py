"""Tkinter user interface for the Picture Restore puzzle."""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .board import PuzzleBoard
from .difficulty import DIFFICULTIES
from .game import PuzzleGame
from .image_processor import ImageLoadError, ImageProcessor
from .tile import Tile
from .transformations import TransformationFactory


# ---------------------------------------------------------------------- #
# Canvases
# ---------------------------------------------------------------------- #
class ImageCanvas(tk.Canvas):
    """Base canvas that shows an image split into a grid.

    Subclasses override draw_overlays() to add their own markings.
    redraw() calls it without knowing which subclass it is (polymorphism).
    """

    BACKGROUND = "#1f1f1f"
    HINT_COLOUR = "#1e90ff"

    def __init__(self, master, size):
        super().__init__(master, width=size, height=size, bg=self.BACKGROUND,
                         highlightthickness=0)
        self._photo = None        # keep a reference or Tk discards the image
        self._grid_size = 3
        self._side = size
        self._placeholder_text = "No image loaded"
        self._draw_placeholder()

    @property
    def tile_size(self):
        return self._side // self._grid_size

    def show(self, image_bgr, grid_size):
        """Display a BGR image and remember the grid it is divided into."""
        self._grid_size = grid_size
        self._side = image_bgr.shape[0]
        rgb = ImageProcessor.to_rgb(image_bgr)
        self._photo = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.config(width=self._side, height=self._side)
        self.redraw()

    def redraw(self):
        self.delete("all")
        if self._photo is None:
            self._draw_placeholder()
            return
        self.create_image(0, 0, anchor="nw", image=self._photo)
        self.draw_overlays()

    def draw_overlays(self):
        """Hook for subclasses."""

    def cell_box(self, position):
        """(x0, y0, x1, y1) pixel box of a grid position."""
        row, col = divmod(position, self._grid_size)
        t = self.tile_size
        return col * t, row * t, (col + 1) * t, (row + 1) * t

    def _draw_hint_circle(self, position):
        x0, y0, x1, y1 = self.cell_box(position)
        inset = self.tile_size * 0.15
        self.create_oval(x0 + inset, y0 + inset, x1 - inset, y1 - inset,
                         outline=self.HINT_COLOUR, width=4)

    def _draw_placeholder(self):
        size = int(self["width"])
        self.create_text(size // 2, size // 2, text=self._placeholder_text,
                         fill="#888888", font=("Segoe UI", 12))


class OriginalCanvas(ImageCanvas):
    """Left-hand reference image. Ignores clicks; can show a hint target."""

    def __init__(self, master, size):
        super().__init__(master, size)
        self._hint_home = None

    def set_hint(self, position):
        self._hint_home = position
        self.redraw()

    def draw_overlays(self):
        if self._hint_home is not None:
            self._draw_hint_circle(self._hint_home)


class BoardCanvas(ImageCanvas):
    """Right-hand puzzle image: the only canvas that reacts to clicks."""

    GRID_COLOUR = "#d9d9d9"
    SELECT_COLOUR = "#ffb300"
    TICK_COLOUR = "#1fae4b"
    DONE_COLOUR = "#1fae4b"

    def __init__(self, master, size):
        super().__init__(master, size)
        self._game = None

    def attach_game(self, game):
        self._game = game

    def position_at(self, x, y):
        """Grid position under a pixel, or None if outside the image."""
        if self._photo is None or not (0 <= x < self._side and 0 <= y < self._side):
            return None
        t = self.tile_size
        col, row = x // t, y // t
        if col >= self._grid_size or row >= self._grid_size:
            return None
        return row * self._grid_size + col

    def draw_overlays(self):
        self._draw_grid()
        if self._game is None:
            return
        board = self._game.board
        for position in range(board.tile_count):
            if board.is_tile_correct(position):
                self._draw_tick(position)
        if self._game.selected is not None:
            x0, y0, x1, y1 = self.cell_box(self._game.selected)
            self.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2,
                                  outline=self.SELECT_COLOUR, width=4)
        if self._game.hint_position is not None:
            self._draw_hint_circle(self._game.hint_position)
        if self._game.solved_by_player or self._game.auto_solved:
            self.create_rectangle(2, 2, self._side - 2, self._side - 2,
                                  outline=self.DONE_COLOUR, width=4)

    def _draw_grid(self):
        """Faint dashed lines on tile boundaries."""
        t = self.tile_size
        for i in range(1, self._grid_size):
            self.create_line(i * t, 0, i * t, self._side,
                             fill=self.GRID_COLOUR, dash=(3, 3))
            self.create_line(0, i * t, self._side, i * t,
                             fill=self.GRID_COLOUR, dash=(3, 3))

    def _draw_tick(self, position):
        """Small green tick in the top-right corner of a finished tile."""
        x0, y0, x1, _ = self.cell_box(position)
        r = max(7, self.tile_size // 9)
        cx, cy = x1 - r - 4, y0 + r + 4
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill="white",
                         outline=self.TICK_COLOUR, width=2)
        self.create_line(cx - r * 0.5, cy, cx - r * 0.1, cy + r * 0.45,
                         cx + r * 0.55, cy - r * 0.45,
                         fill=self.TICK_COLOUR, width=max(2, r // 3),
                         capstyle="round", joinstyle="round")


# ---------------------------------------------------------------------- #
# Main window
# ---------------------------------------------------------------------- #
class PuzzleApp:
    """Main application window: builds the layout and connects the classes."""

    TITLE = "Picture Restore Puzzle - HIT137"
    GRID_SIZES = (3, 4, 5)
    TIMER_INTERVAL_MS = 500

    def __init__(self, root=None):
        self._root = root or tk.Tk()
        self._root.title(self.TITLE)
        self._root.minsize(760, 560)

        self._processor = ImageProcessor(self._board_size_for_screen())
        self._factory = TransformationFactory()
        self._source_image = None
        self._source_name = ""
        self._prepared_image = None
        self._game = None
        self._timer_job = None

        self._grid_var = tk.IntVar(value=3)
        self._difficulty_var = tk.StringVar(value="Normal")
        self._fit_var = tk.StringVar(value=ImageProcessor.FIT_CROP)

        self._build_controls()
        self._build_canvases()
        self._build_status_bar()
        self._bind_mouse()
        self._update_status()

    # -------------------------- layout -------------------------------- #
    def _board_size_for_screen(self):
        """Pick a board size so both images fit side by side on screen."""
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        return max(240, min(520, (screen_w - 120) // 2, screen_h - 280))

    def _build_controls(self):
        bar = ttk.Frame(self._root, padding=(10, 8))
        bar.pack(side="top", fill="x")

        ttk.Button(bar, text="Load Image...", command=self.load_image).pack(side="left")

        grid_box = ttk.LabelFrame(bar, text="Grid", padding=(6, 0))
        grid_box.pack(side="left", padx=(12, 0))
        for n in self.GRID_SIZES:
            ttk.Radiobutton(grid_box, text=f"{n} x {n}", value=n,
                            variable=self._grid_var).pack(side="left", padx=2)

        ttk.Label(bar, text="Difficulty:").pack(side="left", padx=(12, 2))
        ttk.Combobox(bar, textvariable=self._difficulty_var, state="readonly",
                     width=8, values=list(DIFFICULTIES)).pack(side="left")

        ttk.Label(bar, text="Fit:").pack(side="left", padx=(12, 2))
        ttk.Combobox(bar, textvariable=self._fit_var, state="readonly", width=6,
                     values=[ImageProcessor.FIT_CROP, ImageProcessor.FIT_PAD]
                     ).pack(side="left")

        self._solve_btn = ttk.Button(bar, text="Solve", command=self.solve,
                                     state="disabled")
        self._solve_btn.pack(side="right")
        self._hint_btn = ttk.Button(bar, text="Hint", command=self.show_hint,
                                    state="disabled")
        self._hint_btn.pack(side="right", padx=4)
        self._new_btn = ttk.Button(bar, text="New Shuffle", command=self.new_shuffle,
                                   state="disabled")
        self._new_btn.pack(side="right", padx=4)

    def _build_canvases(self):
        area = ttk.Frame(self._root, padding=(10, 0))
        area.pack(side="top", fill="both", expand=True)
        size = self._processor.board_side(3)

        left = ttk.Frame(area)
        left.pack(side="left", expand=True, padx=8)
        ttk.Label(left, text="Original (reference)").pack()
        self._original_canvas = OriginalCanvas(left, size)
        self._original_canvas.pack()

        right = ttk.Frame(area)
        right.pack(side="left", expand=True, padx=8)
        ttk.Label(right, text="Puzzle (click to play)").pack()
        self._board_canvas = BoardCanvas(right, size)
        self._board_canvas.pack()

    def _build_status_bar(self):
        status = ttk.Frame(self._root, padding=(10, 8))
        status.pack(side="bottom", fill="x")
        self._status_vars = {key: tk.StringVar() for key in
                             ("moves", "left", "hints", "time", "score", "message")}
        for key in ("moves", "left", "hints", "time", "score"):
            ttk.Label(status, textvariable=self._status_vars[key],
                      font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 18))
        ttk.Label(status, textvariable=self._status_vars["message"],
                  foreground="#555555").pack(side="right")

        help_text = ("Left-click: select / swap    Right-click: rotate 90\u00b0    "
                     "Shift + Left-click: flip")
        ttk.Label(self._root, text=help_text, foreground="#555555",
                  padding=(10, 0)).pack(side="bottom", anchor="w")

    def _bind_mouse(self):
        canvas = self._board_canvas
        canvas.bind("<Button-1>", self._on_left_click)
        canvas.bind("<Shift-Button-1>", self._on_shift_click)
        if sys.platform == "darwin":          # macOS reports right-click as Button-2
            canvas.bind("<Button-2>", self._on_right_click)
            canvas.bind("<Control-Button-1>", self._on_right_click)
        else:
            canvas.bind("<Button-3>", self._on_right_click)

    # -------------------------- actions ------------------------------- #
    def load_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"),
                       ("JPEG", "*.jpg *.jpeg"), ("PNG", "*.png"),
                       ("Bitmap", "*.bmp"), ("All files", "*.*")])
        if not path:            # dialog cancelled
            return
        try:
            image = self._processor.load(path)
        except ImageLoadError as error:
            messagebox.showerror("Cannot load image", str(error))
            return
        self._source_image = image
        self._source_name = os.path.basename(path)
        self._start_round()

    def new_shuffle(self):
        """Re-scramble the current image using the current settings."""
        if self._source_image is not None:
            self._start_round()

    def _start_round(self):
        """Build a fresh board from the loaded image. Fully resets the round."""
        try:
            grid_size = self._grid_var.get()
            difficulty = DIFFICULTIES[self._difficulty_var.get()]
            prepared = self._processor.prepare(self._source_image, grid_size,
                                               self._fit_var.get())
            tiles = [Tile(i, img) for i, img in
                     enumerate(ImageProcessor.split(prepared, grid_size))]
            board = PuzzleBoard(tiles, grid_size)
            scramble = self._factory.create_scramble(
                grid_size, difficulty.transformation_count(grid_size))
            game = PuzzleGame(board, scramble, difficulty)
        except Exception as error:  # keep the app alive on unexpected input
            messagebox.showerror("Something went wrong",
                                 f"The image could not be prepared:\n{error}")
            return

        self._prepared_image = prepared
        self._game = game
        self._board_canvas.attach_game(game)
        self._original_canvas.show(prepared, grid_size)
        self._original_canvas.set_hint(None)
        self._status_vars["message"].set(
            f"{self._source_name}  |  {grid_size}x{grid_size}, {difficulty.label}: "
            f"{difficulty.describe(grid_size)}")
        self._new_btn.config(state="normal")
        self._refresh()
        self._restart_timer()

    def _on_left_click(self, event):
        self._handle_click(event, PuzzleGame.click_select)

    def _on_right_click(self, event):
        self._handle_click(event, PuzzleGame.click_rotate)

    def _on_shift_click(self, event):
        self._handle_click(event, PuzzleGame.click_flip)
        return "break"     # stop the plain left-click binding as well

    def _handle_click(self, event, action):
        if self._game is None or self._game.finished:
            return          # input locked
        position = self._board_canvas.position_at(event.x, event.y)
        if position is None:
            return          # clicks outside the image are ignored
        action(self._game, position)
        self._refresh()
        if self._game.solved_by_player:
            self._announce_win()

    def show_hint(self):
        if self._game is None or self._game.request_hint() is None:
            return
        self._refresh()

    def solve(self):
        if self._game is None:
            return
        self._game.solve()
        self._refresh()
        self._status_vars["message"].set("Puzzle solved automatically. "
                                         "Load another image to play again.")

    def _announce_win(self):
        game = self._game
        messagebox.showinfo(
            "Picture restored!",
            f"Well done - every tile is back in place.\n\n"
            f"Moves: {game.moves}\nHints used: {PuzzleGame.MAX_HINTS - game.hints_left}\n"
            f"Time: {self._format_time(game.elapsed_seconds())}\n"
            f"Score: {game.score}\n\nLoad another image to keep playing.")

    # -------------------------- display ------------------------------- #
    def _refresh(self):
        """Re-render the puzzle image and all overlays after any change."""
        game = self._game
        if game is not None:
            tile_images = [tile.render() for tile in game.board.tiles()]
            assembled = ImageProcessor.assemble(tile_images, game.board.grid_size)
            self._board_canvas.show(assembled, game.board.grid_size)
            self._original_canvas.set_hint(game.hint_home)
        self._update_status()

    def _update_status(self):
        game = self._game
        v = self._status_vars
        if game is None:
            v["moves"].set("Moves: 0")
            v["left"].set("Tiles left: -")
            v["hints"].set(f"Hints left: {PuzzleGame.MAX_HINTS}")
            v["time"].set("Time: 0:00")
            v["score"].set("Score: -")
            v["message"].set("Load an image to start.")
            return

        v["moves"].set(f"Moves: {game.moves}")
        v["left"].set(f"Tiles left: {game.tiles_left()}")
        v["hints"].set(f"Hints left: {game.hints_left}")
        remaining = game.time_remaining()
        if remaining is not None and not game.finished:
            v["time"].set(f"Time left: {self._format_time(remaining)}")
        else:
            v["time"].set(f"Time: {self._format_time(game.elapsed_seconds())}")
        v["score"].set(f"Score: {game.score}" if game.score is not None else "Score: -")

        playing = not game.finished
        self._hint_btn.config(state="normal" if playing and game.hints_left > 0
                              else "disabled")
        self._solve_btn.config(state="normal" if not game.auto_solved
                               and not game.solved_by_player else "disabled")

    @staticmethod
    def _format_time(seconds):
        return f"{seconds // 60}:{seconds % 60:02d}"

    # --------------------------- timer -------------------------------- #
    def _restart_timer(self):
        if self._timer_job is not None:
            self._root.after_cancel(self._timer_job)
        self._tick()

    def _tick(self):
        game = self._game
        if game is not None and not game.finished:
            if game.time_remaining() == 0:
                game.time_up()
                self._refresh()
                self._status_vars["message"].set("Time's up!")
                messagebox.showwarning(
                    "Time's up!", "You ran out of time.\n\nPress Solve to see the "
                    "answer, or load another image to try again.")
            else:
                self._update_status()
        self._timer_job = self._root.after(self.TIMER_INTERVAL_MS, self._tick)

    def run(self):
        self._root.mainloop()
