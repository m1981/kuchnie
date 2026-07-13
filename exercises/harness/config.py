"""Environment-configurable paths — the harness's single source of location.

Every machine-specific location lives here, overridable by environment so a
second machine or CI only sets variables instead of editing code:

  KUCHNIE_HB5_PATH   home_builder_5 checkout (default: sibling of this repo)
  BLENDER_BIN        Blender executable (same variable the hb5 inspection
                     harness honours)
  KUCHNIE_STRICT     "1" -> GapLog failures raise instead of being recorded
"""
from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def repo_root() -> Path:
    """The kuchnie repo root (derived, never configured)."""
    return Path(__file__).resolve().parents[2]


def hb5_path() -> Path:
    """home_builder_5 checkout."""
    env = os.environ.get("KUCHNIE_HB5_PATH")
    if env:
        return Path(env)
    return repo_root().parent / "home_builder_5"


def hb5_parent() -> Path:
    """Directory to put on sys.path so `import home_builder_5` works."""
    return hb5_path().parent


def blender_bin() -> Path:
    return Path(os.environ.get("BLENDER_BIN", _DEFAULT_BLENDER))


def strict_mode() -> bool:
    return os.environ.get("KUCHNIE_STRICT") == "1"
