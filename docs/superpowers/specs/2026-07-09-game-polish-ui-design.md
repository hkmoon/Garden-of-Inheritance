# Game-Polish UI — Design

- **Date:** 2026-07-09
- **Status:** Approved (design), pending implementation plan
- **Branch:** codex/refactor

## Goal

Make the Garden of Inheritance Tkinter UI feel as polished and charming as the
reference web game at `/Users/moon/Projects/mac/game` — **without changing the
palette, mood, game logic, or save format.** We keep the existing daytime
parchment / wood / green look and add the game's *chrome quality*: rounded HUD
chips with softly glowing icons, pill buttons with real hover / press /
disabled states, soft-shadowed rounded panel cards, and garden tiles with depth
and a selection glow.

Direction and scope were chosen by the user:

- **Mood:** keep the current daytime garden tone; add game-level polish only.
  No night-farm recolor, no dynamic day/night tint.
- **Scope:** the **main garden window** plus the **frequently-used popups**
  (Inventory, Mendel's Law Wizard, Pollinate / Emasculation dialogs). Menus and
  the deeper secondary windows (Trait Explorer, History Archive Browser,
  Temperature Tracker) are out of scope for this pass.

A static mockup rendered with the real palette established the target look and
was approved before writing this spec.

## Why this approach

Tkinter's native widgets cannot render rounded corners, gradients, drop
shadows, or glow. Three options were considered:

1. **Refined native Tk/ttk only** — palette + spacing + hover colors. Lowest
   effort but cannot achieve the game's rounded/soft look; rejected.
2. **Full canvas rewrite of all chrome** — maximum control, far more code and
   bug surface than the polish warrants; rejected.
3. **Hybrid + Pillow-composited widgets (chosen)** — a small reusable toolkit
   renders the signature pieces as Pillow images placed on Tk canvases/labels;
   native widgets remain for menus and secondary-window form internals.

Pillow is **already a dependency** (used in `tile.py`, `icon_loader.py`,
`garden_of_inheritance_legacy.py`, `wildlife.py`, `traitinheritanceexplorer.py`;
version 10.4.0 present), so the toolkit adds **no new dependency**.

## Architecture

### New module: `garden_of_inheritance/widgets.py`

A presentational toolkit. All colors come from `theme.py` (extended with a few
gradient stops). All rendered images are cached by a key of
`(kind, size, state, palette-signature, scale)` so each variant is composited
once, not per frame or per redraw.

Rendering helpers (private):

- `rounded_grad(size, radius, top, bottom)` → `RGBA` with a vertical gradient
  clipped to a rounded-rectangle mask.
- `soft_shadow(size, radius, blur, alpha)` → blurred rounded silhouette +
  padding offset, for compositing behind a component.
- `glow_dot(diameter, inner, outer, glow)` → radial-ish icon dot with an outer
  Gaussian glow and a white specular highlight (the coin / firefly icon).
- Supersampling: render at `SCALE = 2` (auto-detected from Tk `scaling` where
  available) and downsample with `LANCZOS` for Retina crispness, mirroring the
  mockup.

Public API:

- `chip(text, *, icon=None, height=34, ...) -> PhotoImage` — dark rounded pill
  with optional glowing icon dot. Used for HUD counters and the date strip.
- `class PillButton(parent, text, command, *, variant="wood", state=..., ...)`
  — a Tk `Canvas` subclass that displays a cached pill image and swaps images
  on `<Enter>`, `<Leave>`, `<ButtonPress-1>`, `<ButtonRelease-1>`. Exposes a
  `command` callback and `config(state=...)` so it is a **drop-in replacement**
  for the current `tk.Button` call sites. Variants: `wood` (default),
  `success`, `danger`, `muted`. States: `normal`, `hover`, `pressed`,
  `disabled`.
- `panel_card(width, height, *, title=None) -> (PhotoImage, content_bbox)` —
  rounded parchment card with soft shadow, optional wood header band, and a
  content region for the caller to place native widgets or striped rows over.
- `law_pill(text, done) -> PhotoImage` — glossy-green ✓ pill when a law is
  unlocked, muted ○ pill when pending.

### `theme.py` additions

Add gradient stop pairs and state colors used by the toolkit (kept alongside the
existing flat colors so nothing changes for current consumers):

- `CHIP_BG`, `CHIP_BORDER`, `CHIP_TEXT`
- Icon gradients: `ICON_GOLD = (inner, outer, glow)`, `ICON_SEED`, etc.
- Button gradient stops per variant: `BTN_WOOD = (top, bottom, border)`,
  `BTN_SUCCESS`, `BTN_DANGER`, `BTN_MUTED`, and hover/pressed derivations.
- `PANEL_GRAD = (PANEL_BG, PANEL_ALT)`, `SHADOW_RGBA`.
- `TILE_SOIL_GRAD`, `SELECTION_GLOW` (reuse `SELECTION_GOLD`).

## Integration points

Main window (`garden_of_inheritance_legacy.py`, `tile.py`):

- **Top status strip** → `chip()` images on the existing header canvas:
  date/time/temp chip, Seeds chip (gold icon), Starter chip (seed icon).
  Replaces the flat pale-blue strip.
- **Sidebar action buttons** (Water, Inspect, Harvest seeds, Collect pollen,
  Pollinate, Remove plant, Genotype) → `PillButton` with variants
  (Pollinate = success, Remove plant = danger).
- **Toolbar row** (Observatory, Resume, FF, Next 1h, Plant, Water All, Measure
  Temp) → `PillButton`, wood variant.
- **Garden tiles** (`tile.py` canvas drawing) → soil gradient + furrow depth +
  gold selection glow on the active plot.
- **Mendelian-law tracker** → `law_pill()` images; keep the existing Unlock
  button as a `PillButton`.

Popups:

- **Inventory** (`inventory.py`) → `panel_card` framing + striped rows +
  `PillButton` actions.
- **Mendel's Law Wizard** (`mendelian_law_wizard.py`) → card framing +
  `PillButton` navigation.
- **Pollinate / Emasculation dialogs** (`pollination_dialog.py`,
  `emasculation_dialog.py`) → card framing + `PillButton` confirm/cancel.

Native `tk.Button` sites are swapped **one at a time**, verifying identical
behavior (command, enable/disable) after each swap.

## Data flow & performance

- Toolkit functions are pure: palette + geometry in, `PhotoImage` out. No game
  state flows through the toolkit.
- Image cache keyed as above; buttons hold references to their state images to
  prevent Tk garbage-collection of `PhotoImage`s (a classic Tk pitfall — the
  toolkit keeps a module-level and per-widget reference).
- Redraws swap cached images (cheap); no per-frame compositing. Garden tile
  images are cached per visual variant exactly as today.

## Constraints & safety

- **No new dependency** (Pillow already present; graceful behavior if a font is
  missing — fall back to a default font, never crash).
- **Purely presentational**: save format, serialization, and Mendelian logic
  are untouched.
- Public method names / callbacks on `GardenApp` and dialogs are preserved.
- If image compositing ever fails, `PillButton` falls back to a styled native
  `tk.Button` so the app never breaks on a rendering error.

## Testing

- `tests/test_widgets.py` (headless-friendly, no Tk root required for the image
  helpers):
  - each toolkit function returns a non-empty `RGBA` image of the requested
    size at every state/variant;
  - the cache returns the identical object for identical keys and distinct
    objects for distinct keys;
  - missing-font path falls back without raising.
- Manual before/after screenshot pass (via the launch-and-capture method used
  during design) on: main window, Inventory, Law Wizard, Pollinate dialog.
- Existing suite (`python3 -m unittest discover`) must stay green.

## Out of scope (future passes)

- Trait Inheritance Explorer, History Archive Browser, Temperature Tracker
  restyle.
- Dynamic day/night background tint (the app already tracks in-game time and a
  moon/sun glyph, so this is a natural follow-up if wanted).
- Menu bar restyle.

## Risks & mitigations

- **macOS Tk button color quirks** → sidestepped by using Canvas-based
  `PillButton` images rather than fighting native aqua buttons.
- **PhotoImage GC** → explicit reference retention in the toolkit and widgets.
- **Retina blur** → supersampled render + LANCZOS downsample.
- **Behavioral drift when swapping buttons** → one-at-a-time swaps with a
  behavior check after each.
