import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garden_of_inheritance.field_textures import load_field_textures, season_for_month

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTURES_DIR = os.path.join(REPO, "icons", "textures")


class TestSeasonForMonth(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(season_for_month(4), "spring")
        self.assertEqual(season_for_month(7), "summer")
        self.assertEqual(season_for_month(10), "autumn")
        self.assertEqual(season_for_month(12), "winter")
        self.assertEqual(season_for_month(1), "winter")

    def test_invalid_month_defaults_to_spring(self):
        self.assertEqual(season_for_month(0), "spring")
        self.assertEqual(season_for_month("x"), "spring")


class TestLoadFieldTextures(unittest.TestCase):
    def test_loads_real_textures(self):
        result = load_field_textures(85, TEXTURES_DIR)
        self.assertIsNotNone(result)
        pil_imgs, n_grass, n_soil = result
        # 9 grass + 2 soil variants per season exist for spring
        self.assertEqual(n_grass, 9)
        self.assertEqual(n_soil, 2)
        self.assertIn(("grass", "spring", 0, 100), pil_imgs)
        self.assertIn(("grass", "spring", 8, 100), pil_imgs)
        self.assertIn(("soil", "autumn", 1, 100), pil_imgs)
        self.assertIn(("grass", "winter", 0, 100), pil_imgs)
        # every image is tile-sized
        for img in pil_imgs.values():
            self.assertEqual(img.size, (85, 85))
        # *_old.png files must be ignored (soil_winter1_old.png exists on disk)
        for key in pil_imgs:
            self.assertEqual(len(key), 4)

    def test_resizes_to_requested_tile_size(self):
        pil_imgs, _, _ = load_field_textures(64, TEXTURES_DIR)
        self.assertEqual(pil_imgs[("grass", "spring", 0, 100)].size, (64, 64))

    def test_missing_dir_returns_none(self):
        self.assertIsNone(load_field_textures(85, "/nonexistent/path/xyz"))

    def test_empty_dir_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(load_field_textures(85, d))


if __name__ == "__main__":
    unittest.main()
