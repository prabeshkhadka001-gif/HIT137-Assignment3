"""Game rules for one round (one loaded image). Contains no GUI code."""

import random
import time

from .transformations import (FlipTransformation, RotateTransformation,
                              SwapTransformation)


class PuzzleGame:
    """Tracks moves, selection, hints, timing and completion for one round."""

    MAX_HINTS = 3

    def __init__(self, board, scramble, difficulty, rng=None):
        self._board = board
        self._scramble = list(scramble)
        self._difficulty = difficulty
        self._rng = rng or random.Random()

        self._history = []          # player's moves, for Solve to undo
        self._moves = 0
        self._hints_used = 0
        self._hint_position = None
        self._selected = None
        self._finished = False
        self._solved_by_player = False
        self._auto_solved = False
        self._timed_out = False
        self._score = None

        # All transformations are generated first, then applied together.
        for transformation in self._scramble:
            transformation.apply(self._board)

        self._start_time = time.monotonic()
        self._end_time = None

    # ------------------------------------------------------------------ #
    # Read-only state for the GUI
    # ------------------------------------------------------------------ #
    @property
    def board(self):
        return self._board

    @property
    def moves(self):
        return self._moves

    @property
    def selected(self):
        return self._selected

    @property
    def hint_position(self):
        return self._hint_position

    @property
    def hint_home(self):
        """Where the hinted tile belongs (shown on the original image)."""
        if self._hint_position is None:
            return None
        return self._board.tile_at(self._hint_position).home_index

    @property
    def hints_left(self):
        return self.MAX_HINTS - self._hints_used

    @property
    def finished(self):
        return self._finished

    @property
    def solved_by_player(self):
        return self._solved_by_player

    @property
    def auto_solved(self):
        return self._auto_solved

    @property
    def timed_out(self):
        return self._timed_out

    @property
    def score(self):
        return self._score

    @property
    def scramble_size(self):
        return len(self._scramble)

    def tiles_left(self):
        return len(self._board.incorrect_positions())

    def elapsed_seconds(self):
        end = self._end_time if self._end_time is not None else time.monotonic()
        return int(end - self._start_time)

    def time_remaining(self):
        """Seconds left on a timed difficulty, otherwise None."""
        limit = self._difficulty.time_limit(self._board.grid_size)
        if limit is None:
            return None
        return max(0, limit - self.elapsed_seconds())

    # ------------------------------------------------------------------ #
    # Player actions
    # ------------------------------------------------------------------ #
    def click_select(self, position):
        """Left click: select, deselect, or swap with the selected tile."""
        if self._finished:
            return
        if self._selected is None:
            self._selected = position
        elif self._selected == position:
            self._selected = None
        else:
            first = self._selected
            self._selected = None
            self._perform(SwapTransformation(first, position))

    def click_rotate(self, position):
        """Right click: rotate the tile 90 degrees clockwise."""
        if not self._finished:
            self._perform(RotateTransformation(position, 1))

    def click_flip(self, position):
        """Shift + left click: flip the tile horizontally."""
        if not self._finished:
            self._perform(FlipTransformation(position, FlipTransformation.HORIZONTAL))

    def _perform(self, transformation):
        transformation.apply(self._board)
        self._history.append(transformation)
        self._moves += 1
        self._hint_position = None   # hint disappears after the next move
        if self._board.is_solved():
            self._finish_by_player()

    def _finish_by_player(self):
        self._finished = True
        self._solved_by_player = True
        self._selected = None
        self._end_time = time.monotonic()
        self._score = self._calculate_score()

    def _calculate_score(self):
        """1000 points, minus 10 per move beyond the scramble size,
        50 per hint and 1 per second. Never below zero."""
        extra_moves = max(0, self._moves - len(self._scramble))
        penalty = extra_moves * 10 + self._hints_used * 50 + self.elapsed_seconds()
        return max(0, 1000 - penalty)

    # ------------------------------------------------------------------ #
    # Hint, Solve and time limit
    # ------------------------------------------------------------------ #
    def request_hint(self):
        """Mark one random incorrect tile. Returns its position, or None."""
        if self._finished or self._hints_used >= self.MAX_HINTS:
            return None
        wrong = self._board.incorrect_positions()
        if not wrong:
            return None
        self._hints_used += 1
        self._hint_position = self._rng.choice(wrong)
        return self._hint_position

    def solve(self):
        """Undo the player's moves, then the scramble, both in reverse order."""
        for transformation in reversed(self._history):
            transformation.undo(self._board)
        for transformation in reversed(self._scramble):
            transformation.undo(self._board)
        if not self._board.is_solved():   # safety net, should never trigger
            self._board.reset()

        self._history.clear()
        self._moves = 0
        self._score = None
        self._selected = None
        self._hint_position = None
        self._finished = True
        self._auto_solved = True
        if self._end_time is None:
            self._end_time = time.monotonic()

    def time_up(self):
        """Called by the GUI when a timed round runs out."""
        if self._finished:
            return
        self._finished = True
        self._timed_out = True
        self._selected = None
        self._hint_position = None
        self._end_time = time.monotonic()
