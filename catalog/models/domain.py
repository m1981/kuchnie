"""Pydantic response models for the catalog API.

Maps directly to view columns: v_decors_full, v_worktops_full,
v_pairings_full, v_variants_availability.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ProducerOut(BaseModel):
    id: int
    slug: str
    name: str
    country: Optional[str] = None
    website: Optional[str] = None


class DecorSummary(BaseModel):
    """One row from v_decors_full (flat: one per variant)."""
    decor_pk: int
    decor_id: str
    decor_name: str
    decor_name_en: Optional[str] = None
    group_name: Optional[str] = None
    color_family: Optional[str] = None
    ncs: Optional[str] = None
    ral: Optional[str] = None
    pantone: Optional[str] = None
    img: Optional[str] = None
    one_global: bool = False
    new_2024: bool = False
    discontinued: bool = False
    producer: str
    variant_pk: int
    variant_id: str
    material_type: str
    material: str
    structure: Optional[str] = None
    structure_name: Optional[str] = None
    structure_type: Optional[str] = None
    roles: str  # JSON string: '["front","carcass"]'
    thickness_mm: Optional[float] = None
    width_mm: Optional[int] = None
    length_mm: Optional[int] = None
    format_mm: Optional[str] = None
    sidedness: Optional[str] = None
    express: Optional[str] = None
    konfekcja: bool = False
    splashback_available: bool = False
    hpl_available: bool = False
    countertop: Optional[str] = None
    multi_structures: Optional[str] = None


class VariantOut(BaseModel):
    """Single variant from v_decors_full."""
    variant_pk: int
    variant_id: str
    material_type: str
    material: str
    structure: Optional[str] = None
    structure_name: Optional[str] = None
    structure_type: Optional[str] = None
    roles: str
    thickness_mm: Optional[float] = None
    width_mm: Optional[int] = None
    length_mm: Optional[int] = None
    format_mm: Optional[str] = None
    sidedness: Optional[str] = None
    express: Optional[str] = None
    konfekcja: bool = False
    splashback_available: bool = False
    hpl_available: bool = False
    countertop: Optional[str] = None
    multi_structures: Optional[str] = None


class DecorWithVariants(BaseModel):
    """Decor grouped with its variants (for /decors/{id})."""
    decor_id: str
    decor_name: str
    decor_name_en: Optional[str] = None
    group_name: Optional[str] = None
    color_family: Optional[str] = None
    ncs: Optional[str] = None
    ral: Optional[str] = None
    pantone: Optional[str] = None
    img: Optional[str] = None
    producer: str
    variants: list[VariantOut] = []


class PairingOut(BaseModel):
    """Row from v_pairings_full."""
    pairing_pk: int
    front_decor_id: str
    front_decor_name: str
    target_decor_id: str
    target_decor_name: str
    pairing_type: str
    match_type: str
    priority: int
    notes: Optional[str] = None


class WorktopOut(BaseModel):
    """Row from v_worktops_full."""
    variant_pk: int
    variant_id: str
    decor_id: str
    decor_name_pl: str
    decor_name_en: Optional[str] = None
    producer: str
    collection: str
    material_type: str
    structure_code: Optional[str] = None
    thickness_mm: Optional[float] = None
    construction: str
    profile_code: str
    edge_radius_mm: float
    profiled_sides: str
    max_length_mm: int
    available_widths_mm: str  # JSON string
    edge_material: Optional[str] = None
    edge_material_thickness_mm: Optional[float] = None
    core_color: Optional[str] = None
    splashback_available: bool = False
    matching_board_available: bool = False


class AvailabilityOut(BaseModel):
    """Row from v_variants_availability."""
    variant_id: str
    decor_id: str
    decor_name: str
    producer: str
    material_type: str
    structure: Optional[str] = None
    thickness_mm: Optional[float] = None
    channel: str
    available: bool
    min_order_qty: int
    warehouse: Optional[str] = None
    lead_time: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class StatsOut(BaseModel):
    producers: int
    decors: int
    variants: int
    pairings: int
    worktops: int


# ── Configurator models ──────────────────────────────────────────


class SessionOut(BaseModel):
    session_token: str
    current_step: str


class SelectRequest(BaseModel):
    step: str
    variant_id: str | None = None
    edge_id: int | None = None


class ConfiguratorOption(BaseModel):
    variant_id: str | None = None
    edge_id: int | None = None
    name: str
    decor_name: str | None = None
    color_family: str | None = None
    img_url: str | None = None
    recommendation: str | None = None
    material_type: str | None = None
    structure: str | None = None
    thickness_mm: float | None = None


class ConfiguratorStepOut(BaseModel):
    current_step: str
    options: list[ConfiguratorOption]


class BOMItem(BaseModel):
    role: str
    variant_id: str | None = None
    edge_id: int | None = None
    name: str
    decor_name: str | None = None
    material_type: str | None = None
    structure: str | None = None
    thickness_mm: float | None = None


class BOMOut(BaseModel):
    complete: bool
    items: list[BOMItem]


class TemplateOut(BaseModel):
    slug: str
    name: str
    description: str | None = None
    hero_image: str | None = None
    front_variant_id: str | None = None


class FromTemplateRequest(BaseModel):
    template_slug: str
