"""Thin package entrypoint that loads the legacy app module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_LEGACY_MODULE_NAME = "garden_of_inheritance_legacy"
_LEGACY_PATH = Path(__file__).resolve().parent.parent / "garden_of_inheritance_legacy.py"


def _load_legacy_module():
    existing = sys.modules.get(_LEGACY_MODULE_NAME)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load legacy app module from {_LEGACY_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_LEGACY_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_legacy = _load_legacy_module()

GardenApp = _legacy.GardenApp
main = _legacy.main

__all__ = ["GardenApp", "main"]
