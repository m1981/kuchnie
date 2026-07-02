#!/usr/bin/env python3
"""
Demo script showing how to use the new BOM system.

This script demonstrates:
1. Creating a test project with materials and hardware
2. Adding cabinets using recipes
3. Generating BOM trees
4. Comparing old vs new system
5. Showing purchasing strategies in action

Run with: uv run python examples/demo_bom_system.py
"""

from sqlmodel import Session, create_engine, SQLModel, select
from kitchen_erp.models import Cabinet, Material, HardwareSet, ProjectDefaults, Project
from kitchen_erp.bom_generator import BOMGenerator
from kitchen_erp.purchasing import get_strategy_for_material
from kitchen_erp.recipe_loader import get_recipe


def create_demo_database():
    """Create in-memory database with demo data"""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create materials
        print("Creating materials database...")
        corpus = Material(
            name="Egger W1000 Premium White",
            brand="Egger",
            category="Board",
            price_per_unit=12.50,
            unit="m2"
        )
        back = Material(
            name="HDF White 3mm",
            brand="Generic",
            category="Panel",
            price_per_unit=4.50,
            unit="m2"
        )
        front = Material(
            name="Egger W1000 Premium White",
            brand="Egger",
            category="Board",
            price_per_unit=12.50,
            unit="m2"
        )
        edge = Material(
            name="ABS White 1mm",
            brand="Generic",
            category="Edgebanding",
            price_per_unit=0.80,
            unit="lm"
        )
        
        session.add_all([corpus, back, front, edge])
        session.commit()
        
        # Create hardware
        print("Creating hardware database...")
        hinges = HardwareSet(
            name="Blum Clip Top",
            brand="Blum",
            price_per_set=2.50
        )
        drawers = HardwareSet(
            name="Blum Legrabox",
            brand="Blum",
            price_per_set=35.00
        )
        
        session.add_all([hinges, drawers])
        session.commit()
        
        # Create project
        print("Creating demo project...")
        project = Project(
            customer_name="Demo Kitchen - Modern Style",
            waste_factor=1.20,
            labor_markup=1.50
        )
        session.add(project)
        session.commit()
        
        # Create defaults
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
        
        return engine, project.id


def demo_recipe_system():
    """Demonstrate recipe-driven cabinet creation"""
    print("\n" + "="*70)
    print("DEMO 1: Recipe System (Data-Driven Design)")
    print("="*70)
    
    # Show available recipes
    from kitchen_erp.recipe_loader import load_recipes
    recipes = load_recipes()
    
    print(f"\nAvailable cabinet types ({len(recipes)} recipes loaded):")
    for recipe_id, recipe in recipes.items():
        print(f"  • {recipe_id}: {recipe['name']}")
        print(f"    Type: {recipe['type']}, Tags: {', '.join(recipe['tags'])}")
    
    # Show detailed recipe
    print("\nDetailed recipe for DRAWER_BASE:")
    drawer_recipe = get_recipe("DRAWER_BASE")
    print(f"  Name: {drawer_recipe['name']}")
    print(f"  Type: {drawer_recipe['type']}")
    print(f"  Tags: {drawer_recipe['tags']}")
    print(f"  Default dimensions: {drawer_recipe['default_dimensions']}")
    print(f"  Formulas:")
    for formula_name, formula in drawer_recipe['formulas'].items():
        print(f"    {formula_name}: {formula}")


def demo_bom_generation(engine, project_id):
    """Demonstrate BOM generation for a single cabinet"""
    print("\n" + "="*70)
    print("DEMO 2: BOM Generation (Composite Pattern)")
    print("="*70)
    
    with Session(engine) as session:
        # Get project and defaults
        project = session.get(Project, project_id)
        defaults = session.exec(
            select(ProjectDefaults).where(ProjectDefaults.project_id == project_id)
        ).first()
        
        # Create a test cabinet
        print("\nCreating test cabinet: Drawer Base 800mm...")
        cabinet = Cabinet(
            project_id=project_id,
            module_kind="DRAWER_BASE",
            name="Drawer Base 800",
            type="BASE",
            width_mm=800,
            height_mm=802,
            depth_mm=560,
            door_count=0,
            drawer_count=4
        )
        session.add(cabinet)
        session.commit()
        session.refresh(cabinet)
        
        # Generate BOM using new system
        print("\nGenerating BOM tree...")
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        print(f"\nBOM Tree for: {bom_tree.name}")
        print(f"Total Cost: ${bom_tree.cost:.2f}")
        print("\nHierarchical breakdown:")
        
        parts = bom_tree.get_all_parts()
        for i, part in enumerate(parts, 1):
            print(f"  {i}. {part.name}")
            print(f"     Quantity: {part.quantity_net:.4f} {part.unit}")
            print(f"     Unit Price: ${part.unit_price:.2f}")
            print(f"     Cost: ${part.cost:.2f}")
        
        return cabinet.id


def demo_rules_engine(engine, cabinet_id):
    """Demonstrate tag-based hardware addition"""
    print("\n" + "="*70)
    print("DEMO 3: Rules Engine (Tag-Based Hardware)")
    print("="*70)
    
    with Session(engine) as session:
        cabinet = session.get(Cabinet, cabinet_id)
        defaults = session.exec(
            select(ProjectDefaults).where(
                ProjectDefaults.project_id == cabinet.project_id
            )
        ).first()
        
        # Show recipe tags
        recipe = get_recipe(cabinet.module_kind)
        print(f"\nCabinet: {cabinet.name}")
        print(f"Recipe tags: {recipe['tags']}")
        
        # Show what hardware gets added
        from kitchen_erp.rules_engine import RulesEngine
        engine_rules = RulesEngine()
        required_hardware = engine_rules.get_required_hardware_for_tags(recipe['tags'])
        
        print("\nAutomatically added hardware:")
        for hw in required_hardware:
            print(f"  • {hw['name']}: {hw['qty_per_unit']} {hw['unit']} @ ${hw['price']:.2f}")
        
        # Generate BOM to see actual quantities
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        print("\nActual hardware in BOM (with multipliers):")
        hardware_parts = [p for p in bom_tree.get_all_parts() if not p.material_id]
        for part in hardware_parts:
            print(f"  • {part.name}: {part.quantity_net:.0f} {part.unit} = ${part.cost:.2f}")


def demo_purchasing_strategies(engine, project_id):
    """Demonstrate realistic purchasing calculations"""
    print("\n" + "="*70)
    print("DEMO 4: Purchasing Strategies (Strategy Pattern)")
    print("="*70)
    
    with Session(engine) as session:
        project = session.get(Project, project_id)
        defaults = session.exec(
            select(ProjectDefaults).where(ProjectDefaults.project_id == project_id)
        ).first()
        
        # Add more cabinets to show aggregation
        print("\nAdding more cabinets to project...")
        cabinets = [
            Cabinet(
                project_id=project_id,
                module_kind="WALL_CABINET",
                name="Wall 800",
                type="WALL",
                width_mm=800,
                height_mm=720,
                depth_mm=320,
                door_count=2,
                drawer_count=0
            ),
            Cabinet(
                project_id=project_id,
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
        
        # Aggregate materials
        print(f"\nAggregating materials across {len(project.cabinets)} cabinets...")
        material_totals = {}
        
        for cabinet in project.cabinets:
            generator = BOMGenerator(cabinet, defaults)
            bom_tree = generator.generate()
            
            for part in bom_tree.get_all_parts():
                if part.material_id:
                    key = (part.material_id, part.unit)
                    if key not in material_totals:
                        material_totals[key] = {
                            "name": part.name.split(": ")[-1],
                            "quantity_net": 0,
                            "unit": part.unit,
                            "unit_price": part.unit_price,
                            "material_id": part.material_id
                        }
                    material_totals[key]["quantity_net"] += part.quantity_net
        
        # Apply purchasing strategies
        print("\nPurchasing Strategy Results:")
        print("-" * 70)
        print(f"{'Material':<30} {'Net Need':<15} {'Must Buy':<15} {'Waste':<10}")
        print("-" * 70)
        
        for (mat_id, unit), data in material_totals.items():
            material = session.get(Material, mat_id)
            strategy = get_strategy_for_material(material.category)
            
            net_qty = data["quantity_net"]
            purchase_qty = strategy.calculate_purchase_quantity(net_qty)
            waste_factor = strategy.get_waste_factor(net_qty)
            
            print(f"{data['name']:<30} {net_qty:>6.2f} {unit:<8} "
                  f"{purchase_qty:>6.2f} {unit:<8} "
                  f"{(waste_factor-1)*100:>5.1f}%")
        
        print("-" * 70)
        print("\nKey insight: You must buy full sheets/rolls, not fractional amounts!")
        print("This is why the new system gives more realistic costs.")


def demo_old_vs_new_comparison(engine, cabinet_id):
    """Compare old and new BOM systems"""
    print("\n" + "="*70)
    print("DEMO 5: Old vs New System Comparison")
    print("="*70)
    
    with Session(engine) as session:
        cabinet = session.get(Cabinet, cabinet_id)
        defaults = session.exec(
            select(ProjectDefaults).where(
                ProjectDefaults.project_id == cabinet.project_id
            )
        ).first()
        
        # OLD WAY
        print("\nOLD SYSTEM (Cabinet.calculate_cost):")
        old_result = cabinet.calculate_cost(defaults, waste_factor=1.20)
        print(f"  Total Cost: ${old_result.total_cost:.2f}")
        print(f"  Material Cost: ${old_result.material_cost:.2f}")
        print(f"  Hardware Cost: ${old_result.hardware_cost:.2f}")
        print(f"  Number of line items: {len(old_result.trace_lines)}")
        
        # NEW WAY
        print("\nNEW SYSTEM (BOMGenerator):")
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        print(f"  Total Cost: ${bom_tree.cost:.2f}")
        
        parts = bom_tree.get_all_parts()
        material_parts = [p for p in parts if p.material_id]
        hardware_parts = [p for p in parts if not p.material_id]
        
        material_cost = sum(p.cost for p in material_parts)
        hardware_cost = sum(p.cost for p in hardware_parts)
        
        print(f"  Material Cost: ${material_cost:.2f}")
        print(f"  Hardware Cost: ${hardware_cost:.2f}")
        print(f"  Number of parts: {len(parts)}")
        
        # Comparison
        print("\nCOMPARISON:")
        diff = bom_tree.cost - old_result.total_cost
        diff_pct = (diff / old_result.total_cost) * 100 if old_result.total_cost > 0 else 0
        
        print(f"  Difference: ${diff:.2f} ({diff_pct:+.1f}%)")
        print(f"  New system has {len(parts) - len(old_result.trace_lines)} more items")
        
        if diff > 0:
            print("\n  ✓ New system is more accurate (includes more components)")
        else:
            print("\n  ✓ Costs are similar (within expected range)")


def main():
    """Run all demos"""
    print("\n" + "="*70)
    print("KITCHEN APP BOM SYSTEM - INTERACTIVE DEMO")
    print("="*70)
    print("\nThis demo shows the new BOM architecture in action.")
    print("All 4 design patterns are demonstrated:")
    print("  1. Recipe Pattern - Data-driven cabinet definitions")
    print("  2. Composite Pattern - Hierarchical BOM trees")
    print("  3. Rules Engine - Tag-based hardware addition")
    print("  4. Strategy Pattern - Realistic purchasing logic")
    
    # Create demo database
    engine, project_id = create_demo_database()
    
    # Run demos
    demo_recipe_system()
    cabinet_id = demo_bom_generation(engine, project_id)
    demo_rules_engine(engine, cabinet_id)
    demo_purchasing_strategies(engine, project_id)
    demo_old_vs_new_comparison(engine, cabinet_id)
    
    print("\n" + "="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("  1. Run the integration tests: uv run pytest tests/test_integration_bom.py -v")
    print("  2. Review MIGRATION_GUIDE.md for UI integration steps")
    print("  3. Try adding your own cabinet types to recipes.json")
    print("  4. Experiment with custom hardware rules in rules_engine.py")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
