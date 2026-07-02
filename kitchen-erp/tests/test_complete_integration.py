"""Complete end-to-end integration test"""
import pytest
from sqlmodel import Session, create_engine, SQLModel, select
from kitchen_erp.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.bom_generator import BOMGenerator
from kitchen_erp.purchasing import get_strategy_for_material


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


def test_complete_kitchen_workflow(session: Session):
    """
    Test complete workflow from project creation to final BOM.
    
    This simulates a real user creating a kitchen project and getting costs.
    """
    # Step 1: Create materials
    corpus = Material(name="Egger W1000", category="Board", price_per_unit=12.50, unit="m2")
    back = Material(name="HDF 3mm", category="Panel", price_per_unit=4.50, unit="m2")
    front = Material(name="Egger W1000", category="Board", price_per_unit=12.50, unit="m2")
    edge = Material(name="ABS White", category="Edgebanding", price_per_unit=0.80, unit="lm")
    
    session.add_all([corpus, back, front, edge])
    session.commit()
    
    # Step 2: Create hardware
    hinges = HardwareSet(name="Blum Clip Top", price_per_set=2.50)
    drawers = HardwareSet(name="Blum Legrabox", price_per_set=35.00)
    
    session.add_all([hinges, drawers])
    session.commit()
    
    # Step 3: Create project
    project = Project(
        customer_name="Test Customer",
        waste_factor=1.20,
        labor_markup=1.50
    )
    session.add(project)
    session.commit()
    
    # Step 4: Create project defaults
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=corpus.id,
        back_mat_id=back.id,
        front_mat_id=front.id,
        edge_band_mat_id=edge.id,
        hinge_sys_id=hinges.id,
        drawer_sys_id=drawers.id,
        waste_factor=1.20
    )
    session.add(defaults)
    session.commit()
    
    # Step 5: Add cabinets to project
    cabinets = [
        Cabinet(
            project_id=project.id,
            module_kind="WALL_CABINET",
            name="Wall 400",
            type="WALL",
            width_mm=400,
            height_mm=720,
            depth_mm=320,
            door_count=1,
            drawer_count=0
        ),
        Cabinet(
            project_id=project.id,
            module_kind="DRAWER_BASE",
            name="Drawer Base 800",
            type="BASE",
            width_mm=800,
            height_mm=802,
            depth_mm=560,
            door_count=0,
            drawer_count=4
        ),
        Cabinet(
            project_id=project.id,
            module_kind="SINK_BASE",
            name="Sink Base 800",
            type="BASE",
            width_mm=800,
            height_mm=802,
            depth_mm=560,
            door_count=1,
            drawer_count=0
        ),
    ]
    
    session.add_all(cabinets)
    session.commit()
    session.refresh(project)
    
    # Step 6: Generate BOM for each cabinet
    print("\n" + "="*60)
    print("INDIVIDUAL CABINET BOMS")
    print("="*60)
    
    cabinet_costs = []
    for cabinet in project.cabinets:
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        print(f"\n{cabinet.name}:")
        print(f"  Total: ${bom_tree.cost:.2f}")
        print(f"  Parts:")
        for part in bom_tree.get_all_parts():
            print(f"    - {part.name}: {part.quantity_net:.2f} {part.unit} @ ${part.unit_price:.2f} = ${part.cost:.2f}")
        
        cabinet_costs.append(bom_tree.cost)
    
    # Step 7: Aggregate materials across project
    print("\n" + "="*60)
    print("PROJECT-LEVEL MATERIAL AGGREGATION")
    print("="*60)
    
    material_totals = {}
    hardware_totals = {}
    
    for cabinet in project.cabinets:
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        for part in bom_tree.get_all_parts():
            if part.material_id:
                key = (part.material_id, part.unit)
                if key not in material_totals:
                    material_totals[key] = {
                        "name": part.name,
                        "quantity_net": 0,
                        "unit": part.unit,
                        "unit_price": part.unit_price,
                        "material_id": part.material_id
                    }
                material_totals[key]["quantity_net"] += part.quantity_net
            else:
                if part.name not in hardware_totals:
                    hardware_totals[part.name] = {
                        "quantity_net": 0,
                        "unit": part.unit,
                        "unit_price": part.unit_price
                    }
                hardware_totals[part.name]["quantity_net"] += part.quantity_net
    
    # Step 8: Apply purchasing strategies
    print("\nMATERIALS (with purchasing strategies):")
    total_material_cost = 0
    
    for (mat_id, unit), data in material_totals.items():
        material = session.get(Material, mat_id)
        strategy = get_strategy_for_material(material.category)
        
        net_qty = data["quantity_net"]
        purchase_qty = strategy.calculate_purchase_quantity(net_qty)
        waste_factor = strategy.get_waste_factor(net_qty)
        cost = purchase_qty * data["unit_price"]
        
        total_material_cost += cost
        
        print(f"  {data['name']}:")
        print(f"    Net required: {net_qty:.2f} {unit}")
        print(f"    Must purchase: {purchase_qty:.2f} {unit}")
        print(f"    Waste: {(waste_factor - 1) * 100:.1f}%")
        print(f"    Cost: ${cost:.2f}")
    
    print("\nHARDWARE:")
    total_hardware_cost = 0
    
    for name, data in hardware_totals.items():
        cost = data["quantity_net"] * data["unit_price"]
        total_hardware_cost += cost
        
        print(f"  {name}:")
        print(f"    Quantity: {data['quantity_net']:.0f} {data['unit']}")
        print(f"    Cost: ${cost:.2f}")
    
    # Step 9: Calculate final project cost
    subtotal = total_material_cost + total_hardware_cost
    markup = subtotal * (project.labor_markup - 1)
    total = subtotal + markup
    
    print("\n" + "="*60)
    print("PROJECT SUMMARY")
    print("="*60)
    print(f"Materials: ${total_material_cost:.2f}")
    print(f"Hardware: ${total_hardware_cost:.2f}")
    print(f"Subtotal: ${subtotal:.2f}")
    print(f"Labor/Markup ({project.labor_markup}x): ${markup:.2f}")
    print(f"TOTAL: ${total:.2f}")
    
    # Assertions
    assert len(cabinet_costs) == 3
    assert all(cost > 0 for cost in cabinet_costs)
    assert total_material_cost > 0
    assert total_hardware_cost > 0
    assert total > subtotal
    
    # Verify purchasing strategies are working
    # (purchase qty should be higher than net qty for boards)
    corpus_entries = [v for k, v in material_totals.items() if "Corpus" in v["name"]]
    assert len(corpus_entries) > 0
    
    for entry in corpus_entries:
        material = session.get(Material, entry["material_id"])
        strategy = get_strategy_for_material(material.category)
        purchase_qty = strategy.calculate_purchase_quantity(entry["quantity_net"])
        
        # Purchase quantity should be >= net quantity
        assert purchase_qty >= entry["quantity_net"]
    
    print("\n✅ Complete integration test passed!")


def test_recipe_driven_cabinet_creation(session: Session):
    """Test that new cabinets can be created using recipes"""
    from kitchen_erp.recipe_loader import get_recipe
    
    # Load recipe
    recipe = get_recipe("DRAWER_BASE")
    
    # Verify recipe structure
    assert "name" in recipe
    assert "tags" in recipe
    assert "formulas" in recipe
    assert "default_dimensions" in recipe
    
    # Create cabinet using recipe defaults
    cabinet = Cabinet(
        project_id=1,
        module_kind="DRAWER_BASE",
        name=recipe["name"],
        type=recipe["type"],
        width_mm=recipe["default_dimensions"]["width_mm"],
        height_mm=recipe["default_dimensions"]["height_mm"],
        depth_mm=recipe["default_dimensions"]["depth_mm"],
        door_count=0,
        drawer_count=4
    )
    
    assert cabinet.width_mm == 400
    assert cabinet.height_mm == 802
    assert cabinet.depth_mm == 560
    
    print("✅ Recipe-driven cabinet creation works!")


def test_tag_based_hardware_addition(session: Session):
    """Test that tags automatically add correct hardware"""
    from kitchen_erp.recipe_loader import get_recipe_tags
    from kitchen_erp.rules_engine import RulesEngine
    from kitchen_erp.schemas import BOMAssembly
    
    # Get tags for drawer base
    tags = get_recipe_tags("DRAWER_BASE")
    
    assert "is_base" in tags
    assert "has_drawers" in tags
    
    # Apply rules
    engine = RulesEngine()
    assembly = BOMAssembly(name="Test")
    
    engine.apply_rules(tags, assembly, multipliers={"has_drawers": 4})
    
    parts = assembly.get_all_parts()
    part_names = [p.name for p in parts]
    
    # Should have legs (from is_base tag)
    assert any("Cabinet legs" in name for name in part_names)
    
    # Should have drawer slides (from has_drawers tag)
    slides = next((p for p in parts if "Drawer slides" in p.name), None)
    assert slides is not None
    assert slides.quantity_net == 4  # 4 drawers
    
    print("✅ Tag-based hardware addition works!")
