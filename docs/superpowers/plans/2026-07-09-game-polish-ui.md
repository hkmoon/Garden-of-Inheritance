# Game-Polish UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Garden of Inheritance Tkinter UI game-level chrome (rounded HUD chips, pill buttons with hover/press/disabled states, soft-shadowed panel cards, garden-tile depth + selection glow) using the existing daytime palette, applied to the main window and the Inventory / Law Wizard / Pollinate + Emasculation popups.

**Architecture:** A new presentational toolkit `garden_of_inheritance/widgets.py` renders the signature pieces as Pillow images placed on Tk canvases/labels; images are cached per `(kind, size, state, palette, scale)`. Integration reuses existing seams — the legacy `make_icon_button`, inline toolbar `tk.Button(**self.button_style)` sites, `inventory._button_style`, and `tile.py`'s canvas items — swapping native widgets one at a time so behavior is identical. Palette values come from `theme.py`, extended with gradient/state stops.

**Tech Stack:** Python 3, Tkinter, Pillow (already a dependency — version 10.4.0 present), `unittest`.

## Global Constraints

- **No new dependency.** Pillow is already imported across the codebase; add nothing to the runtime requirements.
- **Purely presentational.** Do not change save format, serialization, or Mendelian/game logic. Preserve public method names and callbacks on `GardenApp` and dialogs.
- **Never crash on render.** Missing font → fall back to a default font. Image compositing failure → fall back to a styled native `tk.Button` / flat fill. The app must launch even if the toolkit fails.
- **Palette is unchanged in mood.** Reuse existing `theme.py` colors; only ADD gradient/state stops, never repurpose existing constants for current consumers.
- **Retina crispness.** Render supersampled at `SCALE = 2` and downsample with `LANCZOS`.
- **Keep Measure Temp native.** The `measure_temp_btn` has a state machine (`_update_temp_button_state`, legacy `garden_of_inheritance_legacy.py:4579`) that recolors it via `bg/fg/_base_bg/_hover_bg`; leave it a native `tk.Button` to avoid behavior drift. Every other scoped button converts.
- **Run from the project root** so `import garden_of_inheritance...` resolves: `/Users/moon/Projects/Python/Garden-of-Inheritance`.
- **Test command:** `python3 -m unittest discover -s tests -v` (must stay green). Toolkit image tests need no display; widget tests self-skip when no Tk display is available.

---

## File Structure

- `garden_of_inheritance/theme.py` — **modify**: add gradient/state palette constants (Task 1).
- `garden_of_inheritance/widgets.py` — **create**: the toolkit (Tasks 2–5).
- `tests/test_widgets.py` — **create**: toolkit tests (Tasks 2–5).
- `garden_of_inheritance_legacy.py` — **modify**: status chips (Task 6), sidebar+toolbar+Unlock buttons (Task 7), law pills (Task 8).
- `tile.py` — **modify**: soil gradient + selection glow (Task 9).
- `inventory.py` — **modify**: panel card + buttons (Task 10).
- `mendelian_law_wizard.py` — **modify**: card + buttons (Task 11).
- `pollination_dialog.py`, `emasculation_dialog.py` — **modify**: card + buttons (Task 12).
- `README.md` — **modify**: note Pillow requirement (Task 13).

---

## Task 1: Extend theme.py with gradient/state stops

**Files:**
- Modify: `garden_of_inheritance/theme.py` (append at end, after `POD_TINT_YELLOW`)
- Test: `tests/test_widgets.py`

**Interfaces:**
- Produces (all module-level constants in `theme`):
  - `CHIP_BG: str`, `CHIP_BORDER: str`, `CHIP_TEXT: str`
  - `ICON_GOLD: tuple[str, str, str]` (inner, outer, glow-rgba-hex8), `ICON_SEED: tuple[str, str, str]`
  - `BTN_WOOD`, `BTN_SUCCESS`, `BTN_DANGER`, `BTN_MUTED`: each `tuple[str, str, str]` = (top, bottom, border)
  - `PANEL_GRAD: tuple[str, str]` = (top, bottom)
  - `SHADOW_RGBA: tuple[int, int, int, int]`
  - `TILE_SOIL_GRAD: tuple[str, str]` = (top, bottom)
  - `hover(hex_color: str, amount: float = 0.10) -> str`, `press(hex_color: str, amount: float = 0.12) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/test_widgets.py` with:

```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garden_of_inheritance import theme


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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widgets.TestThemeStops -v`
Expected: FAIL — `AttributeError: module 'garden_of_inheritance.theme' has no attribute 'BTN_WOOD'`.

- [ ] **Step 3: Append the constants and helpers to `theme.py`**

Append to the end of `garden_of_inheritance/theme.py`:

```python
# ---------------------------------------------------------------------------
# Game-polish gradient / state stops (added for widgets.py). Additive only —
# existing flat constants above are unchanged.
# ---------------------------------------------------------------------------

CHIP_BG = "#2e2212"
CHIP_BORDER = WOOD_DARK
CHIP_TEXT = "#f5e9c8"

# (inner, outer, glow-rgba-hex8) for glowing icon dots
ICON_GOLD = ("#ffe082", "#d89020", "#ffdc7855")
ICON_SEED = ("#fff4c0", "#c8e04a", "#f0f59655")

# (top, bottom, border) gradient stops per button variant
BTN_WOOD = (WOOD_LIGHT, WOOD_MID, WOOD_DARK)
BTN_SUCCESS = (BUTTON_SUCCESS_HOVER, BUTTON_SUCCESS_BG, "#4d6631")
BTN_DANGER = (BUTTON_DANGER_HOVER, BUTTON_DANGER_BG, "#6e2f22")
BTN_MUTED = ("#c9bfa6", "#b3a888", "#8a7f63")

PANEL_GRAD = (PANEL_BG, PANEL_ALT)
SHADOW_RGBA = (40, 24, 10, 95)

TILE_SOIL_GRAD = ("#a8743e", "#8a5a30")


def _clamp(v: int) -> int:
    return 0 if v < 0 else 255 if v > 255 else v


def _to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _to_hex(rgb) -> str:
    return "#%02x%02x%02x" % tuple(_clamp(int(c)) for c in rgb)


def hover(hex_color: str, amount: float = 0.10) -> str:
    """Lighten a hex color toward white by `amount` (0..1)."""
    r, g, b = _to_rgb(hex_color)
    return _to_hex((r + (255 - r) * amount, g + (255 - g) * amount, b + (255 - b) * amount))


def press(hex_color: str, amount: float = 0.12) -> str:
    """Darken a hex color toward black by `amount` (0..1)."""
    r, g, b = _to_rgb(hex_color)
    return _to_hex((r * (1 - amount), g * (1 - amount), b * (1 - amount)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_widgets.TestThemeStops -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add garden_of_inheritance/theme.py tests/test_widgets.py
git commit -m "feat(theme): add gradient/state palette stops for widget toolkit"
```

---

## Task 2: widgets.py rendering helpers + font loader + image cache

**Files:**
- Create: `garden_of_inheritance/widgets.py`
- Test: `tests/test_widgets.py` (add a class)

**Interfaces:**
- Produces:
  - `SCALE: int` (= 2)
  - `_load_font(family: str, size: int, bold: bool = False) -> ImageFont` (never raises)
  - `rounded_grad(size, radius, top_rgb, bottom_rgb) -> PIL.Image (RGBA)`
  - `soft_shadow(size, radius, blur=7, rgba=theme.SHADOW_RGBA) -> (PIL.Image RGBA, pad:int)`
  - `glow_dot(diameter, inner_hex, outer_hex, glow_hex8) -> PIL.Image (RGBA, size 3*diameter square)`
  - `_cache_get(key, factory)` — memoize helper backed by module dict `_IMAGE_CACHE`
  - `_hx(hex_color) -> (r,g,b)` and `_hx8(hex8) -> (r,g,b,a)`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_widgets.py`:

```python
from PIL import Image  # noqa: E402


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widgets.TestRenderHelpers -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'garden_of_inheritance.widgets'`.

- [ ] **Step 3: Create `garden_of_inheritance/widgets.py` with helpers**

```python
"""Pillow-backed UI toolkit: game-polish chrome for the Tkinter UI.

Presentational only. Never raises on render — falls back gracefully so the app
always launches. All colors come from `theme`.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from garden_of_inheritance import theme

SCALE = 2  # supersample factor for crisp edges on Retina

_IMAGE_CACHE: dict = {}

_FONT_DIRS = [
    "/System/Library/Fonts/Supplemental",
    "/System/Library/Fonts",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
]
_FONT_FILES = {
    ("Trebuchet MS", False): "Trebuchet MS.ttf",
    ("Trebuchet MS", True): "Trebuchet MS Bold.ttf",
    ("Georgia", False): "Georgia.ttf",
    ("Georgia", True): "Georgia Bold.ttf",
}


def _cache_get(key, factory):
    img = _IMAGE_CACHE.get(key)
    if img is None:
        img = factory()
        _IMAGE_CACHE[key] = img
    return img


def _hx(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hx8(hex8):
    h = hex8.lstrip("#")
    if len(h) == 6:
        h += "ff"
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4, 6))


def _load_font(family, size, bold=False):
    """Resolve a font family to a truetype file; fall back safely."""
    px = int(size * SCALE)
    fname = _FONT_FILES.get((family, bold)) or _FONT_FILES.get((family, False))
    if fname:
        for d in _FONT_DIRS:
            path = os.path.join(d, fname)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, px)
                except Exception:
                    pass
    for d in _FONT_DIRS:  # generic fallback
        arial = os.path.join(d, "Arial Bold.ttf" if bold else "Arial.ttf")
        if os.path.exists(arial):
            try:
                return ImageFont.truetype(arial, px)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _vgrad(size, top_rgb, bottom_rgb):
    w, h = size
    strip = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        strip.putpixel((0, y), tuple(int(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * t) for i in range(3)))
    return strip.resize((w, h))


def rounded_grad(size, radius, top_rgb, bottom_rgb):
    w, h = size
    base = _vgrad(size, top_rgb, bottom_rgb).convert("RGBA")
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    base.putalpha(mask)
    return base


def soft_shadow(size, radius, blur=7, rgba=None):
    if rgba is None:
        rgba = theme.SHADOW_RGBA
    w, h = size
    pad = blur * 3
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle(
        [pad, pad, pad + w - 1, pad + h - 1], radius=radius, fill=tuple(rgba))
    return layer.filter(ImageFilter.GaussianBlur(blur)), pad


def glow_dot(diameter, inner_hex, outer_hex, glow_hex8):
    s = int(diameter)
    layer = Image.new("RGBA", (s * 3, s * 3), (0, 0, 0, 0))
    gd = ImageDraw.Draw(layer)
    gd.ellipse([s * 0.7, s * 0.7, s * 2.3, s * 2.3], fill=_hx8(glow_hex8))
    layer = layer.filter(ImageFilter.GaussianBlur(s * 0.35))
    gd = ImageDraw.Draw(layer)
    gd.ellipse([s, s, s * 2, s * 2], fill=_hx(outer_hex))
    gd.ellipse([s * 1.12, s * 1.05, s * 1.7, s * 1.62], fill=_hx(inner_hex))
    gd.ellipse([s * 1.22, s * 1.15, s * 1.45, s * 1.38], fill=(255, 255, 255, 210))
    return layer
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_widgets.TestRenderHelpers -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add garden_of_inheritance/widgets.py tests/test_widgets.py
git commit -m "feat(widgets): render helpers, font loader, image cache"
```

---

## Task 3: chip() and law_pill()

**Files:**
- Modify: `garden_of_inheritance/widgets.py`
- Test: `tests/test_widgets.py`

**Interfaces:**
- Consumes: helpers from Task 2, `theme` stops from Task 1.
- Produces:
  - `chip(text, *, icon=None, height=34, font_size=15) -> PIL.Image (RGBA)` — `icon` is one of `None`, `"gold"`, `"seed"`.
  - `law_pill(text, done, *, height=34, font_size=13) -> PIL.Image (RGBA)`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_widgets.py`:

```python
class TestChipAndLawPill(unittest.TestCase):
    def setUp(self):
        from garden_of_inheritance import widgets
        self.w = widgets

    def test_chip_height_matches_and_has_width(self):
        img = self.w.chip("Seeds 22", icon="gold", height=34)
        self.assertEqual(img.mode, "RGBA")
        self.assertEqual(img.size[1], 34 * self.w.SCALE)
        self.assertGreater(img.size[0], 40)

    def test_chip_without_icon(self):
        img = self.w.chip("1 April 1856", height=30)
        self.assertEqual(img.size[1], 30 * self.w.SCALE)

    def test_law_pill_done_vs_pending_differ(self):
        done = self.w.law_pill("Dominance", True)
        pend = self.w.law_pill("Dominance", False)
        self.assertEqual(done.size[1], pend.size[1])
        self.assertNotEqual(list(done.getdata()), list(pend.getdata()))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widgets.TestChipAndLawPill -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'chip'`.

- [ ] **Step 3: Append `chip` and `law_pill` to `widgets.py`**

```python
_ICON_STOPS = {"gold": theme.ICON_GOLD, "seed": theme.ICON_SEED}


def _text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1], bb


def chip(text, *, icon=None, height=34, font_size=15):
    key = ("chip", text, icon, height, font_size, SCALE)

    def build():
        h = height * SCALE
        pad_x = 15 * SCALE
        font = _load_font(theme.UI_FONT, font_size, bold=True)
        probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        tw, th, _ = _text_size(probe, text, font)
        ds = h - 14 * SCALE if icon else 0
        dot_gap = (ds + 8 * SCALE) if icon else 0
        w = int(pad_x * 2 + dot_gap + tw)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2,
                            fill=_hx(theme.CHIP_BG) + (210,),
                            outline=_hx(theme.CHIP_BORDER), width=2 * SCALE)
        x = pad_x
        if icon and icon in _ICON_STOPS:
            dot = glow_dot(int(ds), *_ICON_STOPS[icon])
            img.alpha_composite(dot, (int(x - ds), int(h // 2 - dot.size[1] // 2)))
            x += ds + 8 * SCALE
        _, _, bb = _text_size(d, text, font)
        d.text((x, (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font, fill=_hx(theme.CHIP_TEXT))
        return img

    return _cache_get(key, build)


def law_pill(text, done, *, height=34, font_size=13):
    key = ("law_pill", text, bool(done), height, font_size, SCALE)

    def build():
        label = ("✓ " if done else "○ ") + text
        top, bottom, border = (
            (theme.BUTTON_SUCCESS_HOVER, theme.BUTTON_SUCCESS_BG, "#5d7a37") if done
            else theme.BTN_MUTED)
        tcol = theme.BUTTON_FG if done else "#7a6f56"
        h = height * SCALE
        pad_x = 16 * SCALE
        font = _load_font(theme.UI_FONT, font_size, bold=True)
        probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        tw, _, _ = _text_size(probe, label, font)
        w = int(pad_x * 2 + tw)
        img = rounded_grad((w, h), h // 2, _hx(top), _hx(bottom))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1, 1, w - 2, h - 2], radius=h // 2 - 1,
                            outline=_hx(border), width=2 * SCALE)
        if done:
            gl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle(
                [4 * SCALE, 3 * SCALE, w - 4 * SCALE, h // 2], radius=h // 2 - 2,
                fill=(255, 255, 255, 30))
            img.alpha_composite(gl)
        _, _, bb = _text_size(d, label, font)
        d.text(((w - tw) / 2, (h - (bb[3] - bb[1])) / 2 - bb[1]), label, font=font, fill=_hx(tcol))
        return img

    return _cache_get(key, build)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_widgets.TestChipAndLawPill -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add garden_of_inheritance/widgets.py tests/test_widgets.py
git commit -m "feat(widgets): chip() and law_pill() renderers"
```

---

## Task 4: PillButton widget + make_button factory

**Files:**
- Modify: `garden_of_inheritance/widgets.py`
- Test: `tests/test_widgets.py`

**Interfaces:**
- Consumes: helpers from Task 2, `theme` stops from Task 1.
- Produces:
  - `_pill_image(text, variant, state, size, font_size, icon_path) -> PIL.Image` (cached)
  - `class PillButton(tkinter.Canvas)` with:
    - `__init__(self, parent, text="", command=None, *, variant="wood", icon_path=None, min_width=0, height=40, font_size=13, state="normal", **_ignored)`
    - `configure(self, **kw)` / alias `config` — accepts `text`, `state` (`"normal"`/`"disabled"`), `command`, `variant`; ignores legacy tk.Button kwargs.
    - `cget(self, key)` — supports `"text"`, `"state"`.
    - `invoke(self)` — fire command if enabled.
  - `make_button(parent, text="", command=None, *, variant="wood", icon_path=None, min_width=0, height=40, font_size=13, **compat) -> PillButton` — swallows legacy style kwargs (`bg`, `fg`, `image`, `compound`, `relief`, `bd`, `borderwidth`, `padx`, `pady`, `font`, `highlightthickness`, `activebackground`, `activeforeground`, `overrelief`).

**Design notes for the implementer:**
- `PillButton` is a `tkinter.Canvas` with `highlightthickness=0, bd=0, bg=<parent bg>`. It draws ONE `create_image` item and swaps its image on state change. It keeps references to all four state images in `self._imgs` so Tk does not garbage-collect the `PhotoImage`s.
- The `PhotoImage`s are created lazily from the cached PIL images via `ImageTk.PhotoImage`. A per-instance dict avoids recreating them.
- Hover/press via `<Enter> <Leave> <ButtonPress-1> <ButtonRelease-1>`. Command fires on release only if the pointer is still inside and state != disabled.
- Any exception during image build → set `self._failed = True` and draw a flat rounded rect with text via native canvas items (still functional).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_widgets.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widgets.TestPillButton -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'PillButton'` (or all skip if no display; run locally where a display exists).

- [ ] **Step 3: Append `_pill_image`, `PillButton`, `make_button` to `widgets.py`**

Add this import near the top of `widgets.py` (below the existing PIL import):

```python
import tkinter as tk

from PIL import ImageTk
```

Append:

```python
_VARIANT_STOPS = {
    "wood": theme.BTN_WOOD,
    "success": theme.BTN_SUCCESS,
    "danger": theme.BTN_DANGER,
    "muted": theme.BTN_MUTED,
}


def _state_stops(variant, state):
    top, bottom, border = _VARIANT_STOPS.get(variant, theme.BTN_WOOD)
    if state == "hover":
        return theme.hover(top), theme.hover(bottom), border
    if state == "pressed":
        return theme.press(top), theme.press(bottom), border
    if state == "disabled":
        return theme.BTN_MUTED[0], theme.BTN_MUTED[1], theme.BTN_MUTED[2]
    return top, bottom, border


def _pill_image(text, variant, state, size, font_size, icon_path):
    key = ("pill", text, variant, state, size, font_size, icon_path, SCALE)

    def build():
        w, h = size[0] * SCALE, size[1] * SCALE
        top, bottom, border = _state_stops(variant, state)
        img = rounded_grad((w, h), h // 2, _hx(top), _hx(bottom))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([1, 1, w - 2, h - 2], radius=h // 2 - 1,
                            outline=_hx(border), width=2 * SCALE)
        if state != "pressed":  # top gloss
            gl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(gl).rounded_rectangle(
                [4 * SCALE, 3 * SCALE, w - 4 * SCALE, h // 2], radius=h // 2 - 2,
                fill=(255, 255, 255, 34))
            img.alpha_composite(gl)
        tcol = (109, 100, 80) if state == "disabled" else _hx(theme.BUTTON_FG)
        if isinstance(tcol, tuple) is False:
            tcol = _hx(theme.BUTTON_FG)
        icon_w = 0
        x0 = 14 * SCALE
        if icon_path and os.path.exists(icon_path):
            try:
                ic = Image.open(icon_path).convert("RGBA")
                target = int(h * 0.6)
                ic.thumbnail((target, target))
                img.alpha_composite(ic, (x0, (h - ic.size[1]) // 2))
                icon_w = ic.size[0] + 6 * SCALE
            except Exception:
                icon_w = 0
        font = _load_font(theme.UI_FONT, font_size, bold=True)
        bb = d.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        content_w = icon_w + tw
        start = max(x0 if icon_path else 0, (w - content_w) // 2)
        tx = start + icon_w
        d.text((tx, (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font,
               fill=tcol if isinstance(tcol, tuple) else _hx(theme.BUTTON_FG))
        return img

    return _cache_get(key, build)


def _measure_pill_width(text, font_size, icon_path, min_width, height):
    font = _load_font(theme.UI_FONT, font_size, bold=True)
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    bb = probe.textbbox((0, 0), text, font=font)
    tw = (bb[2] - bb[0]) / SCALE
    icon_w = 0
    if icon_path and os.path.exists(icon_path):
        icon_w = height * 0.6 + 6
    w = int(tw + icon_w + 32)
    return max(min_width, w, height)


class PillButton(tk.Canvas):
    _LEGACY_KW = {"bg", "fg", "image", "compound", "relief", "bd", "borderwidth",
                  "padx", "pady", "font", "highlightthickness", "activebackground",
                  "activeforeground", "overrelief", "anchor", "justify", "cursor"}

    def __init__(self, parent, text="", command=None, *, variant="wood",
                 icon_path=None, min_width=0, height=40, font_size=13,
                 state="normal", **_ignored):
        self._text = text
        self._command = command
        self._variant = variant
        self._icon_path = icon_path
        self._font_size = font_size
        self._height = height
        self._state = "disabled" if state == "disabled" else "normal"
        self._pointer_in = False
        self._imgs = {}
        self._failed = False
        w = _measure_pill_width(text, font_size, icon_path, min_width, height)
        try:
            parent_bg = parent.cget("bg")
        except Exception:
            parent_bg = theme.PANEL_BG
        super().__init__(parent, width=w, height=height, highlightthickness=0,
                         bd=0, bg=parent_bg, takefocus=1)
        self._img_item = self.create_image(0, 0, anchor="nw")
        self._render()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _current_visual_state(self):
        if self._state == "disabled":
            return "disabled"
        return self._state  # "normal"/"hover"/"pressed" set transiently

    def _photo(self, vstate):
        if vstate not in self._imgs:
            try:
                pil = _pill_image(self._text, self._variant, vstate,
                                  (int(self["width"]), self._height), self._font_size,
                                  self._icon_path)
                self._imgs[vstate] = ImageTk.PhotoImage(pil)
            except Exception:
                self._failed = True
                return None
        return self._imgs[vstate]

    def _render(self, vstate=None):
        vstate = vstate or ("disabled" if self._state == "disabled" else "normal")
        photo = self._photo(vstate)
        if photo is None:  # fallback: flat drawn pill
            self.delete("all")
            self.create_rectangle(0, 0, int(self["width"]), self._height,
                                  fill=theme.WOOD_MID, outline=theme.WOOD_DARK)
            self.create_text(int(self["width"]) // 2, self._height // 2,
                             text=self._text, fill=theme.BUTTON_FG)
            return
        self.itemconfig(self._img_item, image=photo)

    def _on_enter(self, _):
        self._pointer_in = True
        if self._state != "disabled":
            self._render("hover")

    def _on_leave(self, _):
        self._pointer_in = False
        if self._state != "disabled":
            self._render("normal")

    def _on_press(self, _):
        if self._state != "disabled":
            self._render("pressed")

    def _on_release(self, _):
        if self._state == "disabled":
            return
        self._render("hover" if self._pointer_in else "normal")
        if self._pointer_in and self._command:
            self._command()

    def invoke(self):
        if self._state != "disabled" and self._command:
            self._command()

    def configure(self, **kw):
        redraw = False
        resize = False
        for legacy in list(kw):
            if legacy in self._LEGACY_KW:
                kw.pop(legacy)
        if "text" in kw:
            self._text = kw.pop("text"); self._imgs.clear(); redraw = True; resize = True
        if "command" in kw:
            self._command = kw.pop("command")
        if "variant" in kw:
            self._variant = kw.pop("variant"); self._imgs.clear(); redraw = True
        if "state" in kw:
            self._state = "disabled" if kw.pop("state") == "disabled" else "normal"
            self._imgs.clear(); redraw = True
        if resize:
            neww = _measure_pill_width(self._text, self._font_size, self._icon_path, 0, self._height)
            super().configure(width=neww)
        if kw:
            super().configure(**kw)
        if redraw:
            self._render()

    config = configure

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return self._state
        return super().cget(key)


def make_button(parent, text="", command=None, *, variant="wood", icon_path=None,
                min_width=0, height=40, font_size=13, **compat):
    return PillButton(parent, text=text, command=command, variant=variant,
                      icon_path=icon_path, min_width=min_width, height=height,
                      font_size=font_size)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_widgets.TestPillButton -v`
Expected: PASS (5 tests) on a machine with a display; SKIP if headless.

- [ ] **Step 5: Commit**

```bash
git add garden_of_inheritance/widgets.py tests/test_widgets.py
git commit -m "feat(widgets): PillButton widget + make_button factory"
```

---

## Task 5: panel_card()

**Files:**
- Modify: `garden_of_inheritance/widgets.py`
- Test: `tests/test_widgets.py`

**Interfaces:**
- Consumes: helpers from Task 2.
- Produces: `panel_card(width, height, *, title=None, title_font_size=16) -> (PIL.Image RGBA, content_bbox: tuple[int,int,int,int])` — the returned image already includes a soft drop shadow; `content_bbox` is in **downsampled (CSS) pixels** relative to the image's top-left, telling the caller where native widgets/rows may be placed over a Label showing the image.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_widgets.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_widgets.TestPanelCard -v`
Expected: FAIL — `AttributeError: ... 'panel_card'`.

- [ ] **Step 3: Append `panel_card` to `widgets.py`**

```python
def panel_card(width, height, *, title=None, title_font_size=16):
    key = ("panel_card", width, height, title, title_font_size, SCALE)

    def build():
        w, h = width * SCALE, height * SCALE
        radius = 18 * SCALE
        card = rounded_grad((w, h), radius, _hx(theme.PANEL_GRAD[0]), _hx(theme.PANEL_GRAD[1]))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle([1, 1, w - 2, h - 2], radius=radius - 1,
                            outline=_hx(theme.PANEL_BORDER), width=3 * SCALE)
        header_h = 0
        if title:
            header_h = 46 * SCALE
            d.rounded_rectangle([1, 1, w - 2, header_h], radius=radius - 1, fill=_hx(theme.WOOD_MID))
            d.rectangle([1, header_h - radius, w - 2, header_h], fill=_hx(theme.WOOD_MID))
            font = _load_font(theme.DISPLAY_FONT, title_font_size, bold=True)
            d.text((18 * SCALE, (header_h - title_font_size * SCALE) / 2 - 2 * SCALE),
                   title, font=font, fill=_hx(theme.TEXT_LIGHT))
        shadow, pad = soft_shadow((w, h), radius, blur=12)
        canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        canvas.alpha_composite(shadow, (0, int(pad * 0.6)))
        canvas.alpha_composite(card, (pad, pad))
        # content bbox in CSS px, relative to canvas top-left
        cx = (pad + 14 * SCALE) // SCALE
        cy = (pad + header_h + 12 * SCALE) // SCALE
        cw = (pad + w - 14 * SCALE) // SCALE
        ch = (pad + h - 14 * SCALE) // SCALE
        return canvas, (int(cx), int(cy), int(cw), int(ch))

    return _cache_get(key, build)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_widgets.TestPanelCard -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Full toolkit suite + commit**

Run: `python3 -m unittest discover -s tests -v`
Expected: all green (widget tests SKIP if headless).

```bash
git add garden_of_inheritance/widgets.py tests/test_widgets.py
git commit -m "feat(widgets): panel_card() renderer; toolkit complete"
```

---

## Task 6: Main window — status strip → chips

**Files:**
- Modify: `garden_of_inheritance_legacy.py` — imports (top), Seeds/Starter labels (`:2534-2551`), and add a date/time/temp chip. The clock text is produced near `:1040-1069` (`clock_hour`) and shown today in the topbar.

**Interfaces:**
- Consumes: `widgets.chip`, `ImageTk`.
- Produces: `self._chip_imgs` (dict holding `PhotoImage` refs), helper `self._set_chip(label_widget, text, icon)`.

**Manual verification** (this task and all later integration tasks) uses the launch-and-capture method:

```bash
python3 Garden-of-Inheritance.py >/tmp/goi.log 2>&1 &
APP_PID=$!; sleep 9
osascript -e 'tell application "System Events" to tell (first process whose unix id is '"$APP_PID"') to set frontmost to true' \
          -e 'tell application "System Events" to tell (first process whose unix id is '"$APP_PID"') to perform action "AXRaise" of window 1' \
          -e 'tell application "System Events" to tell (first process whose unix id is '"$APP_PID"') to set position of window 1 to {60, 60}'
sleep 2; screencapture -x /tmp/goi_after.png; kill $APP_PID
```

- [ ] **Step 1: Add imports**

Near the existing `from garden_of_inheritance import theme` (`:108`), add:

```python
from garden_of_inheritance import widgets
from PIL import ImageTk
```

(If `ImageTk` is already imported at `:73`, skip that line.)

- [ ] **Step 2: Convert Seeds & Starter labels to chip labels**

The Seeds/Starter labels (`:2534-2551`) are `tk.Label` bound to `self.seed_counter_var` / `self.starter_var` via `textvariable`. Replace both `tk.Label(...)` blocks with image-bearing labels and a helper. Insert this helper method on the class (near `_update_law_status_label`, `:2746`):

```python
    def _set_chip(self, label, text, icon=None):
        try:
            pil = widgets.chip(text, icon=icon, height=30)
            photo = ImageTk.PhotoImage(pil)
            if not hasattr(self, "_chip_imgs"):
                self._chip_imgs = {}
            self._chip_imgs[str(label)] = photo  # keep ref
            label.configure(image=photo, text="", bg=self.panel_bg)
        except Exception:
            label.configure(text=text)  # fallback to plain text
```

Replace the Seeds label block (`:2534-2541`) with:

```python
        self.seed_label = tk.Label(inventory_left, bg=self.panel_bg)
        self.seed_label.pack(side="left", padx=(0, 10))
        self._set_chip(self.seed_label, "Seeds  0", icon="gold")
```

Replace the Starter label block (`:2544-2551`) with:

```python
        self.starter_label = tk.Label(inventory_left, bg=self.panel_bg)
        self.starter_label.pack(side="left", padx=(0, 16))
        self._set_chip(self.starter_label, "Starter  0", icon="seed")
```

- [ ] **Step 3: Redraw chips when counters change**

Find where `self.seed_counter_var` / `self.starter_var` are `.set(...)` (`:2851-2855`). Immediately after those `.set(...)` calls, add:

```python
            self._set_chip(self.starter_label, f"Starter  {self.available_seeds}", icon="seed")
            self._set_chip(self.seed_label, f"Seeds  {len(self.harvest_inventory)}", icon="gold")
```

(Keep the existing `.set()` calls; they harmlessly update the now-unused `textvariable`. Match the exact attribute names used at that site — `self.available_seeds`, `self.harvest_inventory`.)

- [ ] **Step 4: Verify launch + screenshot**

Run the manual verification block above. Open `/tmp/goi_after.png`.
Expected: Seeds and Starter now render as dark rounded chips with a glowing gold / seed dot; counts update after planting/harvesting. No traceback in `/tmp/goi.log`.

- [ ] **Step 5: Commit**

```bash
git add garden_of_inheritance_legacy.py
git commit -m "feat(ui): render Seeds/Starter counters as game-style chips"
```

---

## Task 7: Main window — sidebar + toolbar + Unlock buttons → PillButton

**Files:**
- Modify: `garden_of_inheritance_legacy.py` — `make_icon_button` (`:2400-2430`), toolbar buttons (`:2556-2740`), Unlock (`:2734-2740`).

**Interfaces:**
- Consumes: `widgets.make_button`.
- Produces: same button attribute names (`self.water_btn`, `self.pollinate_btn`, `self.remove_btn`, `self.observatory_btn`, `self.pause_btn`, etc.) so existing reconfigure sites keep working.

**Variant map:** Pollinate → `success`; Remove plant → `danger`; Unlock → `success`; everything else → `wood`.

- [ ] **Step 1: Route `make_icon_button` through the toolkit**

Replace the body of `make_icon_button` (`:2400-2430`) with:

```python
        def make_icon_button(parent, text, icon_name, command):
            variant = {"Pollinate": "success", "Remove plant": "danger"}.get(text, "wood")
            icon_path = os.path.join(icon_loader.ICONS_DIR, icon_name)
            btn = widgets.make_button(parent, text=text, command=command,
                                      variant=variant, icon_path=icon_path,
                                      height=38, font_size=11, min_width=150)
            btn.pack(anchor="nw", pady=3, fill="x")
            return btn
```

Note: `self._apply_hover(btn)` is no longer needed (PillButton owns its hover). The `self.inspect_btn.bind("<Button-3>", ...)` at `:2439` still works (Canvas supports `bind`). Leave it.

- [ ] **Step 2: Convert toolbar buttons**

For each toolbar `tk.Button(...)` in `:2556-2740`, replace construction with `widgets.make_button(...)`, keeping the same attribute name, `command`, and text. Convert these: `observatory_btn`, `pause_btn`, the Next-phase button, Plant, `water_all` button, and the Unlock button. **Do NOT convert `measure_temp_btn`** (`:2664`, keep native per Global Constraints).

Example — Observatory (`:2557-2570`) becomes:

```python
        self.observatory_btn = widgets.make_button(
            inventory_left, text="Observatory",
            icon_path=os.path.join(icon_loader.ICONS_DIR, "observatory.png"),
            command=lambda: (
                self.temp_tracker.open_observatory()
                if hasattr(self, 'temp_tracker') and self.temp_tracker
                else messagebox.showinfo("Observatory", "Temperature tracker not available")),
            height=36, font_size=11)
        self.observatory_btn.pack(side="left", padx=2)
```

Apply the same shape to Resume/Pause, Next, Plant, Water All, Unlock — reuse each button's existing `text=`, `command=`, and `.pack(...)` args. For the pause button keep the toggle text logic; `self.pause_btn.configure(text=...)` at `:5792` and `:5986-5992` now hits `PillButton.configure`, which re-renders — no change needed there.

- [ ] **Step 3: Unlock button variant**

The Unlock button (`:2734-2740`) becomes:

```python
        self.unlock_btn = widgets.make_button(law_row, text="Unlock", variant="success",
                                              command=self._open_law_wizard, height=34, font_size=12)
        self.unlock_btn.pack(side="left", padx=(0, 10))
```

(Use the exact parent and command from the existing block — confirm the command name at `:2737`.)

- [ ] **Step 4: Verify launch + screenshot**

Run the manual verification block. Open `/tmp/goi_after.png` and hover/click a few buttons live.
Expected: sidebar + toolbar are rounded pill buttons with icons; Pollinate green, Remove red; hover lightens, press sinks; Pause↔Resume still toggles; Measure Temp still native and its enable/disable still works. No traceback.

- [ ] **Step 5: Commit**

```bash
git add garden_of_inheritance_legacy.py
git commit -m "feat(ui): convert sidebar/toolbar/unlock buttons to pill buttons"
```

---

## Task 8: Main window — Mendelian law tracker → law pills

**Files:**
- Modify: `garden_of_inheritance_legacy.py` — `_update_law_status_label` (`:2746+`) and the law row label (`:2704-2732`).

**Interfaces:**
- Consumes: `widgets.law_pill`, `ImageTk`.
- Produces: `self._law_pill_imgs` (ref holder); three `tk.Label`s `self.law_pill_labels` in place of the single `law_status_label`.

- [ ] **Step 1: Replace the single status label with three pill labels**

At the law row construction (`:2722-2732`), replace the `self.law_status_label = tk.Label(...)` block with a container plus three image labels:

```python
        self.law_pills_frame = tk.Frame(law_row, bg=self.panel_bg)
        self.law_pills_frame.pack(side="left", anchor="w", padx=(0, 10))
        self.law_pill_labels = []
        for _ in range(3):
            lbl = tk.Label(self.law_pills_frame, bg=self.panel_bg)
            lbl.pack(side="left", padx=(0, 8))
            self.law_pill_labels.append(lbl)
        self._law_pill_imgs = []
```

- [ ] **Step 2: Render pills in `_update_law_status_label`**

Read `_update_law_status_label` (`:2746+`) to find the three booleans it uses to decide each law's unlocked state (e.g. `self.law1_unlocked` / equivalent flags). Replace the body that builds the text string with:

```python
    def _update_law_status_label(self):
        labels = ["Law of Dominance", "Law of Segregation (3:1)",
                  "Law of Independent Assortment (9:3:3:1)"]
        # Reuse the SAME unlocked flags the old text logic used:
        done = [self._law1_done(), self._law2_done(), self._law3_done()]
        self._law_pill_imgs = []
        for i, lbl in enumerate(getattr(self, "law_pill_labels", [])):
            try:
                photo = ImageTk.PhotoImage(widgets.law_pill(labels[i], done[i], height=30))
                self._law_pill_imgs.append(photo)
                lbl.configure(image=photo, text="")
            except Exception:
                lbl.configure(text=("✓ " if done[i] else "○ ") + labels[i])
```

Replace `self._law1_done()/_law2_done()/_law3_done()` with the actual boolean expressions found in the original method (do not invent flag names — copy the real ones). Keep any side effects the original method had (e.g. enabling the Unlock button) intact.

- [ ] **Step 3: Verify launch + screenshot; unlock a law**

Run the manual verification block, then (in the live app) unlock a law and confirm its pill turns glossy-green with a ✓.
Expected: three law pills render; pending = muted ○, unlocked = green ✓. No traceback.

- [ ] **Step 4: Commit**

```bash
git add garden_of_inheritance_legacy.py
git commit -m "feat(ui): render Mendelian law tracker as pills"
```

---

## Task 9: Garden tiles — soil gradient + selection glow

**Files:**
- Modify: `tile.py` — soil layer creation (`:186-233`), selection toggle (`:436-440`).

**Interfaces:**
- Consumes: `widgets.rounded_grad`, `theme.TILE_SOIL_GRAD`, `theme.SELECTION_GOLD`, `ImageTk`.
- Produces: `self._soil_grad_img` (per-tile ref), a second selection item `self.sel_glow`.

**Design note:** The tile is a Tk `Canvas`. Add ONE cached gradient `PhotoImage` behind the existing soil texture and thicken the selection into a two-ring glow. Keep flat `bg_rect` as a fallback if image creation fails.

- [ ] **Step 1: Add a module-level cached soil gradient PhotoImage helper**

Near the top of `tile.py` (after the existing `from garden_of_inheritance import theme`, `:11`), add:

```python
from garden_of_inheritance import widgets

_SOIL_GRAD_CACHE = {}


def _soil_gradient_photo(w, h):
    key = (int(w), int(h))
    photo = _SOIL_GRAD_CACHE.get(key)
    if photo is None:
        try:
            from PIL import ImageTk
            pil = widgets.rounded_grad((int(w) * widgets.SCALE, int(h) * widgets.SCALE),
                                       8 * widgets.SCALE,
                                       widgets._hx(theme.TILE_SOIL_GRAD[0]),
                                       widgets._hx(theme.TILE_SOIL_GRAD[1]))
            pil = pil.resize((int(w), int(h)))
            photo = ImageTk.PhotoImage(pil)
            _SOIL_GRAD_CACHE[key] = photo
        except Exception:
            return None
    return photo
```

- [ ] **Step 2: Place the gradient behind the soil texture**

In `_build_soil` (the method around `:186-219` that creates `bg_rect`, `grass_strip`, `furrow_lines`, `bg_img_item`), immediately AFTER `self.bg_rect` is created (`:195-199`), add a gradient image item:

```python
        self._soil_grad_photo = _soil_gradient_photo(self.tile_w - 4, self.tile_h - 4)
        if self._soil_grad_photo is not None:
            self._soil_grad_item = self.create_image(2, 2, anchor="nw", image=self._soil_grad_photo)
        else:
            self._soil_grad_item = None
```

Use the tile's real width/height attributes — inspect the surrounding code for the correct names (e.g. `self.tile_w`/`self.tile_h` or the constants passed to `Canvas(...)` at `:157-163`); substitute the actual ones. Ensure the furrow lines and `bg_img_item` are raised above it (they are created after, so default stacking already puts them on top).

- [ ] **Step 3: Upgrade the selection into a glow**

At the selection toggle (`:436-440`), replace:

```python
            if self.selected:
                self.itemconfig(self.sel_rect, outline=theme.SELECTION_GOLD)
                self.tag_raise(self.sel_rect)
            else:
                self.itemconfig(self.sel_rect, outline="")
```

with a two-ring version. First, in `_build_soil` where `self.sel_rect` is created (`:222-224`), add a softer outer ring right after it:

```python
        self.sel_glow = self.create_rectangle(
            1, 1, 1, 1, outline="", width=6)
```

(Match the coordinates/size used for `sel_rect` but inset by ~2px less so it reads as an outer halo; copy `sel_rect`'s coordinate expressions.)

Then the toggle becomes:

```python
            if self.selected:
                self.itemconfig(self.sel_rect, outline=theme.SELECTION_GOLD, width=3)
                self.itemconfig(self.sel_glow, outline=theme.SELECTION_GOLD)
                self.tag_raise(self.sel_glow)
                self.tag_raise(self.sel_rect)
            else:
                self.itemconfig(self.sel_rect, outline="")
                self.itemconfig(self.sel_glow, outline="")
```

- [ ] **Step 4: Verify launch + screenshot; select a tile**

Run the manual verification block; in the live app click a tile.
Expected: soil has a subtle top-to-bottom gradient with visible furrows; the selected tile shows a gold glow ring. Plant sprites still render on top. No traceback.

- [ ] **Step 5: Commit**

```bash
git add tile.py
git commit -m "feat(ui): garden tile soil gradient + selection glow"
```

---

## Task 10: Inventory popup → panel card + pill buttons

**Files:**
- Modify: `inventory.py` — `_button_style` seam (`:21-29`), button construction sites (21 `tk.Button`), and the main dialog frame.

**Interfaces:**
- Consumes: `widgets.make_button`, `widgets.panel_card`.
- Produces: unchanged public dialog API.

- [ ] **Step 1: Add a toolkit button helper next to `_button_style`**

After `_button_fg` (`:28-29`), add:

```python
def _pill(parent, text, command, variant="wood", **compat):
    from garden_of_inheritance import widgets
    return widgets.make_button(parent, text=text, command=command, variant=variant,
                               height=34, font_size=11)
```

- [ ] **Step 2: Convert the dialog's action buttons**

For each `tk.Button(parent, text=..., command=..., **_button_style(app))` in `inventory.py`, replace with `_pill(parent, text, command)` (choose `variant="danger"` for any delete/discard button, `variant="success"` for confirm/plant). Keep each button's `.pack()/.grid()` call and any attribute assignment (`self.some_btn = ...`). Work one button at a time; after each, run the app and open the Inventory window to confirm it still functions.

- [ ] **Step 3: Frame the dialog body as a panel card (optional but included)**

Where the Inventory window builds its outermost content frame, set its background to `theme.PANEL_BG` and add a header label using `theme.DISPLAY_FONT`. (Full panel-card image backgrounds are best applied to fixed-size sub-panels; for the resizable list, applying the parchment `bg` + wood header band via `tk.Frame(bg=theme.WOOD_MID)` is sufficient and avoids image-resize churn.) Add a wood-colored header strip:

```python
        header = tk.Frame(self, bg=theme.WOOD_MID, height=40)
        header.pack(fill="x")
        tk.Label(header, text="Inventory", bg=theme.WOOD_MID, fg=theme.TEXT_LIGHT,
                 font=(theme.DISPLAY_FONT, 16, "bold")).pack(side="left", padx=14, pady=8)
```

(Adapt `self`/parent to the actual dialog class; place before the existing body packs.)

- [ ] **Step 4: Verify — open Inventory in the live app**

Launch, open the Inventory window, exercise its buttons (plant/discard/close).
Expected: pill buttons + wood header; all actions behave as before. No traceback.

- [ ] **Step 5: Commit**

```bash
git add inventory.py
git commit -m "feat(ui): restyle Inventory popup with pill buttons + header"
```

---

## Task 11: Mendel's Law Wizard popup → card + pill buttons

**Files:**
- Modify: `mendelian_law_wizard.py` — 10 `tk.Button` + 5 `ttk.Button` sites, `apply_window_options` call (`:157`).

**Interfaces:**
- Consumes: `widgets.make_button`.

- [ ] **Step 1: Add a local pill helper**

Near the top of the wizard's dialog class module (after imports), add:

```python
def _wiz_pill(parent, text, command, variant="wood"):
    from garden_of_inheritance import widgets
    return widgets.make_button(parent, text=text, command=command, variant=variant,
                               height=36, font_size=12)
```

- [ ] **Step 2: Convert nav + action buttons**

Replace each `tk.Button(...)` and `ttk.Button(...)` used for navigation/actions (Next, Back, Confirm, Cancel, Close) with `_wiz_pill(...)`, mapping Confirm/Unlock → `success`, Cancel/Close → `muted`. Preserve `command`, text, and geometry calls. Convert one button at a time and re-open the wizard after each to confirm behavior.

- [ ] **Step 3: Verify — open the Law Wizard live**

Launch, open the wizard (Unlock button), step through pages, confirm/cancel.
Expected: pill buttons throughout; navigation and unlock flow unchanged. No traceback.

- [ ] **Step 4: Commit**

```bash
git add mendelian_law_wizard.py
git commit -m "feat(ui): restyle Mendel's Law Wizard with pill buttons"
```

---

## Task 12: Pollinate + Emasculation dialogs → pill buttons + header

**Files:**
- Modify: `pollination_dialog.py` (1 `tk.Button`, 1 `Canvas`), `emasculation_dialog.py` (1 `tk.Button`, 1 `Canvas`).

**Interfaces:**
- Consumes: `widgets.make_button`.

- [ ] **Step 1: Convert the confirm/close button in each dialog**

In `pollination_dialog.py`, replace the single `tk.Button(...)` with:

```python
        from garden_of_inheritance import widgets
        confirm_btn = widgets.make_button(parent, text=<existing text>, command=<existing command>,
                                          variant="success", height=36, font_size=12)
```

Keep the button's existing `.pack()/.grid()` and any variable it was assigned to. Do the same in `emasculation_dialog.py` (variant `"danger"` if the action is destructive, else `"success"`). Substitute `<existing text>`/`<existing command>`/`parent` with the real values at the site.

- [ ] **Step 2: Add a wood header strip to each dialog**

At the top of each dialog's body construction, add a header matching Task 10 Step 3 (title text = "Pollinate" / "Emasculate", parent = the dialog frame).

- [ ] **Step 3: Verify — trigger both dialogs live**

Launch; select a flower, open Pollinate; open Emasculation.
Expected: header + pill confirm button; the pollinate/emasculate actions still work. No traceback.

- [ ] **Step 4: Commit**

```bash
git add pollination_dialog.py emasculation_dialog.py
git commit -m "feat(ui): restyle Pollinate/Emasculation dialogs"
```

---

## Task 13: Full verification pass + docs

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: all green (existing `test_laws`, `test_persistence`, plus `test_widgets`; widget tests SKIP only if headless).

- [ ] **Step 2: Compile check**

Run: `python3 -m py_compile garden_of_inheritance/*.py tile.py inventory.py mendelian_law_wizard.py pollination_dialog.py emasculation_dialog.py garden_of_inheritance_legacy.py`
Expected: no output (success).

- [ ] **Step 3: Before/after screenshot sweep**

Using the manual verification block, capture the main window, Inventory, Law Wizard, and Pollinate dialog. Visually confirm: chips, pill buttons (with hover/press), law pills, tile gradient + selection glow, dialog headers. Save to `/tmp/goi_final_*.png` for the summary.

- [ ] **Step 4: Update README dependency note**

In `README.md`, under "Standard library modules", add a short subsection:

```markdown
## Third-party dependency
- Pillow (PIL) — used for icons, plant textures, and the polished UI toolkit.
  Install with: `python3 -m pip install pillow`
```

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: note Pillow dependency; game-polish UI complete"
```

---

## Self-Review Notes (author check)

- **Spec coverage:** chips (T6), pill buttons w/ states (T4, T7, T10–12), panel cards/headers (T5, T10, T12), garden depth + selection glow (T9), law pills (T8), theme stops (T1), tests (T2–T5), no-new-dependency + no-crash fallbacks (T2–T4 built in), README note (T13). Measure Temp intentionally excluded (Global Constraints).
- **Type consistency:** `make_button`/`PillButton`/`chip`/`law_pill`/`panel_card`/`rounded_grad`/`soft_shadow`/`glow_dot`/`_hx`/`SCALE` names are used consistently across tasks.
- **Anchors to confirm during implementation** (legacy file is large; line numbers may drift): the counter `.set()` site (T6 S3), pause/temp reconfigure sites, the real law-unlocked booleans (T8 S2), and tile width/height attribute names (T9 S2). Each such step says to confirm the real names on the spot rather than assume.
