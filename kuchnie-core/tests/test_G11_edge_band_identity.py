"""G11: Edge-band identity by thickness.

Proves:
  1. EdgeBand carries catalog_edge_code for ordering
  2. BOM groups by (material_type, thickness_mm) not just material
  3. Edging CSV includes catalog edge code column
  4. Edge bands with different thicknesses produce separate BOM lines
  5. Edge bands with different catalog codes produce separate BOM lines
  6. EdgeBand carries an optional purchase-identity width_mm; BOM groups
     by width when known (supplier/decor-dependent — never derived by core)
  7. Real decompositions (via the loader + decomposer, not hand-built
     fixtures) actually emit distinct corpus (0.8mm) vs front (2.0mm)
     edge-band thicknesses end-to-end

Gap: G11 (edge-band identity by thickness)
Spec: docs/specs/purchasing-variants.md § "G11 edging-by-thickness"
"""

import pytest
from pathlib import Path

from kuchnie_core.model import (
    EdgeBand,
    Panel,
    PanelRole,
    CabinetInstance,
    DecompositionResult,
    Accessory,
)
from kuchnie_core.bom import calculate_bom, BOMItem
from kuchnie_core.export.edging_csv import collect_edging_rows, rows_to_csv, HEADER
from kuchnie_core.loader import load_cabinet
from kuchnie_core.decomposer import decompose

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ── EdgeBand model ──────────────────────────────────────────────


def test_edge_band_has_catalog_edge_code():
    """EdgeBand carries optional catalog_edge_code for ordering."""
    band = EdgeBand(
        material="ABS_swiss_krono.U119_VL",
        thickness_mm=0.8,
        length_mm=500,
        catalog_edge_code="K-8685-SM/BS/PD",
    )
    assert band.catalog_edge_code == "K-8685-SM/BS/PD"


def test_edge_band_catalog_edge_code_defaults_to_empty():
    """catalog_edge_code defaults to empty string (backward compat)."""
    band = EdgeBand(
        material="ABS_swiss_krono.U119_VL",
        thickness_mm=0.8,
        length_mm=500,
    )
    assert band.catalog_edge_code == ""


def test_edge_band_equality_includes_catalog_edge_code():
    """Two EdgeBands with different catalog codes are not equal."""
    band1 = EdgeBand(
        material="ABS_swiss_krono.U119_VL",
        thickness_mm=0.8,
        length_mm=500,
        catalog_edge_code="K-8685-SM/BS/PD",
    )
    band2 = EdgeBand(
        material="ABS_swiss_krono.U119_VL",
        thickness_mm=0.8,
        length_mm=500,
        catalog_edge_code="K-9999-OTHER",
    )
    assert band1 != band2


# ── BOM grouping by thickness ───────────────────────────────────


def _panel_with_edges(
    panel_id: str,
    material: str,
    edges: dict[str, EdgeBand],
) -> Panel:
    """Helper: create a panel with specified edge bands."""
    return Panel(
        id=panel_id,
        name=f"Panel {panel_id}",
        material=material,
        thickness_mm=18,
        width_mm=500,
        height_mm=700,
        banded_edges=edges,
        role=PanelRole.LEFT_SIDE,
    )


def _bom_edge_lines(bom_items: list[BOMItem]) -> list[BOMItem]:
    """Filter BOM items to edge_band category only."""
    return [item for item in bom_items if item.category == "edge_band"]


def test_bom_groups_by_thickness():
    """Edge bands with different thicknesses produce separate BOM lines."""
    # Panel with 0.8mm carcass edge and 2.0mm front edge
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=2.0,
                length_mm=500,
            ),
            "back": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
            ),
        },
    )
    result = DecompositionResult(
        cabinet_id="test",
        cabinet_type="test",
        panels=[panel],
    )
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    # Should have 2 separate lines (one per thickness)
    assert len(edge_lines) == 2

    # Verify different materials (thickness encoded in material)
    materials = {item.material for item in edge_lines}
    assert len(materials) == 2


def test_bom_groups_by_catalog_edge_code():
    """Edge bands with different catalog codes produce separate BOM lines."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-8685-SM/BS/PD",
            ),
            "back": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-9999-OTHER",
            ),
        },
    )
    result = DecompositionResult(
        cabinet_id="test",
        cabinet_type="test",
        panels=[panel],
    )
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    # Should have 2 separate lines (one per catalog code)
    assert len(edge_lines) == 2

    # Verify different materials (catalog code encoded in material)
    materials = {item.material for item in edge_lines}
    assert len(materials) == 2


def test_bom_same_thickness_same_code_same_material_key():
    """Edge bands with same thickness and code produce same material key."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-8685-SM/BS/PD",
            ),
            "back": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-8685-SM/BS/PD",
            ),
        },
    )
    result = DecompositionResult(
        cabinet_id="test",
        cabinet_type="test",
        panels=[panel],
    )
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    # Should have 2 lines (one per edge - BOM doesn't aggregate)
    assert len(edge_lines) == 2
    # Both should have the same material key (for downstream aggregation)
    assert edge_lines[0].material == edge_lines[1].material
    # Material key should include thickness and catalog code
    assert "0.8" in edge_lines[0].material
    assert "K-8685-SM/BS/PD" in edge_lines[0].material


# ── Edging CSV ──────────────────────────────────────────────────


def test_edging_row_has_catalog_edge_code():
    """EdgingRow carries catalog_edge_code from EdgeBand."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-8685-SM/BS/PD",
            ),
        },
    )
    rows = collect_edging_rows([panel])
    assert len(rows) == 1
    assert rows[0].catalog_edge_code == "K-8685-SM/BS/PD"


def test_edging_row_catalog_edge_code_defaults_to_empty():
    """EdgingRow catalog_edge_code defaults to empty when not provided."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
            ),
        },
    )
    rows = collect_edging_rows([panel])
    assert len(rows) == 1
    assert rows[0].catalog_edge_code == ""


def test_edging_csv_includes_catalog_edge_code_column():
    """CSV header includes Kod_krawedzi column for ordering."""
    assert "Kod_krawedzi" in HEADER


def test_edging_csv_output_includes_catalog_edge_code():
    """CSV output includes catalog edge code when available."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-8685-SM/BS/PD",
            ),
        },
    )
    rows = collect_edging_rows([panel])
    csv_text = rows_to_csv(rows)

    # Should contain the catalog code
    assert "K-8685-SM/BS/PD" in csv_text

    # Verify column position (should be last column)
    lines = csv_text.strip().split("\n")
    header_cols = lines[0].split(";")
    data_cols = lines[1].split(";")

    code_col_idx = header_cols.index("Kod_krawedzi")
    assert data_cols[code_col_idx] == "K-8685-SM/BS/PD"


def test_edging_csv_output_empty_code_when_not_available():
    """CSV output includes empty string when catalog code not available."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
            ),
        },
    )
    rows = collect_edging_rows([panel])
    csv_text = rows_to_csv(rows)

    # Verify column position exists but is empty
    lines = csv_text.strip().split("\n")
    header_cols = lines[0].split(";")
    data_cols = lines[1].split(";")

    code_col_idx = header_cols.index("Kod_krawedzi")
    assert data_cols[code_col_idx] == ""


# ── BOM material key format ─────────────────────────────────────


def test_bom_material_key_includes_thickness():
    """BOM material key encodes thickness for ordering clarity."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=2.0,
                length_mm=500,
            ),
        },
    )
    result = DecompositionResult(
        cabinet_id="test",
        cabinet_type="test",
        panels=[panel],
    )
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    assert len(edge_lines) == 1
    # Material key should include thickness
    assert "2.0" in edge_lines[0].material


def test_bom_material_key_includes_catalog_code():
    """BOM material key encodes catalog code when available."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                catalog_edge_code="K-8685-SM/BS/PD",
            ),
        },
    )
    result = DecompositionResult(
        cabinet_id="test",
        cabinet_type="test",
        panels=[panel],
    )
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    assert len(edge_lines) == 1
    # Material key should include catalog code
    assert "K-8685-SM/BS/PD" in edge_lines[0].material


# ── Backward compatibility ──────────────────────────────────────


def test_edge_band_without_catalog_code_works():
    """Existing EdgeBand construction without catalog_edge_code still works."""
    band = EdgeBand(
        material="ABS_swiss_krono.U119_VL",
        thickness_mm=0.8,
        length_mm=500,
    )
    assert band.catalog_edge_code == ""
    assert band.material == "ABS_swiss_krono.U119_VL"


def test_bom_backward_compatible_material_key():
    """BOM material key is backward compatible when no catalog code."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
            ),
        },
    )
    result = DecompositionResult(
        cabinet_id="test",
        cabinet_type="test",
        panels=[panel],
    )
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    assert len(edge_lines) == 1
    # Material key should still include thickness (new behavior)
    # but without catalog code
    assert "0.8" in edge_lines[0].material
    assert "K-" not in edge_lines[0].material


# ── Width in purchase identity ──────────────────────────────────


def test_edge_band_width_mm_defaults_to_zero():
    """width_mm defaults to 0.0 ('unknown') — core never derives it."""
    band = EdgeBand(
        material="ABS_swiss_krono.U119_VL",
        thickness_mm=0.8,
        length_mm=500,
    )
    assert band.width_mm == 0.0


def test_bom_groups_by_width_when_known():
    """Same material+thickness but different purchase widths (e.g. Egger
    23mm vs Kronospan-partner 22mm for 18mm board) produce separate BOM
    lines."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                width_mm=23.0,
            ),
            "back": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                width_mm=22.0,
            ),
        },
    )
    result = DecompositionResult(cabinet_id="test", cabinet_type="test", panels=[panel])
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    assert len(edge_lines) == 2
    materials = {item.material for item in edge_lines}
    assert len(materials) == 2
    assert any("x23" in m for m in materials)
    assert any("x22" in m for m in materials)


def test_bom_material_key_width_absent_unchanged_format():
    """When width_mm is unknown (0.0), the material key format is
    unchanged from pre-width behavior — no bare 'x0' suffix leaks in."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
            ),
        },
    )
    result = DecompositionResult(cabinet_id="test", cabinet_type="test", panels=[panel])
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    assert len(edge_lines) == 1
    assert edge_lines[0].material == "ABS_swiss_krono.U119_VL_0.8"
    assert "x" not in edge_lines[0].material.split("_0.8")[-1]


def test_edging_row_carries_width_mm():
    """EdgingRow carries width_mm from EdgeBand."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                width_mm=23.0,
            ),
        },
    )
    rows = collect_edging_rows([panel])
    assert len(rows) == 1
    assert rows[0].width_mm == 23.0


def test_edging_csv_includes_width_column():
    """CSV header includes the width column, placed right after
    Grubość_mm and before Kod_krawedzi."""
    assert "Szerokosc_obrzeza_mm" in HEADER
    grubosc_idx = HEADER.index("Grubość_mm")
    width_idx = HEADER.index("Szerokosc_obrzeza_mm")
    code_idx = HEADER.index("Kod_krawedzi")
    assert width_idx == grubosc_idx + 1
    assert code_idx == width_idx + 1


def test_edging_csv_output_includes_width_when_known():
    """CSV output emits the width value when EdgeBand.width_mm is set."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
                width_mm=23.0,
            ),
        },
    )
    rows = collect_edging_rows([panel])
    csv_text = rows_to_csv(rows)

    lines = csv_text.strip().split("\n")
    header_cols = lines[0].split(";")
    data_cols = lines[1].split(";")

    width_col_idx = header_cols.index("Szerokosc_obrzeza_mm")
    assert data_cols[width_col_idx] == "23"


def test_edging_csv_output_empty_width_when_unknown():
    """CSV output emits an empty string when width_mm is unset (0.0)."""
    panel = _panel_with_edges(
        "P1",
        "swiss_krono.U119_VL",
        {
            "front": EdgeBand(
                material="ABS_swiss_krono.U119_VL",
                thickness_mm=0.8,
                length_mm=500,
            ),
        },
    )
    rows = collect_edging_rows([panel])
    csv_text = rows_to_csv(rows)

    lines = csv_text.strip().split("\n")
    header_cols = lines[0].split(";")
    data_cols = lines[1].split(";")

    width_col_idx = header_cols.index("Szerokosc_obrzeza_mm")
    assert data_cols[width_col_idx] == ""


# ── End-to-end: real decomposition emits distinct thicknesses ───
#
# The hand-built-Panel tests above prove the BOM/CSV plumbing. These
# prove the gap is actually closed: a real YAML → load_cabinet →
# decompose pipeline (no test-only shortcuts) must itself produce
# front bands at 2.0mm and carcass bands at 0.8mm, and calculate_bom
# on that real decomposition must emit at least two distinct edge_band
# material keys differing by thickness.


def test_k01_front_panels_banded_at_2mm_carcass_at_0_8mm():
    """K01.yaml has no oklejanie.grubosc_frontu override, so fronts use
    the owner-confirmed 2.0mm default while carcass panels keep 0.8mm."""
    result = decompose(load_cabinet(FIXTURES / "K01.yaml"))

    front_panels = [p for p in result.panels if p.role == PanelRole.FRONT_DRAWER]
    carcass_panels = [
        p for p in result.panels
        if p.role in (PanelRole.LEFT_SIDE, PanelRole.RIGHT_SIDE, PanelRole.BOTTOM)
    ]
    assert front_panels, "expected drawer front panels in K01 decomposition"
    assert carcass_panels, "expected carcass panels in K01 decomposition"

    for p in front_panels:
        for band in p.banded_edges.values():
            assert band.thickness_mm == 2.0

    for p in carcass_panels:
        for band in p.banded_edges.values():
            assert band.thickness_mm == 0.8


def test_k01_bom_emits_distinct_thickness_material_keys():
    """calculate_bom on a real K01 decomposition produces at least two
    distinct edge_band material keys differing in thickness."""
    result = decompose(load_cabinet(FIXTURES / "K01.yaml"))
    bom = calculate_bom(result)
    edge_lines = _bom_edge_lines(bom.items)

    assert edge_lines, "expected edge_band BOM lines"
    materials = {item.material for item in edge_lines}
    assert any("_0.8" in m for m in materials)
    assert any("_2.0" in m for m in materials)
    assert len(materials) >= 2


# ── Loader: oklejanie.grubosc_frontu ─────────────────────────────


def test_loader_reads_grubosc_frontu_when_present(tmp_path):
    """YAML with oklejanie.grubosc_frontu overrides the front default."""
    yaml_text = (FIXTURES / "K01.yaml").read_text()
    assert "grubosc_frontu" not in yaml_text
    yaml_text = yaml_text.replace(
        "grubosc: 0.8\n", "grubosc: 0.8\n        grubosc_frontu: 1.0\n"
    )
    custom = tmp_path / "K01_custom.yaml"
    custom.write_text(yaml_text)

    cab = load_cabinet(custom)
    assert cab.front_edge_banding_thickness_mm == 1.0
    assert cab.edge_banding_thickness_mm == 0.8  # unaffected


def test_loader_defaults_grubosc_frontu_to_2mm_when_absent():
    """YAML without oklejanie.grubosc_frontu defaults front thickness
    to the owner-confirmed 2.0mm."""
    cab = load_cabinet(FIXTURES / "K01.yaml")
    assert cab.front_edge_banding_thickness_mm == 2.0
