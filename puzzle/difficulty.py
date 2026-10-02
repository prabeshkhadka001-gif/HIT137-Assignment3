"""Difficulty levels (extra feature).

Each level is its own subclass and overrides the same two methods, so the
game can ask any difficulty object "how many transformations?" and "is there
a time limit?" without checking which level it is (polymorphism).
"""


class Difficulty:
    """Base difficulty: the assignment's standard settings."""

    label = "Normal"

    def transformation_count(self, grid_size):
        """6 for 3x3, 12 for 4x4, 20 for 5x5 (n * (n - 1))."""
        return grid_size * (grid_size - 1)

    def time_limit(self, grid_size):
        """Seconds allowed to finish, or None for no limit."""
        return None

    def describe(self, grid_size):
        limit = self.time_limit(grid_size)
        text = f"{self.transformation_count(grid_size)} transformations"
        return text + (f", {limit} s limit" if limit else ", no time limit")


class EasyDifficulty(Difficulty):
    """Half the usual number of transformations, no time limit."""

    label = "Easy"

    def transformation_count(self, grid_size):
        return max(3, super().transformation_count(grid_size) // 2)


class NormalDifficulty(Difficulty):
    """Exactly the assignment's standard settings."""

    label = "Normal"


class HardDifficulty(Difficulty):
    """Standard transformations, but the puzzle must be finished in time."""

    label = "Hard"
    SECONDS_PER_TILE = 8

    def time_limit(self, grid_size):
        return grid_size * grid_size * self.SECONDS_PER_TILE


DIFFICULTIES = {level.label: level for level in
                (EasyDifficulty(), NormalDifficulty(), HardDifficulty())}
