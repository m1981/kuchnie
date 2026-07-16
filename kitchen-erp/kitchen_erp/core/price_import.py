# kitchen_erp/core/price_import.py
"""Supplier price ingestion — wk-39ed9155 (spec:
docs/specs/purchasing-variants.md § "Price ingestion").

One doorway, many sources. Two-phase, provenance-first:

1. Capture — the raw source file is archived verbatim before anything is
   parsed; every landed row's source_ref points at the archive copy.
2. Normalize — every source is mapped onto the ONE canonical landing schema
   (semicolon CSV):

       supplier;item_code;description;unit;price_net;currency;valid_from;source_ref

   The first adapter is the dumbest that works: a column-map config turning
   an arbitrary supplier CSV into landing rows. XLS/PDF adapters come later
   (kuchnie-hij follow-ups); suppliers' XLS exports re-save as CSV meanwhile.
3. Validate before import — schema-incomplete rows, insane units, unparsable
   numbers/dates and price jumps beyond ±tolerance of the last known price
   are REFUSED with a reason, never coerced. Refusals go back to a human.

Accepted rows land append-only in SupplierPrice; Material.price_per_unit is
then updated for mirrored rows (item_code == catalog_variant_id) — pricing
is the ERP's own domain, exactly the write the material mirror abstains
from (material_mirror.py).

Prices decay: valid_from + PRICE_TTL_DAYS is an implicit expiry. A quote
standing on a stale (or provenance-free) price renders ESTIMATE-grade with
the age visible (assess_quote_freshness). Estimate ≠ offer, everywhere,
forever.
"""
from __future__ import annotations

import csv
import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from sqlmodel import Session, select

from .models import Material, SupplierPrice

LANDING_FIELDS = (
    "supplier", "item_code", "description", "unit",
    "price_net", "currency", "valid_from", "source_ref",
)
# Fields that must be non-empty for a row to be schema-complete.
# description is allowed empty; source_ref is stamped with the archive path.
_REQUIRED_FIELDS = ("supplier", "item_code", "unit", "price_net", "currency", "valid_from")

# Units a supplier price may be quoted in (BOMPart units + Polish synonyms).
SANE_UNITS = {"m2", "lm", "mb", "pcs", "szt", "sets", "kpl"}

# Price-jump gate: a new price further than this fraction from the last
# known price for the same item_code is refused for human eyeballs.
DEFAULT_TOLERANCE = 0.5

# Implicit TTL on every landed price (spec: "prices decay").
PRICE_TTL_DAYS = 90


class LandingSchemaError(ValueError):
    """The file as a whole cannot be read as landing rows (wrong header,
    wrong delimiter, unsupported format). Per-row problems are Refusals."""


@dataclass
class Refusal:
    """One refused row: never imported, never coerced."""
    line_no: int
    reason: str
    raw: dict


@dataclass
class ImportReport:
    archived_path: str
    accepted: list[SupplierPrice] = field(default_factory=list)
    refused: list[Refusal] = field(default_factory=list)
    materials_updated: int = 0
    unmatched_item_codes: list[str] = field(default_factory=list)


def archive_source(source: Path, archive_dir: Path) -> Path:
    """Copy the raw source verbatim into archive_dir (capture phase).
    Name = <sha256:8>-<original name>, so re-imports of identical files
    land on the same archive copy."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:8]
    target = archive_dir / f"{digest}-{source.name}"
    if not target.exists():
        shutil.copy2(source, target)
    return target


def read_source_rows(
    source: Path,
    column_map: dict[str, str] | None = None,
    constants: dict[str, str] | None = None,
) -> list[dict]:
    """Normalize phase: read a CSV source into raw landing-field dicts.

    Without column_map the file must be the canonical landing CSV
    (semicolon-separated, exact header). With column_map (landing field →
    source column name) any delimiter-sniffed CSV is adapted; constants
    fill landing fields the source has no column for (typically supplier
    and currency, known per file); unmapped optional fields default empty."""
    if source.suffix.lower() not in {".csv", ".txt"}:
        raise LandingSchemaError(
            f"unsupported source format '{source.suffix}': only CSV adapters exist "
            "(re-save XLS as CSV, or wire a new adapter)"
        )
    text = source.read_text(encoding="utf-8-sig")
    if column_map is None:
        reader = csv.DictReader(text.splitlines(), delimiter=";")
        if tuple(reader.fieldnames or ()) != LANDING_FIELDS:
            raise LandingSchemaError(
                f"header is not the landing schema {';'.join(LANDING_FIELDS)!r} "
                f"(got {reader.fieldnames!r}); pass column_map for supplier formats"
            )
        return [dict(row) for row in reader]

    constants = constants or {}
    missing = [f for f in _REQUIRED_FIELDS if f not in column_map and f not in constants]
    if missing:
        raise LandingSchemaError(f"column_map/constants lack required landing fields: {missing}")
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=";,\t")
    except (csv.Error, IndexError) as exc:
        raise LandingSchemaError(f"cannot sniff CSV dialect: {exc}") from exc
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    rows = []
    for row in reader:
        landed = {}
        for f in LANDING_FIELDS:
            src = column_map.get(f)
            landed[f] = (row.get(src) or "").strip() if src else constants.get(f, "")
        rows.append(landed)
    return rows


def _last_known_price(session: Session, item_code: str) -> float | None:
    row = session.exec(
        select(SupplierPrice)
        .where(SupplierPrice.item_code == item_code)
        .order_by(SupplierPrice.valid_from.desc(), SupplierPrice.id.desc())  # type: ignore[union-attr]
    ).first()
    return row.price_net if row else None


def validate_landing_rows(
    rows: list[dict],
    session: Session,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    source_ref: str = "",
) -> tuple[list[SupplierPrice], list[Refusal]]:
    """Validate phase. Returns (accepted SupplierPrice objects — NOT yet
    added to the session — and refusals). Refused rows are reported with a
    reason and never coerced. Line numbers count data rows from 2 (header=1)."""
    accepted: list[SupplierPrice] = []
    refused: list[Refusal] = []
    for i, raw in enumerate(rows, start=2):
        missing = [f for f in _REQUIRED_FIELDS if not (raw.get(f) or "").strip()]
        if missing:
            refused.append(Refusal(i, f"schema-incomplete: missing {', '.join(missing)}", raw))
            continue
        unit = raw["unit"].strip()
        if unit not in SANE_UNITS:
            refused.append(Refusal(i, f"unit '{unit}' not in {sorted(SANE_UNITS)}", raw))
            continue
        try:
            price_net = float(raw["price_net"].replace(",", "."))
        except ValueError:
            refused.append(Refusal(i, f"price_net '{raw['price_net']}' is not a number", raw))
            continue
        if price_net <= 0:
            refused.append(Refusal(i, f"price_net {price_net} must be > 0", raw))
            continue
        currency = raw["currency"].strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            refused.append(Refusal(i, f"currency '{raw['currency']}' is not a 3-letter code", raw))
            continue
        try:
            valid_from = date.fromisoformat(raw["valid_from"].strip())
        except ValueError:
            refused.append(Refusal(i, f"valid_from '{raw['valid_from']}' is not an ISO date", raw))
            continue
        item_code = raw["item_code"].strip()
        last = _last_known_price(session, item_code)
        if last is not None and abs(price_net - last) > tolerance * last:
            refused.append(Refusal(
                i,
                f"price jump {last} -> {price_net} exceeds ±{tolerance:.0%} of last "
                "known — needs human eyeballs",
                raw,
            ))
            continue
        accepted.append(SupplierPrice(
            supplier=raw["supplier"].strip(),
            item_code=item_code,
            description=(raw.get("description") or "").strip(),
            unit=unit,
            price_net=price_net,
            currency=currency,
            valid_from=valid_from,
            source_ref=(raw.get("source_ref") or "").strip() or source_ref,
        ))
    return accepted, refused


def import_price_file(
    session: Session,
    source: Path,
    archive_dir: Path,
    *,
    column_map: dict[str, str] | None = None,
    constants: dict[str, str] | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> ImportReport:
    """The doorway: capture → normalize → validate → land → update Material.

    Accepted rows are committed to SupplierPrice; Material.price_per_unit is
    updated where catalog_variant_id == item_code (newest valid_from wins).
    Refused rows are only reported. Raises LandingSchemaError if the file as
    a whole is unreadable (nothing is landed, but the capture copy stays)."""
    source = Path(source)
    archived = archive_source(source, Path(archive_dir))
    rows = read_source_rows(source, column_map, constants)
    accepted, refused = validate_landing_rows(
        rows, session, tolerance=tolerance, source_ref=str(archived)
    )
    report = ImportReport(archived_path=str(archived), accepted=accepted, refused=refused)

    for price in accepted:
        session.add(price)
    # newest valid_from per item_code drives the Material update
    newest: dict[str, SupplierPrice] = {}
    for price in accepted:
        cur = newest.get(price.item_code)
        if cur is None or price.valid_from >= cur.valid_from:
            newest[price.item_code] = price
    for item_code, price in newest.items():
        material = session.exec(
            select(Material).where(Material.catalog_variant_id == item_code)
        ).first()
        if material is None:
            report.unmatched_item_codes.append(item_code)
            continue
        material.price_per_unit = price.price_net
        session.add(material)
        report.materials_updated += 1
    session.commit()
    return report


# --- Freshness: prices decay (spec: "quotes standing on stale prices render
# estimate-grade with age visible") ---------------------------------------

@dataclass
class PriceFreshness:
    material_id: int | None
    material_name: str
    valid_from: date | None   # None = no supplier provenance (hand-priced)
    age_days: int | None      # visible age; None when no provenance
    status: str               # "fresh" | "stale" | "no_provenance"


@dataclass
class QuoteFreshness:
    grade: str                # "current" | "estimate"
    lines: list[PriceFreshness]


def assess_quote_freshness(
    session: Session,
    materials: list[Material],
    *,
    as_of: date | None = None,
    ttl_days: int = PRICE_TTL_DAYS,
) -> QuoteFreshness:
    """Grade a quote by the freshness of every price it stands on. Any
    stale or provenance-free price renders the whole quote estimate-grade
    (grade="estimate"), with per-line age visible."""
    as_of = as_of or datetime.utcnow().date()
    lines: list[PriceFreshness] = []
    for material in materials:
        latest = None
        if material.catalog_variant_id:
            latest = session.exec(
                select(SupplierPrice)
                .where(SupplierPrice.item_code == material.catalog_variant_id)
                .order_by(SupplierPrice.valid_from.desc(), SupplierPrice.id.desc())  # type: ignore[union-attr]
            ).first()
        if latest is None:
            lines.append(PriceFreshness(material.id, material.name, None, None, "no_provenance"))
            continue
        age = (as_of - latest.valid_from).days
        status = "fresh" if age <= ttl_days else "stale"
        lines.append(PriceFreshness(material.id, material.name, latest.valid_from, age, status))
    grade = "current" if lines and all(l.status == "fresh" for l in lines) else "estimate"
    return QuoteFreshness(grade=grade, lines=lines)
