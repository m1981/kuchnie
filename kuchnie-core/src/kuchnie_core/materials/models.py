"""Lightweight DTOs for material catalog data.

These are plain data containers — no logic, no DB dependency, no imports
from this package. Used by protocol.py, resolver.py, and catalog.py.

All fields use mm units (suffix _mm) per project convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VariantInfo:
    """Resolved material variant — the purchasable SKU.

    One Decor (K8685 "Biel Alpejska") can have many Variants
    (different thickness, material, structure). This represents ONE.
    """
    code: str                      # "K8685-CH-18-SM"
    decor_code: str                # "K8685"
    decor_name: str                # "Biel Alpejska"
    producer: str                  # "kronospan"
    material_type: str             # "chipboard", "mdf_acrylic", "worktop_postformed"
    structure: str                 # "SM", "PE", "RS"
    thickness_mm: float            # 18.0, 18.3, 38.0
    roles: tuple[str, ...] = ()    # ("front", "carcass"), ("worktop",)
    format_mm: tuple[int, int] = (0, 0)  # (2800, 2070)
    sidedness: str = ""            # "two_sided_same", "one_sided"
    hpl_available: bool = False
    splashback_available: bool = False


@dataclass(frozen=True)
class EdgeInfo:
    """Edge banding product — applied to ONE edge of a panel."""
    code: str                      # "WK-8685-RS"
    supplier: str                  # "schilsner", "rehau"
    material: str                  # "ABS", "Unoflex", "HPL"
    thickness_mm: float            # 1.2, 1.5
    width_mm: float                # 23, 42, 43
    radius_mm: float = 0           # 3.3, 1.5, 0


@dataclass(frozen=True)
class WorktopInfo:
    """Worktop-specific specification."""
    variant_code: str              # "868S-PF-U-600"
    decor_code: str                # "868S"
    decor_name: str                # "Biel Alpejska"
    construction: str              # "postformed", "slim_line", "black_wood"
    profile: str                   # "U", "U-U", "R3", "SQUARE", "NATURAL"
    edge_radius_mm: float          # 3.3, 1.5, 0
    available_widths_mm: tuple[int, ...] = ()  # (600, 900, 1200)
    max_length_mm: int = 4100
    edge_material: str = ""        # "Unoflex", "ABS 1.5mm", "naturalna"
    thickness_mm: float = 38.0
    core_color: str = ""           # "Biały", "Czarny" (Slim Line only)


@dataclass(frozen=True)
class PropertyFlag:
    """A boolean property of a variant (EAV-style)."""
    property: str                  # "antibacterial", "waterproof"
    value: bool = True


@dataclass(frozen=True)
class AvailabilityInfo:
    """Stock/delivery status for a variant."""
    channel: str                   # "express_24h", "konfekcja", "standard"
    available: bool = True
    warehouse: str = ""            # "Mielec", "Żary"
    lead_time: str = ""            # "24h", "7d"
    min_order_qty: int = 1
