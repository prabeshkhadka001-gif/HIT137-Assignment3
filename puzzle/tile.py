"""Tile: a single square piece of the puzzle image."""

import cv2


class Tile:
    """One puzzle piece.

    A tile stores its untouched source pixels, the board position it belongs
    to (its "home"), and its current orientation. The image shown on screen
    is always rebuilt from the source pixels, so rotating or flipping a tile
    many times never degrades its quality.

    Orientation model
    -----------------
    The orientation is two private values:
        _rotation : number of 90 degree clockwise turns (0-3)
        _flipped  : whether a horizontal flip is applied first

    so the displayed image is   rotate_cw^r( flip_h^f( source ) ).

    These eight combinations cover every rotation and flip a square can have,
    and the update rules below keep the state exact (no image comparison is
    needed to know whether a tile is upright).
    """

    def __init__(self, home_index, image):
        self._home_index = home_index
        self._source = image.copy()
        self._rotation = 0
        self._flipped = False

    # ------------------------------------------------------------------ #
    # Read-only properties (encapsulation: state changes only via methods)
    # ------------------------------------------------------------------ #
    @property
    def home_index(self):
        """Board position where this tile belongs."""
        return self._home_index

    @property
    def rotation(self):
        """Clockwise quarter turns currently applied (0-3)."""
        return self._rotation

    @property
    def flipped(self):
        """True if a horizontal flip is part of the current orientation."""
        return self._flipped

    # ------------------------------------------------------------------ #
    # Orientation changes
    # ------------------------------------------------------------------ #
    def rotate_cw(self, quarter_turns=1):
        """Rotate the tile clockwise by 90 degrees * quarter_turns."""
        self._rotation = (self._rotation + quarter_turns) % 4

    def flip_horizontal(self):
        """Mirror the tile left-to-right.

        Flipping after a rotation r is the same as rotating by -r after a
        flip, so the rotation count is negated and the flip flag toggled.
        """
        self._rotation = (-self._rotation) % 4
        self._flipped = not self._flipped

    def flip_vertical(self):
        """Mirror the tile top-to-bottom.

        A vertical flip equals a horizontal flip followed by a 180 degree
        turn, which gives the rule below.
        """
        self._rotation = (2 - self._rotation) % 4
        self._flipped = not self._flipped

    def reset_orientation(self):
        """Return the tile to its original upright orientation."""
        self._rotation = 0
        self._flipped = False

    def is_upright(self):
        """True when the tile shows its original orientation."""
        return self._rotation == 0 and not self._flipped

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def render(self):
        """Return the tile pixels (BGR numpy array) in their current orientation."""
        image = self._source
        if self._flipped:
            image = cv2.flip(image, 1)
        for _ in range(self._rotation):
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        return image

    def __repr__(self):
        return (f"Tile(home={self._home_index}, rotation={self._rotation * 90}, "
                f"flipped={self._flipped})")
