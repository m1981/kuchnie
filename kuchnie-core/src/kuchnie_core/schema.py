"""Kitchen YAML schema — Pydantic models for contract validation.

This schema defines the contract between Blender (Home Builder 5)
and kuchnie_core.  Any YAML that passes this schema can be consumed
by load_kitchen() and decompose().

Usage:
    from kuchnie_core.schema import KitchenSchema
    
    # Validate YAML before loading
    kitchen = KitchenSchema.from_yaml('kitchen.yaml')
    
    # Or validate dict
    kitchen = KitchenSchema(**yaml_dict)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# ── Drawer specification ─────────────────────────────────────────

class DrawerSpec(BaseModel):
    """Blum drawer system specification."""
    id: str = Field(..., description="Drawer identifier (e.g. 'S1')")
    height_mm: int = Field(..., gt=0, description="Drawer front height in mm")
    system: str = Field(
        default="tandembox_antaro",
        description="Blum system: tandembox_antaro, merivobox, legrabox"
    )
    height_code: str = Field(
        ...,
        description="Blum height code: N, M, K, C, F"
    )
    nl: int = Field(
        ...,
        description="Nominal length in mm: 270, 300, 350, 400, 450, 500, 550, 600, 650"
    )
    capacity_kg: int = Field(
        default=40,
        description="Carrying capacity: 40 or 70 kg"
    )
    
    @field_validator('height_code')
    @classmethod
    def valid_height_code(cls, v: str) -> str:
        valid = ('N', 'M', 'K', 'C', 'F')
        if v not in valid:
            raise ValueError(f"Invalid height code '{v}'. Valid: {valid}")
        return v
    
    @field_validator('nl')
    @classmethod
    def valid_nl(cls, v: int) -> int:
        valid = (270, 300, 350, 400, 450, 500, 550, 600, 650)
        if v not in valid:
            raise ValueError(f"Invalid NL {v}. Valid: {valid}")
        return v
    
    @field_validator('system')
    @classmethod
    def valid_system(cls, v: str) -> str:
        valid = ('tandembox_antaro', 'merivobox', 'legrabox')
        if v not in valid:
            raise ValueError(f"Invalid system '{v}'. Valid: {valid}")
        return v
    
    @field_validator('capacity_kg')
    @classmethod
    def valid_capacity(cls, v: int) -> int:
        if v not in (40, 70):
            raise ValueError(f"Invalid capacity {v}kg. Valid: 40, 70")
        return v


# ── Shelf specification ──────────────────────────────────────────

class ShelfSpec(BaseModel):
    """Shelf specification."""
    id: str = Field(..., description="Shelf identifier (e.g. 'P1')")


# ── Front specification ──────────────────────────────────────────

class FrontSpec(BaseModel):
    """Front (door or drawer front) specification."""
    id: str = Field(..., description="Front identifier (e.g. 'F1')")
    type: str = Field(
        ...,
        description="Front type: 'drawer', 'door'"
    )
    linked_to: Optional[str] = Field(
        None,
        description="Linked drawer ID (for drawer fronts)"
    )
    side: Optional[str] = Field(
        None,
        description="Door swing side: 'left', 'right'"
    )
    hinge_count: Optional[int] = Field(
        None,
        ge=2,
        le=4,
        description="Number of hinges (2-4)"
    )
    margins: Optional[dict] = Field(
        None,
        description="Margins: {left, right, top, bottom} in mm"
    )
    
    @field_validator('type')
    @classmethod
    def valid_front_type(cls, v: str) -> str:
        valid = ('drawer', 'door')
        if v not in valid:
            raise ValueError(f"Invalid front type '{v}'. Valid: {valid}")
        return v
    
    @field_validator('side')
    @classmethod
    def valid_side(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ('left', 'right'):
            raise ValueError(f"Invalid side '{v}'. Valid: left, right")
        return v


# ── Handle specification ─────────────────────────────────────────

class HandleSpec(BaseModel):
    """Handle specification."""
    type: str = Field(
        default="rail",
        description="Handle type: rail, knob, push, gola"
    )
    spacing_mm: Optional[int] = Field(
        None,
        gt=0,
        description="Handle spacing in mm (for rail handles)"
    )


# ── Cabinet specification ────────────────────────────────────────

class CabinetSpec(BaseModel):
    """Cabinet specification — the core contract unit."""
    id: str = Field(..., description="Cabinet identifier (e.g. 'K01')")
    type: str = Field(
        ...,
        description="Cabinet type: dolna_szufladowa, dolna_drzwiowa, gorna_drzwiowa, etc."
    )
    description: str = Field(
        default="",
        description="Human-readable description"
    )
    width_mm: int = Field(..., gt=0, description="Cabinet width in mm")
    height_mm: int = Field(..., gt=0, description="Cabinet height in mm")
    depth_mm: int = Field(..., gt=0, description="Cabinet depth in mm")
    
    body_material: str = Field(
        ...,
        description="Body material code (e.g. 'swiss_krono.U119_VL')"
    )
    back_material: str = Field(
        ...,
        description="Back material code (e.g. 'HDF_3mm')"
    )
    front_material: str = Field(
        ...,
        description="Front material code (e.g. 'swiss_krono.U119_EM')"
    )
    
    thickness_side_mm: int = Field(
        default=18,
        gt=0,
        description="Side panel thickness in mm"
    )
    thickness_back_mm: int = Field(
        default=3,
        gt=0,
        description="Back panel thickness in mm"
    )
    thickness_front_mm: int = Field(
        default=18,
        gt=0,
        description="Front panel thickness in mm"
    )
    thickness_shelf_mm: int = Field(
        default=18,
        gt=0,
        description="Shelf thickness in mm"
    )
    thickness_bottom_mm: int = Field(
        default=18,
        gt=0,
        description="Bottom panel thickness in mm"
    )
    groove_depth_mm: int = Field(
        default=8,
        gt=0,
        description="Back panel groove depth in mm"
    )
    plinth_height_mm: int = Field(
        default=100,
        ge=0,
        description="Plinth (toe kick) height in mm"
    )
    
    drawers: list[DrawerSpec] = Field(
        default_factory=list,
        description="Drawer configurations (see drawer_order for stacking)"
    )
    drawer_order: Optional[str] = Field(
        default=None,
        description="How the drawers list is stacked: 'bottom_up' (model "
                    "contract) or 'top_down' (normalized by reversal at "
                    "load). Required when 2+ drawers have unequal heights "
                    "— ambiguous order puts runner drillings on the wrong "
                    "rows (G8, scrap-risk).",
        pattern="^(bottom_up|top_down)$",
    )
    shelves: list[ShelfSpec] = Field(
        default_factory=list,
        description="Shelf configurations"
    )
    fronts: list[FrontSpec] = Field(
        default_factory=list,
        description="Front configurations"
    )
    handles: HandleSpec = Field(
        default_factory=HandleSpec,
        description="Handle configuration"
    )
    
    @field_validator('type')
    @classmethod
    def valid_cabinet_type(cls, v: str) -> str:
        valid = (
            'dolna_szufladowa', 'dolna_drzwiowa', 'dolna_legrabox',
            'gorna_drzwiowa', 'wysoka_drzwiowa',
            'narożna_ślepa', 'narożna_diagonalna',
            'cargo', 'piekarnik',
        )
        if v not in valid:
            raise ValueError(f"Invalid cabinet type '{v}'. Valid: {valid}")
        return v
    
    @model_validator(mode='after')
    def width_exceeds_sides(self) -> 'CabinetSpec':
        side = self.thickness_side_mm
        if self.width_mm <= 2 * side:
            raise ValueError(
                f"Width {self.width_mm}mm too small for {side}mm sides. "
                f"Must be > {2 * side}mm"
            )
        return self


# ── Row specification ────────────────────────────────────────────

class RowSpec(BaseModel):
    """Row of cabinets along one wall."""
    label: str = Field(..., description="Wall label (e.g. 'Ściana północna')")
    wall_width_mm: int = Field(..., gt=0, description="Wall width in mm")
    wall_height_mm: int = Field(
        default=2800,
        gt=0,
        description="Wall height in mm"
    )
    cabinets: list[CabinetSpec] = Field(
        ...,
        min_length=1,
        description="Cabinets in this row"
    )
    
    @model_validator(mode='after')
    def cabinets_fit_in_wall(self) -> 'RowSpec':
        total_cab_width = sum(c.width_mm for c in self.cabinets)
        if total_cab_width > self.wall_width_mm:
            raise ValueError(
                f"Total cabinet width {total_cab_width}mm exceeds "
                f"wall width {self.wall_width_mm}mm"
            )
        return self


# ── Material specification ───────────────────────────────────────

class MaterialSpec(BaseModel):
    """Material codes for the kitchen."""
    body: str = Field(..., description="Body material code")
    back: str = Field(
        default="HDF_3mm",
        description="Back material code"
    )
    front: str = Field(..., description="Front material code")
    worktop: Optional[str] = Field(
        None,
        description="Worktop material code"
    )


# ── Settings specification ───────────────────────────────────────

class SettingsSpec(BaseModel):
    """Kitchen construction settings."""
    base_height: int = Field(default=720, gt=0)
    base_depth: int = Field(default=560, gt=0)
    wall_height: int = Field(default=720, gt=0)
    wall_depth: int = Field(default=300, gt=0)
    tall_height: int = Field(default=2000, gt=0)
    tall_depth: int = Field(default=560, gt=0)
    plinth_height: int = Field(default=120, ge=0)
    corpus_thickness: int = Field(default=18, gt=0)
    back_thickness: int = Field(default=3, gt=0)
    front_thickness: int = Field(default=19, gt=0)


# ── Worktop specification ────────────────────────────────────────

class WorktopSpec(BaseModel):
    """Worktop specification."""
    row_label: str = Field(..., description="Row label this worktop covers")
    material: str = Field(..., description="Worktop material code")
    thickness_mm: int = Field(default=40, gt=0)
    depth_mm: int = Field(default=600, gt=0)
    overhang_front_mm: int = Field(default=20, ge=0)
    overhang_ends_mm: int = Field(default=30, ge=0)


# ── Kitchen specification (top-level) ────────────────────────────

class KitchenSchema(BaseModel):
    """Top-level kitchen specification — the full contract."""
    version: str = Field(
        ...,
        description="Schema version (e.g. '2.0')"
    )
    project_name: str = Field(
        default="",
        description="Project name"
    )
    settings: SettingsSpec = Field(
        default_factory=SettingsSpec,
        description="Construction settings"
    )
    materials: MaterialSpec = Field(
        ...,
        description="Material codes"
    )
    rows: list[RowSpec] = Field(
        ...,
        min_length=1,
        description="Kitchen rows (walls)"
    )
    worktops: list[WorktopSpec] = Field(
        default_factory=list,
        description="Worktop specifications"
    )
    
    @classmethod
    def from_yaml(cls, path: str | Path) -> KitchenSchema:
        """Load and validate kitchen from YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Kitchen YAML not found: {path}")
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def to_yaml(self, path: str | Path) -> Path:
        """Save kitchen to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, allow_unicode=True)
        
        return path
