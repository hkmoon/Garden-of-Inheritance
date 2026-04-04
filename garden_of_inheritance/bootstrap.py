"""Bootstrap and configuration helpers for the application."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path


def get_base_dir(anchor_file: str) -> Path:
    """Resolve the application base directory, handling frozen builds."""
    try:
        if getattr(sys, "frozen", False):
            return Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        return Path(os.path.dirname(os.path.abspath(anchor_file)))
    except Exception:
        return Path(os.getcwd())


def configure_logging(base_dir: Path) -> str:
    """Configure app logging if the root logger is still unconfigured."""
    log_path = os.path.join(str(base_dir), "pea_garden.log")
    if not logging.getLogger().handlers:
        logging.basicConfig(
            filename=log_path,
            filemode="a",
            level=logging.ERROR,
            format="%(asctime)s %(levelname)s %(message)s",
        )
    return log_path


def resource_path(base_dir: Path, *parts: str) -> Path:
    """Resolve a resource relative to the app base directory."""
    return base_dir.joinpath(*parts)


def grid_config_path(anchor_file: str) -> str:
    """Return the persisted grid-config path beside the launcher."""
    try:
        base = os.path.dirname(os.path.abspath(anchor_file))
    except Exception:
        base = os.getcwd()
    return os.path.join(base, "mendel_garden_config.json")


def load_grid_config(anchor_file: str, default_rows: int, default_cols: int):
    """Load persisted grid settings, returning ``None`` when unavailable."""
    path = grid_config_path(anchor_file)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            cfg = json.load(handle)
        rows = int(cfg.get("rows", default_rows))
        cols = int(cfg.get("cols", default_cols))
        if rows <= 0 or cols <= 0:
            raise ValueError
        show_dialog = bool(cfg.get("show_dialog", True))
        return {"rows": rows, "cols": cols, "show_dialog": show_dialog}
    except Exception:
        return None


def save_grid_config(anchor_file: str, rows: int, cols: int, show_dialog: bool) -> None:
    """Persist grid settings without letting config errors break the app."""
    path = grid_config_path(anchor_file)
    cfg = {"rows": int(rows), "cols": int(cols), "show_dialog": bool(show_dialog)}
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(cfg, handle)
    except Exception:
        pass

