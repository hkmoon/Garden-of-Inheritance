import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garden_of_inheritance import theme

from PIL import Image  # noqa: E402


def _is_hex(s):
    return isinstance(s, str) and s.startswith("#") and len(s) in (7, 9)


class TestThemeStops(unittest.TestCase):
    def test_button_variants_are_triples_of_hex(self):
        for name in ("BTN_WOOD", "BTN_SUCCESS", "BTN_DANGER", "BTN_MUTED"):
            trip = getattr(theme, name)
            self.assertEqual(len(trip), 3, name)
            self.assertTrue(all(_is_hex(c) for c in trip), f"{name}={trip}")

    def test_chip_and_panel_stops_exist(self):
        self.assertTrue(_is_hex(theme.CHIP_BG))
        self.assertTrue(_is_hex(theme.CHIP_BORDER))
        self.assertEqual(len(theme.PANEL_GRAD), 2)
        self.assertEqual(len(theme.TILE_SOIL_GRAD), 2)
        self.assertEqual(len(theme.SHADOW_RGBA), 4)

    def test_icon_gradients_are_triples(self):
        self.assertEqual(len(theme.ICON_GOLD), 3)
        self.assertEqual(len(theme.ICON_SEED), 3)

    def test_hover_press_return_hex(self):
        self.assertTrue(_is_hex(theme.hover("#a66a39")))
        self.assertTrue(_is_hex(theme.press("#a66a39")))
        # hover lightens, press darkens relative to input luminance
        self.assertNotEqual(theme.hover("#a66a39"), theme.press("#a66a39"))


class TestRenderHelpers(unittest.TestCase):
    def setUp(self):
        from garden_of_inheritance import widgets
        self.w = widgets

    def test_rounded_grad_size_and_mode(self):
        img = self.w.rounded_grad((80, 40), 12, (200, 150, 90), (140, 90, 50))
        self.assertEqual(img.size, (80, 40))
        self.assertEqual(img.mode, "RGBA")
        # corners are transparent (rounded), center is opaque
        self.assertEqual(img.getpixel((0, 0))[3], 0)
        self.assertEqual(img.getpixel((40, 20))[3], 255)

    def test_soft_shadow_returns_image_and_pad(self):
        img, pad = self.w.soft_shadow((60, 30), 10)
        self.assertIsInstance(pad, int)
        self.assertEqual(img.mode, "RGBA")
        self.assertGreater(img.size[0], 60)

    def test_glow_dot_is_square_and_has_alpha(self):
        d = self.w.glow_dot(20, "#ffe082", "#d89020", "#ffdc7855")
        self.assertEqual(d.size, (60, 60))
        self.assertGreater(d.getpixel((30, 30))[3], 0)  # center opaque-ish

    def test_load_font_never_raises(self):
        f = self.w._load_font("NoSuchFontFamily", 14, bold=True)
        self.assertIsNotNone(f)

    def test_cache_returns_same_object(self):
        calls = []
        def factory():
            calls.append(1)
            return Image.new("RGBA", (4, 4))
        a = self.w._cache_get(("k", 1), factory)
        b = self.w._cache_get(("k", 1), factory)
        self.assertIs(a, b)
        self.assertEqual(len(calls), 1)


class TestChipAndLawPill(unittest.TestCase):
    def setUp(self):
        from garden_of_inheritance import widgets
        self.w = widgets

    def test_chip_height_matches_and_has_width(self):
        img = self.w.chip("Seeds 22", icon="gold", height=34)
        self.assertEqual(img.mode, "RGBA")
        self.assertEqual(img.size[1], 34)
        self.assertGreater(img.size[0], 40)

    def test_chip_without_icon(self):
        img = self.w.chip("1 April 1856", height=30)
        self.assertEqual(img.size[1], 30)

    def test_law_pill_done_vs_pending_differ(self):
        done = self.w.law_pill("Dominance", True)
        pend = self.w.law_pill("Dominance", False)
        self.assertEqual(done.size[1], pend.size[1])
        self.assertNotEqual(list(done.getdata()), list(pend.getdata()))


def _make_root():
    """Return a withdrawn Tk root, or None if no display is available."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        return root
    except Exception:
        return None


class TestPillButton(unittest.TestCase):
    def setUp(self):
        self.root = _make_root()
        if self.root is None:
            self.skipTest("no Tk display")
        from garden_of_inheritance import widgets
        self.w = widgets

    def tearDown(self):
        if self.root is not None:
            self.root.destroy()

    def test_pill_image_states_differ(self):
        normal = self.w._pill_image("Water", "wood", "normal", (140, 40), 13, None)
        pressed = self.w._pill_image("Water", "wood", "pressed", (140, 40), 13, None)
        self.assertNotEqual(list(normal.getdata()), list(pressed.getdata()))

    def test_command_fires_on_invoke(self):
        fired = []
        b = self.w.PillButton(self.root, "Go", command=lambda: fired.append(1))
        b.invoke()
        self.assertEqual(fired, [1])

    def test_disabled_does_not_fire(self):
        fired = []
        b = self.w.PillButton(self.root, "Go", command=lambda: fired.append(1), state="disabled")
        b.invoke()
        self.assertEqual(fired, [])

    def test_configure_text_and_state(self):
        b = self.w.PillButton(self.root, "Pause")
        b.configure(text="Resume", state="disabled")
        self.assertEqual(b.cget("text"), "Resume")
        self.assertEqual(b.cget("state"), "disabled")

    def test_make_button_swallows_legacy_kwargs(self):
        b = self.w.make_button(self.root, text="X", command=lambda: None,
                               bg="#fff", relief="flat", bd=0, padx=12, image=None)
        self.assertIsInstance(b, self.w.PillButton)


class TestPanelCard(unittest.TestCase):
    def setUp(self):
        from garden_of_inheritance import widgets
        self.w = widgets

    def test_panel_card_returns_image_and_bbox(self):
        img, bbox = self.w.panel_card(300, 200, title="Inventory")
        self.assertEqual(img.mode, "RGBA")
        self.assertEqual(len(bbox), 4)
        # content region is inside the card
        self.assertGreaterEqual(bbox[0], 0)
        self.assertLess(bbox[2], img.size[0])

    def test_panel_card_no_title_has_taller_content(self):
        _, bbox_titled = self.w.panel_card(300, 200, title="X")
        _, bbox_plain = self.w.panel_card(300, 200, title=None)
        self.assertLess(bbox_plain[1], bbox_titled[1])


if __name__ == "__main__":
    unittest.main()
