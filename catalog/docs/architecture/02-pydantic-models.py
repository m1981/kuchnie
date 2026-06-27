"""
KUCHNIE CATALOG — Pydantic v2 Models
Version: 1.0.0 (design)
Date: 2026-06-27

These models serve as:
  1. API request/response schemas (FastAPI)
  2. YAML/JSON validation (before DB insert)
  3. DB row mapping (via SQLAlchemy or raw queries)
  4. Business logic layer (domain models)

Hierarchy:
  Producer → Collection → Material → Variant
  Decor → Variant (many-to-many through Variant)
  Decor → Pairing → Decor
  Variant → VariantEdge → Edge
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────────────────
# ENUMS (constrained choices)
# ──────────────────────────────────────────────────────────────────


class MaterialTypeSlug(str, Enum):
    """What kind of product is this?"""
    CHIPBOARD = "chipboard"
    MDF_ACRYLIC = "mdf_acrylic"
    MDF_LACQUERED = "mdf_lacquered"
    MDF_FOIL = "mdf_foil"
    COMPACT = "compact"
    HPL = "hpl"
    WORKTOP_POSTFORMED = "worktop_postformed"
    WORKTOP_FITLINE = "worktop_fitline"
    WORKTOP_ABS_EDGE = "worktop_abs_edge"
    WORKTOP_SLIM = "worktop_slim"
    SPLASHBACK = "splashback"


class Role(str, Enum):
    """What can this variant be used for?"""
    CARCASS = "carcass"
    FRONT = "front"
    WORKTOP = "worktop"
    SPLASHBACK = "splashback"
    PLINTH = "plinth"
    SIDE_PANEL = "side_panel"
    HOUSING = "housing"
    HPL = "hpl"


class PairingType(str, Enum):
    """What kind of pairing is this?"""
    CARCASS = "carcass"
    WORKTOP = "worktop"
    SPLASHBACK = "splashback"
    SIDE_PANEL = "side_panel"
    PLINTH = "plinth"


class MatchType(str, Enum):
    """How well does the pairing match?"""
    EXACT = "exact"       # same decor, different material
    CLOSE = "close"       # similar color, different decor
    DEFAULT = "default"   # universal fallback (e.g., white carcass)


class Sidedness(str, Enum):
    """How is the board laminated?"""
    ONE_SIDED = "one_sided"
    TWO_SIDED_SAME = "two_sided_same"
    TWO_SIDED_DIFFERENT = "two_sided_different"


class StructureType(str, Enum):
    """Surface texture category."""
    SMOOTH = "smooth"
    WOOD_GRAIN = "wood_grain"
    STONE = "stone"
    METAL = "metal"


class StructureFinish(str, Enum):
    """Surface finish."""
    MATT = "matt"
    SILK_MATT = "silk_matt"
    GLOSS = "gloss"
    STRUCTURED = "structured"


# ──────────────────────────────────────────────────────────────────
# COLOR FAMILIES (enum for validation)
# ──────────────────────────────────────────────────────────────────

COLOR_FAMILIES = [
    "bialy", "bezowy", "szary", "czarny", "brazowy", "kremowy",
    "dab", "orzech", "jesion", "buk", "brzoza", "olcha",
    "wisnia", "klon", "wenge", "wiaz",
    "marmur", "beton", "lupek",
    "niebieski", "zielony", "czerwony", "rozowy", "zloty", "srebrny",
    "metal", "unikolor",
]


# ──────────────────────────────────────────────────────────────────
# BASE MODELS (shared fields)
# ──────────────────────────────────────────────────────────────────


class TimestampMixin(BaseModel):
    """Audit timestamps."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IDMixin(BaseModel):
    """Database primary key."""
    id: Optional[int] = None


# ──────────────────────────────────────────────────────────────────
# PRODUCER
# ──────────────────────────────────────────────────────────────────


class ProducerBase(BaseModel):
    """Producer create/update schema."""
    slug: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")
    name: str = Field(..., min_length=1, max_length=100)
    country: Optional[str] = None
    website: Optional[str] = None


class Producer(IDMixin, TimestampMixin, ProducerBase):
    """Producer read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# MATERIAL TYPE
# ──────────────────────────────────────────────────────────────────


class MaterialTypeBase(BaseModel):
    """Material type create/update schema."""
    slug: MaterialTypeSlug
    name: str = Field(..., min_length=1, max_length=100)
    core: str = Field(..., description="Core material: chipboard, mdf, compact, hpl")
    description: Optional[str] = None


class MaterialType(IDMixin, TimestampMixin, MaterialTypeBase):
    """Material type read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# COLLECTION
# ──────────────────────────────────────────────────────────────────


class CollectionBase(BaseModel):
    """Collection create/update schema."""
    slug: str = Field(..., min_length=1, max_length=50)
    producer_slug: str = Field(..., description="FK to producer.slug")
    name: str = Field(..., min_length=1, max_length=200)
    source_pdf: Optional[str] = None
    has_edgebanding: bool = True
    has_hdf: bool = False
    has_countertops: bool = False
    has_express: bool = False


class Collection(IDMixin, TimestampMixin, CollectionBase):
    """Collection read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# STRUCTURE
# ──────────────────────────────────────────────────────────────────


class StructureBase(BaseModel):
    """Structure create/update schema."""
    code: str = Field(..., min_length=2, max_length=5, pattern=r"^[A-Z0-9]+$")
    name: str = Field(..., min_length=1, max_length=100)
    type: Optional[StructureType] = None
    finish: Optional[StructureFinish] = None
    fingerprint_resistant: bool = False
    description: Optional[str] = None
    producer_slug: Optional[str] = None  # NULL = shared


class Structure(IDMixin, TimestampMixin, StructureBase):
    """Structure read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# MATERIAL (purchasable format)
# ──────────────────────────────────────────────────────────────────


class MaterialBase(BaseModel):
    """Material create/update schema."""
    slug: str = Field(..., min_length=1, max_length=50)
    material_type_slug: MaterialTypeSlug
    collection_slug: str
    name: str = Field(..., min_length=1, max_length=200)
    thicknesses_mm: Optional[list[int]] = None
    format_mm: Optional[list[int]] = None
    sidedness: Optional[Sidedness] = None
    has_edgebanding: bool = True
    has_hdf: bool = False
    has_express: bool = False


class Material(IDMixin, TimestampMixin, MaterialBase):
    """Material read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# DECOR
# ──────────────────────────────────────────────────────────────────


class DecorBase(BaseModel):
    """Decor create/update schema."""
    business_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Manufacturer's decor code: K8685, 868S, H3303",
    )
    producer_slug: str
    name: str = Field(..., min_length=1, max_length=200)
    group_name: Optional[str] = None
    color_family: Optional[str] = Field(None, description="Must be in COLOR_FAMILIES")
    ncs: Optional[str] = None
    ral: Optional[str] = None
    pantone: Optional[str] = None
    img: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("color_family")
    @classmethod
    def validate_color_family(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in COLOR_FAMILIES:
            raise ValueError(f"Invalid color_family: {v}. Must be one of {COLOR_FAMILIES}")
        return v

    @field_validator("business_id")
    @classmethod
    def validate_business_id(cls, v: str) -> str:
        # Kronospan: must start with K (except worktops like 868S)
        # Egger: starts with H
        # Swiss-Krono: TBD
        return v.strip()


class Decor(IDMixin, TimestampMixin, DecorBase):
    """Decor read schema (from DB)."""
    pass


class DecorWithVariants(Decor):
    """Decor with nested variants (for API responses)."""
    variants: list["Variant"] = []


# ──────────────────────────────────────────────────────────────────
# EDGE
# ──────────────────────────────────────────────────────────────────


class EdgeBase(BaseModel):
    """Edge create/update schema."""
    code: str = Field(..., min_length=1, max_length=50)
    supplier_slug: Optional[str] = None
    finish: Optional[str] = None
    material: Optional[str] = None
    thickness_mm: Optional[float] = None
    width_mm: Optional[float] = None
    radius_mm: Optional[float] = None
    notes: Optional[str] = None


class Edge(IDMixin, TimestampMixin, EdgeBase):
    """Edge read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# VARIANT
# ──────────────────────────────────────────────────────────────────


class VariantBase(BaseModel):
    """Variant create/update schema."""
    business_id: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Variant code: K8685-CH, 868S-PF-600",
    )
    decor_business_id: str = Field(..., description="FK to decor.business_id")
    material_slug: str = Field(..., description="FK to material.slug")
    structure_code: Optional[str] = Field(None, description="FK to structure.code")

    roles: list[Role] = Field(..., min_length=1, description="What can this variant be used for?")

    # Physical properties
    thickness_mm: Optional[float] = None
    width_mm: Optional[int] = None
    length_mm: Optional[int] = None
    format_mm: Optional[list[int]] = None
    sidedness: Optional[Sidedness] = None

    # Availability
    express: Optional[list[int]] = None
    konfekcja: bool = False
    splashback_available: bool = False
    hpl_available: bool = False
    countertop: Optional[str] = None
    multi_structures: Optional[str] = None

    # Edges
    edge_codes: Optional[list[str]] = Field(
        None, description="FK to edge.code — edges for this variant"
    )

    notes: Optional[str] = None


class Variant(IDMixin, TimestampMixin, VariantBase):
    """Variant read schema (from DB)."""
    pass


class VariantWithDecor(Variant):
    """Variant with nested decor (for API responses)."""
    decor: Optional[Decor] = None
    edges: list[Edge] = []


# ──────────────────────────────────────────────────────────────────
# PAIRING
# ──────────────────────────────────────────────────────────────────


class PairingBase(BaseModel):
    """Pairing create/update schema."""
    front_decor_id: str = Field(
        ...,
        description="FK to decor.business_id. Use '*' for wildcard (any decor).",
    )
    target_decor_id: str = Field(..., description="FK to decor.business_id")
    pairing_type: PairingType
    match_type: MatchType
    priority: int = Field(1, ge=1, le=99, description="1 = highest priority")
    notes: Optional[str] = None


class Pairing(IDMixin, TimestampMixin, PairingBase):
    """Pairing read schema (from DB)."""
    pass


class PairingWithDecors(Pairing):
    """Pairing with nested decor names (for API responses)."""
    front_decor_name: Optional[str] = None
    target_decor_name: Optional[str] = None


# ──────────────────────────────────────────────────────────────────
# TAG
# ──────────────────────────────────────────────────────────────────


class TagBase(BaseModel):
    """Tag create/update schema."""
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")


class Tag(IDMixin, TimestampMixin, TagBase):
    """Tag read schema (from DB)."""
    pass


# ──────────────────────────────────────────────────────────────────
# API REQUEST/RESPONSE SCHEMAS
# ──────────────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 1


class DecorFilter(BaseModel):
    """Query parameters for filtering decors."""
    producer: Optional[str] = None
    color_family: Optional[str] = None
    material_type: Optional[MaterialTypeSlug] = None
    role: Optional[Role] = None
    structure: Optional[str] = None
    tag: Optional[str] = None
    search: Optional[str] = None


class VariantFilter(BaseModel):
    """Query parameters for filtering variants."""
    decor_id: Optional[str] = None
    material_type: Optional[MaterialTypeSlug] = None
    role: Optional[Role] = None
    structure: Optional[str] = None
    thickness_mm: Optional[float] = None
    min_thickness: Optional[float] = None
    max_thickness: Optional[float] = None


class PairingQuery(BaseModel):
    """Query parameters for finding pairings."""
    front_decor_id: str
    pairing_type: PairingType
    match_types: Optional[list[MatchType]] = None


# ──────────────────────────────────────────────────────────────────
# MIGRATION SCHEMAS (YAML → DB)
# ──────────────────────────────────────────────────────────────────


class YamlVariant(BaseModel):
    """Variant as it appears in decors.yaml (for migration)."""
    id: str
    material: str
    collection: str
    structure: str
    roles: list[str]
    thickness_mm: Optional[float] = None
    format: Optional[list[int]] = None
    sidedness: Optional[str] = None
    express: Optional[list[int]] = None
    konfekcja: bool = False
    hdf_laminate: bool = False
    countertop: Optional[str] = None
    multi_structures: Optional[str] = None
    edge: Optional[dict] = None


class YamlDecor(BaseModel):
    """Decor as it appears in decors.yaml (for migration)."""
    id: str
    name: str
    group: str
    color_family: str
    tags: Optional[list[str]] = None
    ncs: Optional[str] = None
    ral: Optional[str] = None
    pantone: Optional[str] = None
    img: Optional[str] = None
    notes: Optional[str] = None
    variants: list[YamlVariant]


class YamlDecorsFile(BaseModel):
    """Top-level decors.yaml file structure."""
    _comment: Optional[str] = None
    _generated: Optional[str] = None
    decors: list[YamlDecor]


# ──────────────────────────────────────────────────────────────────
# REBUILD (for forward references)
# ──────────────────────────────────────────────────────────────────

DecorWithVariants.model_rebuild()
VariantWithDecor.model_rebuild()
