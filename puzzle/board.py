"""The puzzle board: which tile sits in which position."""


class PuzzleBoard:
    """Holds the tiles in their current positions (row by row)."""

    def __init__(self, tiles, grid_size):
        if len(tiles) != grid_size * grid_size:
            raise ValueError("Number of tiles does not match the grid size.")
        self._grid_size = grid_size
        self._slots = list(tiles)

    @property
    def grid_size(self):
        return self._grid_size

    @property
    def tile_count(self):
        return len(self._slots)

    def tile_at(self, position):
        return self._slots[position]

    def tiles(self):
        """Tiles in display order (a copy, so callers cannot rearrange the board)."""
        return list(self._slots)

    def swap_positions(self, position_a, position_b):
        self._slots[position_a], self._slots[position_b] = (
            self._slots[position_b], self._slots[position_a])

    def is_tile_correct(self, position):
        """True when the tile at this position is home and upright."""
        tile = self._slots[position]
        return tile.home_index == position and tile.is_upright()

    def incorrect_positions(self):
        return [p for p in range(len(self._slots)) if not self.is_tile_correct(p)]

    def is_solved(self):
        return not self.incorrect_positions()

    def reset(self):
        """Put every tile home and upright (used as a safety net by Solve)."""
        self._slots.sort(key=lambda tile: tile.home_index)
        for tile in self._slots:
            tile.reset_orientation()
