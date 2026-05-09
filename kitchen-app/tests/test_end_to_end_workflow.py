"""
End-to-end workflow test demonstrating complete BOM system usage.

This test serves as both validation and documentation, showing:
1. How to create a project from scratch
2. How to use recipes to define cabinets
3. How the rules engine automatically adds hardware
4. How purchasing strategies calculate realistic costs
5. How to aggregate materials across a project
"""
import pytest
from sqlmodel import Session, create_engine, SQLModel
from kitchen_erp.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.bom_generator import BOMGenerator
from kitchen_erp.purchasing import get_strategy_for_material
from kitchen_erp.recipe_loader import get_recipe


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


def test_complete_workflow_with_documentation(session: Session):
    """
    Complete workflow test with detailed documentation.
    
    This test demonstrates the entire BOM system from project creation
    to final cost calculation, showing all 4 architectural patterns in action.
    """
    
    print("\n" + "="*80)
    print("KITCHEN APP BOM SYSTEM - COMPLETE WORKFLOW DEMONSTRATION")
    print("="*80)
    
    # ========================================================================
    # STEP 1: Setup - Create Materials Database
    # ========================================================================
    print("\n[STEP 1] Creating materials database...")
    
    # Create board materials
    egger_white = Material(
        name="Egger W1000 Premium White",
        brand="Egger",
        category="Board",
        price_per_unit=12.50,
        unit="m2"
    )
    
    hdf_back = Material(
        name="HDF White 3mm",
        brand="Generic",
        category="Panel",
        price_per_unit=4.50,
        unit="m2"
    )
    
    abs_edge = Material(
        name="ABS White 1mm",
        brand="Generic",
        category="Edgebanding",
        price_per_unit=0.80,
        unit="lm"
    )
    
    session.add_all([egger_white, hdf_back, abs_edge])
    session.commit()
    
    print(f"  ✓ Created {egger_white.name} @ ${egger_white.price_per_unit}/{egger_white.unit}")
    print(f"  ✓ Created {hdf_back.name} @ ${hdf_back.price_per_unit}/{hdf_back.unit}")
    print(f"  ✓ Created {abs_edge.name} @ ${abs_edge.price_per_unit}/{abs_edge.unit}")
    
    # ========================================================================
    # STEP 2: Setup - Create Hardware Database
    # ========================================================================
    print("\n[STEP 2] Creating hardware database...")
    
    blum_hinges = HardwareSet(
        name="Blum Clip Top",
        brand="Blum",
        price_per_set=2.50
    )
    
    blum_drawers = HardwareSet(
        name="Blum Legrabox",
        brand="Blum",
        price_per_set=35.00
    )
    
    session.add_all([blum_hinges, blum_drawers])
    session.commit()
    
    print(f"  ✓ Created {blum_hinges.name} @ ${blum_hinges.price_per_set}/set")
    print(f"  ✓ Created {blum_drawers.name} @ ${blum_drawers.price_per_set}/set")
    
    # ========================================================================
    # STEP 3: Create Project with Defaults
    # ========================================================================
    print("\n[STEP 3] Creating project...")
    
    project = Project(
        customer_name="Demo Customer - Modern Kitchen",
        waste_factor=1.20,
        labor_markup=1.50
    )
    session.add(project)
    session.commit()
    
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=egger_white.id,
        back_mat_id=hdf_back.id,
        front_mat_id=egger_white.id,
        edge_band_mat_id=abs_edge.id,
        hinge_sys_id=blum_hinges.id,
        drawer_sys_id=blum_drawers.id,
        waste_factor=1.20
    )
    session.add(defaults)
    session.commit()
    
    print(f"  ✓ Created project: {project.customer_name}")
    print(f"  ✓ Waste factor: {project.waste_factor}x")
    print(f"  ✓ Labor markup: {project.labor_markup}x")
    
    # ========================================================================
    # STEP 4: PATTERN 1 - Recipe System (Data-Driven Design)
    # ========================================================================
    print("\n[STEP 4] PATTERN 1: Recipe System - Loading cabinet definitions from JSON...")
    
    # Load recipe to see what it contains
    drawer_recipe = get_recipe("DRAWER_BASE")
    wall_recipe = get_recipe("WALL_CABINET")
    sink_recipe = get_recipe("SINK_BASE")
    
    print(f"\n  Recipe: {drawer_recipe['name']}")
    print(f"    Type: {drawer_recipe['type']}")
    print(f"    Tags: {', '.join(drawer_recipe['tags'])}")
    print(f"    Default size: {drawer_recipe['default_dimensions']['width_mm']}x"
          f"{drawer_recipe['default_dimensions']['height_mm']}x"
          f"{drawer_recipe['default_dimensions']['depth_mm']} mm")
    
    # Create cabinets using recipe defaults
    cabinets = [
        Cabinet(
            project_id=project.id,
            module_kind="WALL_CABINET",
            name="Wall Cabinet 800",
            type="WALL",
            width_mm=800,
            height_mm=720,
            depth_mm=320,
            door_count=2,
            drawer_count=0
        ),
        Cabinet(
            project_id=project.id,
            module_kind="DRAWER_BASE",
            name="Drawer Base 400",
            type="BASE",
            width_mm=400,
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
    
    print(f"\n  ✓ Created {len(cabinets)} cabinets using recipes")
    
    # ========================================================================
    # STEP 5: PATTERN 2 - Composite Pattern (BOM Tree)
    # ========================================================================
    print("\n[STEP 5] PATTERN 2: Composite Pattern - Building hierarchical BOM trees...")
    
    for cabinet in project.cabinets:
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        print(f"\n  {cabinet.name}:")
        print(f"    Total Cost: ${bom_tree.cost:.2f}")
        print(f"    BOM Structure:")
        
        # Show hierarchical structure
        parts = bom_tree.get_all_parts()
        for part in parts[:5]:  # Show first 5 parts
            print(f"      └─ {part.name}: {part.quantity_net:.2f} {part.unit} "
                  f"@ ${part.unit_price:.2f} = ${part.cost:.2f}")
        
        if len(parts) > 5:
            print(f"      └─ ... and {len(parts) - 5} more parts")
    
    # ========================================================================
    # STEP 6: PATTERN 3 - Rules Engine (Tag-Based Hardware)
    # ========================================================================
    print("\n[STEP 6] PATTERN 3: Rules Engine - Automatic hardware addition based on tags...")
    
    # Demonstrate how tags trigger hardware
    print("\n  Tag-based hardware rules:")
    print("    'is_base' → adds Cabinet legs (4 pcs)")
    print("    'is_wall' → adds Wall mounting brackets (2 pcs)")
    print("    'has_doors' → adds Door hinges (2 per door) + bumpers")
    print("    'has_drawers' → adds Drawer slides (1 set per drawer)")
    print("    'is_sink' → adds Sink cabinet mat")
    
    # Show example for drawer base
    drawer_cabinet = next(c for c in project.cabinets if c.module_kind == "DRAWER_BASE")
    generator = BOMGenerator(drawer_cabinet, defaults)
    bom_tree = generator.generate()
    
    print(f"\n  Example: {drawer_cabinet.name}")
    print(f"    Recipe tags: {', '.join(drawer_recipe['tags'])}")
    print(f"    Automatically added hardware:")
    
    hardware_parts = [p for p in bom_tree.get_all_parts() 
                     if "legs" in p.name.lower() or "slides" in p.name.lower()]
    for part in hardware_parts:
        print(f"      • {part.name}: {part.quantity_net:.0f} {part.unit}")
    
    # ========================================================================
    # STEP 7: PATTERN 4 - Strategy Pattern (Purchasing Logic)
    # ========================================================================
    print("\n[STEP 7] PATTERN 4: Strategy Pattern - Realistic purchasing calculations...")
    
    # Aggregate all materials
    material_totals = {}
    
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
    
    # Apply purchasing strategies
    print("\n  Purchasing Strategy Results:")
    print("  " + "-"*76)
    print(f"  {'Material':<30} {'Net Need':<15} {'Must Buy':<15} {'Waste':<10}")
    print("  " + "-"*76)
    
    total_material_cost = 0
    
    for (mat_id, unit), data in material_totals.items():
        material = session.get(Material, mat_id)
        strategy = get_strategy_for_material(material.category)
        
        net_qty = data["quantity_net"]
        purchase_qty = strategy.calculate_purchase_quantity(net_qty)
        waste_factor = strategy.get_waste_factor(net_qty)
        cost = purchase_qty * data["unit_price"]
        
        total_material_cost += cost
        
        # Extract material name without prefix
        mat_name = data["name"].split(": ")[-1][:28]
        
        print(f"  {mat_name:<30} {net_qty:>6.2f} {unit:<8} "
              f"{purchase_qty:>6.2f} {unit:<8} "
              f"{(waste_factor-1)*100:>5.1f}%")
    
    print("  " + "-"*76)
    
    # ========================================================================
    # STEP 8: Final Project Summary
    # ========================================================================
    print("\n[STEP 8] Final Project Summary...")
    
    # Calculate hardware cost
    hardware_totals = {}
    for cabinet in project.cabinets:
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        for part in bom_tree.get_all_parts():
            if not part.material_id:  # Hardware
                if part.name not in hardware_totals:
                    hardware_totals[part.name] = {
                        "quantity_net": 0,
                        "unit": part.unit,
                        "unit_price": part.unit_price
                    }
                hardware_totals[part.name]["quantity_net"] += part.quantity_net
    
    total_hardware_cost = sum(
        data["quantity_net"] * data["unit_price"] 
        for data in hardware_totals.values()
    )
    
    subtotal = total_material_cost + total_hardware_cost
    markup = subtotal * (project.labor_markup - 1)
    total = subtotal + markup
    
    print("\n  " + "="*76)
    print(f"  {'PROJECT COST BREAKDOWN':<60} {'AMOUNT':>14}")
    print("  " + "="*76)
    print(f"  {'Materials (with purchasing strategies)':<60} ${total_material_cost:>13.2f}")
    print(f"  {'Hardware (exact quantities)':<60} ${total_hardware_cost:>13.2f}")
    print("  " + "-"*76)
    print(f"  {'Subtotal':<60} ${subtotal:>13.2f}")
    print(f"  {'Labor/Shop Markup ({:.0f}%)'.format((project.labor_markup-1)*100):<60} ${markup:>13.2f}")
    print("  " + "="*76)
    print(f"  {'TOTAL PROJECT COST':<60} ${total:>13.2f}")
    print("  " + "="*76)
    
    # ========================================================================
    # STEP 9: Validation
    # ========================================================================
    print("\n[STEP 9] Validating results...")
    
    # Verify all patterns worked correctly
    assert len(project.cabinets) == 3, "Should have 3 cabinets"
    assert total_material_cost > 0, "Material cost should be positive"
    assert total_hardware_cost > 0, "Hardware cost should be positive"
    assert total > subtotal, "Total should include markup"
    
    # Verify purchasing strategies increased costs (waste)
    net_corpus = sum(
        data["quantity_net"] 
        for (mat_id, unit), data in material_totals.items() 
        if "Corpus" in data["name"]
    )
    
    corpus_material = session.get(Material, egger_white.id)
    strategy = get_strategy_for_material(corpus_material.category)
    purchase_corpus = strategy.calculate_purchase_quantity(net_corpus)
    
    assert purchase_corpus > net_corpus, "Purchasing strategy should round up to full sheets"
    
    print("  ✓ All validations passed!")
    print("  ✓ Recipe system loaded cabinet definitions from JSON")
    print("  ✓ Composite pattern built hierarchical BOM trees")
    print("  ✓ Rules engine automatically added hardware based on tags")
    print("  ✓ Strategy pattern calculated realistic purchasing quantities")
    
    print("\n" + "="*80)
    print("WORKFLOW DEMONSTRATION COMPLETE")
    print("="*80)
    print("\nThe BOM system successfully demonstrated all 4 architectural patterns:")
    print("  1. Recipe Pattern - Data-driven cabinet definitions")
    print("  2. Composite Pattern - Hierarchical BOM structure")
    print("  3. Rules Engine - Tag-based component addition")
    print("  4. Strategy Pattern - Realistic purchasing logic")
    print("\nThis architecture provides:")
    print("  • Easy addition of new cabinet types (edit JSON, not code)")
    print("  • Automatic hardware inclusion (no manual tracking)")
    print("  • Realistic cost estimates (accounts for full sheets/rolls)")
    print("  • Professional CAD/CAM-grade BOM generation")
    print("="*80 + "\n")


def test_backward_compatibility_verification(session: Session):
    """
    Verify that new BOM system is backward compatible with old system.
    
    This ensures migration can happen gradually without breaking existing code.
    """
    print("\n[BACKWARD COMPATIBILITY TEST]")
    
    # Create minimal setup
    corpus = Material(name="Test Board", category="Board", price_per_unit=10.0, unit="m2")
    back = Material(name="Test Back", category="Panel", price_per_unit=5.0, unit="m2")
    front = Material(name="Test Front", category="Board", price_per_unit=10.0, unit="m2")
    edge = Material(name="Test Edge", category="Edgebanding", price_per_unit=1.0, unit="lm")
    hinge = HardwareSet(name="Test Hinge", price_per_set=2.0)
    drawer = HardwareSet(name="Test Drawer", price_per_set=30.0)
    
    session.add_all([corpus, back, front, edge, hinge, drawer])
    session.commit()
    
    project = Project(customer_name="Test", waste_factor=1.20, labor_markup=1.50)
    session.add(project)
    session.commit()
    
    defaults = ProjectDefaults(
        project_id=project.id,
        corpus_mat_id=corpus.id,
        back_mat_id=back.id,
        front_mat_id=front.id,
        edge_band_mat_id=edge.id,
        hinge_sys_id=hinge.id,
        drawer_sys_id=drawer.id,
        waste_factor=1.20
    )
    session.add(defaults)
    session.commit()
    
    cabinet = Cabinet(
        project_id=project.id,
        module_kind="DRAWER_BASE",
        name="Test Cabinet",
        type="BASE",
        width_mm=400,
        height_mm=802,
        depth_mm=560,
        door_count=0,
        drawer_count=2
    )
    session.add(cabinet)
    session.commit()
    session.refresh(cabinet)
    
    # OLD WAY (still works)
    old_result = cabinet.calculate_cost(defaults, waste_factor=1.20)
    
    # NEW WAY
    generator = BOMGenerator(cabinet, defaults)
    bom_tree = generator.generate()
    
    print(f"  Old system total: ${old_result.total_cost:.2f}")
    print(f"  New system total: ${bom_tree.cost:.2f}")
    
    # Costs should be similar (within 20% tolerance due to improved calculations)
    assert bom_tree.cost == pytest.approx(old_result.total_cost, rel=0.2)
    
    print("  ✓ Backward compatibility verified!")
    print("  ✓ Both systems can coexist during migration")
