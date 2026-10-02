"""Image loading, resizing, tiling and reassembly with OpenCV."""

import os

import cv2
import numpy as np


class ImageLoadError(Exception):
    """Raised when a file cannot be read as a supported image."""


class ImageProcessor:
    """Handles every OpenCV operation the game needs."""

    SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
    FIT_CROP = "Crop"
    FIT_PAD = "Pad"
    PAD_COLOUR = (45, 45, 45)  # BGR

    def __init__(self, max_board_size=480):
        self._max_board_size = max_board_size

    @property
    def max_board_size(self):
        return self._max_board_size

    @max_board_size.setter
    def max_board_size(self, value):
        self._max_board_size = max(150, int(value))

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #
    def load(self, path):
        """Read an image file and return it as a BGR numpy array.

        np.fromfile + cv2.imdecode is used instead of cv2.imread so that
        paths containing non-English characters also work on Windows.
        """
        extension = os.path.splitext(path)[1].lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ImageLoadError(
                f"'{os.path.basename(path)}' is not a supported image.\n"
                "Please choose a JPG, PNG or BMP file.")
        try:
            data = np.fromfile(path, dtype=np.uint8)
        except OSError as error:
            raise ImageLoadError(f"Could not open the file:\n{error}") from error

        image = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
        if image is None:
            raise ImageLoadError(
                f"'{os.path.basename(path)}' could not be read as an image.\n"
                "The file may be damaged or not really an image.")
        return image

    # ------------------------------------------------------------------ #
    # Preparing the board image
    # ------------------------------------------------------------------ #
    def board_side(self, grid_size):
        """Largest square side that fits on screen and divides evenly into the grid."""
        return (self._max_board_size // grid_size) * grid_size

    def prepare(self, image, grid_size, fit_mode=FIT_CROP):
        """Resize the image (keeping its aspect ratio) to a square board.

        FIT_CROP scales the short side to the board and crops the centre.
        FIT_PAD  scales the long side to the board and pads the rest.
        Either way the result is side x side where side divides evenly by
        grid_size, so every tile is the same square size and can be rotated.
        """
        side = self.board_side(grid_size)
        height, width = image.shape[:2]

        if fit_mode == self.FIT_PAD:
            scale = side / max(height, width)
        else:
            scale = side / min(height, width)

        new_w = max(1, round(width * scale))
        new_h = max(1, round(height * scale))
        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)

        if fit_mode == self.FIT_PAD:
            top = (side - new_h) // 2
            left = (side - new_w) // 2
            result = cv2.copyMakeBorder(
                resized, top, side - new_h - top, left, side - new_w - left,
                cv2.BORDER_CONSTANT, value=self.PAD_COLOUR)
        else:
            top = (new_h - side) // 2
            left = (new_w - side) // 2
            result = resized[top:top + side, left:left + side]

        # Guard against rounding leaving the image one pixel off.
        if result.shape[0] != side or result.shape[1] != side:
            result = cv2.resize(result, (side, side), interpolation=cv2.INTER_AREA)
        return np.ascontiguousarray(result)

    # ------------------------------------------------------------------ #
    # Tiling
    # ------------------------------------------------------------------ #
    @staticmethod
    def split(image, grid_size):
        """Cut a square image into grid_size * grid_size tiles, row by row."""
        tile = image.shape[0] // grid_size
        return [image[r * tile:(r + 1) * tile, c * tile:(c + 1) * tile].copy()
                for r in range(grid_size) for c in range(grid_size)]

    @staticmethod
    def assemble(tile_images, grid_size):
        """Join a row-by-row list of tile images back into one image."""
        rows = [np.hstack(tile_images[r * grid_size:(r + 1) * grid_size])
                for r in range(grid_size)]
        return np.vstack(rows)

    @staticmethod
    def to_rgb(image):
        """Convert OpenCV's BGR order to RGB for display."""
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
