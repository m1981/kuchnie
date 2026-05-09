# kitchen_app/state.py
import re
import reflex as rx
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import select
from kitchen_erp.database import get_session, engine, SQLModel
from kitchen_erp.models import Project, Cabinet, Material, HardwareSet, ProjectDefaults
from kitchen_erp.schemas import CostTraceLine

MODULE_LABELS = {
    "BASE_CABINET": "Base cabinet",
    "DRAWER_BASE": "Drawer base",
    "SINK_BASE": "Sink base",
    "DISHWASHER": "Dishwasher",
    "OVEN": "Oven",
    "COOKTOP": "Cooktop",
    "WALL_CABINET": "Wall cabinet",
    "HOOD": "Extractor hood",
    "FILLER": "Pull-out filler",
    "SIDE_PANEL": "Side panel",
    "COUNTERTOP": "Countertop",
    "SINK": "Sink",
    "FAUCET": "Faucet",
}


class CabinetUI(BaseModel):
    """ViewModel for the frontend to render cabinets easily."""
    id: int
    name: str
    price: float
    width_label: str
    css_width: str
    css_height: str
    doors: list[int] = []
    drawers: list[int] = []
    width_mm: float
    height_mm: float
    depth_mm: float
    door_count: int
    drawer_count: int
    has_custom_front: bool = False
    module_kind: str = "BASE_CABINET"
    module_label: str = "Base cabinet"
    x_mm: float = 0
    y_mm: float = 0
    equipment_price: float = 0
    css_left: str = "0px"
    css_bottom: str = "0px"
    css_top: str = "0px"
    css_depth: str = "0px"
    is_wall: bool = False
    is_appliance: bool = False
    is_countertop: bool = False
    is_sink: bool = False
    is_faucet: bool = False
    is_hood: bool = False
    is_filler: bool = False
    is_panel: bool = False
    is_cooktop: bool = False
    can_have_fronts: bool = True
    show_canvas_label: bool = True


class CostTraceLineUI(BaseModel):
    """ViewModel for rendering calculation trace rows without UI math."""
    category: str
    label: str
    quantity_label: str
    unit_price_label: str
    waste_label: str
    formula: str
    subtotal_label: str

class KitchenState(rx.State):
    """The reactive state for our UI."""
    project_name: str = "Loading..."
    total_price: float = 0.0

    wall_cabinets: list[CabinetUI] = []
    base_cabinets: list[CabinetUI] = []
    plan_modules: list[CabinetUI] = []

    total_wall_width: float = 0.0
    total_base_width: float = 0.0
    canvas_width_label: str = "4000mm"
    canvas_height_label: str = "2400mm"
    canvas_css_width: str = "800px"
    canvas_css_height: str = "480px"

    selected_cabinet_id: int | None = None
    selected_cabinet: CabinetUI | None = None

    materials: list[str] = []
    global_front_mat_name: str = ""
    local_front_mat_name: str = ""
    field_warnings: dict[str, str] = {}
    cost_trace_open: bool = False
    cost_trace_title: str = ""
    cost_trace_lines: list[CostTraceLineUI] = []
    cost_trace_total: float = 0.0
    cost_trace_summary: str = ""
    equipment_options: list[str] = [
        "Drawer Base", "Sink Base", "Dishwasher", "Oven", "Cooktop", "Filler",
        "Side Panel", "Countertop", "Sink", "Faucet", "Wall Cabinet 400",
        "Wall Cabinet 800", "Hood",
    ]

    def _ensure_cabinet_schema(self, session):
        columns = {row[1] for row in session.exec(text("PRAGMA table_info(cabinet)")).all()}
        migrations = {
            "module_kind": "ALTER TABLE cabinet ADD COLUMN module_kind VARCHAR DEFAULT 'BASE_CABINET'",
            "x_mm": "ALTER TABLE cabinet ADD COLUMN x_mm FLOAT DEFAULT 0",
            "y_mm": "ALTER TABLE cabinet ADD COLUMN y_mm FLOAT DEFAULT 0",
            "equipment_price": "ALTER TABLE cabinet ADD COLUMN equipment_price FLOAT DEFAULT 0",
        }
        for column_name, statement in migrations.items():
            if column_name not in columns:
                session.exec(text(statement))
        session.commit()

    @rx.var
    def local_material_options(self) -> list[str]:
        """Combines the default option with the materials list."""
        return ["Use Global Default"] + self.materials

    def _format_cost_trace_line(self, line: CostTraceLine) -> CostTraceLineUI:
        return CostTraceLineUI(
            category=line.category,
            label=line.label,
            quantity_label=f"{line.quantity:g} {line.unit}".strip(),
            unit_price_label=f"${line.unit_price:.2f}",
            waste_label=f"{line.waste_factor:.2f}x" if line.waste_factor is not None else "-",
            formula=line.formula,
            subtotal_label=f"${line.subtotal:.2f}",
        )

    def _module_ui(self, cab: Cabinet, cost: float) -> CabinetUI:
        scale = 0.2
        module_kind = cab.module_kind or ("WALL_CABINET" if cab.type == "WALL" else "BASE_CABINET")
        is_wall = module_kind == "WALL_CABINET" or cab.type == "WALL"
        is_appliance = module_kind in ["DISHWASHER", "OVEN", "COOKTOP", "HOOD"]
        can_have_fronts = module_kind not in [
            "DISHWASHER", "OVEN", "COOKTOP", "HOOD", "COUNTERTOP", "SINK", "FAUCET", "SIDE_PANEL"
        ]

        return CabinetUI(
            id=cab.id,
            name=cab.name,
            price=cost,
            width_label=f"{cab.width_mm:g}mm",
            css_width=f"{cab.width_mm * scale}px",
            css_height=f"{cab.height_mm * scale}px",
            css_depth=f"{cab.depth_mm * scale}px",
            css_left=f"{cab.x_mm * scale}px",
            css_bottom=f"{cab.y_mm * scale}px",
            css_top=f"{(2400 - cab.y_mm - cab.height_mm) * scale}px",
            doors=list(range(cab.door_count)),
            drawers=list(range(cab.drawer_count)),
            width_mm=cab.width_mm,
            height_mm=cab.height_mm,
            depth_mm=cab.depth_mm,
            door_count=cab.door_count,
            drawer_count=cab.drawer_count,
            has_custom_front=cab.override_front_mat_id is not None,
            module_kind=module_kind,
            module_label=MODULE_LABELS.get(module_kind, module_kind.replace("_", " ").title()),
            x_mm=cab.x_mm,
            y_mm=cab.y_mm,
            equipment_price=cab.equipment_price,
            is_wall=is_wall,
            is_appliance=is_appliance,
            is_countertop=module_kind == "COUNTERTOP",
            is_sink=module_kind == "SINK",
            is_faucet=module_kind == "FAUCET",
            is_hood=module_kind == "HOOD",
            is_filler=module_kind == "FILLER",
            is_panel=module_kind == "SIDE_PANEL",
            is_cooktop=module_kind == "COOKTOP",
            can_have_fronts=can_have_fronts,
            show_canvas_label=module_kind not in ["COUNTERTOP", "SINK", "FAUCET", "COOKTOP", "SIDE_PANEL"],
        )

    def load_ikea_layout(self):
        with next(get_session()) as session:
            project = session.exec(select(Project)).first()
            if not project:
                self.load_mock_data()
                project = session.exec(select(Project)).first()
            if not project:
                return

            for cab in list(project.cabinets):
                session.delete(cab)
            session.commit()

            def add_module(
                name: str,
                module_kind: str,
                cab_type: str,
                x_mm: float,
                y_mm: float,
                width_mm: float,
                height_mm: float,
                depth_mm: float,
                doors: int = 0,
                drawers: int = 0,
                equipment_price: float = 0,
                order_index: int = 0,
            ):
                cab = Cabinet(
                    project=project,
                    name=name,
                    type=cab_type,
                    module_kind=module_kind,
                    x_mm=x_mm,
                    y_mm=y_mm,
                    width_mm=width_mm,
                    height_mm=height_mm,
                    depth_mm=depth_mm,
                    door_count=doors,
                    drawer_count=drawers,
                    equipment_price=equipment_price,
                    order_index=order_index,
                )
                session.add(cab)

            left_offset = 1750
            base_y = 90
            base_h = 802
            add_module("Drawer base", "DRAWER_BASE", "BASE", left_offset, base_y, 400, base_h, 560, drawers=4, order_index=0)
            add_module("Sink base", "SINK_BASE", "BASE", left_offset + 400, base_y, 400, base_h, 560, doors=1, order_index=1)
            add_module("Dishwasher", "DISHWASHER", "BASE", left_offset + 800, base_y, 600, base_h, 560, equipment_price=650, order_index=2)
            add_module("Oven cabinet", "OVEN", "BASE", left_offset + 1400, base_y, 600, base_h, 560, drawers=1, equipment_price=780, order_index=3)
            add_module("Pull-out filler", "FILLER", "BASE", left_offset + 2000, base_y, 200, base_h, 560, doors=1, equipment_price=80, order_index=4)
            add_module("Side panel", "SIDE_PANEL", "BASE", left_offset + 2200, base_y, 50, base_h, 560, equipment_price=35, order_index=5)
            add_module("Concrete-look worktop", "COUNTERTOP", "DECOR", left_offset, base_y + base_h, 2250, 56, 620, equipment_price=120)
            add_module("Inset sink", "SINK", "DECOR", left_offset + 410, base_y + base_h + 12, 320, 170, 420, equipment_price=220)
            add_module("Tall faucet", "FAUCET", "DECOR", left_offset + 565, base_y + base_h + 180, 70, 270, 80, equipment_price=110)
            add_module("Black cooktop", "COOKTOP", "DECOR", left_offset + 1500, base_y + base_h + 18, 500, 80, 500, equipment_price=420)
            add_module("Wall cabinet 400", "WALL_CABINET", "WALL", left_offset, 1570, 400, 620, 310, doors=1, order_index=0)
            add_module("Wall cabinet 800", "WALL_CABINET", "WALL", left_offset + 400, 1570, 800, 620, 310, doors=2, order_index=1)
            add_module("Extractor hood", "HOOD", "WALL", left_offset + 1400, 1480, 600, 710, 420, equipment_price=360, order_index=2)

            project.customer_name = "IKEA Planner Recreation"
            session.add(project)
            session.commit()

        self.close_sidebar()
        self.load_mock_data()

    def clear_layout(self):
        with next(get_session()) as session:
            project = session.exec(select(Project)).first()
            if not project:
                return

            for cab in list(project.cabinets):
                session.delete(cab)
            project.customer_name = "Custom Kitchen Layout"
            session.add(project)
            session.commit()

        self.close_sidebar()
        self.load_mock_data()

    def close_cost_trace(self):
        self.cost_trace_open = False

    def open_selected_cabinet_cost_trace(self):
        if self.selected_cabinet_id is None:
            return

        with next(get_session()) as session:
            project = session.exec(select(Project)).first()
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if not project or not project.defaults or not cab:
                return

            cost_result = cab.calculate_cost(project.defaults, project.waste_factor)
            self.cost_trace_title = f"{cab.name} cost trace"
            self.cost_trace_lines = [self._format_cost_trace_line(line) for line in cost_result.trace_lines]
            self.cost_trace_total = cost_result.total_cost
            self.cost_trace_summary = (
                f"Material ${cost_result.material_cost:.2f} + "
                f"hardware ${cost_result.hardware_cost:.2f}"
            )
            self.cost_trace_open = True

    def open_project_cost_trace(self):
        with next(get_session()) as session:
            project = session.exec(select(Project)).first()
            if not project or not project.defaults:
                return

            cabs = sorted(project.cabinets, key=lambda c: (0 if c.type == "WALL" else 1, c.order_index))
            trace_rows: list[CostTraceLineUI] = []
            raw_total = 0.0

            for cab in cabs:
                cost_result = cab.calculate_cost(project.defaults, project.waste_factor)
                raw_total += cost_result.total_cost
                for line in cost_result.trace_lines:
                    prefixed = line.model_copy(update={"label": f"{cab.name}: {line.label}"})
                    trace_rows.append(self._format_cost_trace_line(prefixed))

            markup_cost = raw_total * (project.labor_markup - 1)
            final_total = raw_total * project.labor_markup
            trace_rows.append(
                CostTraceLineUI(
                    category="Project",
                    label="Labor / shop markup",
                    quantity_label=f"${raw_total:.2f} base",
                    unit_price_label=f"{project.labor_markup:.2f}x",
                    waste_label="-",
                    formula=f"{raw_total:.2f} x ({project.labor_markup:.2f} - 1)",
                    subtotal_label=f"${markup_cost:.2f}",
                )
            )

            self.cost_trace_title = "Project cost trace"
            self.cost_trace_lines = trace_rows
            self.cost_trace_total = round(final_total, 2)
            self.cost_trace_summary = (
                f"{len(cabs)} cabinets, raw BOM ${raw_total:.2f}, "
                f"markup {project.labor_markup:.2f}x"
            )
            self.cost_trace_open = True

    def change_global_front(self, formatted_name: str):
        # Extract the actual name by splitting at " - "
        # e.g., "Egger - U999 Black" -> "U999 Black"
        mat_name = formatted_name.split(" - ")[1] if " - " in formatted_name else formatted_name

        with next(get_session()) as session:
            mat = session.exec(select(Material).where(Material.name == mat_name)).first()
            project = session.exec(select(Project)).first()
            if mat and project and project.defaults:
                project.defaults.front_mat_id = mat.id
                session.add(project.defaults)
                session.commit()
        self.load_mock_data()

    def change_local_front(self, formatted_name: str):
        if not self.selected_cabinet_id: return

        mat_name = formatted_name.split(" - ")[1] if " - " in formatted_name else formatted_name

        with next(get_session()) as session:
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if cab:
                if formatted_name == "Use Global Default":
                    cab.override_front_mat_id = None
                else:
                    mat = session.exec(select(Material).where(Material.name == mat_name)).first()
                    if mat:
                        cab.override_front_mat_id = mat.id
                session.add(cab)
                session.commit()
        self.load_mock_data()

    def _parse_number(self, raw_value: str, is_float: bool) -> float | int | None:
        """UX: Forgiving parser. Extracts numbers even if user types '600mm' or ' 600 '."""
        if not raw_value: return 0
        # Strip everything except digits and decimal points
        cleaned = re.sub(r'[^\d.]', '', str(raw_value))
        if not cleaned: return None
        try:
            return float(cleaned) if is_float else int(float(cleaned))
        except ValueError:
            return None

    def _apply_cabinet_constraints(self, cab: Cabinet, field: str, raw_value: str):
        # Clear previous warning for this specific field
        if field in self.field_warnings:
            del self.field_warnings[field]

        # 1. Forgiving Parsing
        if field in ["width_mm", "height_mm", "depth_mm", "x_mm", "y_mm", "equipment_price"]:
            val = self._parse_number(raw_value, is_float=True)
        elif field in ["door_count", "drawer_count"]:
            val = self._parse_number(raw_value, is_float=False)
        else:
            setattr(cab, field, raw_value)
            return

        if val is None:
            return  # Invalid string with no numbers, just ignore

        original_val = val

        # 2. HARD CLAMPS (Physics & Manufacturing Limits)
        limits = {
            "BASE": {"width_mm": (150, 1200), "height_mm": (450, 900), "depth_mm": (300, 650), "door_count": (0, 2),
                     "drawer_count": (0, 5), "x_mm": (0, 4000), "y_mm": (0, 2400), "equipment_price": (0, 100000)},
            "WALL": {"width_mm": (150, 1200), "height_mm": (300, 1200), "depth_mm": (200, 400), "door_count": (0, 2),
                     "drawer_count": (0, 0), "x_mm": (0, 4000), "y_mm": (0, 2400), "equipment_price": (0, 100000)},
            "TALL": {"width_mm": (300, 900), "height_mm": (1900, 2750), "depth_mm": (500, 650), "door_count": (0, 4),
                     "drawer_count": (0, 5), "x_mm": (0, 4000), "y_mm": (0, 2400), "equipment_price": (0, 100000)},
            "DECOR": {"width_mm": (20, 4000), "height_mm": (20, 2400), "depth_mm": (20, 1200),
                      "door_count": (0, 0), "drawer_count": (0, 0), "x_mm": (0, 4000), "y_mm": (0, 2400),
                      "equipment_price": (0, 100000)}
        }

        if cab.type in limits and field in limits[cab.type]:
            min_val, max_val = limits[cab.type][field]
            val = max(min_val, min(max_val, val))

            if val != original_val:
                self.field_warnings[field] = f"Adjusted to fit limits ({min_val}-{max_val})."

        setattr(cab, field, val)

        # 3. CARPENTER'S HEURISTICS (Real-world European Kitchen Rules)

        # Rule A: Side-hinged doors > 600mm destroy hinges.
        # BUT Wall cabinets can use top-hinged flap doors, so 1 door is fine up to 1200mm!
        if cab.width_mm > 600 and cab.door_count == 1:
            if cab.type in ["BASE", "TALL"]:
                cab.door_count = 2
                self.field_warnings["door_count"] = "Base/Tall doors > 600mm are too heavy. Forced 2 doors."
            elif cab.type == "WALL" and cab.width_mm > 1200:
                # Even flap doors have limits
                cab.door_count = 2
                self.field_warnings["door_count"] = "Wall cabinets > 1200mm require 2 doors."

        # Rule B: Drawers and Doors combo
        if cab.drawer_count > 0 and cab.door_count > 2:
            cab.door_count = 2
            self.field_warnings["door_count"] = "Max 2 doors when drawers are present."

        # Rule C: The "Useless Drawer" Warning
        # We don't force it to 0, because maybe they want a custom spice pull-out, but we warn them.
        if cab.drawer_count > 0 and cab.width_mm < 300:
            self.field_warnings["drawer_count"] = "Warning: Usable inside width will be very narrow."

        # Rule D: The "Shelf Sag" Warning
        # Wide cabinets need center partitions or thick shelves.
        if cab.width_mm > 900 and cab.drawer_count == 0:
            self.field_warnings["width_mm"] = "Warning: Shelves > 900mm may sag under heavy load."

        # Rule E: The "Jumbo Board" Warning
        if cab.height_mm > 2700:
            self.field_warnings["height_mm"] = "Warning: Exceeds standard 2800mm board size. Grain matching difficult."

        # NOTE: We completely removed the "Must have at least one front" rule.
        # 0 doors and 0 drawers is now perfectly valid (Open Shelving).

    def update_cabinet_field(self, field: str, value: str):
        if not self.selected_cabinet_id: return
        with next(get_session()) as session:
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if not cab: return

            self._apply_cabinet_constraints(cab, field, value)

            session.add(cab)
            session.commit()

        self.load_mock_data()

    def add_cabinet(self, cab_type: str):
        with next(get_session()) as session:
            project = session.exec(select(Project)).first()
            if not project: return
            max_order = max([c.order_index for c in project.cabinets if c.type == cab_type] or [-1])

            if cab_type == "BASE":
                new_cab = Cabinet(project=project, name="New Base", type="BASE", module_kind="BASE_CABINET", x_mm=1750, y_mm=90, width_mm=600, height_mm=802, depth_mm=560, door_count=1, order_index=max_order + 1)
            elif cab_type == "WALL":
                new_cab = Cabinet(project=project, name="New Wall", type="WALL", module_kind="WALL_CABINET", x_mm=1750, y_mm=1570, width_mm=600, height_mm=620, depth_mm=300, door_count=1, order_index=max_order + 1)
            elif cab_type == "TALL":
                new_cab = Cabinet(project=project, name="New Tall", type="TALL", module_kind="BASE_CABINET", x_mm=1750, y_mm=90, width_mm=600, height_mm=2100, depth_mm=560, door_count=2, order_index=max_order + 1)

            session.add(new_cab)
            session.commit()
        self.load_mock_data()

    def add_equipment(self, equipment_name: str):
        specs = {
            "Drawer Base": ("Drawer base", "DRAWER_BASE", "BASE", 400, 802, 560, 0, 4, 0, 0, 90),
            "Sink Base": ("Sink base", "SINK_BASE", "BASE", 400, 802, 560, 1, 0, 0, 0, 90),
            "Dishwasher": ("Dishwasher", "DISHWASHER", "BASE", 600, 802, 560, 0, 0, 650, 0, 90),
            "Oven": ("Oven cabinet", "OVEN", "BASE", 600, 802, 560, 0, 1, 780, 0, 90),
            "Filler": ("Pull-out filler", "FILLER", "BASE", 200, 802, 560, 1, 0, 80, 0, 90),
            "Side Panel": ("Side panel", "SIDE_PANEL", "BASE", 50, 802, 560, 0, 0, 35, 0, 90),
            "Countertop": ("Countertop", "COUNTERTOP", "DECOR", 2250, 56, 620, 0, 0, 120, 0, 892),
            "Sink": ("Inset sink", "SINK", "DECOR", 320, 170, 420, 0, 0, 220, 410, 904),
            "Faucet": ("Tall faucet", "FAUCET", "DECOR", 70, 270, 80, 0, 0, 110, 565, 1072),
            "Cooktop": ("Black cooktop", "COOKTOP", "DECOR", 500, 80, 500, 0, 0, 420, 1500, 910),
            "Wall Cabinet 400": ("Wall cabinet 400", "WALL_CABINET", "WALL", 400, 620, 310, 1, 0, 0, 0, 1570),
            "Wall Cabinet 800": ("Wall cabinet 800", "WALL_CABINET", "WALL", 800, 620, 310, 2, 0, 0, 0, 1570),
            "Hood": ("Extractor hood", "HOOD", "WALL", 600, 710, 420, 0, 0, 360, 0, 1480),
        }
        if equipment_name not in specs:
            return

        name, module_kind, cab_type, width, height, depth, doors, drawers, price, x_offset, y = specs[equipment_name]
        with next(get_session()) as session:
            project = session.exec(select(Project)).first()
            if not project:
                return
            siblings = [c for c in project.cabinets if c.type == cab_type]
            max_order = max([c.order_index for c in siblings] or [-1])
            base_modules = [c for c in project.cabinets if c.type in ["BASE", "TALL"]]
            base_start = min([c.x_mm for c in base_modules] or [1750])
            base_x = max([c.x_mm + c.width_mm for c in base_modules] or [1750])
            wall_x = max([c.x_mm + c.width_mm for c in project.cabinets if c.type == "WALL"] or [1750])
            new_cab = Cabinet(
                project=project,
                name=name,
                type=cab_type,
                module_kind=module_kind,
                x_mm=wall_x if cab_type == "WALL" else base_start + x_offset if cab_type == "DECOR" else base_x,
                y_mm=y,
                width_mm=width,
                height_mm=height,
                depth_mm=depth,
                door_count=doors,
                drawer_count=drawers,
                equipment_price=price,
                order_index=max_order + 1,
            )
            session.add(new_cab)
            session.commit()
        self.load_mock_data()

    def move_cabinet(self, cab_id: int, direction: int):
        with next(get_session()) as session:
            cab = session.get(Cabinet, cab_id)
            if not cab: return
            step_mm = 50
            cab.x_mm = max(0, min(4000 - cab.width_mm, cab.x_mm + (direction * step_mm)))
            session.add(cab)
            session.commit()
        self.load_mock_data()

    def move_selected_cabinet(self, direction: int):
        if self.selected_cabinet_id is None:
            return
        self.move_cabinet(self.selected_cabinet_id, direction)

    def delete_cabinet(self):
        if not self.selected_cabinet_id: return
        with next(get_session()) as session:
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if cab:
                session.delete(cab)
                session.commit()
        self.close_sidebar()
        self.load_mock_data()

    def select_cabinet(self, cab_id: int):
        self.selected_cabinet_id = cab_id
        # Clear warnings when switching cabinets so old errors don't persist
        self.field_warnings = {}
        self._update_selected_cabinet_ui()

    def close_sidebar(self):
        self.selected_cabinet_id = None
        self.selected_cabinet = None
        self.field_warnings = {}

    def _update_selected_cabinet_ui(self):
        if self.selected_cabinet_id is None: return
        for cab in self.plan_modules:
            if cab.id == self.selected_cabinet_id:
                self.selected_cabinet = cab
                with next(get_session()) as session:
                    db_cab = session.get(Cabinet, cab.id)
                    if db_cab.override_front_mat_id:
                        local_mat = session.get(Material, db_cab.override_front_mat_id)
                        # Format it to match the dropdown list
                        self.local_front_mat_name = f"{local_mat.brand} - {local_mat.name}" if local_mat else "Use Global Default"
                    else:
                        self.local_front_mat_name = "Use Global Default"
                break

    def load_mock_data(self):
        SQLModel.metadata.create_all(engine)
        with next(get_session()) as session:
            self._ensure_cabinet_schema(session)
            existing = session.exec(select(Project)).first()

            if not existing:
                # ==========================================
                # 📖 MASTER CATALOG (Easy Maintenance Area)
                # ==========================================

                # 1. Hardware
                hw_catalog = [
                    HardwareSet(brand="Blum", name="Clip Top Hinge", price_per_set=2.50),
                    HardwareSet(brand="Hettich", name="Sensys Hinge", price_per_set=2.20),
                    HardwareSet(brand="Blum", name="Legrabox Drawer", price_per_set=35.00),
                    HardwareSet(brand="Hettich", name="AvanTech Drawer", price_per_set=32.00),
                ]

                # 2. Utility Materials
                utility_catalog = [
                    Material(category="Back", brand="Generic", name="HDF White 3mm", price_per_unit=4.50, unit="m2"),
                    Material(category="Edge", brand="Generic", name="ABS White 1mm", price_per_unit=0.80, unit="lm"),
                    Material(category="Edge", brand="Generic", name="ABS Color 1mm", price_per_unit=1.20, unit="lm"),
                ]

                # 3. MDF / Particle Boards (The Brands)
                board_catalog = [
                    # EGGER (Standard & Premium)
                    Material(category="Board", brand="Egger", name="W1000 Premium White", price_per_unit=12.50,
                             unit="m2"),
                    Material(category="Board", brand="Egger", name="U999 Black", price_per_unit=14.00, unit="m2"),
                    Material(category="Board", brand="Egger", name="H3131 Davos Oak", price_per_unit=18.50, unit="m2"),
                    Material(category="Board", brand="Egger", name="U708 Light Grey", price_per_unit=13.00, unit="m2"),
                    Material(category="Board", brand="Egger", name="F204 Marmara Marble", price_per_unit=22.00,
                             unit="m2"),

                    # KRONOSPAN (Budget & Standard)
                    Material(category="Board", brand="Krono", name="K101 Front White", price_per_unit=9.50, unit="m2"),
                    Material(category="Board", brand="Krono", name="0190 Black", price_per_unit=11.00, unit="m2"),
                    Material(category="Board", brand="Krono", name="D1811 Walnut", price_per_unit=14.50, unit="m2"),
                    Material(category="Board", brand="Krono", name="0171 Slate Grey", price_per_unit=10.50, unit="m2"),
                    Material(category="Board", brand="Krono", name="8685 Snow White", price_per_unit=9.00, unit="m2"),

                    # FORNER (Premium Supermattes & Gloss)
                    Material(category="Board", brand="Forner", name="Velvet Ultramatte Black", price_per_unit=38.00,
                             unit="m2"),
                    Material(category="Board", brand="Forner", name="Velvet Ultramatte White", price_per_unit=38.00,
                             unit="m2"),
                    Material(category="Board", brand="Forner", name="Pearl Gloss", price_per_unit=35.00, unit="m2"),
                    Material(category="Board", brand="Forner", name="Cashmere Matte", price_per_unit=36.50, unit="m2"),
                    Material(category="Board", brand="Forner", name="Navy Blue Matte", price_per_unit=36.50, unit="m2"),

                    # CLEAF (Deep Textures)
                    Material(category="Board", brand="Cleaf", name="Ares Beton", price_per_unit=42.00, unit="m2"),
                    Material(category="Board", brand="Cleaf", name="Pembroke Oak", price_per_unit=45.00, unit="m2"),
                    Material(category="Board", brand="Cleaf", name="Nadir Linen", price_per_unit=40.00, unit="m2"),
                    Material(category="Board", brand="Cleaf", name="Piombo Matte", price_per_unit=48.00, unit="m2"),
                    Material(category="Board", brand="Cleaf", name="Sherwood Dark", price_per_unit=45.00, unit="m2"),
                ]

                # Insert everything into the database
                session.add_all(hw_catalog + utility_catalog + board_catalog)
                session.commit()

                # ==========================================
                # Create the Default Project
                # ==========================================
                project = Project(customer_name="Smith Family Kitchen")

                # Fetch defaults from the newly created catalog
                def_corpus = session.exec(select(Material).where(Material.name == "W1000 Premium White")).first()
                def_back = session.exec(select(Material).where(Material.name == "HDF White 3mm")).first()
                def_edge = session.exec(select(Material).where(Material.name == "ABS White 1mm")).first()
                def_hinge = session.exec(select(HardwareSet).where(HardwareSet.name == "Clip Top Hinge")).first()
                def_drawer = session.exec(select(HardwareSet).where(HardwareSet.name == "Legrabox Drawer")).first()

                defaults = ProjectDefaults(
                    project=project,
                    corpus_mat_id=def_corpus.id,
                    front_mat_id=def_corpus.id,
                    back_mat_id=def_back.id,
                    edge_band_mat_id=def_edge.id,
                    hinge_sys_id=def_hinge.id,
                    drawer_sys_id=def_drawer.id
                )

                cab1 = Cabinet(project=project, name="Sink Base", type="BASE", module_kind="SINK_BASE",
                               x_mm=1750, y_mm=90, width_mm=800, height_mm=802, depth_mm=560, door_count=2)
                cab2 = Cabinet(project=project, name="Drawer Base", type="BASE", module_kind="DRAWER_BASE",
                               x_mm=2550, y_mm=90, width_mm=600, height_mm=802, depth_mm=560, drawer_count=3)
                cab3 = Cabinet(project=project, name="Tall Oven", type="TALL", module_kind="OVEN",
                               x_mm=3150, y_mm=90, width_mm=600, height_mm=2100, depth_mm=560, door_count=2, drawer_count=5,
                               equipment_price=780)
                cab4 = Cabinet(project=project, name="Wall Cabinet", type="WALL", module_kind="WALL_CABINET",
                               x_mm=1750, y_mm=1570, width_mm=800, height_mm=620, depth_mm=300, door_count=2)

                session.add_all([project, defaults, cab1, cab2, cab3, cab4])
                session.commit()
                existing = project

            # ==========================================
            # Populate UI State
            # ==========================================

            # Fetch only "Board" category materials for the dropdowns
            all_boards = session.exec(select(Material).where(Material.category == "Board")).all()

            # Format the string for the UI dropdown: "Brand - Name"
            self.materials = [f"{m.brand} - {m.name}" for m in all_boards]

            global_mat = session.get(Material, existing.defaults.front_mat_id)
            self.global_front_mat_name = f"{global_mat.brand} - {global_mat.name}" if global_mat else ""

            self.project_name = existing.customer_name
            total_price = 0.0

            wall_cabs = sorted([c for c in existing.cabinets if c.type == "WALL"], key=lambda c: c.order_index)
            base_cabs = sorted([c for c in existing.cabinets if c.type in ["BASE", "TALL"]],
                               key=lambda c: c.order_index)
            decor_cabs = sorted([c for c in existing.cabinets if c.type == "DECOR"], key=lambda c: (c.y_mm, c.x_mm))

            for i, cab in enumerate(wall_cabs): cab.order_index = i
            for i, cab in enumerate(base_cabs): cab.order_index = i
            session.commit()

            wall_list, base_list, plan_modules = [], [], []
            wall_width, base_width = 0.0, 0.0

            for cab in wall_cabs + base_cabs + decor_cabs:
                cost_result = cab.calculate_cost(existing.defaults, existing.waste_factor)
                total_price += cost_result.total_cost
                cab_ui = self._module_ui(cab, cost_result.total_cost)
                plan_modules.append(cab_ui)

                if cab.type == "WALL":
                    wall_list.append(cab_ui)
                    wall_width += cab.width_mm
                elif cab.type in ["BASE", "TALL"]:
                    base_list.append(cab_ui)
                    base_width += cab.width_mm

            self.wall_cabinets = wall_list
            self.base_cabinets = base_list
            self.plan_modules = sorted(plan_modules, key=lambda item: (item.y_mm, item.x_mm, item.height_mm))
            self.total_wall_width = wall_width
            self.total_base_width = base_width
            self.total_price = round(total_price * existing.labor_markup, 2)

            self._update_selected_cabinet_ui()
