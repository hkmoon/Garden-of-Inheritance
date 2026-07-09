# Natural Field Textures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate the dormant field-texture pipeline so the garden renders as a contiguous Stardew-style grass meadow with rounded tilled-soil patches where plants grow.

**Architecture:** A new loader module (`garden_of_inheritance/field_textures.py`) reads the 46 existing pixel-art PNGs from `icons/textures/` into the dict format `tile.py`'s dormant `_try_set_bg_image()` pipeline already expects (`app._bg_pil_images` keyed `(mode, season, variant, 100)`). The legacy app loads them once at startup, refreshes `_bg_current_season` from the game month in `render_all`, and `tile.render()` gains one cheap texture-refresh call. Tile gutters go to 0 so grass tiles merge into one field. Load failure leaves all attributes unset → the existing flat-color rendering runs unchanged.

**Tech Stack:** Python 3, Tkinter, Pillow (existing dependency), `unittest`.

## Global Constraints

- **Commits are HELD** (session rule): do NOT run `git commit`/`git add`/any git state-changing command. Leave changes in the working tree; skip every "Commit" step.
- **No new dependency.** Pillow only.
- **Purely presentational.** No change to game logic, save format, plant/selection behavior.
- **Never crash on render.** Loader returns `None` on any failure and never raises; app hookup is wrapped so a loader failure leaves today's flat rendering intact.
- **Do not modify** `_try_set_bg_image`, `_find_base_image`, or the snow code in `tile.py` — the pipeline is correct; we only feed it (one added call in `render()` aside).
- Run everything from `/Users/moon/Projects/Python/Garden-of-Inheritance`.
- Test command: `python3 -m unittest discover -s tests -v` (currently 23 tests; must stay green).

## Verified anchors (real names/lines; line numbers may drift slightly)

- `TILE_SIZE = 85` at `garden_of_inheritance_legacy.py:436`; textures are 85×85 (resize is a safety net for the 64/128 comment).
- Tiles are square: `tile.py:43-44` (`self.w = configs['TILE_SIZE']; self.h = self.w`).
- Tile creation loop: `garden_of_inheritance_legacy.py:2617-2626`; gutter at `:2624` (`padx=2, pady=2`).
- `render_all` starts at `garden_of_inheritance_legacy.py:2780`; tile loop at `:2824-2833`.
- `tile.render()` defined at `tile.py:458`. Texture refresh currently only happens via `set_soil_color` (`tile.py:711`), which is NOT called every frame → the render() hook in Task 2 is required.
- Pipeline reads: `app._bg_pil_images` (dict `(mode, season, vi, bucket)` → PIL image), `app._bg_grass_variants`, `app._bg_soil_variants`, `app._bg_current_season`; `TileCanvas._lighting_bucket` defaults to `100` (`tile.py:158`).
- Texture files: `icons/textures/{grass|soil}_{spring|summer|autumn|winter}{N}.png`, N is 1-based; `*_old.png` files exist and must be ignored.
- `icon_loader.ICONS_DIR` is the canonical icons base path in the legacy app.

---

## Task 1: Loader module `field_textures.py` (TDD)

**Files:**
- Create: `garden_of_inheritance/field_textures.py`
- Test: `tests/test_field_textures.py`

**Interfaces:**
- Produces:
  - `load_field_textures(tile_size: int, textures_dir: str) -> tuple | None` — returns `(pil_imgs, n_grass_variants, n_soil_variants)`; `pil_imgs` maps `(mode, season, vi, 100)` → `PIL.Image` sized `(tile_size, tile_size)`; returns `None` if the dir is missing/empty/unreadable. Never raises.
  - `season_for_month(month: int) -> str` — 3–5 `'spring'`, 6–8 `'summer'`, 9–11 `'autumn'`, else `'winter'` (invalid input → `'spring'`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_field_textures.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_field_textures -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'garden_of_inheritance.field_textures'`.

- [ ] **Step 3: Write the implementation**

Create `garden_of_inheritance/field_textures.py`:

```python
"""Loader for the Stardew-style field textures in icons/textures/.

Feeds tile.py's dormant texture pipeline: `_try_set_bg_image()` renders from
``app._bg_pil_images`` keyed ``(mode, season, variant, lighting_bucket)``.
This module only builds that dict — it never touches Tk and never raises.
"""
from __future__ import annotations

import os
import re

from PIL import Image

SEASONS = ("spring", "summer", "autumn", "winter")
_LIGHTING_BUCKET = 100  # full daylight; matches TileCanvas._lighting_bucket default

_NAME_RE = re.compile(r"^(grass|soil)_(spring|summer|autumn|winter)(\d+)\.png$")


def season_for_month(month) -> str:
    """Map a calendar month to a texture season; invalid input → 'spring'."""
    try:
        m = int(month)
    except (TypeError, ValueError):
        return "spring"
    if 3 <= m <= 5:
        return "spring"
    if 6 <= m <= 8:
        return "summer"
    if 9 <= m <= 11:
        return "autumn"
    if m == 12 or 1 <= m <= 2:
        return "winter"
    return "spring"


def load_field_textures(tile_size, textures_dir):
    """Load grass/soil seasonal textures for the tile background pipeline.

    Returns ``(pil_imgs, n_grass_variants, n_soil_variants)`` where
    ``pil_imgs[(mode, season, variant_index, 100)]`` is a PIL image sized
    ``(tile_size, tile_size)``. Returns ``None`` if nothing usable is found.
    Never raises.
    """
    try:
        size = int(tile_size)
        if size <= 0 or not os.path.isdir(textures_dir):
            return None

        pil_imgs = {}
        n_variants = {"grass": 0, "soil": 0}
        for fname in sorted(os.listdir(textures_dir)):
            m = _NAME_RE.match(fname)
            if not m:
                continue  # skips *_old.png and anything unexpected
            mode, season, num = m.group(1), m.group(2), int(m.group(3))
            if num < 1:
                continue
            try:
                img = Image.open(os.path.join(textures_dir, fname)).convert("RGBA")
                if img.size != (size, size):
                    img = img.resize((size, size), Image.LANCZOS)
            except Exception:
                continue  # one bad file must not kill the field
            vi = num - 1
            pil_imgs[(mode, season, vi, _LIGHTING_BUCKET)] = img
            n_variants[mode] = max(n_variants[mode], num)

        if not pil_imgs:
            return None
        return pil_imgs, max(1, n_variants["grass"]), max(1, n_variants["soil"])
    except Exception:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_field_textures -v`
Expected: PASS (6 tests).

Also run the full suite: `python3 -m unittest discover -s tests -v` → 29 tests, all OK.

- [ ] **Step 5: Commit — SKIPPED (commits held per Global Constraints)**

---

## Task 2: Wire the pipeline into the app

**Files:**
- Modify: `tile.py:458` (top of `render()`)
- Modify: `garden_of_inheritance_legacy.py` — import (~:109), tile-creation loop end (~:2626), `render_all` top (~:2780), gutter (~:2624)

**Interfaces:**
- Consumes: `field_textures.load_field_textures(tile_size, textures_dir)`, `field_textures.season_for_month(month)` from Task 1; existing `icon_loader.ICONS_DIR`, `TILE_SIZE`.
- Produces: `self._bg_pil_images`, `self._bg_grass_variants`, `self._bg_soil_variants`, `self._bg_current_season` on the app — the names `tile.py:763-788` already reads.

- [ ] **Step 1: Texture refresh in `tile.render()`**

At `tile.py:458`, make the first statement of `render()` a pipeline refresh (it early-exits on unchanged key, so this is ~free per frame; it returns False and never raises when textures are absent):

```python
    def render(self):
        # Refresh the field texture first (no-op when textures are not loaded
        # or the (mode, season, variant, snow) key is unchanged).
        self._try_set_bg_image()
```

Keep the rest of `render()` exactly as is.

- [ ] **Step 2: Import in the legacy app**

Next to the existing `from garden_of_inheritance import widgets` (~`garden_of_inheritance_legacy.py:109`), add:

```python
from garden_of_inheritance import field_textures
```

- [ ] **Step 3: Load textures at startup**

Immediately AFTER the tile-creation loop ends (`:2617-2626`, after `self.tiles.append(tile)`'s loop closes), insert:

```python
        # Activate the Stardew-style field texture pipeline. On any failure
        # the attributes stay unset and tiles keep the flat-color fallback.
        try:
            _loaded = field_textures.load_field_textures(
                TILE_SIZE, os.path.join(icon_loader.ICONS_DIR, "textures"))
            if _loaded:
                (self._bg_pil_images,
                 self._bg_grass_variants,
                 self._bg_soil_variants) = _loaded
                self._bg_current_season = field_textures.season_for_month(
                    getattr(self.garden, "month", 4))
        except Exception:
            pass
```

- [ ] **Step 4: Refresh season in `render_all`**

At the very top of `render_all` (`:2780`, first lines of the method body), insert:

```python
        # Keep the texture season in sync with the sim calendar (cheap: the
        # per-tile pipeline early-exits when the season key is unchanged).
        if getattr(self, "_bg_pil_images", None):
            self._bg_current_season = field_textures.season_for_month(
                getattr(self.garden, "month", 4))
```

- [ ] **Step 5: Contiguous field**

At `:2624` change:

```python
            tile.grid(row=idx // TILES_PER_ROW, column=idx % TILES_PER_ROW, padx=2, pady=2)
```

to:

```python
            tile.grid(row=idx // TILES_PER_ROW, column=idx % TILES_PER_ROW, padx=0, pady=0)
```

- [ ] **Step 6: Verify**

1. `python3 -m py_compile tile.py garden_of_inheritance_legacy.py garden_of_inheritance/field_textures.py` → clean.
2. `python3 -m unittest discover -s tests -v` → 29 OK.
3. Launch smoke + screenshot (raise window via osascript as in prior waves; capture `/tmp/goi_field.png`): expect a contiguous grass meadow (no green gutters, no brown boxes), tiles varying subtly; no traceback in the launch log.

- [ ] **Step 7: Commit — SKIPPED (commits held per Global Constraints)**

---

## Task 3: End-to-end visual verification

**Files:** none modified (verification only).

- [ ] **Step 1: Full suite + compile**

`python3 -m unittest discover -s tests -v` → 29 OK; py_compile on the three touched files → clean.

- [ ] **Step 2: Live checks**

Launch the app, raise the window, then verify each and screenshot:
1. Empty field = contiguous grass meadow (spring textures for April 1856).
2. Click a tile → gold selection glow visible on grass.
3. Plant a starter seed (Plant button → select tile) → that tile switches to the rounded tilled-soil patch; neighbors stay grass.
4. Remove the plant → after the linger window the tile returns to grass (or verify the soil patch remains during linger).
5. No traceback in the launch log.

- [ ] **Step 3: Report**

Summarize screenshots + results; leave changes uncommitted for user review.

---

## Self-Review Notes

- Spec coverage: loader (T1), season mapping (T1), app hookup + season refresh + render hook + contiguous grid (T2), fallback preservation (loader None-contract + try/except hookup), tests (T1), manual verification (T2/T3). "Explicitly unchanged" items need no task.
- Type consistency: `load_field_textures(tile_size, textures_dir)` and `season_for_month(month)` used identically in T1/T2; pipeline attr names match `tile.py:763-788` verbatim.
- Known drift risk: legacy line numbers (~2617-2830) may shift; anchors are described structurally (after tile loop, top of render_all) so the implementer can relocate.
