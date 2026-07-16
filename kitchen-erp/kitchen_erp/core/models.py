# kitchen_erp/core/models.py
from datetime import date, datetime

from sqlmodel import SQLModel, Field, Relationship

# Project/Order spine (wk-02a62298): stage vocabulary is the L1 process
# stage list in docs/specs/process-coverage.md, in pipeline order. Stage 10
# (Delivery & installation) is "out, permanent" per that spec, so it is not
# a stage a Project can occupy — the sequence skips 9 -> 11.
STAGE_SEQUENCE: list[str] = [
    "1_first_visit",       # First visit (decors) -- krono-compositor-mvp + catalog
    "2_pomiar",             # Pomiar -- kitchen-erp project record, attachments only
    "3_layout_design",      # Layout & design -- home_builder_5 / home-builder-adapter
    "4_decomposition",      # Decomposition -- kuchnie-core
    "5_purchasing",         # Purchasing -- kitchen-erp (rozrys CSV, board/hardware orders)
    "6_cutting_edging",     # Cutting & edging -- external service
    "7_cam_drilling",       # CAM / drilling -- kitchen-cam
    "8_assembly_outputs",   # Assembly outputs -- kitchen-cam
    "9_worktops",           # Worktops -- kuchnie-core BOM + catalog
    "11_handover_archive",  # Handover archive -- kitchen-erp project record
]

STAGE_LABELS: dict[str, str] = {
    "1_first_visit": "First visit (decors)",
    "2_pomiar": "Pomiar",
    "3_layout_design": "Layout & design",
    "4_decomposition": "Decomposition",
    "5_purchasing": "Purchasing",
    "6_cutting_edging": "Cutting & edging",
    "7_cam_drilling": "CAM / drilling",
    "8_assembly_outputs": "Assembly outputs",
    "9_worktops": "Worktops",
    "11_handover_archive": "Handover archive",
}

DEFAULT_STAGE = STAGE_SEQUENCE[0]


class StageTransitionError(ValueError):
    """Raised by Project.transition_stage for an unknown stage or a
    backward/no-op move. This is the only sanctioned way to change
    Project.stage -- nothing else should assign it directly."""


# Variant lifecycle (wk-593a317b increment 1): the state machine from
# docs/specs/purchasing-variants.md § "The variant lifecycle", attached to
# the Project spine above. Forward-only exactly like transition_stage.
# ACCEPTED locks the variant: later edits are explicit change-orders (a
# later increment) -- this increment only enforces the lock.
VARIANT_STATE_SEQUENCE: list[str] = [
    "draft",           # parameters still moving; the only mutable state
    "frozen",          # artifacts derived from ONE decomposition, pinned
    "sent",            # rozrys+DXF out to the cutting service (ArtifactRefs)
    "offer_received",  # verbatim archive + recorded amount (later increment)
    "accepted",        # LOCK -- client accepted at the comparison board
    "ordered",         # hardware CSVs out (later increment)
]

DEFAULT_VARIANT_STATE = VARIANT_STATE_SEQUENCE[0]

# Typed override vocabularies -- the substitution-registry axes of
# purchasing-variants.md § "Substitution registry". Drawer-system ids are
# validated against kuchnie_core.DrawerSystemFactory (the authority),
# lazily imported in Variant.set_overrides.
CORNER_MECHANISMS: list[str] = ["plain_shelves", "half_carousel", "magic_corner"]
HINGE_CLASSES: list[str] = ["standard", "soft_close"]

# Sentinel distinguishing "axis not passed" from "clear back to baseline"
# (None) in Variant.set_overrides.
_UNSET = object()


class VariantStateError(ValueError):
    """Raised by Variant.advance_state for an unknown state or a
    backward/no-op move, and by Variant.set_overrides outside draft.
    advance_state is the only sanctioned way to change Variant.state --
    nothing else should assign it directly."""


class VariantLockedError(VariantStateError):
    """The ACCEPT lock: raised when mutating a variant at or after
    ACCEPTED. Post-accept edits are explicit change-orders (later
    increment); until then they are simply refused."""


class Material(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Egger", "Krono"
    category: str | None = None   # NEW: e.g., "Board", "Edge", "Back"
    price_per_unit: float
    unit: str
    sheet_size_m2: float = Field(default=5.796) # Domyślnie format 2800x2070
    has_woodgrain: bool = Field(default=False)  # Czy ma usłojenie (wymusza większy odpad na CNC)
    # Mirror key (ADR-011 phase 3): set = identity owned by the catalog
    # service (material_mirror converges it); NULL = local-born row
    # (admin UI / utility), never touched by the mirror.
    catalog_variant_id: str | None = Field(default=None, index=True)

class SupplierPrice(SQLModel, table=True):
    """One accepted landing-schema price row (wk-39ed9155, spec:
    docs/specs/purchasing-variants.md § price ingestion). The latest row per
    item_code is the "last known" price for the ±tolerance gate, and its
    valid_from drives freshness grading (stale price → estimate-grade quote).
    Rows are append-only history; Material.price_per_unit is the derived
    convenience copy, updated by price_import for mirrored rows."""
    id: int | None = Field(default=None, primary_key=True)
    supplier: str
    item_code: str = Field(index=True)  # joins Material.catalog_variant_id
    description: str = ""
    unit: str
    price_net: float
    currency: str
    valid_from: date
    source_ref: str  # path to the verbatim archived source
    imported_at: datetime = Field(default_factory=datetime.utcnow)


class HardwareSet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    brand: str | None = None      # NEW: e.g., "Blum", "Hettich"
    price_per_set: float


class HardwareRule(SQLModel, table=True):
    """Tag-based hardware rules for automatic component addition"""
    id: int | None = Field(default=None, primary_key=True)
    tag: str  # e.g., "is_base", "has_doors"
    hardware_name: str  # e.g., "Cabinet legs", "Door hinges"
    qty_per_unit: int  # How many per cabinet/door/drawer
    unit: str  # "pcs", "sets"
    price: float  # Price per unit
    description: str | None = None  # Optional description

class ProjectDefaults(SQLModel, table=True):
    # Primary Key is also a Foreign Key to Project (1-to-1 relationship)
    project_id: int = Field(foreign_key="project.id", primary_key=True, ondelete="CASCADE")

    # Foreign Keys
    corpus_mat_id: int = Field(foreign_key="material.id")
    front_mat_id: int = Field(foreign_key="material.id")
    back_mat_id: int = Field(foreign_key="material.id")
    edge_band_mat_id: int = Field(foreign_key="material.id")
    hinge_sys_id: int = Field(foreign_key="hardwareset.id")
    drawer_sys_id: int = Field(foreign_key="hardwareset.id")

    # Relationships (Navigation properties)
    project: "Project" = Relationship(back_populates="defaults")

    corpus_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.corpus_mat_id]"})
    front_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.front_mat_id]"})
    back_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.back_mat_id]"})
    edge_band_mat: Material = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.edge_band_mat_id]"})
    hinge_sys: HardwareSet = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.hinge_sys_id]"})
    drawer_sys: HardwareSet = Relationship(sa_relationship_kwargs={"foreign_keys": "[ProjectDefaults.drawer_sys_id]"})

class Cabinet(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE")

    name: str
    type: str
    width_mm: float
    height_mm: float
    depth_mm: float
    door_count: int = 0
    drawer_count: int = 0
    module_kind: str = "BASE_CABINET"
    x_mm: float = 0
    y_mm: float = 0
    equipment_price: float = 0

    # NEW: Keep track of the order in the row
    order_index: int = 0

    # Local Overrides (Nullable Foreign Keys)
    override_front_mat_id: int | None = Field(default=None, foreign_key="material.id")
    override_corpus_mat_id: int | None = Field(default=None, foreign_key="material.id")

    # Relationships
    project: "Project" = Relationship(back_populates="cabinets")
    override_front_mat: Material | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Cabinet.override_front_mat_id]"})
    override_corpus_mat: Material | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Cabinet.override_corpus_mat_id]"})
    
    @property
    def has_custom_front(self) -> bool:
        """
        Check if this cabinet should have custom front material.
        
        Used by BOM generator to determine if front material should be included.
        Returns False for equipment-only cabinets.
        """
        fixed_equipment = {
            "DISHWASHER", "OVEN", "COOKTOP", "HOOD", "SINK", "FAUCET",
            "APPLIANCE", "DECOR", "COUNTERTOP"
        }
        return self.module_kind not in fixed_equipment
    
    @property
    def local_front_mat(self) -> Material | None:
        """
        Get the front material for this cabinet (override or None).
        
        Used by BOM generator. If None, generator will use project defaults.
        """
        return self.override_front_mat

class ArtifactRef(SQLModel, table=True):
    """A reference to an artifact produced along the spine (stages 1-11):
    rozrys CSV, BOM export, CNC program, offer PDF, etc. `path` holds a
    filesystem path or an external id/URL -- this table never stores the
    artifact bytes themselves."""
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE")
    kind: str  # e.g. "rozrys_csv", "bom", "cnc_program", "offer_pdf"
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: "Project" = Relationship(back_populates="artifact_refs")


class Variant(SQLModel, table=True):
    """A purchasing variant on a Project (wk-593a317b increment 1).

    Killer feature 1 of docs/specs/purchasing-variants.md: "Variants are
    parameters, not copies". A Variant is the project's baseline design
    plus a typed override set over the substitution-registry axes (front
    decor, drawer-system tier, corner mechanism, hinge class, worktop),
    plus provenance -- NEVER a copied artifact set. Derived artifacts
    (rozrys rows, CNC ops, BOM) are re-derived from ONE decomposition by
    ``kitchen_erp.core.variant_derivation.derive_variant`` on every call;
    nothing derived is stored here, so nothing can go stale against an
    override change.

    Override fields are None when the variant inherits the baseline
    (project defaults) on that axis. Mutate them only through
    ``set_overrides`` -- direct assignment bypasses the draft-only rule
    and the ACCEPT lock, same convention as Project.stage.
    """
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE")

    name: str
    state: str = Field(default=DEFAULT_VARIANT_STATE)

    # Provenance
    created_at: datetime = Field(default_factory=datetime.utcnow)
    baseline_ref: str | None = None  # which design snapshot this varies

    # Typed overrides (substitution-registry axes); None = baseline
    front_decor_id: int | None = Field(default=None, foreign_key="material.id")
    drawer_system: str | None = None    # kuchnie_core DrawerSystemFactory id
    corner_mechanism: str | None = None  # one of CORNER_MECHANISMS
    hinge_class: str | None = None       # one of HINGE_CLASSES
    worktop: str | None = None           # per-lm worktop code (wk-4c37f4ee axis)

    # Relationships
    project: "Project" = Relationship(back_populates="variants")
    front_decor: Material | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Variant.front_decor_id]"}
    )

    @property
    def is_locked(self) -> bool:
        """True from ACCEPTED onward -- the ACCEPT lock of UC-4 step 5."""
        return (VARIANT_STATE_SEQUENCE.index(self.state)
                >= VARIANT_STATE_SEQUENCE.index("accepted"))

    def advance_state(self, new_state: str) -> None:
        """Move the variant forward in VARIANT_STATE_SEQUENCE order.

        Raises VariantStateError for an unknown state id or any
        backward/no-op move -- state only ever advances, and only through
        this method (mirrors Project.transition_stage).
        """
        if new_state not in VARIANT_STATE_SEQUENCE:
            raise VariantStateError(f"unknown variant state: {new_state!r}")
        current_idx = VARIANT_STATE_SEQUENCE.index(self.state)
        new_idx = VARIANT_STATE_SEQUENCE.index(new_state)
        if new_idx <= current_idx:
            raise VariantStateError(
                f"cannot move from {self.state!r} to {new_state!r}: "
                "variant state only advances forward"
            )
        self.state = new_state

    def set_overrides(
        self,
        *,
        front_decor: Material | None = _UNSET,  # type: ignore[assignment]
        drawer_system: str | None = _UNSET,  # type: ignore[assignment]
        corner_mechanism: str | None = _UNSET,  # type: ignore[assignment]
        hinge_class: str | None = _UNSET,  # type: ignore[assignment]
        worktop: str | None = _UNSET,  # type: ignore[assignment]
    ) -> None:
        """Change override axes -- the only sanctioned parameter mutation.

        Passing None clears an axis back to the baseline; an axis not
        passed is left untouched. Only a DRAFT variant may change: from
        ACCEPTED onward this raises VariantLockedError (the ACCEPT lock);
        frozen/sent/offer_received raise VariantStateError -- a sent
        variant is never mutated, you loop back to a sibling draft
        (purchasing-variants.md lifecycle).
        """
        if self.is_locked:
            raise VariantLockedError(
                f"variant {self.name!r} is {self.state}: ACCEPTED variants "
                "are locked; edits require an explicit change-order"
            )
        if self.state != "draft":
            raise VariantStateError(
                f"variant {self.name!r} is {self.state}: parameters only "
                "change in draft -- loop back to a sibling draft variant"
            )
        if drawer_system is not _UNSET and drawer_system is not None:
            from kuchnie_core import DrawerSystemFactory
            if drawer_system not in DrawerSystemFactory.list_ids():
                raise ValueError(
                    f"unknown drawer system: {drawer_system!r}. "
                    f"Valid: {DrawerSystemFactory.list_ids()}"
                )
        if (corner_mechanism is not _UNSET and corner_mechanism is not None
                and corner_mechanism not in CORNER_MECHANISMS):
            raise ValueError(
                f"unknown corner mechanism: {corner_mechanism!r}. "
                f"Valid: {CORNER_MECHANISMS}"
            )
        if (hinge_class is not _UNSET and hinge_class is not None
                and hinge_class not in HINGE_CLASSES):
            raise ValueError(
                f"unknown hinge class: {hinge_class!r}. Valid: {HINGE_CLASSES}"
            )
        if front_decor is not _UNSET:
            self.front_decor = front_decor
            self.front_decor_id = front_decor.id if front_decor else None
        if drawer_system is not _UNSET:
            self.drawer_system = drawer_system
        if corner_mechanism is not _UNSET:
            self.corner_mechanism = corner_mechanism
        if hinge_class is not _UNSET:
            self.hinge_class = hinge_class
        if worktop is not _UNSET:
            self.worktop = worktop

    def overrides(self) -> dict[str, object]:
        """The axes this variant actually overrides (provenance view)."""
        out: dict[str, object] = {}
        if self.front_decor is not None:
            out["front_decor"] = self.front_decor.name
        for axis in ("drawer_system", "corner_mechanism", "hinge_class", "worktop"):
            value = getattr(self, axis)
            if value is not None:
                out[axis] = value
        return out


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    customer_name: str
    waste_factor: float = 1.20
    labor_markup: float = 1.50

    # Project/Order spine (wk-02a62298)
    stage: str = Field(default=DEFAULT_STAGE)

    # Customer contact, beyond the bare customer_name
    customer_email: str | None = None
    customer_phone: str | None = None
    customer_address: str | None = None

    # Lifecycle dates -- all nullable; created_at auto-stamps at creation,
    # the rest are set explicitly as the project moves through the spine.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    quoted_at: datetime | None = None
    ordered_at: datetime | None = None
    production_at: datetime | None = None
    installed_at: datetime | None = None

    # Relationships
    # cascade_delete=True ensures if we delete a project, its cabinets and defaults vanish too.
    cabinets: list[Cabinet] = Relationship(back_populates="project", cascade_delete=True)
    defaults: ProjectDefaults | None = Relationship(back_populates="project", cascade_delete=True)
    artifact_refs: list[ArtifactRef] = Relationship(back_populates="project", cascade_delete=True)
    variants: list[Variant] = Relationship(back_populates="project", cascade_delete=True)

    def transition_stage(self, new_stage: str) -> None:
        """Move the project forward to `new_stage` in STAGE_SEQUENCE order.

        Raises StageTransitionError for an unknown stage id or any
        backward/no-op move -- stage only ever advances, and only through
        this method (no UI or caller may assign .stage directly).
        """
        if new_stage not in STAGE_SEQUENCE:
            raise StageTransitionError(f"unknown stage: {new_stage!r}")
        current_idx = STAGE_SEQUENCE.index(self.stage)
        new_idx = STAGE_SEQUENCE.index(new_stage)
        if new_idx <= current_idx:
            raise StageTransitionError(
                f"cannot move from {self.stage!r} to {new_stage!r}: "
                "stage only advances forward"
            )
        self.stage = new_stage

    def add_artifact(self, kind: str, path: str) -> ArtifactRef:
        """Record an artifact reference for this project (rozrys CSV, BOM,
        CNC program, offer PDF, ...). Caller is responsible for
        session.add()/commit() when persistence is desired."""
        return ArtifactRef(project=self, kind=kind, path=path)
