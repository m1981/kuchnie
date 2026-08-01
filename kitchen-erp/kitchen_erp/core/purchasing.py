"""Purchasing strategies for material procurement"""
from abc import ABC, abstractmethod
from math import ceil
import csv
import io
import re
from dataclasses import dataclass


class PurchasingStrategy(ABC):
    """
    Abstract base class for purchasing strategies.
    
    Different materials are purchased in different ways:
    - Sheet materials (boards) come in fixed sizes
    - Linear materials (edgebanding) come in rolls
    - Countertops come in standard lengths
    - Hardware comes in exact quantities
    """
    
    @abstractmethod
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """
        Calculate the actual quantity to purchase based on net requirement.
        
        Args:
            net_quantity: The exact amount needed
            
        Returns:
            The amount to actually purchase (may be higher due to standard sizes)
        """
        pass
    
    @abstractmethod
    def get_waste_factor(self, net_quantity: float) -> float:
        """
        Calculate the waste factor for this purchase.
        
        Returns:
            Ratio of purchased to net quantity (e.g., 1.2 = 20% waste)
        """
        pass


class SheetMaterialStrategy(PurchasingStrategy):
    """
    Strategy for sheet materials (MDF, plywood, etc.) sold in full sheets.
    Takes into account woodgrain direction which increases nesting waste.
    """

    def __init__(self, sheet_size_m2: float = 5.796, has_woodgrain: bool = False):
        self.sheet_size_m2 = sheet_size_m2
        self.has_woodgrain = has_woodgrain

    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        if net_quantity == 0:
            return 0

        # Jeśli płyta ma usłojenie (woodgrain), program do nestingu nie może
        # obracać formatek o 90 stopni. Zwiększamy zapotrzebowanie netto o 15%
        # przed zaokrągleniem do pełnych arkuszy.
        effective_net = net_quantity * 1.15 if self.has_woodgrain else net_quantity

        sheets_needed = ceil(effective_net / self.sheet_size_m2)
        return sheets_needed * self.sheet_size_m2

    def get_waste_factor(self, net_quantity: float) -> float:
        if net_quantity == 0:
            return 1.0
        purchase_qty = self.calculate_purchase_quantity(net_quantity)
        return purchase_qty / net_quantity


class LinearMaterialStrategy(PurchasingStrategy):
    """
    Strategy for linear materials (edgebanding, profiles) sold in rolls.
    
    Example: Edgebanding comes in 50m rolls
    If you need 45m, you buy 1 roll = 50m
    If you need 55m, you buy 2 rolls = 100m
    """
    
    def __init__(self, roll_length_m: float = 50.0, waste_factor: float = 1.10):
        """
        Initialize linear material strategy.
        
        Args:
            roll_length_m: Length of one roll in meters
            waste_factor: Additional waste for cutting (default 10%)
        """
        self.roll_length_m = roll_length_m
        self.waste_factor = waste_factor
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """Calculate number of full rolls needed, including waste"""
        net_with_waste = net_quantity * self.waste_factor
        rolls_needed = ceil(net_with_waste / self.roll_length_m)
        return rolls_needed * self.roll_length_m
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Calculate total waste factor including cutting waste and roll rounding"""
        purchase_qty = self.calculate_purchase_quantity(net_quantity)
        return purchase_qty / net_quantity if net_quantity > 0 else 1.0


class CountertopStrategy(PurchasingStrategy):
    """
    Strategy for countertops sold in standard lengths.
    
    Example: HPL countertops come in 4100mm lengths
    If you need 3500mm, you buy 1 piece = 4100mm
    If you need 5000mm, you buy 2 pieces = 8200mm
    """
    
    def __init__(self, standard_length_mm: float = 4100.0, width_mm: float = 600.0):
        """
        Initialize countertop strategy.
        
        Args:
            standard_length_mm: Standard length in millimeters
            width_mm: Standard width in millimeters
        """
        self.standard_length_mm = standard_length_mm
        self.width_mm = width_mm
        self.standard_area_m2 = (standard_length_mm * width_mm) / 1_000_000
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """
        Calculate countertop purchase quantity.
        
        Args:
            net_quantity: Net area in m² or length in linear meters
            
        Returns:
            Purchase quantity in m²
        """
        # Assume net_quantity is in m² (area)
        pieces_needed = ceil(net_quantity / self.standard_area_m2)
        return pieces_needed * self.standard_area_m2
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Calculate waste factor for countertop"""
        purchase_qty = self.calculate_purchase_quantity(net_quantity)
        return purchase_qty / net_quantity if net_quantity > 0 else 1.0


class ExactQuantityStrategy(PurchasingStrategy):
    """
    Strategy for items purchased in exact quantities (hardware, hinges, etc.).
    
    No rounding to standard sizes, but may include a small waste factor
    for damaged/lost items.
    """
    
    def __init__(self, waste_factor: float = 1.05):
        """
        Initialize exact quantity strategy.
        
        Args:
            waste_factor: Small buffer for damaged items (default 5%)
        """
        self.waste_factor = waste_factor
    
    def calculate_purchase_quantity(self, net_quantity: float) -> float:
        """Calculate purchase quantity with small waste buffer"""
        return ceil(net_quantity * self.waste_factor)
    
    def get_waste_factor(self, net_quantity: float) -> float:
        """Return the configured waste factor"""
        return self.waste_factor


def get_strategy_for_material(material_category: str) -> PurchasingStrategy:
    """
    Factory function to get appropriate purchasing strategy for material category.
    
    Args:
        material_category: Category of material (e.g., "Board", "Edgebanding", "Countertop")
        
    Returns:
        Appropriate PurchasingStrategy instance
    """
    strategies = {
        "Board": SheetMaterialStrategy(),
        "Panel": SheetMaterialStrategy(),
        "Edgebanding": LinearMaterialStrategy(),
        "Countertop": CountertopStrategy(),
        "Hardware": ExactQuantityStrategy(),
        "Equipment": ExactQuantityStrategy(waste_factor=1.0),  # No waste for equipment
    }
    
    return strategies.get(material_category, ExactQuantityStrategy())


# ---------------------------------------------------------------------------
# wk-593a317b — purchasing order-doc generators (board / edging / hardware)
# ---------------------------------------------------------------------------
#
# These consume ONLY kuchnie_core outputs — calculate_bom() items, edging
# rows (kuchnie_core.export.edging_csv.collect_edging_rows), and
# result.accessories — and never re-derive panel geometry (ADR-015). The
# three row shapes below mirror the hand-computed, owner-confirmed goldens:
#   exercises/walking-skeleton-d60/reference/board-order.csv
#   exercises/walking-skeleton-d60/reference/edging-order.csv
#   exercises/walking-skeleton-d60/reference/hardware-order.csv
# purchasing-ASSUMPTIONS.md (same directory) carries the confirmed business
# rules encoded here: formatki-first (cutting-service is the primary
# artifact, full sheets are a batching view), waste-by-decor-class,
# screws/staples as stock draws (never a PO line), Blum components as
# separate order lines, pack-rounding +1 spare on small fittings.

from kuchnie_core.bom import calculate_bom
from kuchnie_core.export.edging_csv import collect_edging_rows
from kuchnie_core.model import Accessory, DecompositionResult

from .domain_adapter import role_bucket

SHEET_FORMAT = "2800x2070"
SHEET_AREA_M2 = 2.8 * 2.07  # 5.796 m2 per full sheet (2800x2070mm)
ROLL_LENGTH_MB = 150.0

# Owner-confirmed 2026-08-01 (purchasing-ASSUMPTIONS.md #2): waste by decor
# class — plain white 15%, directional decor (grain-matched, nesting can't
# rotate 90deg) 20%, HDF backs 10%. Deliberately separate from the generic
# SheetMaterialStrategy above (that one assumes a single fixed woodgrain
# factor; this purchasing doc needs a waste class per decor).
WASTE_BY_CLASS: dict[str, float] = {
    "plain": 0.15,
    "directional": 0.20,
    "hdf": 0.10,
}


def _material_meta(result: DecompositionResult) -> dict[str, tuple[int, str]]:
    """First-seen (thickness_mm, pricing_bucket) per BOARD material code —
    read directly off already-computed panels (not re-derived) purely to
    annotate/order rows; the net area itself comes from calculate_bom."""
    meta: dict[str, tuple[int, str]] = {}
    for p in result.panels:
        meta.setdefault(p.material, (p.thickness_mm, role_bucket(p.role)))
    return meta


def _edge_material_bucket(result: DecompositionResult) -> dict[str, str]:
    """First-seen pricing bucket per EDGE-BAND material code, derived from
    the panel each banded edge belongs to."""
    out: dict[str, str] = {}
    for p in result.panels:
        bucket = role_bucket(p.role)
        for band in p.banded_edges.values():
            out.setdefault(band.material, bucket)
    return out


# Row order in every generated doc follows this pricing-bucket priority
# (matches the goldens: carcass/corpus board first, drawer-box board next,
# front board, back/HDF last).
_BUCKET_ORDER: dict[str, int] = {"corpus": 0, "box": 1, "front": 2, "back": 3}


# ── Board order ─────────────────────────────────────────────────

@dataclass(frozen=True)
class _BoardDecor:
    producer: str
    decor: str
    structure: str
    waste_class: str  # key into WASTE_BY_CLASS


# core material code -> board decor identity. An unmapped material raises
# (a silently-wrong purchasing doc is worse than a loud KeyError) — extend
# this catalog when a new decor/board is introduced.
BOARD_DECOR_CATALOG: dict[str, _BoardDecor] = {
    "PLYTA_BIALA_18": _BoardDecor("Kronospan", "bialy korpusowy", "PE", "plain"),
    "plyta_16mm": _BoardDecor("Kronospan", "bialy korpusowy", "PE", "plain"),
    "K5307_18": _BoardDecor("Kronospan", "K5307 Dab Artisan", "SN", "directional"),
    "HDF_BIALA_3": _BoardDecor("Kronospan", "HDF bialy lakierowany", "", "hdf"),
}


@dataclass
class BoardOrderRow:
    dostawca: str
    producent: str
    dekor: str
    struktura: str
    grubosc_mm: int
    format_plyty: str
    netto_m2: float
    zapas_proc: int
    brutto_m2: float
    arkusze: int
    tryb_zamowienia: str
    uwagi: str = ""


def board_order_rows(result: DecompositionResult) -> list[BoardOrderRow]:
    """Cutting-service (formatki) board order — one row per board decor.

    Primary purchasing artifact per the 2026-08-01 owner confirmation
    (purchasing-ASSUMPTIONS.md #1: "formatki-first"): net area folds from
    calculate_bom(), waste applies by decor class, sheet count is recorded
    only as the batching-alternative view (Tryb_zamowienia stays pinned to
    the cutting-service mode).
    """
    meta = _material_meta(result)
    net_m2: dict[str, float] = {}
    for item in calculate_bom(result).items:
        if item.category != "panel":
            continue
        net_m2[item.material] = net_m2.get(item.material, 0.0) + item.measure

    rows: list[BoardOrderRow] = []
    for material in sorted(
        net_m2, key=lambda m: _BUCKET_ORDER.get(meta[m][1], 99)
    ):
        decor = BOARD_DECOR_CATALOG.get(material)
        if decor is None:
            raise ValueError(
                f"board_order_rows: no BOARD_DECOR_CATALOG entry for "
                f"material {material!r} — add one before an order doc can "
                f"be generated"
            )
        net = round(net_m2[material], 3)
        waste = WASTE_BY_CLASS[decor.waste_class]
        gross = round(net * (1 + waste), 3)
        sheets = ceil(gross / SHEET_AREA_M2)
        rows.append(BoardOrderRow(
            dostawca="hurtownia plyt",
            producent=decor.producer,
            dekor=decor.decor,
            struktura=decor.structure,
            grubosc_mm=meta[material][0],
            format_plyty=SHEET_FORMAT,
            netto_m2=net,
            zapas_proc=int(round(waste * 100)),
            brutto_m2=gross,
            arkusze=sheets,
            tryb_zamowienia="formatki (usluga ciecia)",
        ))
    return rows


BOARD_ORDER_HEADER = [
    "Dostawca", "Producent", "Dekor", "Struktura", "Grubosc_mm",
    "Format_plyty", "Netto_m2", "Zapas_proc", "Brutto_m2", "Arkusze",
    "Tryb_zamowienia", "Uwagi",
]


def board_order_rows_to_csv(rows: list[BoardOrderRow]) -> str:
    """Render board-order rows to a semicolon-separated CSV string
    matching board-order.csv's schema exactly."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(BOARD_ORDER_HEADER)
    for r in rows:
        writer.writerow([
            r.dostawca, r.producent, r.dekor, r.struktura, r.grubosc_mm,
            r.format_plyty, f"{r.netto_m2:.3f}", r.zapas_proc,
            f"{r.brutto_m2:.3f}", r.arkusze, r.tryb_zamowienia, r.uwagi,
        ])
    return buf.getvalue()


# ── Edging order ────────────────────────────────────────────────

@dataclass(frozen=True)
class _EdgeIdentity:
    producer: str
    decor: str
    width_mm: float
    # "carcass" = white/carcass decor, standing roll already stocked
    #             (order line draws 0)
    # "job"     = job-specific decor, cut-to-length mb, rounded up +1mb
    #             buffer (purchasing-ASSUMPTIONS.md #7)
    order_class: str


# G11 edge identity (material + thickness) -> purchase identity. Width is
# supplier/decor-dependent and NOT derived by kuchnie_core (model.py
# EdgeBand.width_mm docstring) — this is exactly the "ERP catalog layer"
# caller that docstring names. An unmapped identity raises.
EDGE_IDENTITY_CATALOG: dict[str, _EdgeIdentity] = {
    "abs_PLYTA_BIALA_18": _EdgeIdentity("Kronospan", "bialy korpusowy", 22.0, "carcass"),
    "abs_K5307_18": _EdgeIdentity("Kronospan", "K5307 Dab Artisan SN", 22.0, "job"),
}


@dataclass
class EdgingOrderRow:
    dostawca: str
    producent_dekoru: str
    dekor: str
    grubosc_mm: float
    szerokosc_mm: float
    netto_mb: float
    jednostka_zamowienia: str
    ilosc_zamowiona: int
    dlugosc_rolki_mb: float
    uwagi: str = ""


def edging_order_rows(result: DecompositionResult) -> list[EdgingOrderRow]:
    """Edge-band order — one row per G11 edge identity (material +
    thickness). Standing 150mb roll (qty-0 draw) for white/carcass decors
    already stocked; cut-to-length mb, rounded up +1mb buffer, for
    job-specific decors (purchasing-ASSUMPTIONS.md #7).
    """
    bucket_by_material = _edge_material_bucket(result)
    net_mb: dict[tuple[str, float], float] = {}
    for row in collect_edging_rows(result.panels):
        key = (row.material, row.thickness_mm)
        net_mb[key] = net_mb.get(key, 0.0) + row.length_mm / 1000

    rows: list[EdgingOrderRow] = []
    for material, thickness in sorted(
        net_mb,
        key=lambda k: _BUCKET_ORDER.get(bucket_by_material.get(k[0], ""), 99),
    ):
        ident = EDGE_IDENTITY_CATALOG.get(material)
        if ident is None:
            raise ValueError(
                f"edging_order_rows: no EDGE_IDENTITY_CATALOG entry for "
                f"material {material!r} — add one before an order doc can "
                f"be generated"
            )
        net = round(net_mb[(material, thickness)], 2)
        if ident.order_class == "carcass":
            unit = "rolka (zapas staly)"
            ordered = 0
        else:
            unit = "mb (docinka u dealera)"
            ordered = ceil(net) + 1
        rows.append(EdgingOrderRow(
            dostawca="hurtownia plyt",
            producent_dekoru=ident.producer,
            dekor=ident.decor,
            grubosc_mm=thickness,
            szerokosc_mm=ident.width_mm,
            netto_mb=net,
            jednostka_zamowienia=unit,
            ilosc_zamowiona=ordered,
            dlugosc_rolki_mb=ROLL_LENGTH_MB,
        ))
    return rows


EDGING_ORDER_HEADER = [
    "Dostawca", "Producent_dekoru", "Dekor", "Grubosc_mm", "Szerokosc_mm",
    "Netto_mb", "Jednostka_zamowienia", "Ilosc_zamowiona", "Dlugosc_rolki_mb",
    "Uwagi",
]


def edging_order_rows_to_csv(rows: list[EdgingOrderRow]) -> str:
    """Render edging-order rows to a semicolon-separated CSV string
    matching edging-order.csv's schema exactly."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(EDGING_ORDER_HEADER)
    for r in rows:
        writer.writerow([
            r.dostawca, r.producent_dekoru, r.dekor, f"{r.grubosc_mm:.1f}",
            f"{r.szerokosc_mm:.0f}", f"{r.netto_mb:.2f}",
            r.jednostka_zamowienia, r.ilosc_zamowiona,
            f"{r.dlugosc_rolki_mb:.0f}", r.uwagi,
        ])
    return buf.getvalue()


# ── Hardware order ──────────────────────────────────────────────

@dataclass
class HardwareOrderRow:
    dostawca: str
    pozycja: str
    kod_producenta: str
    ilosc_netto: int
    regula_zapasu: str
    ilosc_zamowiona: int
    jm: str
    uwagi: str = ""


# Display priority for LEGRABOX height codes in the order doc (mirrors
# kuchnie_core.legrabox.HEIGHTS key order: N, M, K, C, F).
_LEGRABOX_HEIGHT_ORDER = ["N", "M", "K", "C", "F"]

# Verified Blum SKUs only (purchasing-ASSUMPTIONS.md "component codes
# verified vs guessed") — an unmapped height/NL combination raises rather
# than guessing a wrong part number.
_BLUM_SIDE_CODES: dict[tuple[str, int], str] = {
    ("M", 500): "770M5002S",
    ("C", 500): "770C5002S",
}
_BLUM_SIDE_NAME_TEMPLATES: dict[str, str] = {
    "M": "LEGRABOX pure boki M NL{nl} {cap}kg {colour}",
    "C": "LEGRABOX pure boki C NL{nl} {cap}kg {colour}",
}
# Blum base codes carry geometry only; colour rides in a suffix the dealer
# wraps into their own SKU (owner's dealer listings 2026-08-02: JBM =
# jedwabiscie bialy, CS-M = czarny carbon, ATM = antracyt). Colour is a
# per-project parameter (owner decision 2026-08-02); this is the default.
DEFAULT_LEGRABOX_COLOUR = "jedwabiscie bialy (JBM)"
_BLUM_REAR_COUPLING_CODES: dict[str, str] = {
    "M": "ZB7M000S",
    "C": "ZB7C000S",
}
_BLUM_RUNNER_CODE = "750.5001S"
_BLUM_RUNNER_NAME_TEMPLATE = "Prowadnica korpusu BLUMOTION S {cap}kg NL{nl} (L+P)"
_LEG_CODE = "NM-BD-100-01"

_LEGRABOX_NAME_RE = re.compile(r"^LEGRABOX (?P<height>[A-Z]) NL(?P<nl>\d+) (?P<cap>\d+)kg")


def _parse_legrabox_accessory(acc: Accessory) -> tuple[str, int, int]:
    """(height_code, nl, capacity_kg) parsed from a
    legrabox.make_runner_accessory() name — the only structured data an
    Accessory carries; catalog.py owns the format, this just reads it."""
    m = _LEGRABOX_NAME_RE.match(acc.name)
    if not m:
        raise ValueError(
            f"hardware_order_rows: accessory {acc.name!r} (type="
            f"{acc.type!r}) looks like a LEGRABOX runner but its name "
            f"doesn't match 'LEGRABOX <H> NL<nl> <cap>kg...'"
        )
    return m.group("height"), int(m.group("nl")), int(m.group("cap"))


@dataclass(frozen=True)
class _StaticHardware:
    """Order-doc metadata for a G13 stock/plinth accessory. Keyed by
    Accessory.name, which catalog.py's G13 helpers keep byte-identical to
    these Pozycja strings by construction."""
    dostawca: str
    kod_producenta: str
    regula_zapasu: str
    jm: str
    stock_draw: bool  # True => Ilosc_zamowiona always 0 (never a PO line)
    pack_round: bool = False  # True => Ilosc_zamowiona rounds to 1 opak


# Screws/staples are stock draws, never PO lines (owner-confirmed
# 2026-08-01, purchasing-ASSUMPTIONS.md #5). Legs/clips round to a package
# with a +1 spare (purchasing-ASSUMPTIONS.md #6, still open on exact
# per-package counts).
_STATIC_HARDWARE_CATALOG: dict[str, _StaticHardware] = {
    "Konfirmat 7x50": _StaticHardware(
        "magazyn wlasny", "", "pobranie z zapasu (opak. 100+)", "szt",
        stock_draw=True),
    "Wkret euro 6.3x13": _StaticHardware(
        "magazyn wlasny", "", "pobranie z zapasu", "szt", stock_draw=True),
    "Zszywki/wkrety HDF": _StaticHardware(
        "magazyn wlasny", "", "pobranie z zapasu", "kpl", stock_draw=True),
    "Nozka regulowana 100 mm": _StaticHardware(
        "dealer okuc", _LEG_CODE, "zaokraglenie do opakowania +1", "opak",
        stock_draw=False, pack_round=True),
    "Klips cokolu + zaczep": _StaticHardware(
        "dealer okuc", "", "zaokraglenie do opakowania +1", "opak",
        stock_draw=False, pack_round=True),
}


def _pack_round_opak(net_qty: int) -> int:
    """+1 spare, rounded to a single dealer package. Real per-package piece
    counts are DO-POTWIERDZENIA (purchasing-ASSUMPTIONS.md #6) — this
    returns 1 opak for any positive net quantity (matches the D60 golden)
    and 0 when nothing is needed."""
    return 1 if net_qty > 0 else 0


def hardware_order_rows(
    result: DecompositionResult,
    legrabox_colour: str = DEFAULT_LEGRABOX_COLOUR,
) -> list[HardwareOrderRow]:
    """Hardware order doc.

    Blum LEGRABOX runner accessories explode into separate order lines —
    sides (boki), runner (prowadnica), rear coupling (sprzeglo) — per the
    2026-08-01 owner confirmation (purchasing-ASSUMPTIONS.md #8). Every
    other accessory (G13 stock draws + plinth hardware) looks up its
    order-doc metadata from _STATIC_HARDWARE_CATALOG by name. Consumes
    ONLY result.accessories (ADR-015) — no geometry is re-derived here.

    legrabox_colour is a per-project parameter (owner decision
    2026-08-02): Blum base codes are geometry-only, so colour appears in
    the Pozycja text of the colour-bearing lines (boki, sprzegla) and the
    dealer resolves it to their suffix-wrapped SKU at order time.
    """
    rows: list[HardwareOrderRow] = []

    legrabox_accs = [
        a for a in result.accessories
        if a.type == "runner" and a.name.startswith("LEGRABOX")
    ]
    legrabox_ids = {a.id for a in legrabox_accs}
    other_accs = [a for a in result.accessories if a.id not in legrabox_ids]

    if legrabox_accs:
        parsed = {acc.id: _parse_legrabox_accessory(acc) for acc in legrabox_accs}
        by_height: dict[str, int] = {}
        total_drawers = 0
        nl_cap_common: tuple[int, int] | None = None
        for acc in legrabox_accs:
            height, nl, cap = parsed[acc.id]
            by_height[height] = by_height.get(height, 0) + acc.quantity
            total_drawers += acc.quantity
            nl_cap_common = (nl, cap)

        ordered_heights = [h for h in _LEGRABOX_HEIGHT_ORDER if h in by_height]

        # -- sides (boki), one row per height code --
        for height in ordered_heights:
            qty = by_height[height]
            nl, cap = next(
                (nl, cap) for h, nl, cap in parsed.values() if h == height
            )
            code = _BLUM_SIDE_CODES.get((height, nl))
            if code is None:
                raise ValueError(
                    f"hardware_order_rows: no Blum side code for height "
                    f"{height!r} NL{nl} — add one to _BLUM_SIDE_CODES"
                )
            regula = ("dokladnie (unikalny SKU)" if height == ordered_heights[0]
                      else "dokladnie")
            rows.append(HardwareOrderRow(
                dostawca="dealer Blum",
                pozycja=_BLUM_SIDE_NAME_TEMPLATES[height].format(
                    nl=nl, cap=cap, colour=legrabox_colour),
                kod_producenta=code,
                ilosc_netto=qty,
                regula_zapasu=regula,
                ilosc_zamowiona=qty,
                jm="kpl",
            ))

        # -- runner (prowadnica), one row total, common across heights --
        nl, cap = nl_cap_common
        rows.append(HardwareOrderRow(
            dostawca="dealer Blum",
            pozycja=_BLUM_RUNNER_NAME_TEMPLATE.format(nl=nl, cap=cap),
            kod_producenta=_BLUM_RUNNER_CODE,
            ilosc_netto=total_drawers,
            regula_zapasu="dokladnie",
            ilosc_zamowiona=total_drawers,
            jm="kpl",
        ))

        # -- rear coupling (sprzeglo), one row per height code --
        for height in ordered_heights:
            qty = by_height[height]
            code = _BLUM_REAR_COUPLING_CODES.get(height)
            if code is None:
                raise ValueError(
                    f"hardware_order_rows: no Blum rear-coupling code for "
                    f"height {height!r} — add one to "
                    f"_BLUM_REAR_COUPLING_CODES"
                )
            rows.append(HardwareOrderRow(
                dostawca="dealer Blum",
                pozycja=f"Sprzeglo tylnej scianki {height}, {legrabox_colour}",
                kod_producenta=code,
                ilosc_netto=qty,
                regula_zapasu="dokladnie",
                ilosc_zamowiona=qty,
                jm="szt",
            ))

    for acc in other_accs:
        cat = _STATIC_HARDWARE_CATALOG.get(acc.name)
        if cat is None:
            raise ValueError(
                f"hardware_order_rows: no _STATIC_HARDWARE_CATALOG entry "
                f"for accessory {acc.name!r} (type={acc.type!r}) — add one "
                f"before an order doc can be generated"
            )
        ordered = (
            0 if cat.stock_draw else
            _pack_round_opak(acc.quantity) if cat.pack_round else
            acc.quantity
        )
        rows.append(HardwareOrderRow(
            dostawca=cat.dostawca,
            pozycja=acc.name,
            kod_producenta=cat.kod_producenta,
            ilosc_netto=acc.quantity,
            regula_zapasu=cat.regula_zapasu,
            ilosc_zamowiona=ordered,
            jm=cat.jm,
        ))

    return rows


HARDWARE_ORDER_HEADER = [
    "Dostawca", "Pozycja", "Kod_producenta", "Ilosc_netto", "Regula_zapasu",
    "Ilosc_zamowiona", "Jm", "Uwagi",
]


def hardware_order_rows_to_csv(rows: list[HardwareOrderRow]) -> str:
    """Render hardware-order rows to a semicolon-separated CSV string
    matching hardware-order.csv's schema exactly."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", lineterminator="\n")
    writer.writerow(HARDWARE_ORDER_HEADER)
    for r in rows:
        writer.writerow([
            r.dostawca, r.pozycja, r.kod_producenta, r.ilosc_netto,
            r.regula_zapasu, r.ilosc_zamowiona, r.jm, r.uwagi,
        ])
    return buf.getvalue()
