"""Transformations that can be applied to a puzzle board.

The same classes are used for two jobs:
  * scrambling the picture when an image is loaded, and
  * recording the player's moves (swap / rotate / flip).

Every transformation knows how to apply() itself and how to undo() itself.
The Solve button relies on this: it simply undoes the player's moves and then
the scramble, in reverse order, without needing to know which kind of
transformation each one is (polymorphism).
"""

import random
from abc import ABC, abstractmethod


class Transformation(ABC):
    """Abstract base class for every board transformation."""

    name = "transformation"

    def __init__(self, *positions):
        self._positions = tuple(positions)

    @property
    def positions(self):
        """Board positions this transformation touches."""
        return self._positions

    @abstractmethod
    def apply(self, board):
        """Perform the transformation on the board."""

    @abstractmethod
    def undo(self, board):
        """Reverse the transformation on the board."""

    @abstractmethod
    def describe(self):
        """Short human-readable description."""

    def __str__(self):
        return self.describe()


class SwapTransformation(Transformation):
    """Two tiles exchange positions."""

    name = "swap"

    def __init__(self, position_a, position_b):
        if position_a == position_b:
            raise ValueError("A swap needs two different positions.")
        super().__init__(position_a, position_b)

    def apply(self, board):
        board.swap_positions(*self._positions)

    def undo(self, board):
        # Swapping the same two positions again restores them.
        self.apply(board)

    def describe(self):
        a, b = self._positions
        return f"Swap tiles at positions {a} and {b}"


class RotateTransformation(Transformation):
    """A tile is rotated clockwise by 90, 180 or 270 degrees."""

    name = "rotate"

    def __init__(self, position, quarter_turns=1):
        if quarter_turns not in (1, 2, 3):
            raise ValueError("quarter_turns must be 1, 2 or 3.")
        super().__init__(position)
        self._quarter_turns = quarter_turns

    @property
    def degrees(self):
        return self._quarter_turns * 90

    def apply(self, board):
        board.tile_at(self._positions[0]).rotate_cw(self._quarter_turns)

    def undo(self, board):
        board.tile_at(self._positions[0]).rotate_cw(4 - self._quarter_turns)

    def describe(self):
        return f"Rotate tile at position {self._positions[0]} by {self.degrees} degrees"


class FlipTransformation(Transformation):
    """A tile is flipped horizontally or vertically."""

    name = "flip"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"

    def __init__(self, position, axis=HORIZONTAL):
        if axis not in (self.HORIZONTAL, self.VERTICAL):
            raise ValueError("axis must be 'horizontal' or 'vertical'.")
        super().__init__(position)
        self._axis = axis

    @property
    def axis(self):
        return self._axis

    def apply(self, board):
        tile = board.tile_at(self._positions[0])
        if self._axis == self.HORIZONTAL:
            tile.flip_horizontal()
        else:
            tile.flip_vertical()

    def undo(self, board):
        # Flipping twice along the same axis restores the tile.
        self.apply(board)

    def describe(self):
        return f"Flip tile at position {self._positions[0]} {self._axis}ly"


class TransformationFactory:
    """Creates a random scramble for a board."""

    def __init__(self, rng=None):
        self._rng = rng or random.Random()

    def create_scramble(self, grid_size, count):
        """Return a list of random transformations.

        Rules:
          * all three types (swap, rotate, flip) appear at least once;
          * no tile is targeted twice, so every targeted tile really ends up
            wrong and the scramble can never cancel itself out;
          * the order is shuffled.

        A swap touches two tiles and rotate/flip touch one, so the number of
        swaps is limited to (tiles - count) to fit on the board.
        """
        total_tiles = grid_size * grid_size
        count = max(3, min(count, total_tiles - 1))

        max_swaps = min(total_tiles - count, count - 2)
        num_swaps = self._rng.randint(1, max_swaps)
        remaining = count - num_swaps
        num_rotates = self._rng.randint(1, remaining - 1)
        num_flips = remaining - num_rotates

        targets = self._rng.sample(range(total_tiles), num_swaps * 2 + remaining)
        transformations = []

        for _ in range(num_swaps):
            transformations.append(SwapTransformation(targets.pop(), targets.pop()))
        for _ in range(num_rotates):
            transformations.append(
                RotateTransformation(targets.pop(), self._rng.choice((1, 2, 3))))
        for _ in range(num_flips):
            axis = self._rng.choice((FlipTransformation.HORIZONTAL,
                                     FlipTransformation.VERTICAL))
            transformations.append(FlipTransformation(targets.pop(), axis))

        self._rng.shuffle(transformations)
        return transformations
