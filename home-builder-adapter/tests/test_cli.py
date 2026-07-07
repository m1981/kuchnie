"""CLI seam: argv → open .blend → extract → Kitchen JSON on stdout.

Cold review: the docstring promised ``python -m ... path/to/scene.blend``
but main() never read argv and never opened anything — it silently used
whatever scene the interpreter happened to have. These tests pin the
promised behaviour, with the fake bpy recording open_mainfile calls.
"""

from __future__ import annotations

import json

import pytest

from src import cli


def test_blend_path_is_opened(fake_bpy, base_cabinet_cage, capsys):
    fake_bpy.data.objects = [base_cabinet_cage]
    cli.main(["scene.blend"])
    assert fake_bpy._opened_mainfiles == ["scene.blend"]


def test_blender_double_dash_argv_convention(fake_bpy, base_cabinet_cage, capsys):
    """Inside Blender, script args arrive after a ``--`` separator."""
    fake_bpy.data.objects = [base_cabinet_cage]
    cli.main(["--background", "--python", "x.py", "--", "kuchnia.blend"])
    assert fake_bpy._opened_mainfiles == ["kuchnia.blend"]


def test_no_path_uses_current_scene(fake_bpy, base_cabinet_cage, capsys):
    fake_bpy.data.objects = [base_cabinet_cage]
    cli.main([])
    assert fake_bpy._opened_mainfiles == []


def test_stdout_is_kitchen_json(fake_bpy, base_cabinet_cage, capsys):
    fake_bpy.data.objects = [base_cabinet_cage]
    cli.main([])
    data = json.loads(capsys.readouterr().out)
    assert data["rows"][0]["cabinets"][0]["width_mm"] == 600


def test_empty_scene_exits_nonzero(fake_bpy, capsys):
    fake_bpy.data.objects = []
    with pytest.raises(SystemExit) as exc:
        cli.main([])
    assert exc.value.code == 1
