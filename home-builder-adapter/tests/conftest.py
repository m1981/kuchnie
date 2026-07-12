"""Test scaffolding for the adapter — a fake ``bpy`` good enough for the ACL.

``src.extract`` imports ``bpy`` at module import time, so the fake must be
installed in ``sys.modules`` BEFORE any test module imports ``src.*``.
Only the surface the adapter actually touches is faked:

  * ``bpy.data.objects``            — iterable of scene objects
  * ``obj.get(key, default)``       — custom-property access
  * ``obj.children``                — child objects (shelf counting)
  * ``bpy.ops.wm.open_mainfile``    — .blend loading (recorded, not executed)

Also puts the sibling ``kuchnie-core`` sources on sys.path (dev-time-only
dependency, same pattern as kuchnie-core's own catalog contract test).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "kuchnie-core" / "src"))


class FakeBlenderObject:
    """Mimics a Blender Object: custom props via .get(), .children, and the
    evaluated bounding-box .dimensions (the real hb5 dimension carrier)."""

    def __init__(self, props: dict | None = None, children: list | None = None,
                 dimensions: tuple | None = None):
        self._props = dict(props or {})
        self.children = list(children or [])
        if dimensions is not None:
            self.dimensions = dimensions

    def get(self, key, default=None):
        return self._props.get(key, default)


def _install_fake_bpy() -> types.ModuleType:
    bpy = types.ModuleType("bpy")

    bpy.data = types.SimpleNamespace(objects=[])

    opened: list[str] = []

    def open_mainfile(filepath: str = ""):
        opened.append(filepath)

    bpy.ops = types.SimpleNamespace(
        wm=types.SimpleNamespace(open_mainfile=open_mainfile)
    )
    bpy._opened_mainfiles = opened  # test hook

    sys.modules["bpy"] = bpy
    return bpy


_BPY = _install_fake_bpy()


@pytest.fixture()
def fake_bpy():
    """Fresh fake-bpy state per test."""
    _BPY.data.objects = []
    _BPY._opened_mainfiles.clear()
    return _BPY


@pytest.fixture()
def base_cabinet_cage():
    """A home_builder_5 BASE cabinet cage: 600×720×560 mm, 100 mm toe kick,
    two drawer openings (176 mm and 320 mm). Dimensions in METERS, as
    home_builder_5 stores them."""
    return FakeBlenderObject(props={
        "IS_FRAMELESS_CABINET_CAGE": True,
        "CABINET_TYPE": "BASE",
        "Dim X": 0.6,
        "Dim Y": 0.56,
        "Dim Z": 0.72,
        "Toe Kick Height": 0.1,
        "opening_sizes": [0.176, 0.32],
    })
