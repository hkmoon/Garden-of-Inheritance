"""Loader for the Stardew-style field textures in icons/textures/.

Feeds tile.py's dormant texture pipeline: ``_try_set_bg_image()`` renders from
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
