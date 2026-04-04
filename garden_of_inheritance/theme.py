"""Shared cozy-farm theme values for the Tkinter UI."""

from __future__ import annotations

import sys


DISPLAY_FONT = "Georgia"
UI_FONT = "Trebuchet MS"

APP_BG = "#76b55a"
FIELD_BG = "#7fb95f"
FIELD_EDGE = "#5d8a3f"

PANEL_BG = "#f2dfb2"
PANEL_ALT = "#ead09a"
PANEL_ACCENT = "#d8b06f"
PANEL_BORDER = "#8b5a2b"

WOOD_DARK = "#6b3f1f"
WOOD_MID = "#a66a39"
WOOD_LIGHT = "#cc9152"

TEXT_PRIMARY = "#3f2715"
TEXT_MUTED = "#7a5c3b"
TEXT_LIGHT = "#fff8eb"

BUTTON_BG = "#b87940"
BUTTON_HOVER = "#cf9554"
BUTTON_ACTIVE = "#dca765"
BUTTON_FG = "#fff7e7"
BUTTON_TEXT_FG = TEXT_PRIMARY if sys.platform == "darwin" else BUTTON_FG
BUTTON_SUCCESS_BG = "#6f8d46"
BUTTON_SUCCESS_HOVER = "#87a85a"
BUTTON_DANGER_BG = "#9d4936"
BUTTON_DANGER_HOVER = "#b65c47"
ENTRY_BG = "#fff7e6"
LISTBOX_BG = "#fff8ea"

STATUS_BG = "#f7edd2"
STATUS_BORDER = "#9b7144"

PHASE_BG = "#d6ecf9"
PHASE_FG = "#24405a"

LAW_BG = "#f5e2ba"
SELECTION_GOLD = "#f1c564"

TILE_GRASS_TOP = "#8fcf68"
TILE_GRASS_SHADE = "#5f9440"
TILE_SOIL_EDGE = "#8b5a2b"
TILE_SOIL_FURROW = "#8f5a32"
TILE_LABEL_BG = "#f6e4b7"
TILE_LABEL_FG = "#4a2d18"
TILE_BADGE_EDGE = "#4b2c18"

SOIL_COLORS = [
    "#9c6a39",
    "#a26d3f",
    "#8f6032",
    "#b07a43",
    "#986638",
    "#b78349",
    "#8a5a30",
    "#a8743e",
    "#946437",
]

HEALTH_LOW = (169, 72, 50)
HEALTH_MID = (225, 180, 90)
HEALTH_HIGH = (111, 165, 89)

WATER_LIGHT = (130, 194, 225)
WATER_DARK = (58, 121, 172)

BROWSER_BG = "#bfe0f1"
BROWSER_PANEL = "#f0dfb4"
BROWSER_CARD = "#e7c98d"
BROWSER_FG = TEXT_PRIMARY
BROWSER_MUTED = TEXT_MUTED
BROWSER_ACCENT = "#7b4b24"
BROWSER_BORDER = PANEL_BORDER
BROWSER_CANVAS_BG = "#d8ecf7"
BROWSER_TAB_BG = "#d7bb80"
BROWSER_TAB_ACTIVE = "#c9914f"
BROWSER_TAB_SELECTED = PHASE_BG
BROWSER_TAB_SELECTED_FG = PHASE_FG
BROWSER_WARNING = "#a45a2a"
BROWSER_DANGER = "#8f3825"
BROWSER_SUCCESS = "#668542"
BROWSER_ALT_ROW = "#f5e6bf"
BROWSER_STRIP = "#d8be8a"
BROWSER_EMPHASIS = "#9e6b2d"
POD_TINT_GREEN = "#b6cf95"
POD_TINT_YELLOW = "#d8c57b"


def font_spec(family: str, size: int, *styles: str) -> str:
    """Return a Tcl-safe font spec for Tk options that parse raw strings."""
    parts = [f"{{{family}}}", str(size)]
    parts.extend(str(style) for style in styles if style)
    return " ".join(parts)


def apply_window_options(widget) -> None:
    """Seed Tk option defaults for warm parchment/wood UI surfaces."""
    widget.option_add("*Font", font_spec(UI_FONT, 10))
    widget.option_add("*Label.Font", font_spec(UI_FONT, 10))
    widget.option_add("*Label.Foreground", TEXT_PRIMARY)
    widget.option_add("*Frame.Background", PANEL_BG)
    widget.option_add("*Label.Background", PANEL_BG)
    widget.option_add("*Button.Font", font_spec(UI_FONT, 10, "bold"))
    widget.option_add("*Button.Background", BUTTON_BG)
    widget.option_add("*Button.Foreground", BUTTON_TEXT_FG)
    widget.option_add("*Button.ActiveBackground", BUTTON_HOVER)
    widget.option_add("*Button.ActiveForeground", BUTTON_TEXT_FG)
    widget.option_add("*Entry.Background", ENTRY_BG)
    widget.option_add("*Entry.Foreground", TEXT_PRIMARY)
    widget.option_add("*Listbox.Background", LISTBOX_BG)
    widget.option_add("*Listbox.Foreground", TEXT_PRIMARY)
    widget.option_add("*Checkbutton.Background", PANEL_BG)
    widget.option_add("*Checkbutton.Foreground", TEXT_PRIMARY)
    widget.option_add("*Radiobutton.Background", PANEL_BG)
    widget.option_add("*Radiobutton.Foreground", TEXT_PRIMARY)
    widget.option_add("*Menu.Font", font_spec(UI_FONT, 11))
