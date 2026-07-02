# tests/test_database_integration.py
from sqlmodel import Session, select
from kitchen_erp.models import Material, HardwareSet, Project, ProjectDefaults, Cabinet


def test_full_project_database_lifecycle(session: Session):
    # 1. ARRANGE: Seed the Catalog (Master Data)
    mdf = Material(name="Standard MDF", price_per_unit=10.0, unit="m2")
    oak = Material(name="Premium Oak", price_per_unit=50.0, unit="m2")  # For override
    hdf = Material(name="HDF Back", price_per_unit=5.0, unit="m2")
    edge = Material(name="ABS Edge", price_per_unit=1.0, unit="lm")

    hinge = HardwareSet(name="Blum Hinge", price_per_set=2.0)
    drawer = HardwareSet(name="Blum Drawer", price_per_set=30.0)

    session.add_all([mdf, oak, hdf, edge, hinge, drawer])
    session.commit()  # Commit to generate IDs

    # 2. ACT: Create a Project with Defaults and Cabinets
    project = Project(customer_name="Kowalski Kitchen")

    defaults = ProjectDefaults(
        project=project,  # SQLModel automatically handles the project_id FK!
        corpus_mat_id=mdf.id,
        front_mat_id=mdf.id,
        back_mat_id=hdf.id,
        edge_band_mat_id=edge.id,
        hinge_sys_id=hinge.id,
        drawer_sys_id=drawer.id
    )

    cab1 = Cabinet(
        project=project,
        name="Standard Base",
        type="BASE",
        width_mm=1000, height_mm=1000, depth_mm=500,
        door_count=1
    )

    cab2 = Cabinet(
        project=project,
        name="Island Premium Base",
        type="ISLAND",
        width_mm=1000, height_mm=1000, depth_mm=500,
        door_count=1,
        override_front_mat_id=oak.id  # Local Override!
    )

    session.add(project)
    session.add(defaults)
    session.add_all([cab1, cab2])
    session.commit()

    # 3. ASSERT: Retrieve from DB and verify relationships and math
    # Clear session to ensure we are actually reading from the DB, not memory
    session.expire_all()

    statement = select(Project).where(Project.customer_name == "Kowalski Kitchen")
    db_project = session.exec(statement).first()

    assert db_project is not None
    assert len(db_project.cabinets) == 2
    assert db_project.defaults is not None

    # Test Math on Standard Cabinet (Front is MDF @ $10)
    # Expected: 56.0 (Material: 50.0, Hardware: 6.0)
    cost_cab1 = db_project.cabinets[0].calculate_cost(db_project.defaults, db_project.waste_factor)
    assert cost_cab1.total_cost == 56.0

    # Test Math on Premium Cabinet (Front is Oak @ $50)
    # Front Area is 1m2. Difference from MDF is ($50 - $10) * 1.2 waste = $48 increase.
    # Expected: 56.0 + 48.0 = 104.0
    cost_cab2 = db_project.cabinets[1].calculate_cost(db_project.defaults, db_project.waste_factor)
    assert cost_cab2.total_cost == 104.0