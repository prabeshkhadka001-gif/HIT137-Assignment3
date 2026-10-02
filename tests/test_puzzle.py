"""Unit tests for the game logic. Run with:  python -m unittest discover tests"""

import os
import random
import tempfile
import unittest

import cv2
import numpy as np

from puzzle.board import PuzzleBoard
from puzzle.difficulty import DIFFICULTIES
from puzzle.game import PuzzleGame
from puzzle.image_processor import ImageLoadError, ImageProcessor
from puzzle.tile import Tile
from puzzle.transformations import (FlipTransformation, RotateTransformation,
                                    SwapTransformation, TransformationFactory)


def random_image(height, width, seed=0):
    return np.random.default_rng(seed).integers(0, 255, (height, width, 3), dtype=np.uint8)


def make_game(grid_size, difficulty="Normal", seed=1):
    processor = ImageProcessor(450)
    prepared = processor.prepare(random_image(300, 400), grid_size)
    tiles = [Tile(i, img) for i, img in enumerate(processor.split(prepared, grid_size))]
    board = PuzzleBoard(tiles, grid_size)
    level = DIFFICULTIES[difficulty]
    scramble = TransformationFactory(random.Random(seed)).create_scramble(
        grid_size, level.transformation_count(grid_size))
    return PuzzleGame(board, scramble, level, random.Random(seed)), prepared


class TileTests(unittest.TestCase):
    def setUp(self):
        self.source = random_image(40, 40)
        self.tile = Tile(0, self.source)

    def test_horizontal_flip_matches_opencv(self):
        self.tile.rotate_cw(1)
        expected = cv2.flip(self.tile.render(), 1)
        self.tile.flip_horizontal()
        np.testing.assert_array_equal(self.tile.render(), expected)

    def test_vertical_flip_matches_opencv(self):
        self.tile.rotate_cw(3)
        expected = cv2.flip(self.tile.render(), 0)
        self.tile.flip_vertical()
        np.testing.assert_array_equal(self.tile.render(), expected)

    def test_four_rotations_return_upright(self):
        for _ in range(4):
            self.tile.rotate_cw()
        self.assertTrue(self.tile.is_upright())
        np.testing.assert_array_equal(self.tile.render(), self.source)

    def test_upright_flag_matches_pixels_for_random_moves(self):
        rng = random.Random(3)
        for _ in range(300):
            rng.choice((self.tile.rotate_cw, self.tile.flip_horizontal,
                        self.tile.flip_vertical))()
            pixels_match = np.array_equal(self.tile.render(), self.source)
            self.assertEqual(self.tile.is_upright(), pixels_match)


class ScrambleTests(unittest.TestCase):
    def test_counts_types_and_no_tile_targeted_twice(self):
        for n in (3, 4, 5):
            for level in DIFFICULTIES.values():
                for seed in range(40):
                    count = level.transformation_count(n)
                    scramble = TransformationFactory(random.Random(seed)).create_scramble(n, count)
                    self.assertEqual(len(scramble), count)
                    names = {t.name for t in scramble}
                    self.assertEqual(names, {"swap", "rotate", "flip"})
                    targets = [p for t in scramble for p in t.positions]
                    self.assertEqual(len(targets), len(set(targets)))

    def test_standard_counts(self):
        normal = DIFFICULTIES["Normal"]
        self.assertEqual([normal.transformation_count(n) for n in (3, 4, 5)], [6, 12, 20])

    def test_every_targeted_tile_is_wrong(self):
        for n in (3, 4, 5):
            game, _ = make_game(n)
            targeted = {p for t in game._scramble for p in t.positions}
            self.assertEqual(set(game.board.incorrect_positions()), targeted)


class GameTests(unittest.TestCase):
    def test_solve_restores_after_random_player_moves(self):
        for n in (3, 4, 5):
            game, prepared = make_game(n, seed=n)
            rng = random.Random(9)
            for _ in range(50):
                pos = rng.randrange(n * n)
                rng.choice((game.click_rotate, game.click_flip, game.click_select))(pos)
                if game.finished:
                    break
            game.solve()
            self.assertTrue(game.board.is_solved())
            self.assertEqual(game.moves, 0)
            self.assertIsNone(game.score)
            image = ImageProcessor.assemble([t.render() for t in game.board.tiles()], n)
            np.testing.assert_array_equal(image, prepared)

    def test_select_deselect_and_swap(self):
        game, _ = make_game(3)
        game.click_select(0)
        self.assertEqual(game.selected, 0)
        game.click_select(0)
        self.assertIsNone(game.selected)
        self.assertEqual(game.moves, 0)
        first, second = game.board.tile_at(0), game.board.tile_at(1)
        game.click_select(0)
        game.click_select(1)
        self.assertIs(game.board.tile_at(0), second)
        self.assertIs(game.board.tile_at(1), first)
        self.assertEqual(game.moves, 1)
        self.assertIsNone(game.selected)

    def test_player_can_win_and_input_locks(self):
        game, _ = make_game(3, seed=4)
        # Undo the scramble using real player moves only.
        for t in reversed(game._scramble):
            if isinstance(t, SwapTransformation):
                game.click_select(t.positions[0])
                game.click_select(t.positions[1])
            elif isinstance(t, RotateTransformation):
                for _ in range(4 - t.degrees // 90):
                    game.click_rotate(t.positions[0])
            elif isinstance(t, FlipTransformation):
                if t.axis == FlipTransformation.HORIZONTAL:
                    game.click_flip(t.positions[0])
                else:   # vertical flip = horizontal flip + 180 degrees
                    game.click_flip(t.positions[0])
                    game.click_rotate(t.positions[0])
                    game.click_rotate(t.positions[0])
        self.assertTrue(game.board.is_solved())
        self.assertTrue(game.solved_by_player)
        self.assertIsNotNone(game.score)
        moves = game.moves
        game.click_rotate(0)
        self.assertEqual(game.moves, moves)       # locked

    def test_hint_limit_and_clearing(self):
        game, _ = make_game(4)
        for _ in range(3):
            pos = game.request_hint()
            self.assertIn(pos, game.board.incorrect_positions())
            self.assertEqual(game.hint_home, game.board.tile_at(pos).home_index)
        self.assertEqual(game.hints_left, 0)
        self.assertIsNone(game.request_hint())
        game.click_rotate(0)
        self.assertIsNone(game.hint_position)

    def test_time_up_locks_input(self):
        game, _ = make_game(3, "Hard")
        self.assertEqual(game.time_remaining(), 72)
        game.time_up()
        game.click_rotate(0)
        self.assertEqual(game.moves, 0)


class ImageProcessorTests(unittest.TestCase):
    def test_prepare_sizes_divide_evenly(self):
        processor = ImageProcessor(500)
        for shape in ((300, 800), (900, 200), (37, 41), (1000, 1000)):
            for mode in (ImageProcessor.FIT_CROP, ImageProcessor.FIT_PAD):
                for n in (3, 4, 5):
                    out = processor.prepare(random_image(*shape), n, mode)
                    self.assertEqual(out.shape[0], out.shape[1])
                    self.assertEqual(out.shape[0] % n, 0)
                    self.assertLessEqual(out.shape[0], 500)

    def test_bad_files_raise_clean_error(self):
        processor = ImageProcessor()
        with tempfile.TemporaryDirectory() as folder:
            fake = os.path.join(folder, "notes.txt")
            broken = os.path.join(folder, "broken.png")
            for path in (fake, broken):
                with open(path, "w") as handle:
                    handle.write("not an image")
            for path in (fake, broken, os.path.join(folder, "missing.jpg")):
                with self.assertRaises(ImageLoadError):
                    processor.load(path)

    def test_loads_all_three_formats(self):
        processor = ImageProcessor()
        image = random_image(30, 50)
        with tempfile.TemporaryDirectory() as folder:
            for ext in (".jpg", ".png", ".bmp"):
                path = os.path.join(folder, "pic" + ext)
                cv2.imwrite(path, image)
                self.assertEqual(processor.load(path).shape, (30, 50, 3))


if __name__ == "__main__":
    unittest.main()
