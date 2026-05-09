# Kitchen App BOM System - Quick Reference

## 🚀 Quick Start

### Generate BOM for a Cabinet

```python
from kitchen_erp.bom_generator import BOMGenerator

# Get cabinet and defaults from database
generator = BOMGenerator(cabinet, project_defaults)

# Option 1: Get hierarchical tree
bom_tree = generator.generate()
print(f"Total: ${bom_tree.cost:.2f}")

# Option 2: Get flat list (backward compatible)
flat_bom = generator.generate_flat_bom()

# Option 3: Get cost trace lines for UI
trace_lines = generator.generate_cost_trace_lines()
```

### Add a New Cabinet Type

Edit `kitchen_erp/recipes.json`:

```json
{
  "YOUR_CABINET_ID": {
    "name": "Display Name",
    "type": "BASE",  // or "WALL", "PANEL"
    "tags": ["is_base", "has_doors"],  // See tags below
    "default_dimensions": {
      "width_mm": 600,
      "height_mm": 802,
      "depth_mm": 560
    },
    "limits": {
      "width_min": 400,
      "width_max": 1200
    },
    "formulas": {
      "corpus_m2": "((2 * height_mm * depth_mm) + (2 * width_mm * depth_mm)) / 1000000",
      "back_m2": "(height_mm * width_mm) / 1000000",
      "front_m2": "(height_mm * width_mm) / 1000000"
    }
  }
}
```

## 📋 Available Tags

Tags automatically add hardware components:

| Tag | Adds | Quantity |
|-----|------|----------|
| `is_base` | Cabinet legs | 4 pcs |
| `is_wall` | Wall mounting brackets | 2 pcs |
| `has_doors` | Door hinges + bumpers | 2 per door |
| `has_drawers` | Drawer slides | 1 set per drawer |
| `is_pullout` | Pull-out mechanism | 1 set |
| `is_sink` | Sink cabinet mat | 1 pc |
| `is_appliance` | Ventilation grille | 1 pc |
| `no_back_panel` | (Special: sets back_m2 to 0) | - |

## 🔧 Formula Variables

Available in `formulas` section:

- `width_mm` - Cabinet width in millimeters
- `height_mm` - Cabinet height in millimeters
- `depth_mm` - Cabinet depth in millimeters

**Example formulas:**

```json
{
  "corpus_m2": "((2 * height_mm * depth_mm) + (2 * width_mm * depth_mm) + (width_mm * height_mm)) / 1000000",
  "back_m2": "(height_mm * width_mm) / 1000000",
  "front_m2": "(height_mm * width_mm) / 1000000",
  "perimeter_m": "(2 * (width_mm + height_mm)) / 1000"
}
```

## 🛒 Purchasing Strategies

Apply realistic purchasing logic:

```python
from kitchen_erp.purchasing import get_strategy_for_material

# Get strategy for material category
strategy = get_strategy_for_material("Board")  # or "Edgebanding", "Countertop", "Hardware"

# Calculate purchase quantity
net_qty = 7.2  # m²
purchase_qty = strategy.calculate_purchase_quantity(net_qty)  # 11.592 m² (2 full sheets)
waste_factor = strategy.get_waste_factor(net_qty)  # 1.61 (61% waste)
```

**Available strategies:**

| Material Category | Strategy | Behavior |
|------------------|----------|----------|
| `Board`, `Panel` | Sheet | Rounds to full sheets (5.796 m²) |
| `Edgebanding` | Linear | Rounds to full rolls (50m) + 10% waste |
| `Countertop` | Countertop | Rounds to standard lengths (4100mm) |
| `Hardware`, `Equipment` | Exact | Exact quantity + 5% buffer |

## 🧪 Testing

```bash
# Run all tests
cd kitchen-app && uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_bom_generator.py -v

# Run with coverage
uv run pytest tests/ --cov=kitchen_erp --cov-report=html
```

## 🔄 Migration Checklist

### Phase 1: Testing
- [ ] Run `uv run pytest tests/test_integration_bom.py -v`
- [ ] Compare old vs new costs for sample projects
- [ ] Verify all cabinet types have recipes

### Phase 2: UI Update
- [ ] Update `open_selected_cabinet_cost_trace()` to use `BOMGenerator`
- [ ] Update `open_project_cost_trace()` to use `Project.generate_project_bom()`
- [ ] Test in UI

### Phase 3: Cleanup
- [ ] Remove `Cabinet.calculate_cost()` method
- [ ] Remove old cost calculation code
- [ ] Update documentation

## 🐛 Troubleshooting

### "Recipe not found" error
**Solution:** Add the cabinet type to `kitchen_erp/recipes.json`

### Costs don't match old system
**Expected!** New system is more accurate:
- Uses purchasing strategies (full sheets)
- Includes tag-based hardware
- Aggregates at project level

### Missing hardware in BOM
**Solution:** Check recipe tags. Add appropriate tags like `has_doors`, `has_drawers`, etc.

### Formula evaluation error
**Solution:** Check formula syntax. Only use `width_mm`, `height_mm`, `depth_mm` variables.

## 📚 Key Files

| File | Purpose |
|------|---------|
| `kitchen_erp/recipes.json` | Cabinet definitions |
| `kitchen_erp/bom_generator.py` | Main BOM generator |
| `kitchen_erp/rules_engine.py` | Tag-based hardware rules |
| `kitchen_erp/purchasing.py` | Purchasing strategies |
| `kitchen_erp/recipe_loader.py` | Recipe loading utilities |
| `MIGRATION_GUIDE.md` | Detailed migration instructions |
| `ARCHITECTURE_SUMMARY.md` | Complete implementation summary |

## 💡 Pro Tips

1. **Always test recipes** - Add a test in `tests/test_bom_generator.py` for new cabinet types
2. **Use tags liberally** - They make hardware addition automatic
3. **Check purchasing strategies** - They significantly affect final costs
4. **Keep formulas simple** - Complex calculations should be in Python, not JSON
5. **Document custom rules** - If you add to `HARDWARE_RULES`, document them

## 🎯 Common Patterns

### Custom Hardware for Specific Cabinet
```python
# In rules_engine.py, add to HARDWARE_RULES:
"is_corner_cabinet": [
    {"name": "Corner carousel", "qty_per_unit": 1, "unit": "sets", "price": 85.00}
]
```

### Cabinet Without Back Panel
```json
{
  "formulas": {
    "back_m2": "0"  // No back panel
  }
}
```

### Variable Hardware Based on Size
Use multipliers in BOM generator:
```python
multipliers = {
    "has_doors": cabinet.door_count,
    "has_drawers": cabinet.drawer_count
}
```

## 📞 Need Help?

1. Check `MIGRATION_GUIDE.md` for detailed instructions
2. Review test files for usage examples
3. Read docstrings in `bom_generator.py`
4. Check `ARCHITECTURE_SUMMARY.md` for design decisions
