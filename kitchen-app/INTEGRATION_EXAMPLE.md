# BOM System Integration Example

This document shows **exactly** how to integrate the new BOM system into your Kitchen App UI.

## Complete Working Example

Here's a real-world example showing how to use the new BOM generator in your Reflex UI:

### Step 1: Generate BOM for a Single Cabinet

```python
# In kitchen_app/state.py or wherever you handle cabinet cost display

from kitchen_erp.bom_generator import BOMGenerator
from kitchen_erp.models import Cabinet, ProjectDefaults
from kitchen_erp.database import get_session
from sqlmodel import select

def show_cabinet_bom(cabinet_id: int):
    """
    Generate and display BOM for a single cabinet.
    This is the NEW way - replaces the old calculate_cost() method.
    """
    with next(get_session()) as session:
        # Get the cabinet
        cabinet = session.get(Cabinet, cabinet_id)
        if not cabinet:
            return None
        
        # Get project defaults
        defaults = session.exec(
            select(ProjectDefaults).where(
                ProjectDefaults.project_id == cabinet.project_id
            )
        ).first()
        
        if not defaults:
            return None
        
        # Generate BOM tree using new system
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        # Option A: Get hierarchical tree (for advanced UI)
        print(f"Cabinet: {bom_tree.name}")
        print(f"Total Cost: ${bom_tree.cost:.2f}")
        
        for part in bom_tree.get_all_parts():
            print(f"  - {part.name}: {part.quantity_net} {part.unit} @ ${part.unit_price} = ${part.cost:.2f}")
        
        # Option B: Get flat BOM (backward compatible)
        flat_bom = generator.generate_flat_bom()
        
        # Option C: Get cost trace lines (for existing UI)
        trace_lines = generator.generate_cost_trace_lines()
        
        return {
            "tree": bom_tree,
            "flat": flat_bom,
            "trace_lines": trace_lines
        }
```

### Step 2: Generate BOM for Entire Project

```python
def show_project_bom(project_id: int):
    """
    Generate aggregated BOM for entire project.
    Shows realistic purchasing quantities (full sheets, rolls, etc.)
    """
    from kitchen_erp.purchasing import get_strategy_for_material
    
    with next(get_session()) as session:
        project = session.get(Project, project_id)
        if not project or not project.defaults:
            return None
        
        # Aggregate materials across all cabinets
        material_totals = {}
        hardware_totals = {}
        
        for cabinet in project.cabinets:
            generator = BOMGenerator(cabinet, project.defaults)
            bom_tree = generator.generate()
            
            for part in bom_tree.get_all_parts():
                if part.material_id:
                    # Material with database ID
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
                    # Hardware
                    if part.name not in hardware_totals:
                        hardware_totals[part.name] = {
                            "quantity_net": 0,
                            "unit": part.unit,
                            "unit_price": part.unit_price
                        }
                    hardware_totals[part.name]["quantity_net"] += part.quantity_net
        
        # Apply purchasing strategies
        purchase_list = []
        total_cost = 0
        
        for (mat_id, unit), data in material_totals.items():
            material = session.get(Material, mat_id)
            if not material:
                continue
            
            # Get appropriate purchasing strategy
            strategy = get_strategy_for_material(material.category)
            
            # Calculate what you actually need to buy
            net_qty = data["quantity_net"]
            purchase_qty = strategy.calculate_purchase_quantity(net_qty)
            waste_factor = strategy.get_waste_factor(net_qty)
            cost = purchase_qty * data["unit_price"]
            
            total_cost += cost
            
            purchase_list.append({
                "material": data["name"],
                "category": material.category,
                "net_required": f"{net_qty:.2f} {unit}",
                "must_purchase": f"{purchase_qty:.2f} {unit}",
                "waste": f"{(waste_factor - 1) * 100:.1f}%",
                "unit_price": f"${data['unit_price']:.2f}",
                "total_cost": f"${cost:.2f}"
            })
        
        # Add hardware
        for name, data in hardware_totals.items():
            cost = data["quantity_net"] * data["unit_price"]
            total_cost += cost
            
            purchase_list.append({
                "material": name,
                "category": "Hardware",
                "net_required": f"{data['quantity_net']:.0f} {data['unit']}",
                "must_purchase": f"{data['quantity_net']:.0f} {data['unit']}",
                "waste": "0%",
                "unit_price": f"${data['unit_price']:.2f}",
                "total_cost": f"${cost:.2f}"
            })
        
        return {
            "purchase_list": purchase_list,
            "total_cost": total_cost
        }
```

### Step 3: Display in Reflex UI

```python
# Example Reflex component for displaying BOM

import reflex as rx
from kitchen_app.state import KitchenState

def bom_display() -> rx.Component:
    """Display BOM with expandable tree structure"""
    return rx.vstack(
        rx.heading("Bill of Materials", size="lg"),
        
        # Total cost at top
        rx.hstack(
            rx.text("Total Cost:", weight="bold"),
            rx.text(
                KitchenState.bom_total_cost,
                color="green",
                size="xl",
                weight="bold"
            ),
            spacing="2"
        ),
        
        # Material breakdown
        rx.accordion.root(
            rx.accordion.item(
                header=rx.accordion.header("Materials"),
                content=rx.accordion.content(
                    rx.foreach(
                        KitchenState.bom_materials,
                        lambda item: rx.hstack(
                            rx.text(item.name),
                            rx.spacer(),
                            rx.text(f"{item.quantity} {item.unit}"),
                            rx.text(f"${item.cost:.2f}", color="green"),
                            width="100%"
                        )
                    )
                )
            ),
            
            rx.accordion.item(
                header=rx.accordion.header("Hardware"),
                content=rx.accordion.content(
                    rx.foreach(
                        KitchenState.bom_hardware,
                        lambda item: rx.hstack(
                            rx.text(item.name),
                            rx.spacer(),
                            rx.text(f"{item.quantity} {item.unit}"),
                            rx.text(f"${item.cost:.2f}", color="green"),
                            width="100%"
                        )
                    )
                )
            ),
            
            collapsible=True,
            width="100%"
        ),
        
        width="100%",
        spacing="4"
    )
```

## Comparison: Old vs New

### Old Way (Still Works)

```python
# OLD: Hardcoded in Cabinet.calculate_cost()
result = cabinet.calculate_cost(defaults, waste_factor=1.20)
print(f"Total: ${result.total_cost}")

# Problems:
# - Hardcoded logic in model
# - Flat list, no hierarchy
# - Waste factor applied per cabinet (unrealistic)
# - Can't add new cabinet types without code changes
```

### New Way (Recommended)

```python
# NEW: Recipe-driven, tag-based
generator = BOMGenerator(cabinet, defaults)
bom_tree = generator.generate()
print(f"Total: ${bom_tree.cost}")

# Benefits:
# - Logic in separate engine
# - Hierarchical tree structure
# - Realistic purchasing strategies
# - Add new cabinets by editing JSON
```

## Real-World Usage Patterns

### Pattern 1: Quick Cost Estimate

```python
# Just need total cost for a cabinet
generator = BOMGenerator(cabinet, defaults)
bom_tree = generator.generate()
total = bom_tree.cost
```

### Pattern 2: Detailed Breakdown

```python
# Need itemized list for customer quote
generator = BOMGenerator(cabinet, defaults)
trace_lines = generator.generate_cost_trace_lines()

for line in trace_lines:
    print(f"{line.label}: ${line.subtotal:.2f}")
```

### Pattern 3: Material Shopping List

```python
# Generate shopping list for entire project
from kitchen_erp.purchasing import get_strategy_for_material

# Aggregate all materials
all_materials = {}
for cabinet in project.cabinets:
    generator = BOMGenerator(cabinet, project.defaults)
    bom_tree = generator.generate()
    
    for part in bom_tree.get_all_parts():
        if part.material_id:
            # Add to shopping list...
            pass

# Apply purchasing strategies
for material_id, data in all_materials.items():
    material = session.get(Material, material_id)
    strategy = get_strategy_for_material(material.category)
    
    # This tells you how many full sheets/rolls to buy
    purchase_qty = strategy.calculate_purchase_quantity(data["net_qty"])
```

### Pattern 4: Cost Comparison

```python
# Compare different material options
cabinet = session.get(Cabinet, cabinet_id)

# Option 1: Default materials
gen1 = BOMGenerator(cabinet, defaults)
cost1 = gen1.generate().cost

# Option 2: Override with premium material
cabinet.override_front_mat_id = premium_material_id
gen2 = BOMGenerator(cabinet, defaults)
cost2 = gen2.generate().cost

print(f"Standard: ${cost1:.2f}")
print(f"Premium: ${cost2:.2f}")
print(f"Difference: ${cost2 - cost1:.2f}")
```

## Testing Your Integration

```python
# Test that new system works
def test_integration():
    with next(get_session()) as session:
        # Create test cabinet
        cabinet = Cabinet(
            project_id=1,
            module_kind="DRAWER_BASE",
            name="Test",
            width_mm=400,
            height_mm=802,
            depth_mm=560,
            door_count=0,
            drawer_count=4
        )
        session.add(cabinet)
        session.commit()
        
        # Get defaults
        defaults = session.exec(
            select(ProjectDefaults).where(ProjectDefaults.project_id == 1)
        ).first()
        
        # Generate BOM
        generator = BOMGenerator(cabinet, defaults)
        bom_tree = generator.generate()
        
        # Verify
        assert bom_tree.cost > 0
        assert len(bom_tree.get_all_parts()) > 0
        
        print("✅ Integration test passed!")
        print(f"   Total cost: ${bom_tree.cost:.2f}")
        print(f"   Parts count: {len(bom_tree.get_all_parts())}")
```

## Troubleshooting

### Issue: "Recipe not found"

**Solution:** Make sure `recipes.json` has an entry for the `module_kind`:

```json
{
  "DRAWER_BASE": {
    "name": "Drawer base",
    "type": "BASE",
    "tags": ["is_base", "has_drawers"],
    ...
  }
}
```

### Issue: Missing hardware in BOM

**Solution:** Check that recipe has correct tags:

```json
{
  "tags": ["is_base", "has_doors"]  // ← These trigger hardware addition
}
```

### Issue: Costs seem too high

**Expected!** New system is more accurate:
- Uses purchasing strategies (full sheets)
- Includes all hardware based on tags
- More realistic than old system

## Next Steps

1. **Test with real data** - Create a test project and compare old vs new costs
2. **Update one UI component** - Start with single cabinet BOM display
3. **Gradually migrate** - Keep old system running while testing new
4. **Remove old code** - Once confident, delete `Cabinet.calculate_cost()`

## Support

- See `MIGRATION_GUIDE.md` for step-by-step migration
- See `QUICK_REFERENCE.md` for API reference
- See `ARCHITECTURE_SUMMARY.md` for design decisions
- Run tests: `cd kitchen-app && uv run pytest tests/ -v`
