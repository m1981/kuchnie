"""Shared fixtures for kitchen-cad tests."""

from __future__ import annotations

import pytest

from kitchen_cad.models import (
    CorpusSpec,
    DrawerSpec,
    HandleSpec,
    HingeSpec,
)


@pytest.fixture()
def base_door_spec() -> CorpusSpec:
    """Standard 800×720×510 base cabinet with one door and one shelf."""
    return CorpusSpec(
        id="K01",
        name="Szafka dolna drzwiowa 800",
        corpus_type="base_door",
        width=800,
        height=720,
        depth=510,
        panel_thickness=18,
        back_thickness=3,
        back_groove_depth=8,
        material_corpus="U119_VL",
        material_back="HDF_3mm_bialy",
        material_front="U119_EM",
        edge_material="ABS_0.8",
        shelves=[352],
        doors=[2],
        hinges=HingeSpec(count=2),
        handles=HandleSpec(),
    )


@pytest.fixture()
def base_drawer_spec() -> CorpusSpec:
    """Standard 800×720×510 base cabinet with two drawers."""
    return CorpusSpec(
        id="K02",
        name="Szafka dolna szufladowa 800",
        corpus_type="base_drawer",
        width=800,
        height=720,
        depth=510,
        panel_thickness=18,
        back_thickness=3,
        back_groove_depth=8,
        material_corpus="U119_VL",
        material_back="HDF_3mm_bialy",
        material_front="U119_EM",
        edge_material="ABS_0.8",
        drawers=[
            DrawerSpec(internal_height=150, runner_type="blum_metabox"),
            DrawerSpec(internal_height=270, runner_type="blum_metabox"),
        ],
        handles=HandleSpec(),
    )


@pytest.fixture()
def wall_door_spec() -> CorpusSpec:
    """Standard 800×720×300 wall cabinet with one door and one shelf."""
    return CorpusSpec(
        id="G01",
        name="Szafka wisząca drzwiowa 800",
        corpus_type="wall_door",
        width=800,
        height=720,
        depth=300,
        panel_thickness=18,
        back_thickness=3,
        back_groove_depth=8,
        material_corpus="U119_VL",
        material_back="HDF_3mm_bialy",
        material_front="U119_EM",
        edge_material="ABS_0.8",
        shelves=[352],
        doors=[2],
        hinges=HingeSpec(count=2),
    )
