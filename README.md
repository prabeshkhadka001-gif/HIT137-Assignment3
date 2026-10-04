HIT137-Assignment3
HIT137 Assignment 3: Tkinter and OpenCV image puzzle game.

Group members

| Name | Student ID | GitHub |
|---|---|---|
| Parivesh Khadka Chhetri | s398438 | prabeshkhadka001-gif |
| Pawan Koirala | s408952| Purshottam285 |
| Noel karunathilake| s389821| noelmaskym |

This is the description of the assignment for HIT137.

A desktop puzzle game built with Tkinter and OpenCV in object-oriented Python. A picture is cut into a grid of tiles and scrambled with random swaps, rotations and flips. The player restores it by clicking the tiles: left-click to select and swap, right-click to rotate, and Shift + left-click to flip.


 How to run

```bash
pip install -r requirements.txt
python main.py
```

Python 3.8 or newer. Tkinter is included in the default Windows installer of Python.
Python3-tk (on Linux: install with apt)

Use the unit tests with:

```bash
python -m unittest discover tests -v
```

How to play

1. Choose a grid size (3 x 3, 4 x 4 or 5 x 5), a difficulty and a fit mode.
2. Click on Load Image... and select a JPG, PNG or BMP file.
3. The original is shown on the left for reference; the scrambled puzzle is on the right.

Action | Effect (also including puzzle image) |
|---|---|
Click on a tile | Mark the tile (orange border) |
Click on a second tile | Swap the two tiles |
Double click the selected tile | Deselect it |
Right click on a tile | Rotate 90° clockwise (macOS: Ctrl+click also works)
Shift + left click of a tile | Flip horizontally |

All the tiles will have a green tick on them if they are in the correct orientation and position.
The swaps, rotations and flips count as one move each.

board.One of the wrong tiles is highlighted in blue with Hint circle on the puzzle and in its proper position on the board.
  original. The circles are removed on the next move. 3 hints per image and then the button
  is disabled.
Untransforms - restores the picture and clears, undoing all transformations.
  moves and score.
New Shuffle re-scrambles the current image against the current settings.
Once the image has been restored, the player is informed, the puzzle is locked and another image is shown.
  can be loaded.

Project structure

```
main.py                    Entry point
puzzle/
    tile.py                Tile: one piece, its home position and orientation
    transformations.py     Transformation base class + Swap / Rotate / Flip, scramble factory
    board.py               PuzzleBoard: which tile is in which position
    difficulty.py          Difficulty base class + Easy / Normal / Hard
    game.py                PuzzleGame: moves, selection, hints, solve, timer, score
    image_processor.py     OpenCV loading, resizing, cropping/padding, tiling, reassembly
    gui.py                 Tkinter canvases and the main window
tests/test_puzzle.py       Unit tests for the logic and image processing
sample_images/             Test images in JPG, PNG and BMP
outputs/                   Screenshots of the running application
```

## How the requirements are met

### Object-oriented programming

| Concept | Where |
|---|---|
Encapsulation: The state of each component is kept by private attributes whose values can be read only from read-only properties, state changes only through methods. `ImageProcessor.max_board_size` has a validating setter.
Each class sets up its state in the initializer, which is called `__init__()`. The initializer of subclasses calls `super().__init__()`. |
These are examples of methods that can be used: Tile.rotate_cw(), PuzzleBoard.swap_positions(), PuzzleGame.request_hint(). |
All of the classes will communicate with each other in the following way: `PuzzleApp` will use the `ImageProcessor` to create the `Tile`s, load them into a `PuzzleBoard`, request a scramble from the `TransformationFactory` and pass the information to the `PuzzleGame`. The `BoardCanvas` will read the game state and draw its overlays. |
Inheritance: `SwapTransformation`, `RotateTransformation`, `FlipTransformation` are abstract classes of the class `Transformation`, as are `EasyDifficulty`, `NormalDifficulty` and `HardDifficulty` which are children of the class `Difficulty`, and `OriginalCanvas`, `BoardCanvas` are children of the class `ImageCanvas`, which are children of the class `tk.Canvas`, which are children of the class `Exception`. |
PuzzleGame.solve() called without checking the types of the elements in a mixed list.PuzzleGame.solve() called undo(), without checking the type of the elements in a mixed list. Each subclass of ImageCanvas overrides draw_overlays(), which is called by the player's movements when the player calls ImageCanvas.redraw(). The game inquires about `transformation_count()` and `time_limit()` from any `Difficulty` object.

### Image processing (OpenCV)

* Files are loaded using `np.fromfile` + `cv2.imdecode` (on non-English paths as well)
  Windows). Supported formats are .jpg file, .png file and .bmp file – any other file type will display a file error message box.
Resizes the image to fit the screen while preserving the aspect ratio, then centre crops the image.
  is divided into equal segments by the side of a square whose side is divisible by the measuring size or is divided into equal segments by a padded size that is a multiple of the measuring size.
  All tiles are square and can be easily rotated.
All the scramble is generated at once and applied. It is always possible to construct at least one swap,
  one rotation (90°/180°/270°) and one flip (horizontal or vertical), types selected
  At random on each load. Count goes up by the grid: 6 / 12 / 20 on Normal.
  No tile is targeted more than once so each targeted tile actually is wrong.
After each action, the tiles are reconnected to make a single picture using `np.hstack` /
  `np.vstack` and redisplayed.

### Orientation tracking

Each tile contains the information of rotation by a quarter turn clockwise and the horizontal flip. The
rotate and flip methods update these with precise rules, so the game is always aware if a number of them has been rotated and/or flipped.
tile is not tilted and looks at no pixels. A tile is in its home position when it is in correct position.
and upright. This state must always be equal to what the unit tests (which are based on actual pixels).

### Error handling

The file dialog will not respond if it is cancelled.
If you find non-image, unsupported, damaged or missing files, they display a message box: the app continues running.
Clicking outside the puzzle image, the original image, and after the puzzle.
  Completed istructures are not considered.
Any unexpected error that occurs when preparing an image is detected and displayed in a message box.

## Extra features
- Hard (slightly more complex), Extremely Hard (moderately more complex), and
  Hard (standard transformations + countdown 8 seconds per tile; when time is up)
  the puzzle locks).
On each round, shown is the Timer.
On completion: 1000-10 per move over the scramble size, 50 per hint and
  1 per second.
Fit modes (crop or pad)
To play the same picture again with a different scramble use the *New Shuffle* function.
* **Unit tests** that test orientation maths, scramble rules, hints, solve and image loading.

Known limitation

Tiles that are a single flat colour (for example the bars added in Pad mode) look the same
During all orientations, so they can be able to turn their heads to the right without a tick. The Hint button will indicate these.
Most of these can be avoided in Crop mode (the default).
