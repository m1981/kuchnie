"""Integration tests showing how new BOM system works with existing code"""
import pytest
from sqlmodel import Session, create_engine, SQLModel, select
from kitchen_erp.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.bom_generator import BOMGenerator
from kitchen_erp.schemas import CabinetCostResult


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
        price_per_unit=12.50
    )
    back_mat = Material(
        name="Generic HDF White 3mm",
        category="Panel",
        price_per_unit=4.50
    )
    front_mat = Material(
        name="Egger W1000 Premium White",
        category="Board",
        price_per_unit=12.50
    )
    
    session.add_all([corpus_mat, back_mat, front_mat])
    session.commit()
    
    # Create hardware
    hinge_sys = HardwareSet(name="Blum Clip Top", price_per_set=2.50)
    drawer_sys = HardwareSet(name="Blum Legrabox", price_per_set=35.00)
    
    session.add_all([hinge_sys, drawer_sys])
    session.commit()
    
    # Create project
    project = Project(name="Test Kitchen")
    session.add(project)
    session.commit()
    
    # Create defaults
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=corpus_mat.id,
        back_mat_id=back_mat.id,
        front_mat_id=front_mat.id,
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


def test_backward_compatibility_old_vs_new(session: Session, test_project: Project):
    """Test that new BOM generator produces similar results to old calculate_cost()"""
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()
    
    for cabinet in test_project.cabinets:
        # OLD WAY
        old_result: CabinetCostResult = cabinet.calculate_cost(defaults, waste_factor=1.20)
        
        # NEW WAY
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        # Costs should be similar (may differ slightly due to improved calculations)
        # Allow 10% tolerance for now
        assert bom_tree.cost == pytest.approx(old_result.total_cost, rel=0.1)


def test_new_bom_has_more_detail_than_old(session: Session, test_project: Project):
    """Test that new BOM provides more detailed breakdown than old system"""
    defaults = session.exec(
        select(ProjectDefaults).where(ProjectDefaults.project_id == test_project.id)
    ).first()
    
    cabinet = test_project.cabinets[0]  # Wall cabinet
    
    # OLD WAY
    old_result = cabinet.calculate_cost(defaults, waste_factor=1.20)
    old_line_count = len(old_result.trace_lines)
    
    # NEW WAY
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    new_parts = bom_tree.get_all_parts()
    
    # New system should have at least as many items (likely more due to hardware rules)
    assert len(new_parts) >= old_line_count


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
    project = Project(name="Oven Test")
    session.add(project)
    session.commit()
    
    corpus_mat = Material(name="Test Board", category="Board", price_per_unit=10.0)
    back_mat = Material(name="Test Back", category="Panel", price_per_unit=5.0)
    front_mat = Material(name="Test Front", category="Board", price_per_unit=10.0)
    hinge = HardwareSet(name="Test Hinge", price_per_set=2.0)
    drawer = HardwareSet(name="Test Drawer", price_per_set=30.0)
    
    session.add_all([corpus_mat, back_mat, front_mat, hinge, drawer])
    session.commit()
    
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=corpus_mat.id,
        back_mat_id=back_mat.id,
        front_mat_id=front_mat.id,
        hinge_sys_id=hinge.id,
        drawer_sys_id=drawer.id,
        waste_factor=1.20
    )
    session.add(defaults)
    session.commit()
    
    oven_cabinet = Cabinet(
        project_id=project.id,
        module_kind="OVEN_BASE",
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
    from kitchen_erp.purchasing import get_strategy_for_material
    
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
