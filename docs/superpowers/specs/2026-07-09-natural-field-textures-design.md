# Natural Field Textures (Stardew-style) — Design

- **Date:** 2026-07-09
- **Status:** Approved (design), pending implementation plan
- **Branch:** codex/refactor

## Goal

Make the garden read as one natural field — a grass meadow with rounded tilled-soil
patches where plants grow — instead of the current grid of flat brown boxes with
green gutters. Reference feel: Stardew Valley.

User decisions:
- **Empty tiles show grass**; tilled soil appears only where a plant lives (or
  briefly lingers after removal) — the texture pipeline's native behavior.
- **Tiles are fully contiguous** (no 2px gutters) so the grass reads as one field.

## Key discovery

The repo already contains both halves of this feature, disconnected:

- `icons/textures/` holds 46 pixel-art textures (85×85): 9 grass variants × 4
  seasons, 2 soil-patch variants × 4 seasons (rounded organic patches), winter/snow
  sets.
- `tile.py` has a complete, dormant rendering pipeline:
  `_try_set_bg_image()` (tile.py:744) renders from `app._bg_pil_images` keyed by
  `(mode, season, variant, lighting_bucket)`, with per-tile seeded variant
  selection, winter→autumn base fallback, snow blending, and PhotoImage caching.
  `set_soil_color` (tile.py:697) already routes through it and falls back to flat
  colors when textures are absent.
- **Nothing ever populates `app._bg_pil_images`** — so the pipeline never runs.

The design is therefore: load the textures, feed the pipeline, remove the gutters.

## Architecture

### 1. New module: `garden_of_inheritance/field_textures.py`

One public function:

```python
def load_field_textures(tile_size: int) -> tuple[dict, int, int] | None
```

- Scans `icons/textures/` for files named `{grass|soil}_{season}{N}.png`
  (seasons: spring/summer/autumn/winter; N is 1-based).
- Resizes each to `(tile_size, tile_size)` with LANCZOS.
- Returns `(pil_imgs, n_grass_variants, n_soil_variants)` where `pil_imgs` maps
  `(mode, season, N-1, 100)` → PIL Image (bucket fixed at 100 = full daylight,
  matching `TileCanvas._lighting_bucket`'s default).
- Returns `None` on any failure (missing dir, unreadable file set, PIL error).
  Never raises.

### 2. App hookup (`garden_of_inheritance_legacy.py`)

At startup (after tiles are created), call the loader; on success set
`self._bg_pil_images`, `self._bg_grass_variants`, `self._bg_soil_variants`, and
`self._bg_current_season`. On `None`, set nothing — every tile keeps today's flat
rendering (fallback preserved by the existing pipeline guard).

Season derivation: from the in-game month — 3–5 spring, 6–8 summer, 9–11 autumn,
12/1/2 winter. Set at startup and refresh whenever the month changes (hook the
existing daily/hourly update path; exact site chosen at plan time). The pipeline
itself handles winter (autumn base + snow only when snowing).

### 3. Contiguous field

`tile.grid(..., padx=2, pady=2)` → `padx=0, pady=0`
(garden_of_inheritance_legacy.py:2624). The `grid_frame`'s outer padding stays.

### 4. Explicitly unchanged

- Wave-3 flat soil gradient / grass strip / furrows stay in code as the fallback
  layer beneath `bg_img_item` (no removal).
- Selection gold glow, water/health bars, plant sprites, labels, badges, click
  bindings — all render above the texture and are untouched.
- No new dependency (Pillow already used); save format and game logic untouched.

## Testing

- `tests/test_field_textures.py`:
  - loader returns dict with expected key shape and counts (9 grass, 2 soil per
    available season), images sized `(tile_size, tile_size)`;
  - missing/empty textures dir → `None`, no exception.
- Manual: launch → spring grass meadow, contiguous; plant a starter seed → rounded
  tilled patch appears on that tile; selection glow visible on grass.
- Existing suite stays green.

## Out of scope (future)

- Day/night lighting buckets for textures (pipeline supports it; no bucket assets).
- Snow-cover driver (`set_snow_cover` callers) — snow stays dormant until wired.
- Restyling water/health bars or plant sprites.
