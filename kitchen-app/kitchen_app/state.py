# kitchen_app/state.py
import reflex as rx
from sqlmodel import select
from kitchen_erp.database import get_session, engine, SQLModel
from kitchen_erp.models import Project, Cabinet, Material, HardwareSet, ProjectDefaults


class KitchenState(rx.State):
    """The reactive state for our UI."""

    project_name: str = "Loading..."
    total_price: float = 0.0

    # We store pure dictionaries for the UI to easily render without SQLModel relationship serialization issues
    cabinets_ui: list[dict] = []

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

                # Map to a simple dict for the frontend
                ui_list.append({
                    "id": cab.id,
                    "name": cab.name,
                    "width_mm": cab.width_mm,
                    "height_mm": cab.height_mm,
                    "price": cost_result.total_cost,
                    "is_tall": cab.type == "TALL"
                })

            self.cabinets_ui = ui_list
            self.total_price = round(total * existing.labor_markup, 2)