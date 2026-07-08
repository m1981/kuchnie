# tests/test_database_integration.py
from sqlmodel import Session, select
from kitchen_erp.core.models import Material, HardwareSet, Project, ProjectDefaults, Cabinet


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

    # Cost math itself is pinned in test_calculations.py; here we verify the
    # DB-loaded objects price through the canonical path and that the
    # override_front_mat relationship survives the round trip: the premium
    # cabinet (Oak front @ $50) must cost more than the standard (MDF @ $10).
    from kitchen_erp.core.bom_generator import BOMGenerator
    cost_cab1 = BOMGenerator(db_project.cabinets[0], db_project.defaults).generate().cost
    cost_cab2 = BOMGenerator(db_project.cabinets[1], db_project.defaults).generate().cost
    assert cost_cab1 > 0
    assert cost_cab2 > cost_cab1