# ADR-012: `kuchnie_core.model` extensions required to unblock ADR-010

## Status

Accepted 2026-07-01. **Blocks execution of ADR-010** (migration mapping /
deleted sections).

## Context

ADR-010 renamed `kitchen-cad` → `kitchen-cam` and specified a migration
plan in which:

1. `kitchen_cam.machining` (`drill_engine.py`) imports `Panel`, `CabinetInstance`
   from `kuchnie_core.model`.
2. `kitchen_cam.models` / `panel_calculator` / `csv_generator` are deleted.
3. `kitchen_cam.dxf.legrabox_side_panel` pulls `LegraboxHeight` from
   `kuchnie_core.legrabox`.

Commit `8e85da1` executed only the rename ("Phase C"). The migration and
deletion phases were skipped because the domain models do not yet have
field parity. Attempting the swap causes `machining.py` to fail to
import: it references attributes that do not exist on `kuchnie_core`
types.

The additive part of ADR-010 that IS safe to execute today (CSV merge)
has been done: `kuchnie_core.export.cutlist_csv` already provided the
aggregated cutting list, and this commit adds `kuchnie_core.export.edging_csv`
for per-edge worklists. The Polish semicolon format (UTF-8-SIG BOM,
`;` delimiter, Polish headers) is preserved and now guarded by tests
(`tests/test_edging_csv.py::test_csv_uses_semicolon_delimiter`,
`test_cutlist_csv_polish_format`).

Everything else in ADR-010 requires model extensions in `kuchnie_core`.
This ADR enumerates those extensions so they can be executed as a single
coherent design pass rather than piecemeal.

## Decision

Extend `kuchnie_core.model` with the following before executing the
remaining ADR-010 steps. Ordering below matches implementation order:
each layer builds on the previous.

### 1. `PanelRole` (new enum in `kuchnie_core.model`)

```python
class PanelRole(str, Enum):
    LEFT_SIDE    = "left_side"
    RIGHT_SIDE   = "right_side"
    BOTTOM       = "bottom"
    TOP          = "top"
    SHELF        = "shelf"
    BACK         = "back"
    FRONT_DOOR   = "front_door"
    FRONT_DRAWER = "front_drawer"
    PLINTH       = "plinth"
```

Add `role: PanelRole | None = None` on `Panel`. Existing code that sets
`name="Lewy bok"` continues to work; new code that filters by role
(machining) sets `role` explicitly. English enum values keep the model
layer English-only (per AGENTS.md convention: "Model fields English,
YAML keys Polish"). Populate in `catalog.py` decomposition functions.

### 2. `MachiningOp` face + drill discriminators

```python
@dataclass
class MachiningOp:
    type: str                 # existing: "drill" | "groove" | "rabbet" | "dado"
    # NEW ↓
    face: str = "inside"      # "inside" | "outside" | "front" | "back"
    drill_type: str = ""      # "" | "system32" | "hinge_cup" | "hinge_screw"
                              # | "hinge_dowel" | "dowel_connector" | "minifix"
                              # | "handle" | "shelf_pin"
    # existing ↓
    x_mm: float = 0
    y_mm: float = 0
    diameter_mm: float = 0
    depth_mm: float = 0
    width_mm: float = 0
    length_mm: float = 0
    note: str = ""
```

Both new fields default to safe values so existing tests do not break.
`drill_type` remains a string (not enum) to keep the model lean and let
`kitchen-cam` extend the vocabulary without a core dependency inversion.

### 3. `HingeSpec` extension in `kuchnie_core.blum_hinges`

Add a plain dataclass `HingeGeometry` that the abstract `BlumHinge`
exposes:

```python
@dataclass(frozen=True)
class HingeGeometry:
    cup_diameter_mm: int       # already on BlumHinge
    cup_drill_depth_mm: int    # already on BlumHinge
    edge_to_cup_centre_mm: float = 5.0
    screw_spacing_mm: float    = 45.0
    screw_offset_x_mm: float   = 9.5
    screw_diameter_mm: float   = 3.0
    screw_depth_mm: float      = 2.0
    first_position_mm: float   = 100.0  # first hinge Y position from door edge

class BlumHinge:
    @property
    def geometry(self) -> HingeGeometry: ...
```

Provides `machining.apply_hinges` with the drilling geometry it needs
without a parallel `HingeSpec` type.

### 4. `HandleSpec` (new, on `CabinetInstance`)

```python
@dataclass
class HandleSpec:
    type: str = "bar"          # "bar" | "knob" | "profile" | "recessed"
    spacing_mm: float = 128.0  # centre-to-centre distance
    hole_diameter_mm: float = 5.0
    position: str = "center"   # "center" | "top" | "bottom"
```

Replace `CabinetInstance.handles: dict` with `handles: HandleSpec | None`.
Loader remains the YAML→English adapter (AGENTS.md rule).

### 5. `ShelfPinSpec` (new, on `CabinetInstance`)

```python
@dataclass
class ShelfPinSpec:
    diameter_mm: float = 5.0
    depth_mm: float = 8.0
    front_offset_mm: float = 50.0   # X from front edge of side panel
    back_offset_mm: float  = 80.0   # X from back edge of side panel
    max_per_row: int = 3
```

Add `shelf_pins: ShelfPinSpec = field(default_factory=ShelfPinSpec)` on
`CabinetInstance`.

### 6. `CabinetInstance.config` — discriminated cabinet-type config

Today `CabinetInstance.type` is a free string and variant-specific data
lives in loose `list[dict]` fields (`drawers`, `shelves`, `fronts`).
Introduce a discriminated union analogous to `kitchen_cam.models`:

```python
@dataclass class BaseDoorConfig    : shelves: list[float]; doors: list[int]
@dataclass class BaseDrawerConfig  : drawers: list[DrawerSlot]
@dataclass class CornerBlindConfig : corner_side, second_width_mm, shelves, doors
@dataclass class CornerInternalConfig : carousel, shelves, doors
@dataclass class SinkConfig        : has_sorting_drawer, sorting_drawer, doors
@dataclass class CargoConfig       : cargo_type, cargo_colour, doors
@dataclass class OvenConfig        : cavity_height_mm, has_ventilation, reinforced_shelf

CabinetConfig = Union[BaseDoorConfig, BaseDrawerConfig, ...]
```

Add `config: CabinetConfig | None = None` on `CabinetInstance`. Legacy
loose fields (`drawers`, `shelves`, `fronts`) remain until callers
migrate; loader synthesises `config` from them (mirrors
`kitchen_cam.models.CorpusSpec._sync_config_from_legacy`).

### Deletion queue (unblocked once 1–6 land)

Files that get deleted as part of executing the remaining ADR-010 steps:

| File | Blocked on |
|---|---|
| `kitchen-cam/src/kitchen_cam/models.py` | 1, 2, 3, 4, 5, 6 |
| `kitchen-cam/src/kitchen_cam/panel_calculator.py` | 6 (config union) |
| `kitchen-cam/src/kitchen_cam/csv_generator.py` | already superseded by `kuchnie_core.export.*` — deleted with `models.py` (imports it) |
| `kitchen-cam/tests/test_models.py`, `test_panel_calculator.py`, `test_csv_generator.py`, `test_new_configs.py`, `test_drill_engine.py`, `tests/unit/*`, `tests/integration/*`, `tests/e2e/*` | rewritten against `kuchnie_core` |

## Consequences

**Positive**

- Single execution plan: land all six extensions in one design pass with
  tests, then delete the parallel `kitchen_cam.models` layer in a follow-up.
- Prevents "silent drift" — banners on the deprecated modules point at
  this ADR so future contributors do not add features to the doomed layer.
- The CSV migration (cutlist + edging) already works today; the
  domain-model migration proceeds independently.

**Negative**

- `kuchnie_core.model` grows by ~7 dataclasses + 1 enum + fields on
  existing types. Still pure Python, no new deps.
- 84 → ~100 tests in `kuchnie_core` once extensions ship (approximate).
- `catalog.py` decomposition functions must be updated to set `role`
  and populate the new specs. Backwards-compatible default values mean
  the update can be done incrementally per cabinet type.

**Neutral**

- Field naming diverges slightly from `kitchen_cam.models` (English
  everywhere; `_mm` suffixes; snake_case). This is the AGENTS.md
  convention already followed by the rest of `kuchnie_core`.
- Loader (`loader.py`) grows a few new adapter clauses; still a thin
  translator, no business logic.

## Alternatives considered

**12a. Duplicate `kitchen_cam.models` types into `kuchnie_core` verbatim (Pydantic).**
Rejected — `kuchnie_core` uses plain dataclasses by design (no Pydantic
dep, no runtime coercion). Existing 500+ tests assume dataclass semantics.

**12b. Keep `kitchen_cam.models` forever as a "view" over `kuchnie_core`.**
Rejected — perpetuates ADR-010's "single source of truth" violation.
Every new cabinet type would touch two model layers.

**12c. Rewrite `machining.py` against the flatter `kuchnie_core` model
using name-based heuristics and constants.**
Rejected — lossy (drops per-cabinet hardware config), fragile
(regex on Polish names), and papers over the real design work.

## References

- ADR-010: The plan this ADR unblocks.
- ADR-005: `MachiningOp` model — extended here with `face` / `drill_type`.
- ADR-001: Panel is the atomic unit — `PanelRole` is decoration on that atom.
- AGENTS.md: "Model fields English, YAML keys Polish" (governs naming here).
- Deprecation banners at the top of `kitchen-cam/src/kitchen_cam/{models,panel_calculator,csv_generator,machining}.py`
  reference this ADR.
