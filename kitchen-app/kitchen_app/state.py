# kitchen_app/state.py
import re
import reflex as rx
from pydantic import BaseModel
from sqlmodel import select
from kitchen_erp.database import get_session, engine, SQLModel
from kitchen_erp.models import Project, Cabinet, Material, HardwareSet, ProjectDefaults

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

class KitchenState(rx.State):
    """The reactive state for our UI."""
    project_name: str = "Loading..."
    total_price: float = 0.0

    wall_cabinets: list[CabinetUI] = []
    base_cabinets: list[CabinetUI] = []

    total_wall_width: float = 0.0
    total_base_width: float = 0.0

    selected_cabinet_id: int | None = None
    selected_cabinet: CabinetUI | None = None

    materials: list[str] = []
    global_front_mat_name: str = ""
    local_front_mat_name: str = ""
    field_warnings: dict[str, str] = {}

    @rx.var
    def local_material_options(self) -> list[str]:
        """Combines the default option with the materials list."""
        return ["Use Global Default"] + self.materials

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
        if field in ["width_mm", "height_mm", "depth_mm"]:
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
                     "drawer_count": (0, 5)},
            "WALL": {"width_mm": (150, 1200), "height_mm": (300, 1200), "depth_mm": (200, 400), "door_count": (0, 2),
                     "drawer_count": (0, 0)},
            "TALL": {"width_mm": (300, 900), "height_mm": (1900, 2750), "depth_mm": (500, 650), "door_count": (0, 4),
                     "drawer_count": (0, 5)}
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
                new_cab = Cabinet(project=project, name="New Base", type="BASE", width_mm=600, height_mm=720, depth_mm=560, door_count=1, order_index=max_order + 1)
            elif cab_type == "WALL":
                new_cab = Cabinet(project=project, name="New Wall", type="WALL", width_mm=600, height_mm=720, depth_mm=300, door_count=1, order_index=max_order + 1)
            elif cab_type == "TALL":
                new_cab = Cabinet(project=project, name="New Tall", type="TALL", width_mm=600, height_mm=2100, depth_mm=560, door_count=2, order_index=max_order + 1)

            session.add(new_cab)
            session.commit()
        self.load_mock_data()

    def move_cabinet(self, cab_id: int, direction: int):
        with next(get_session()) as session:
            cab = session.get(Cabinet, cab_id)
            if not cab: return
            project = session.get(Project, cab.project_id)

            if cab.type == "WALL":
                siblings = [c for c in project.cabinets if c.type == "WALL"]
            else:
                siblings = [c for c in project.cabinets if c.type in ["BASE", "TALL"]]

            siblings.sort(key=lambda c: c.order_index)
            idx = next((i for i, c in enumerate(siblings) if c.id == cab_id), -1)
            if idx == -1: return

            new_idx = idx + direction
            if 0 <= new_idx < len(siblings):
                swap_cab = siblings[new_idx]
                cab.order_index, swap_cab.order_index = swap_cab.order_index, cab.order_index
                session.add_all([cab, swap_cab])
                session.commit()
        self.load_mock_data()

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
        for cab in self.wall_cabinets + self.base_cabinets:
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

                cab1 = Cabinet(project=project, name="Sink Base", type="BASE", width_mm=800, height_mm=720,
                               depth_mm=560, door_count=2)
                cab2 = Cabinet(project=project, name="Drawer Base", type="BASE", width_mm=600, height_mm=720,
                               depth_mm=560, drawer_count=3)
                cab3 = Cabinet(project=project, name="Tall Oven", type="TALL", width_mm=600, height_mm=2100,
                               depth_mm=560, door_count=2, drawer_count=5)
                cab4 = Cabinet(project=project, name="Wall Cabinet", type="WALL", width_mm=800, height_mm=720,
                               depth_mm=300, door_count=2)

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

            for i, cab in enumerate(wall_cabs): cab.order_index = i
            for i, cab in enumerate(base_cabs): cab.order_index = i
            session.commit()

            wall_list, base_list = [], []
            wall_width, base_width = 0.0, 0.0

            for cab in wall_cabs + base_cabs:
                cost_result = cab.calculate_cost(existing.defaults, existing.waste_factor)
                total_price += cost_result.total_cost

                cab_ui = CabinetUI(
                    id=cab.id, name=cab.name, price=cost_result.total_cost,
                    width_label=f"{cab.width_mm}mm", css_width=f"{cab.width_mm / 10}px",
                    css_height=f"{cab.height_mm / 10}px",
                    doors=list(range(cab.door_count)), drawers=list(range(cab.drawer_count)),
                    width_mm=cab.width_mm, height_mm=cab.height_mm, depth_mm=cab.depth_mm,
                    door_count=cab.door_count, drawer_count=cab.drawer_count,
                    has_custom_front=cab.override_front_mat_id is not None
                )

                if cab.type == "WALL":
                    wall_list.append(cab_ui)
                    wall_width += cab.width_mm
                else:
                    base_list.append(cab_ui)
                    base_width += cab.width_mm

            self.wall_cabinets = wall_list
            self.base_cabinets = base_list
            self.total_wall_width = wall_width
            self.total_base_width = base_width
            self.total_price = round(total_price * existing.labor_markup, 2)

            self._update_selected_cabinet_ui()