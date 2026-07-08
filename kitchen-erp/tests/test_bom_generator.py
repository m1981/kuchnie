"""Tests for BOM generator"""
import pytest
from sqlmodel import Session, create_engine, SQLModel
from kitchen_erp.core.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.core.bom_generator import BOMGenerator
from kitchen_erp.core.schemas import BOMAssembly


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


@pytest.fixture(name="defaults")
def defaults_fixture(session: Session):
    """Create project defaults with materials and hardware"""
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
    session.add(corpus_mat)
    session.add(back_mat)
    session.add(front_mat)
    session.add(edge_mat)
    session.commit()
    
    # Create hardware
    hinge_sys = HardwareSet(
        name="Blum Clip Top",
        price_per_set=2.50
    )
    drawer_sys = HardwareSet(
        name="Blum Legrabox",
        price_per_set=35.00
    )
    
    session.add(hinge_sys)
    session.add(drawer_sys)
    session.commit()
    
    # Create project
    project = Project(customer_name="Test Project")
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
    session.refresh(defaults)
    
    return defaults


def test_bom_generator_drawer_base(session: Session, defaults: ProjectDefaults):
    """Test BOM generation for drawer base cabinet"""
    cabinet = Cabinet(
        project_id=defaults.project_id,
        module_kind="DRAWER_BASE",
        type="BASE",
        name="Test Drawer Base",
        width_mm=400,
        height_mm=802,
        depth_mm=560,
        door_count=0,
        drawer_count=4,
        has_custom_front=True
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    assert isinstance(bom_tree, BOMAssembly)
    assert bom_tree.name == "Test Drawer Base"
    assert bom_tree.cost > 0
    
    # Check that we have parts
    parts = bom_tree.get_all_parts()
    assert len(parts) > 0
    
    # Should have corpus, back, front, edgebanding, legs, and drawer slides
    part_names = [p.name for p in parts]
    assert any("Corpus" in name for name in part_names)
    assert any("Back panel" in name for name in part_names)
    assert any("Front" in name for name in part_names)
    assert any("Edge banding" in name for name in part_names)
    assert any("Cabinet legs" in name for name in part_names)
    assert any("Drawer System" in name for name in part_names)


def test_bom_generator_wall_cabinet(session: Session, defaults: ProjectDefaults):
    """Test BOM generation for wall cabinet"""
    cabinet = Cabinet(
        project_id=defaults.project_id,
        module_kind="WALL_CABINET",
        type="WALL",
        name="Wall 800",
        width_mm=800,
        height_mm=720,
        depth_mm=320,
        door_count=2,
        drawer_count=0,
        has_custom_front=True
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    parts = bom_tree.get_all_parts()
    part_names = [p.name for p in parts]
    
    # Wall cabinet should have wall mounting brackets, not legs
    assert any("Wall mounting brackets" in name for name in part_names)
    assert not any("Cabinet legs" in name for name in part_names)
    
    # Should have hinges for 2 doors
    hinges = next((p for p in parts if "Door hinges" in p.name), None)
    assert hinges is not None
    assert hinges.quantity_net == 4  # 2 hinges per door * 2 doors


def test_bom_generator_oven_cabinet(session: Session, defaults: ProjectDefaults):
    """Test BOM generation for oven cabinet (no back panel)"""
    cabinet = Cabinet(
        project_id=defaults.project_id,
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
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    parts = bom_tree.get_all_parts()
    part_names = [p.name for p in parts]
    
    # Should NOT have back panel (formula returns 0)
    assert not any("Back panel" in name for name in part_names)
    
    # Should have ventilation grille (is_appliance tag)
    assert any("Appliance ventilation grille" in name for name in part_names)


def test_bom_generator_sink_base(session: Session, defaults: ProjectDefaults):
    """Test BOM generation for sink base cabinet"""
    cabinet = Cabinet(
        project_id=defaults.project_id,
        module_kind="SINK_BASE",
        type="BASE",
        name="Sink Base",
        width_mm=800,
        height_mm=802,
        depth_mm=560,
        door_count=1,
        drawer_count=0,
        has_custom_front=True
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    parts = bom_tree.get_all_parts()
    part_names = [p.name for p in parts]
    
    # Should have sink cabinet mat (is_sink tag)
    assert any("Sink cabinet mat" in name for name in part_names)


def test_bom_generator_pullout_filler(session: Session, defaults: ProjectDefaults):
    """Test BOM generation for pull-out filler"""
    cabinet = Cabinet(
        project_id=defaults.project_id,
        module_kind="PULLOUT_FILLER",
        type="BASE",
        name="Pull-out Filler",
        width_mm=200,
        height_mm=802,
        depth_mm=560,
        door_count=0,
        drawer_count=0,
        has_custom_front=True
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    parts = bom_tree.get_all_parts()
    part_names = [p.name for p in parts]
    
    # Should have pull-out mechanism (is_pullout tag)
    assert any("Pull-out mechanism" in name for name in part_names)
    
    # Should NOT have door hinges (no has_doors tag)
    assert not any("Door hinges" in name for name in part_names)



def test_bom_generator_cost_calculation(session: Session, defaults: ProjectDefaults):
    """Test that BOM generator calculates costs correctly"""
    cabinet = Cabinet(
        project_id=defaults.project_id,
        module_kind="WALL_CABINET",
        type="WALL",
        name="Wall 400",
        width_mm=400,
        height_mm=720,
        depth_mm=320,
        door_count=1,
        drawer_count=0,
        has_custom_front=True
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    # Total cost should be sum of all parts
    parts = bom_tree.get_all_parts()
    manual_total = sum(p.cost for p in parts)
    
    assert bom_tree.cost == pytest.approx(manual_total)
    assert bom_tree.cost > 0


def test_bom_generator_no_custom_front(session: Session, defaults: ProjectDefaults):
    """Front material semantics: has_custom_front only selects the MATERIAL.

    A cabinet with physical fronts (doors/drawers) always gets a front part —
    from project defaults when no override is set. A cabinet with zero doors
    and zero drawers gets no front part at all.
    """
    with_drawers = Cabinet(
        project_id=defaults.project_id,
        module_kind="DRAWER_BASE",
        type="BASE",
        name="Default Front Cabinet",
        width_mm=400,
        height_mm=802,
        depth_mm=560,
        door_count=0,
        drawer_count=2,
        has_custom_front=False  # no override -> defaults.front_mat
    )
    session.add(with_drawers)
    session.commit()
    session.refresh(with_drawers)

    parts = BOMGenerator(with_drawers, defaults).generate().get_all_parts()
    front_parts = [p for p in parts if p.name.startswith("Front:")]
    assert len(front_parts) == 1
    assert defaults.front_mat.name in front_parts[0].name
    assert front_parts[0].material_id == defaults.front_mat.id

    no_fronts = Cabinet(
        project_id=defaults.project_id,
        module_kind="DRAWER_BASE",
        type="BASE",
        name="Open Cabinet",
        width_mm=400,
        height_mm=802,
        depth_mm=560,
        door_count=0,
        drawer_count=0,  # nothing to face -> no front material
        has_custom_front=False
    )
    session.add(no_fronts)
    session.commit()
    session.refresh(no_fronts)

    parts = BOMGenerator(no_fronts, defaults).generate().get_all_parts()
    assert not any(p.name.startswith("Front:") for p in parts)
