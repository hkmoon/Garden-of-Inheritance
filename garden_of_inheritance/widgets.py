"""Pillow-backed UI toolkit: game-polish chrome for the Tkinter UI.

Presentational only. Never raises on render — falls back gracefully so the app
always launches. All colors come from `theme`.
"""
from __future__ import annotations

import os

import tkinter as tk

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

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
            dx = int(x - ds)
            dy = int(h // 2 - dot.size[1] // 2)
            # Clamp destination to >=0; shift any negative offset into the
            # source crop so alpha_composite never gets negative coords.
            img.alpha_composite(dot, (max(0, dx), max(0, dy)),
                                (max(0, -dx), max(0, -dy)))
            x += ds + 8 * SCALE
        _, _, bb = _text_size(d, text, font)
        d.text((x, (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font, fill=_hx(theme.CHIP_TEXT))
        img = img.resize((max(1, img.width // SCALE), max(1, img.height // SCALE)), Image.LANCZOS)
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
        img = img.resize((max(1, img.width // SCALE), max(1, img.height // SCALE)), Image.LANCZOS)
        return img

    return _cache_get(key, build)


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
        d.text((tx, (h - (bb[3] - bb[1])) / 2 - bb[1]), text, font=font, fill=tcol)
        img = img.resize((max(1, img.width // SCALE), max(1, img.height // SCALE)), Image.LANCZOS)
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
        self._min_width = min_width
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
            # delete("all") destroyed the image item; recreate it so a later
            # successful render can reuse a live id.
            self._img_item = self.create_image(0, 0, anchor="nw")
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
            neww = _measure_pill_width(self._text, self._font_size, self._icon_path, self._min_width, self._height)
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
