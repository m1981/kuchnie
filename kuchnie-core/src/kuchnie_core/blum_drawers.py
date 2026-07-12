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
from dataclasses import dataclass

from .model import Accessory, MachiningOp, Panel, PanelRole
from . import legrabox as _legrabox


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

    def decompose_drawer_box(
        self,
        cabinet_id: str,
        drawer_id: str,
        kb: int,
        nl: int,
        height_code: str,
        base_material: str = "plyta_16mm",
        back_material: str = "plyta_16mm",
        base_thickness: int = 16,
        back_thickness: int = 16,
    ) -> tuple[list[Panel], list[MachiningOp]]:
        """Decompose one drawer into board-cut panels + runner mounting ops.

        Returns:
          panels:  drawer back + drawer base (the two board-cut parts)
          ops:     runner mounting drill positions for ONE side panel

        Raises:
          ValueError: if height_code is unknown or NL is invalid for that code.
        """
        if height_code not in self.height_codes:
            raise ValueError(
                f"Unknown height code {height_code!r}. "
                f"Valid: {self.height_codes}"
            )
        if not self.is_valid_combo(height_code, nl):
            raise ValueError(
                f"{self.__class__.__name__} {height_code} not available with NL={nl}. "
                f"Valid NLs: {self.valid_nl()}"
            )
        lw_val = self.lw(kb)
        back_w = self.back_panel_width(lw_val)
        back_h = self.back_panel_height(height_code)
        base_w = self.base_panel_width(lw_val)
        base_d = self.base_panel_depth(nl)

        panels = [
            Panel(
                id=f"{cabinet_id}_drawer_{drawer_id}_back",
                name=f"Szuflada {drawer_id} — tył",
                material=back_material,
                thickness_mm=back_thickness,
                width_mm=back_w,
                height_mm=back_h,
                banded_edges={},
                quantity=1,
                role=PanelRole.DRAWER_BACK,
            ),
            Panel(
                id=f"{cabinet_id}_drawer_{drawer_id}_base",
                name=f"Szuflada {drawer_id} — dno",
                material=base_material,
                thickness_mm=base_thickness,
                width_mm=base_w,
                height_mm=base_d,
                banded_edges={},
                quantity=1,
                role=PanelRole.DRAWER_BASE,
            ),
        ]

        # Runner mounting screws
        ops = self._runner_screw_ops(cabinet_id, drawer_id, nl)
        return panels, ops

    def _runner_screw_ops(
        self, cabinet_id: str, drawer_id: str, nl: int
    ) -> list[MachiningOp]:
        """Runner screw positions — first screw at 46mm, then 32mm pitch."""
        # Standard positions (simplified — full chart from Blum per NL)
        first_screw = 46
        ops = [
            MachiningOp(
                type="drill",
                x_mm=0,
                y_mm=first_screw,
                diameter_mm=5,
                depth_mm=0,
                note=f"{self.__class__.__name__} runner screw (NL={nl})",
            ),
        ]
        return ops

    def make_runner_accessory(
        self,
        cabinet_id: str,
        drawer_id: str,
        height_code: str,
        nl: int,
        capacity_kg: int = 40,
        colour: str = "SW-M",
        motion: str = "BLUMOTION S",
    ) -> Accessory:
        """Create an Accessory entry for the runner set."""
        part_nr = f"{self.__class__.__name__.upper()} {height_code} NL{nl} {capacity_kg}kg {colour}"
        return Accessory(
            id=f"{cabinet_id}_runner_{drawer_id}",
            name=f"{part_nr} ({motion})",
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
