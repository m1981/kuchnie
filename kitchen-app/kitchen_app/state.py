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

class KitchenState(rx.State):
    """The reactive state for our UI."""

    project_name: str = "Loading..."
    total_price: float = 0.0

    # Use our typed ViewModel instead of a raw dict
    cabinets_ui: list[CabinetUI] = []

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

            total = 0.0
            ui_list = []

            for cab in existing.cabinets:
                cost_result = cab.calculate_cost(existing.defaults, existing.waste_factor)
                total += cost_result.total_cost

                # Create the ViewModel with pre-calculated CSS
                ui_list.append(
                    CabinetUI(
                        id=cab.id,
                        name=cab.name,
                        price=cost_result.total_cost,
                        width_label=f"{cab.width_mm}mm",
                        css_width=f"{cab.width_mm / 10}px",
                        css_height=f"{cab.height_mm / 10}px",

                        # NEW: Create dummy lists based on the counts
                        doors=list(range(cab.door_count)),
                        drawers=list(range(cab.drawer_count))
                    )
                )

            self.cabinets_ui = ui_list
            self.total_price = round(total * existing.labor_markup, 2)

    def add_cabinet(self, cab_type: str):
        """Inserts a new cabinet into the database and refreshes the UI."""
        with next(get_session()) as session:
            # Get the current active project
            project = session.exec(select(Project)).first()
            if not project:
                return

            # Create a new cabinet based on the button clicked
            if cab_type == "BASE":
                new_cab = Cabinet(project=project, name="New Base", type="BASE", width_mm=600, height_mm=720,
                                  depth_mm=560, door_count=1)
            elif cab_type == "WALL":
                new_cab = Cabinet(project=project, name="New Wall", type="WALL", width_mm=600, height_mm=720,
                                  depth_mm=300, door_count=1)
            elif cab_type == "TALL":
                new_cab = Cabinet(project=project, name="New Tall", type="TALL", width_mm=600, height_mm=2100,
                                  depth_mm=560, door_count=2)

            # Save to database
            session.add(new_cab)
            session.commit()

        # Refresh the UI state (this recalculates the math and redraws the screen!)
        self.load_mock_data()