# kitchen_app/state.py
import reflex as rx
from pydantic import BaseModel # <-- Import standard Pydantic
from sqlmodel import select
from kitchen_erp.database import get_session, engine, SQLModel
from kitchen_erp.models import Project, Cabinet, Material, HardwareSet, ProjectDefaults

class CabinetUI(BaseModel): # <-- Inherit from BaseModel instead of rx.Base
    """ViewModel for the frontend to render cabinets easily."""
    id: int
    name: str
    price: float

    # Pre-formatted strings for the UI
    width_label: str
    css_width: str
    css_height: str

    # NEW: Lists for the UI to loop over
    doors: list[int] = []
    drawers: list[int] = []

    # NEW: Raw data for the Sidebar Inputs
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

    # NEW: Track total widths
    total_wall_width: float = 0.0
    total_base_width: float = 0.0

    # NEW: Sidebar State
    selected_cabinet_id: int | None = None
    selected_cabinet: CabinetUI | None = None

    def select_cabinet(self, cab_id: int):
        """Opens the sidebar for the clicked cabinet."""
        self.selected_cabinet_id = cab_id
        self._update_selected_cabinet_ui()

    def close_sidebar(self):
        self.selected_cabinet_id = None
        self.selected_cabinet = None

    def _update_selected_cabinet_ui(self):
        """Finds the selected cabinet data to populate the sidebar."""
        if self.selected_cabinet_id is None: return
        for cab in self.wall_cabinets + self.base_cabinets:
            if cab.id == self.selected_cabinet_id:
                self.selected_cabinet = cab
                break

    def update_cabinet_field(self, field: str, value: str):
        """Updates a specific field in the database and recalculates."""
        if not self.selected_cabinet_id: return

        with next(get_session()) as session:
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if not cab: return

            # Safely cast the string input from the UI to the correct Python type
            if field in ["width_mm", "height_mm", "depth_mm"]:
                setattr(cab, field, float(value or 0))
            elif field in ["door_count", "drawer_count"]:
                setattr(cab, field, int(value or 0))
            else:
                setattr(cab, field, value)

            session.add(cab)
            session.commit()

        # Reload everything to recalculate prices and redraw boxes
        self.load_mock_data()

    def delete_cabinet(self):
        """Deletes the currently selected cabinet."""
        if not self.selected_cabinet_id: return
        with next(get_session()) as session:
            cab = session.get(Cabinet, self.selected_cabinet_id)
            if cab:
                session.delete(cab)
                session.commit()
        self.close_sidebar()
        self.load_mock_data()

    def load_mock_data(self):
        """Seeds the DB and loads it into the UI state."""
        SQLModel.metadata.create_all(engine)

        with next(get_session()) as session:
            # Check if we already have data
            existing = session.exec(select(Project)).first()
            if not existing:
                # Seed Data (Like our integration test)
                mdf = Material(name="Standard MDF", price_per_unit=10.0, unit="m2")
                hdf = Material(name="HDF Back", price_per_unit=5.0, unit="m2")
                edge = Material(name="ABS Edge", price_per_unit=1.0, unit="lm")
                hinge = HardwareSet(name="Blum Hinge", price_per_set=2.0)
                drawer = HardwareSet(name="Blum Drawer", price_per_set=30.0)

                session.add_all([mdf, hdf, edge, hinge, drawer])
                session.commit()

                project = Project(customer_name="Smith Family Kitchen")
                defaults = ProjectDefaults(
                    project=project, corpus_mat_id=mdf.id, front_mat_id=mdf.id,
                    back_mat_id=hdf.id, edge_band_mat_id=edge.id,
                    hinge_sys_id=hinge.id, drawer_sys_id=drawer.id
                )

                cab1 = Cabinet(project=project, name="Sink Base", type="BASE", width_mm=800, height_mm=720,
                               depth_mm=560, door_count=2)
                cab2 = Cabinet(project=project, name="Drawer Base", type="BASE", width_mm=600, height_mm=720,
                               depth_mm=560, drawer_count=3)
                cab3 = Cabinet(project=project, name="Tall Oven", type="TALL", width_mm=600, height_mm=2100,
                               depth_mm=560, door_count=2)

                session.add_all([project, defaults, cab1, cab2, cab3])
                session.commit()
                existing = project

            # --- Update UI State ---
            self.project_name = existing.customer_name
            total_price = 0.0

            # 1. NORMALIZE ORDER INDEXES (Fixes the arrow bug for old data)
            wall_cabs = sorted([c for c in existing.cabinets if c.type == "WALL"], key=lambda c: c.order_index)
            base_cabs = sorted([c for c in existing.cabinets if c.type in ["BASE", "TALL"]], key=lambda c: c.order_index)

            for i, cab in enumerate(wall_cabs): cab.order_index = i
            for i, cab in enumerate(base_cabs): cab.order_index = i
            session.commit() # Save the fixed indexes

            # 2. CALCULATE UI DATA
            wall_list, base_list = [], []
            wall_width, base_width = 0.0, 0.0

            for cab in wall_cabs + base_cabs:
                cost_result = cab.calculate_cost(existing.defaults, existing.waste_factor)
                total_price += cost_result.total_cost

                cab_ui = CabinetUI(
                    id=cab.id, name=cab.name, price=cost_result.total_cost,
                    width_label=f"{cab.width_mm}mm", css_width=f"{cab.width_mm / 10}px", css_height=f"{cab.height_mm / 10}px",
                    doors=list(range(cab.door_count)), drawers=list(range(cab.drawer_count)),
                    # NEW: Pass raw data to UI
                    width_mm=cab.width_mm, height_mm=cab.height_mm, depth_mm=cab.depth_mm,
                    door_count=cab.door_count, drawer_count=cab.drawer_count
                )

                # Split into rows
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

    def add_cabinet(self, cab_type: str):
        """Inserts a new cabinet into the database and refreshes the UI."""
        with next(get_session()) as session:
            # Get the current active project
            project = session.exec(select(Project)).first()
            if not project:
                return

            # Find the highest order_index so the new cabinet goes to the end of the line
            max_order = max([c.order_index for c in project.cabinets if c.type == cab_type] or [-1])

            if cab_type == "BASE":
                new_cab = Cabinet(project=project, name="New Base", type="BASE", width_mm=600, height_mm=720, depth_mm=560, door_count=1, order_index=max_order + 1)
            elif cab_type == "WALL":
                new_cab = Cabinet(project=project, name="New Wall", type="WALL", width_mm=600, height_mm=720, depth_mm=300, door_count=1, order_index=max_order + 1)
            elif cab_type == "TALL":
                new_cab = Cabinet(project=project, name="New Tall", type="TALL", width_mm=600, height_mm=2100, depth_mm=560, door_count=2, order_index=max_order + 1)

            # Save to database
            session.add(new_cab)
            session.commit()

        # Refresh the UI state (this recalculates the math and redraws the screen!)
        self.load_mock_data()

    def move_cabinet(self, cab_id: int, direction: int):
        """Moves a cabinet left (-1) or right (+1)."""
        with next(get_session()) as session:
            cab = session.get(Cabinet, cab_id)
            if not cab: return

            project = session.get(Project, cab.project_id)

            # Group siblings correctly (Base and Tall share a row)
            if cab.type == "WALL":
                siblings = [c for c in project.cabinets if c.type == "WALL"]
            else:
                siblings = [c for c in project.cabinets if c.type in ["BASE", "TALL"]]

            siblings.sort(key=lambda c: c.order_index)

            # Find current index using ID to avoid object mismatch
            idx = next((i for i, c in enumerate(siblings) if c.id == cab_id), -1)
            if idx == -1: return

            new_idx = idx + direction

            # If the move is valid, swap their order_indexes
            if 0 <= new_idx < len(siblings):
                swap_cab = siblings[new_idx]
                # Swap the indexes
                cab.order_index, swap_cab.order_index = swap_cab.order_index, cab.order_index
                session.add_all([cab, swap_cab])
                session.commit()

        self.load_mock_data()