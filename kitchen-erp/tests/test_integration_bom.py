"""Integration tests showing how new BOM system works with existing code"""
import pytest
from sqlmodel import Session, create_engine, SQLModel, select
from kitchen_erp.core.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.core.bom_generator import BOMGenerator


@pytest.fixture(name="engine")
def engine_fixture():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create database session"""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_project")
def test_project_fixture(session: Session):
    """Create a complete test project with materials, hardware, and cabinets"""
    # Create materials
    corpus_mat = Material(
        name="Egger W1000 Premium White",
        category="Board",
        price_per_unit=12.50,
        unit="m2"
    )
    back_mat = Material(
        name="Generic HDF White 3mm",
        category="Panel",
        price_per_unit=4.50,
        unit="m2"
    )
    front_mat = Material(
        name="Egger W1000 Premium White",
        category="Board",
        price_per_unit=12.50,
        unit="m2"
    )
    
    edge_mat = Material(
        name="ABS White 1mm",
        category="Edgebanding",
        price_per_unit=0.80,
        unit="lm"
    )
    session.add_all([corpus_mat, back_mat, front_mat, edge_mat])
    session.commit()
    
    # Create hardware
    hinge_sys = HardwareSet(name="Blum Clip Top", price_per_set=2.50)
    drawer_sys = HardwareSet(name="Blum Legrabox", price_per_set=35.00)
    
    session.add_all([hinge_sys, drawer_sys])
    session.commit()
    
    # Create project
    project = Project(customer_name="Test Kitchen")
    session.add(project)
    session.commit()
    
    # Create defaults
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=corpus_mat.id,
        back_mat_id=back_mat.id,
        front_mat_id=front_mat.id,
        edge_band_mat_id=edge_mat.id,
        hinge_sys_id=hinge_sys.id,
        drawer_sys_id=drawer_sys.id,
        waste_factor=1.20
    )
    session.add(defaults)
    session.commit()
    
    # Create test cabinets
    cabinets = [
        Cabinet(
            project_id=project.id,
            module_kind="WALL_CABINET",
            type="WALL",
            name="Wall 400",
            width_mm=400,
            height_mm=720,
            depth_mm=320,
            door_count=1,
            drawer_count=0,
            has_custom_front=True
        ),
        Cabinet(
            project_id=project.id,
            module_kind="DRAWER_BASE",
            type="BASE",
            name="Drawer Base 800",
            width_mm=800,
            height_mm=802,
            depth_mm=560,
            door_count=0,
            drawer_count=4,
            has_custom_front=True
        ),
        Cabinet(
            project_id=project.id,
            module_kind="SINK_BASE",
            type="BASE",
            name="Sink Base 800",
            width_mm=800,
            height_mm=802,
            depth_mm=560,
            door_count=1,
            drawer_count=0,
            has_custom_front=True
        ),
    ]
    
    session.add_all(cabinets)
    session.commit()
    
    session.refresh(project)
    return project


def test_canonical_bom_covers_all_cabinets(session: Session, test_project: Project):
    """ADR-011: BOMGenerator is the only cost path and must handle every
    cabinet in a project with a positive, materialized cost."""
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()

    for cabinet in test_project.cabinets:
        bom_tree = BOMGenerator(cabinet, defaults).generate()
        assert bom_tree.cost > 0
        parts = bom_tree.get_all_parts()
        assert any(p.material_id for p in parts), f"{cabinet.name}: no material parts"


def test_canonical_bom_detail_breakdown(session: Session, test_project: Project):
    """The recipe-based BOM itemizes materials, edge banding, CNC services
    and hardware as separate priced lines."""
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()

    cabinet = test_project.cabinets[0]  # Wall cabinet with a door
    parts = BOMGenerator(cabinet, defaults).generate().get_all_parts()
    names = [p.name for p in parts]

    assert len(parts) >= 5
    assert any(n.startswith("Corpus:") for n in names)
    assert any("Edge banding" in n for n in names)
    assert any("CNC Service" in n for n in names)
    assert any("hinges" in n.lower() for n in names)
    assert all(p.cost >= 0 for p in parts)


def test_project_level_aggregation(session: Session, test_project: Project):
    """Test aggregating materials across all cabinets in a project"""
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()
    
    # Aggregate materials from all cabinets
    material_totals = {}
    
    for cabinet in test_project.cabinets:
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        for part in bom_tree.get_all_parts():
            if part.material_id:
                key = (part.material_id, part.unit)
                if key not in material_totals:
                    material_totals[key] = {
                        "name": part.name,
                        "quantity": 0,
                        "unit": part.unit,
                        "unit_price": part.unit_price
                    }
                material_totals[key]["quantity"] += part.quantity_net
    
    # Should have aggregated corpus board from all 3 cabinets
    corpus_entries = [v for k, v in material_totals.items() if "Corpus" in v["name"]]
    assert len(corpus_entries) > 0
    
    # Total corpus should be sum of all cabinets
    total_corpus_m2 = sum(e["quantity"] for e in corpus_entries)
    assert total_corpus_m2 > 0


def test_recipe_driven_hardware_addition(session: Session, test_project: Project):
    """Test that hardware is automatically added based on recipe tags"""
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()
    
    # Sink base should have sink mat (from is_sink tag)
    sink_cabinet = next(c for c in test_project.cabinets if c.module_kind == "SINK_BASE")
    
    generator = BOMGenerator(sink_cabinet, defaults)
    bom_tree = generator.generate()
    parts = bom_tree.get_all_parts()
    
    part_names = [p.name for p in parts]
    assert any("Sink cabinet mat" in name for name in part_names)


def test_no_back_panel_for_oven_cabinet(session: Session):
    """Test that oven cabinet recipe correctly omits back panel"""
    # Create minimal setup for oven cabinet
    project = Project(customer_name="Oven Test")
    session.add(project)
    session.commit()
    
    corpus_mat = Material(name="Test Board", category="Board", price_per_unit=10.0, unit="m2")
    back_mat = Material(name="Test Back", category="Panel", price_per_unit=5.0, unit="m2")
    front_mat = Material(name="Test Front", category="Board", price_per_unit=10.0, unit="m2")
    edge_mat = Material(name="Test Edge", category="Edgebanding", price_per_unit=0.8, unit="lm")
    hinge = HardwareSet(name="Test Hinge", price_per_set=2.0)
    drawer = HardwareSet(name="Test Drawer", price_per_set=30.0)
    
    session.add_all([corpus_mat, back_mat, front_mat, edge_mat, hinge, drawer])
    session.commit()
    
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=corpus_mat.id,
        back_mat_id=back_mat.id,
        front_mat_id=front_mat.id,
        edge_band_mat_id=edge_mat.id,
        hinge_sys_id=hinge.id,
        drawer_sys_id=drawer.id,
        waste_factor=1.20
    )
    session.add(defaults)
    session.commit()
    
    oven_cabinet = Cabinet(
        project_id=project.id,
        module_kind="OVEN_BASE",
        type="BASE",
        name="Oven Cabinet",
        width_mm=600,
        height_mm=802,
        depth_mm=560,
        door_count=0,
        drawer_count=0,
        has_custom_front=False
    )
    session.add(oven_cabinet)
    session.commit()
    
    generator = BOMGenerator(oven_cabinet, defaults)
    bom_tree = generator.generate()
    parts = bom_tree.get_all_parts()
    
    part_names = [p.name for p in parts]
    
    # Should NOT have back panel (formula returns 0)
    assert not any("Back panel" in name for name in part_names)
    
    # Should have ventilation grille (is_appliance tag)
    assert any("Appliance ventilation grille" in name for name in part_names)


def test_purchasing_strategy_integration(session: Session, test_project: Project):
    """Test that purchasing strategies can be applied to BOM parts"""
    from kitchen_erp.core.purchasing import get_strategy_for_material
    
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()
    
    # Generate BOM for all cabinets
    total_corpus_m2 = 0
    
    for cabinet in test_project.cabinets:
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        for part in bom_tree.get_all_parts():
            if "Corpus" in part.name and part.unit == "m2":
                total_corpus_m2 += part.quantity_net
    
    # Apply purchasing strategy
    strategy = get_strategy_for_material("Board")
    purchase_qty = strategy.calculate_purchase_quantity(total_corpus_m2)
    waste_factor = strategy.get_waste_factor(total_corpus_m2)
    
    # Purchase quantity should be higher (rounded to full sheets)
    assert purchase_qty >= total_corpus_m2
    assert waste_factor >= 1.0
    
    print(f"\nPurchasing Analysis:")
    print(f"  Net requirement: {total_corpus_m2:.2f} m²")
    print(f"  Must purchase: {purchase_qty:.2f} m²")
    print(f"  Waste factor: {waste_factor:.2f}x ({(waste_factor-1)*100:.1f}% waste)")
