"""ADR-012 §4 — ``HandleSpec`` replaces ``CabinetInstance.handles: dict``.

Locks in:

  * ``HandleSpec`` field defaults from ADR-012 §4.
  * ``CabinetInstance.handles`` is now ``HandleSpec | None`` (not a dict).
  * Loader translates Polish YAML (``uchwyty: {typ: 'relingowy', ...}``)
    into a ``HandleSpec`` with English values (``type='bar', ...``).
  * Loader accepts the schema-format English dict likewise.
  * BOM accessory name is preserved in Polish for user-facing stability
    (English→Polish display map in ``catalog.py``): a K01 decomposition
    still produces ``"Uchwyt relingowy (rozstaw 256mm)"`` even though
    the internal ``HandleSpec.type`` is now ``"bar"``.
  * Cabinets without handles carry ``handles=None`` (loader short-circuits
    on empty YAML dict) and the decomposer skips the handle accessory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kuchnie_core import CabinetInstance, HandleSpec
from kuchnie_core.decomposer import decompose
from kuchnie_core.loader import (
    _handle_spec_from_polish,
    _handle_spec_from_schema,
    load_cabinet,
)


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


# ── Dataclass defaults (ADR-012 §4) ─────────────────────────────

class TestHandleSpecDefaults:
    def test_default_type_is_bar(self):
        assert HandleSpec().type == "bar"

    def test_default_spacing_is_128(self):
        assert HandleSpec().spacing_mm == 128.0

    def test_default_hole_diameter_is_5(self):
        assert HandleSpec().hole_diameter_mm == 5.0

    def test_default_position_is_center(self):
        assert HandleSpec().position == "center"

    def test_explicit_construction(self):
        s = HandleSpec(type="knob", spacing_mm=96.0, hole_diameter_mm=4.0, position="top")
        assert s.type == "knob"
        assert s.spacing_mm == 96.0
        assert s.hole_diameter_mm == 4.0
        assert s.position == "top"


# ── CabinetInstance field replacement ───────────────────────────

class TestCabinetInstanceHandlesField:
    """``handles`` is now ``HandleSpec | None``, not a dict."""

    def _make(self, **kw):
        defaults = dict(
            id="TEST", type="test", description="test",
            width_mm=800, height_mm=720, depth_mm=510,
            body_material="mat", back_material="mat", front_material="mat",
        )
        defaults.update(kw)
        return CabinetInstance(**defaults)

    def test_default_is_none(self):
        cab = self._make()
        assert cab.handles is None

    def test_accepts_handle_spec(self):
        cab = self._make(handles=HandleSpec(type="knob", spacing_mm=96.0))
        assert cab.handles is not None
        assert cab.handles.type == "knob"
        assert cab.handles.spacing_mm == 96.0


# ── Loader: Polish YAML → HandleSpec ────────────────────────────

class TestHandleSpecFromPolishYaml:

    def test_empty_dict_returns_none(self):
        assert _handle_spec_from_polish({}) is None

    def test_none_returns_none(self):
        assert _handle_spec_from_polish(None) is None

    def test_relingowy_to_bar(self):
        spec = _handle_spec_from_polish({"typ": "relingowy", "rozstaw": 256})
        assert spec is not None
        assert spec.type == "bar"
        assert spec.spacing_mm == 256.0

    def test_kulisty_to_knob(self):
        spec = _handle_spec_from_polish({"typ": "kulisty", "rozstaw": 96})
        assert spec is not None
        assert spec.type == "knob"

    def test_srodek_frontu_to_center(self):
        spec = _handle_spec_from_polish({"typ": "relingowy", "pozycja": "srodek_frontu"})
        assert spec is not None
        assert spec.position == "center"

    def test_srednica_otworu_is_lifted(self):
        spec = _handle_spec_from_polish({"typ": "relingowy", "srednica_otworu": 5})
        assert spec is not None
        assert spec.hole_diameter_mm == 5.0

    def test_unknown_polish_type_passes_through(self):
        # Loader should not silently coerce unknown types — return as-is
        # so a downstream error surfaces the typo.
        spec = _handle_spec_from_polish({"typ": "wymyslony", "rozstaw": 128})
        assert spec is not None
        assert spec.type == "wymyslony"


class TestHandleSpecFromSchema:
    """Schema-format (English keys) direct lift into ``HandleSpec``."""

    def test_empty_returns_none(self):
        assert _handle_spec_from_schema({}) is None
        assert _handle_spec_from_schema(None) is None

    def test_english_keys_lifted(self):
        spec = _handle_spec_from_schema({
            "type": "profile", "spacing_mm": 320.0,
            "hole_diameter_mm": 4.5, "position": "top",
        })
        assert spec is not None
        assert spec.type == "profile"
        assert spec.spacing_mm == 320.0
        assert spec.hole_diameter_mm == 4.5
        assert spec.position == "top"

    def test_missing_fields_use_adr012_defaults(self):
        spec = _handle_spec_from_schema({"type": "bar"})
        assert spec is not None
        assert spec.spacing_mm == 128.0
        assert spec.hole_diameter_mm == 5.0
        assert spec.position == "center"


# ── Real fixture round-trip (K01 has handles) ────────────────────

class TestK01HandleRoundTrip:
    """K01.yaml declares ``uchwyty: {typ: 'relingowy', rozstaw: 256, ...}``."""

    def test_k01_loads_with_handle_spec(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert isinstance(cab.handles, HandleSpec)

    def test_k01_type_translated_to_english(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert cab.handles.type == "bar"

    def test_k01_spacing_preserved(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert cab.handles.spacing_mm == 256.0

    def test_k01_position_translated(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert cab.handles.position == "center"

    def test_k01_hole_diameter_preserved(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        assert cab.handles.hole_diameter_mm == 5.0


# ── BOM Accessory name stays Polish (ADR-012 §4 stability) ──────

class TestBOMAccessoryNamePolish:
    """BOM output must stay Polish — the English→Polish map in catalog.py
    preserves the pre-ADR-012 user-facing accessory name.
    """

    def test_k01_handle_accessory_name_is_polish(self):
        cab = load_cabinet(FIXTURES / "K01.yaml")
        result = decompose(cab)
        handles = [a for a in result.accessories if a.type == "handle"]
        assert len(handles) == 1
        # Same string the pre-ADR-012 code produced from the raw Polish dict.
        assert handles[0].name == "Uchwyt relingowy (rozstaw 256mm)"

    def test_g01_handle_accessory_name_is_polish(self):
        cab = load_cabinet(FIXTURES / "G01.yaml")
        result = decompose(cab)
        handles = [a for a in result.accessories if a.type == "handle"]
        assert len(handles) == 1
        assert handles[0].name == "Uchwyt relingowy (rozstaw 256mm)"

    def test_legrabox_handle_accessory_name_is_polish(self):
        cab = load_cabinet(FIXTURES / "K02_legrabox.yaml")
        result = decompose(cab)
        handles = [a for a in result.accessories if a.type == "handle"]
        assert len(handles) == 1
        assert handles[0].name == "Uchwyt relingowy (rozstaw 256mm)"


# ── Cabinet without handles ─────────────────────────────────────

class TestCabinetWithoutHandles:
    """No ``uchwyty`` block in YAML \u2192 ``handles=None`` and no handle accessory."""

    def _make_cab_no_handles(self):
        # Construct in-memory; simulates a schema-format cabinet with no handles.
        cab = CabinetInstance(
            id="NOHANDLE", type="dolna_szufladowa", description="test",
            width_mm=800, height_mm=720, depth_mm=510,
            body_material="mat", back_material="mat", front_material="mat",
            fronts=[{"id": "S1", "typ": "szufladowy", "powiazany": "d1"}],
            drawers=[{"id": "d1", "typ": "blum_metabox", "wysokosc": 150}],
        )
        return cab

    def test_default_handles_is_none(self):
        cab = self._make_cab_no_handles()
        assert cab.handles is None

    def test_decomposer_skips_handle_accessory(self):
        cab = self._make_cab_no_handles()
        result = decompose(cab)
        assert [a for a in result.accessories if a.type == "handle"] == []
