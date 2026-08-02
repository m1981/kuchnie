"""Blum drawer systems — unified API for TANDEMBOX, MERIVOBOX, LEGRABOX.

All three systems share the same interface:
  - height_codes: list of available height codes
  - side_height(code): metal drawer side height in mm
  - back_panel_height(code): chipboard back panel cutting height
  - runner_clearance_per_side_mm(): runner + clearance
  - lw(kb): Licht Weite (clear width for drawer box)
  - base_panel_width(lw), back_panel_width(lw), base_panel_depth(nl)
  - decompose_drawer_box(...): returns panels + machining ops

Sources:
  - Blum Catalogue 2024/2025
  - TANDEMBOX antaro planning data
  - MERIVOBOX planning data
  - LEGRABOX planning data (DQBQRY, DQBMJY, DQBNYM)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

from .model import Accessory, MachiningOp, Panel, PanelRole
from . import legrabox as _legrabox


# ── Shared defaults ──────────────────────────────────────────────

# The height code a drawer gets when the caller names none. Defined ONCE
# here for every system that does not own a different answer: "M" is the
# only code all three Blum systems publish (kuchnie-27b — kitchen-erp used
# to spell it in its own module).  LEGRABOX overrides it from
# ``legrabox.DEFAULT_HEIGHT_CODE`` because core's
# ``catalog.decompose_dolna_legrabox`` has always defaulted to "C" and core
# is the domain authority; a single cross-system literal is impossible
# because "C" is not a TANDEMBOX or MERIVOBOX code at all.
DEFAULT_HEIGHT_CODE = "M"

# Blum's first pre-punched runner screw, measured from the cabinet's FRONT
# edge. Systems without their own published chart use this single mark.
_FIRST_RUNNER_SCREW_MM = 46


# ── The drawer, described once ───────────────────────────────────

@dataclass(frozen=True)
class DrawerBoxSpec:
    """Everything one drawer box needs, in one value (kuchnie-b30).

    Replaces the 10/11-parameter argument lists of
    ``DrawerSystem.decompose_drawer_box`` and
    ``legrabox.decompose_drawer_box`` — both were on the accepted
    ``docs/arch-smells-baseline.txt`` param-bloat list precisely so this
    could retire them, together with ``make_runner_accessory``'s.

    Three groups of fields, in dependency order:

      * identity + size — ``cabinet_id``/``drawer_id``/``kb``/``nl``
      * PLACEMENT — ``runner_y_mm`` (required, no default: the screw-axis
        height above the carcass side's BOTTOM edge) and ``side_thickness``.
        These are the two data the ``DrawerSystem`` ABC used to lack, which
        is why kitchen-erp re-implemented the stacking loop and mutated the
        emitted ops afterwards (kuchnie-27b).
      * board + purchasing defaults — materials, thicknesses, and the runner
        set's capacity/colour/motion, so ``make_runner_accessory`` describes
        the SAME drawer rather than taking its own parallel argument list.

    ``height_code=None`` means "use the drawer system's default"; resolve it
    with ``DrawerSystem.resolve`` before reading it.
    """

    cabinet_id: str
    drawer_id: str
    kb: int                       # carcass internal width
    nl: int                       # nominal length (runner depth)
    runner_y_mm: float            # placement — required, see above
    height_code: str | None = None
    side_thickness: int = 0
    base_material: str = "plyta_16mm"
    back_material: str = "plyta_16mm"
    base_thickness: int = 16
    back_thickness: int = 16
    capacity_kg: int = 40
    colour: str = "SW-M"
    motion: str = "BLUMOTION S"


# ── Abstract base ────────────────────────────────────────────────

class DrawerSystem(ABC):
    """Unified interface for Blum drawer systems."""

    @property
    @abstractmethod
    def height_codes(self) -> list[str]:
        """Available height codes (e.g. ['N', 'M', 'D'])."""
        ...

    @abstractmethod
    def side_height(self, code: str) -> float:
        """Metal drawer side wall height in mm."""
        ...

    @abstractmethod
    def back_panel_height(self, code: str) -> float:
        """Chipboard back panel cutting height in mm."""
        ...

    @abstractmethod
    def runner_clearance_per_side_mm(self) -> float:
        """Runner + clearance per side in mm."""
        ...

    @abstractmethod
    def valid_nl(self) -> list[int]:
        """All valid nominal lengths in mm."""
        ...

    @abstractmethod
    def is_valid_combo(self, code: str, nl: int) -> bool:
        """Check if height code × NL combination is available."""
        ...

    def lw(self, kb: int) -> int:
        """Lichte Weite = KB - 2 × runner_clearance.

        Raises:
          ValueError: if KB is too small for the runner clearance.
        """
        result = int(kb - 2 * self.runner_clearance_per_side_mm())
        if result <= 0:
            raise ValueError(
                f"KB={kb}mm too small for {self.__class__.__name__} runners. "
                f"Minimum KB: {2 * self.runner_clearance_per_side_mm() + 1}mm"
            )
        return result

    def base_panel_width(self, lw: int) -> int:
        """Drawer base (bottom) panel width = LW - 35."""
        return lw - 35

    def back_panel_width(self, lw: int) -> int:
        """Chipboard back panel width = LW - 38."""
        return lw - 38

    def base_panel_depth(self, nl: int) -> int:
        """Drawer base depth = NL - 10 (chipboard back variant)."""
        return nl - 10

    # ── Defaults + validation ────────────────────────────────────

    @property
    def default_height_code(self) -> str:
        """Height code for a drawer that names none — see DEFAULT_HEIGHT_CODE."""
        return DEFAULT_HEIGHT_CODE

    def resolve(self, spec: DrawerBoxSpec) -> DrawerBoxSpec:
        """Fill in the system's default height code and validate the spec.

        Raises:
          ValueError: if height_code is unknown or NL is invalid for that code.
        """
        if spec.height_code is None:
            spec = replace(spec, height_code=self.default_height_code)
        if spec.height_code not in self.height_codes:
            raise ValueError(
                f"Unknown height code {spec.height_code!r}. "
                f"Valid: {self.height_codes}"
            )
        if not self.is_valid_combo(spec.height_code, spec.nl):
            raise ValueError(
                f"{self.__class__.__name__} {spec.height_code} not available "
                f"with NL={spec.nl}. Valid NLs: {self.valid_nl()}"
            )
        return spec

    # ── Vertical placement — the stacking loop, defined ONCE ─────

    def runner_axis_heights(
        self, drawers: list[dict], bottom_thickness_mm: float
    ) -> list[float]:
        """Runner screw-axis height for each drawer in a bottom-up stack.

        ``drawers`` is the ``CabinetInstance.drawers`` contract (listed
        bottom-up). Each zone starts on top of the carcass bottom panel; the
        screw axis sits ``RUNNER_AXIS_OFFSET_MM`` above its zone floor, and
        a zone is as tall as the drawer's front (``wysokosc``) or, failing
        that, the metal side height of its height code.

        This is the arithmetic ``catalog.decompose_dolna_legrabox`` and
        kitchen-erp's ``_attach_drawer_boxes`` each used to carry a copy of
        (kuchnie-27b). ``RUNNER_AXIS_OFFSET_MM`` currently lives in
        ``legrabox`` and is shared by all three systems — verify per runner
        in the Blum planner before trusting it for TANDEMBOX/MERIVOBOX.
        """
        y = float(bottom_thickness_mm) + _legrabox.RUNNER_AXIS_OFFSET_MM
        heights: list[float] = []
        for drawer in drawers:
            heights.append(y)
            code = drawer.get("height_code") or self.default_height_code
            y += drawer.get("wysokosc") or self.side_height(code)
        return heights

    # ── Decomposition ────────────────────────────────────────────

    def decompose_drawer_box(
        self, spec: DrawerBoxSpec
    ) -> tuple[list[Panel], list[MachiningOp]]:
        """Decompose one drawer into board-cut panels + runner mounting ops.

        Returns:
          panels:  drawer back + drawer base (the two board-cut parts)
          ops:     runner mounting drill positions for ONE side panel, in
                   the carcass-side CAM convention (x = from the FRONT edge,
                   y = above the BOTTOM edge). Already placed at
                   ``spec.runner_y_mm`` — no caller may swap the axes
                   afterwards. Each side needs its own copies.

        Raises:
          ValueError: if height_code is unknown or NL is invalid for that code.
        """
        spec = self.resolve(spec)
        lw_val = self.lw(spec.kb)
        back_w = self.back_panel_width(lw_val)
        back_h = self.back_panel_height(spec.height_code)
        base_w = self.base_panel_width(lw_val)
        base_d = self.base_panel_depth(spec.nl)

        panels = [
            Panel(
                id=f"{spec.cabinet_id}_drawer_{spec.drawer_id}_back",
                name=f"Szuflada {spec.drawer_id} — tył",
                material=spec.back_material,
                thickness_mm=spec.back_thickness,
                width_mm=back_w,
                height_mm=back_h,
                banded_edges={},
                quantity=1,
                role=PanelRole.DRAWER_BACK,
            ),
            Panel(
                id=f"{spec.cabinet_id}_drawer_{spec.drawer_id}_base",
                name=f"Szuflada {spec.drawer_id} — dno",
                material=spec.base_material,
                thickness_mm=spec.base_thickness,
                width_mm=base_w,
                height_mm=base_d,
                banded_edges={},
                quantity=1,
                role=PanelRole.DRAWER_BASE,
            ),
        ]

        # Runner mounting screws
        ops = self._runner_screw_ops(spec)
        return panels, ops

    def _runner_screw_ops(self, spec: DrawerBoxSpec) -> list[MachiningOp]:
        """Runner screw positions for a resolved spec.

        Generic systems publish no per-NL screw chart here yet, so only the
        first mark is emitted — but at the right place: x from the front
        edge, y at the caller's ``runner_y_mm``.
        """
        return [
            MachiningOp(
                type="drill",
                x_mm=_FIRST_RUNNER_SCREW_MM,
                y_mm=spec.runner_y_mm,
                diameter_mm=_legrabox.RUNNER_SCREW_PILOT_DIA_MM,
                depth_mm=_legrabox.RUNNER_SCREW_PILOT_DEPTH_MM,  # blind
                face="inside",
                drill_type="runner_screw",
                note=(f"{self.__class__.__name__} runner screw "
                      f"(NL={spec.nl})"),
            ),
        ]

    def make_runner_accessory(self, spec: DrawerBoxSpec) -> Accessory:
        """Create an Accessory entry for the runner set."""
        spec = self.resolve(spec)
        part_nr = (f"{self.__class__.__name__.upper()} {spec.height_code} "
                   f"NL{spec.nl} {spec.capacity_kg}kg {spec.colour}")
        return Accessory(
            id=f"{spec.cabinet_id}_runner_{spec.drawer_id}",
            name=f"{part_nr} ({spec.motion})",
            type="runner",
            quantity=1,
        )


# ── TANDEMBOX antaro ─────────────────────────────────────────────

@dataclass
class _TandemboxHeight:
    code: str
    side_height_mm: float
    back_panel_height_mm: float
    min_install_height_mm: float


_TANDEMBOX_HEIGHTS: dict[str, _TandemboxHeight] = {
    "N": _TandemboxHeight("N", 83, 56, 68),
    "M": _TandemboxHeight("M", 116, 89, 100),
    "D": _TandemboxHeight("D", 199, 172, 184),
}

_TANDEMBOX_NL_MATRIX: dict[str, dict[int, bool]] = {
    "N": {270: False, 300: False, 350: False, 400: True, 450: True,
          500: True, 550: True, 600: True, 650: False},
    "M": {270: True, 300: True, 350: True, 400: True, 450: True,
          500: True, 550: True, 600: True, 650: True},
    "D": {270: True, 300: True, 350: True, 400: True, 450: True,
          500: True, 550: True, 600: True, 650: True},
}


class TandemboxAntaro(DrawerSystem):
    """Blum TANDEMBOX antaro drawer system."""

    _RUNNER_CLEARANCE = 12.5  # mm per side

    @property
    def height_codes(self) -> list[str]:
        return list(_TANDEMBOX_HEIGHTS.keys())

    def side_height(self, code: str) -> float:
        return _TANDEMBOX_HEIGHTS[code].side_height_mm

    def back_panel_height(self, code: str) -> float:
        return _TANDEMBOX_HEIGHTS[code].back_panel_height_mm

    def runner_clearance_per_side_mm(self) -> float:
        return self._RUNNER_CLEARANCE

    def valid_nl(self) -> list[int]:
        return [270, 300, 350, 400, 450, 500, 550, 600, 650]

    def is_valid_combo(self, code: str, nl: int) -> bool:
        if code not in _TANDEMBOX_NL_MATRIX:
            return False
        return _TANDEMBOX_NL_MATRIX[code].get(nl, False)


# ── MERIVOBOX ────────────────────────────────────────────────────

_MERIVOBOX_HEIGHTS: dict[str, _TandemboxHeight] = {
    "N": _TandemboxHeight("N", 65.5, 39, 50),
    "M": _TandemboxHeight("M", 90, 63, 75),
    "E": _TandemboxHeight("E", 184, 157, 169),
}

_MERIVOBOX_NL_MATRIX: dict[str, dict[int, bool]] = {
    "N": {270: False, 300: False, 350: False, 400: True, 450: True,
          500: True, 550: True, 600: True, 650: False},
    "M": {270: True, 300: True, 350: True, 400: True, 450: True,
          500: True, 550: True, 600: True, 650: True},
    "E": {270: True, 300: True, 350: True, 400: True, 450: True,
          500: True, 550: True, 600: True, 650: True},
}


class Merivobox(DrawerSystem):
    """Blum MERIVOBOX drawer system."""

    _RUNNER_CLEARANCE = 12.5

    @property
    def height_codes(self) -> list[str]:
        return list(_MERIVOBOX_HEIGHTS.keys())

    def side_height(self, code: str) -> float:
        return _MERIVOBOX_HEIGHTS[code].side_height_mm

    def back_panel_height(self, code: str) -> float:
        return _MERIVOBOX_HEIGHTS[code].back_panel_height_mm

    def runner_clearance_per_side_mm(self) -> float:
        return self._RUNNER_CLEARANCE

    def valid_nl(self) -> list[int]:
        return [270, 300, 350, 400, 450, 500, 550, 600, 650]

    def is_valid_combo(self, code: str, nl: int) -> bool:
        if code not in _MERIVOBOX_NL_MATRIX:
            return False
        return _MERIVOBOX_NL_MATRIX[code].get(nl, False)


# ── LEGRABOX ─────────────────────────────────────────────────────


class Legrabox(DrawerSystem):
    """Blum LEGRABOX drawer system.

    Thin adapter over the ``legrabox`` module — the single LEGRABOX
    data/formula source per ADR-006. No LEGRABOX constant lives in this
    file: heights, NL availability, runner clearance, and panel-width
    formulas all resolve through the module.
    """

    @property
    def height_codes(self) -> list[str]:
        return list(_legrabox.HEIGHTS.keys())

    def side_height(self, code: str) -> float:
        return _legrabox.HEIGHTS[code].side_height_mm

    def back_panel_height(self, code: str) -> float:
        return _legrabox.HEIGHTS[code].back_panel_height_mm

    def runner_clearance_per_side_mm(self) -> float:
        return _legrabox.RUNNER_CLEARANCE_PER_SIDE_MM

    def valid_nl(self) -> list[int]:
        return list(_legrabox.VALID_NL)

    def is_valid_combo(self, code: str, nl: int) -> bool:
        return _legrabox.NL_MATRIX.get(code, {}).get(nl, False)

    def base_panel_width(self, lw: int) -> int:
        return _legrabox.base_panel_width(lw)

    def back_panel_width(self, lw: int) -> int:
        return _legrabox.back_panel_width(lw)

    def base_panel_depth(self, nl: int) -> int:
        return _legrabox.base_panel_depth(nl)

    @property
    def default_height_code(self) -> str:
        return _legrabox.DEFAULT_HEIGHT_CODE

    def decompose_drawer_box(
        self, spec: DrawerBoxSpec
    ) -> tuple[list[Panel], list[MachiningOp]]:
        """Validate here, decompose in the module — one implementation.

        Before kuchnie-27b this class inherited the ABC's generic
        single-screw op, so the kitchen-erp path drilled ONE runner screw
        where core drilled the four NL-specific marks from
        ``legrabox.RUNNER_SCREW_POSITIONS``.
        """
        return _legrabox.decompose_drawer_box(self.resolve(spec))

    def make_runner_accessory(self, spec: DrawerBoxSpec) -> Accessory:
        return _legrabox.make_runner_accessory(self.resolve(spec))


# ── Factory ──────────────────────────────────────────────────────

_SYSTEMS: dict[str, type[DrawerSystem]] = {
    "tandembox_antaro": TandemboxAntaro,
    "merivobox": Merivobox,
    "legrabox": Legrabox,
}


class DrawerSystemFactory:
    """Factory for Blum drawer systems."""

    @staticmethod
    def get(system_id: str) -> DrawerSystem:
        """Get drawer system by id.  Raises KeyError if not found."""
        if system_id not in _SYSTEMS:
            raise KeyError(f"Unknown drawer system: {system_id!r}")
        return _SYSTEMS[system_id]()

    @staticmethod
    def list_ids() -> list[str]:
        """List all available drawer system ids."""
        return list(_SYSTEMS.keys())
