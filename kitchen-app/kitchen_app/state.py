# kitchen_app/state.py
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

    @rx.var
    def local_material_options(self) -> list[str]:
        """Combines the default option with the materials list."""
        return ["Use Global Default"] + self.materials

    def change_global_front(self, mat_name: str):
        with next(get_session()) as session:
            mat = session.exec(select(Material).where(Material.name == mat_name)).first()
            project = session.exec(select(Project)).first()
            if mat and project and project.defaults:
                project.defaults.front_mat_id = mat.id
                session.add(project.defaults)
                session.commit()
        self.load_mock_data()

    def change_local_front(self, mat_name: str):
        if not self.selected_cabinet_id: return
        with next(get_session()) as session:
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if cab:
                if mat_name == "Use Global Default":
                    cab.override_front_mat_id = None
                else:
                    mat = session.exec(select(Material).where(Material.name == mat_name)).first()
                    if mat:
                        cab.override_front_mat_id = mat.id
                session.add(cab)
                session.commit()
        self.load_mock_data()

    def _apply_cabinet_constraints(self, cab: Cabinet, field: str, raw_value: str):
        try:
            if field in ["width_mm", "height_mm", "depth_mm"]:
                val = float(raw_value or 0)
            elif field in ["door_count", "drawer_count"]:
                val = int(raw_value or 0)
            else:
                setattr(cab, field, raw_value)
                return
        except ValueError:
            return

        if cab.type == "BASE":
            if field == "width_mm": val = max(150.0, min(1200.0, val))
            elif field == "height_mm": val = max(450.0, min(900.0, val))
            elif field == "depth_mm": val = max(300.0, min(650.0, val))
            elif field == "door_count": val = max(0, min(2, val))
            elif field == "drawer_count": val = max(0, min(5, val))
        elif cab.type == "WALL":
            if field == "width_mm": val = max(150.0, min(1200.0, val))
            elif field == "height_mm": val = max(300.0, min(1200.0, val))
            elif field == "depth_mm": val = max(200.0, min(400.0, val))
            elif field == "door_count": val = max(0, min(2, val))
            elif field == "drawer_count": val = 0
        elif cab.type == "TALL":
            if field == "width_mm": val = max(300.0, min(900.0, val))
            elif field == "height_mm": val = max(1900.0, min(2750.0, val))
            elif field == "depth_mm": val = max(500.0, min(650.0, val))
            elif field == "door_count": val = max(0, min(4, val))
            elif field == "drawer_count": val = max(0, min(5, val))

        setattr(cab, field, val)

        if field == "width_mm" and cab.width_mm > 600 and cab.door_count == 1:
            cab.door_count = 2
        if field == "door_count" and cab.door_count == 1 and cab.width_mm > 600:
            cab.door_count = 2
        if field == "drawer_count" and cab.drawer_count > 0 and cab.door_count > 2:
            cab.door_count = 2

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
        self._update_selected_cabinet_ui()

    def close_sidebar(self):
        self.selected_cabinet_id = None
        self.selected_cabinet = None

    def _update_selected_cabinet_ui(self):
        if self.selected_cabinet_id is None: return
        for cab in self.wall_cabinets + self.base_cabinets:
            if cab.id == self.selected_cabinet_id:
                self.selected_cabinet = cab
                with next(get_session()) as session:
                    db_cab = session.get(Cabinet, cab.id)
                    if db_cab.override_front_mat_id:
                        local_mat = session.get(Material, db_cab.override_front_mat_id)
                        self.local_front_mat_name = local_mat.name if local_mat else "Use Global Default"
                    else:
                        self.local_front_mat_name = "Use Global Default"
                break

    def load_mock_data(self):
        SQLModel.metadata.create_all(engine)
        with next(get_session()) as session:
            existing = session.exec(select(Project)).first()
            if not existing:
                mdf = Material(name="Standard White MDF", price_per_unit=10.0, unit="m2")
                oak = Material(name="Premium Oak Veneer", price_per_unit=45.0, unit="m2")
                pet = Material(name="Supermatte Black PET", price_per_unit=35.0, unit="m2")
                hdf = Material(name="HDF Back", price_per_unit=5.0, unit="m2")
                edge = Material(name="ABS Edge", price_per_unit=1.0, unit="lm")
                hinge = HardwareSet(name="Blum Hinge", price_per_set=2.0)
                drawer = HardwareSet(name="Blum Drawer", price_per_set=30.0)

                session.add_all([mdf, oak, pet, hdf, edge, hinge, drawer])
                session.commit()

                project = Project(customer_name="Smith Family Kitchen")
                defaults = ProjectDefaults(
                    project=project, corpus_mat_id=mdf.id, front_mat_id=mdf.id,
                    back_mat_id=hdf.id, edge_band_mat_id=edge.id,
                    hinge_sys_id=hinge.id, drawer_sys_id=drawer.id
                )

                cab1 = Cabinet(project=project, name="Sink Base", type="BASE", width_mm=800, height_mm=720, depth_mm=560, door_count=2)
                cab2 = Cabinet(project=project, name="Drawer Base", type="BASE", width_mm=600, height_mm=720, depth_mm=560, drawer_count=3)
                cab3 = Cabinet(project=project, name="Tall Oven", type="TALL", width_mm=600, height_mm=2100, depth_mm=560, door_count=2)
                # NEW: Added a Wall Cabinet to the seed data!
                cab4 = Cabinet(project=project, name="Wall Cabinet", type="WALL", width_mm=800, height_mm=720, depth_mm=300, door_count=2)

                session.add_all([project, defaults, cab1, cab2, cab3, cab4])
                session.commit()
                existing = project

            all_mats = session.exec(select(Material)).all()
            self.materials = [m.name for m in all_mats if m.price_per_unit >= 10.0]

            global_mat = session.get(Material, existing.defaults.front_mat_id)
            self.global_front_mat_name = global_mat.name if global_mat else ""

            self.project_name = existing.customer_name
            total_price = 0.0

            wall_cabs = sorted([c for c in existing.cabinets if c.type == "WALL"], key=lambda c: c.order_index)
            base_cabs = sorted([c for c in existing.cabinets if c.type in ["BASE", "TALL"]], key=lambda c: c.order_index)

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
                    width_label=f"{cab.width_mm}mm", css_width=f"{cab.width_mm / 10}px", css_height=f"{cab.height_mm / 10}px",
                    doors=list(range(cab.door_count)), drawers=list(range(cab.drawer_count)),
                    width_mm=cab.width_mm, height_mm=cab.height_mm, depth_mm=cab.depth_mm,
                    door_count=cab.door_count, drawer_count=cab.drawer_count
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