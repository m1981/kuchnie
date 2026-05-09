# Migration Guide: Old BOM System → New BOM Architecture

## Overview

This guide explains how to migrate from the old `Cabinet.calculate_cost()` method to the new BOM generator architecture.

## Why Migrate?

The new system provides:

1. **Recipe-driven design** - Cabinet definitions in JSON, not Python code
2. **Hierarchical BOM** - Tree structure instead of flat list
3. **Tag-based rules** - Automatic hardware addition based on cabinet type
4. **Realistic purchasing** - Accounts for full sheets, rolls, standard lengths
5. **Better separation of concerns** - Clean architecture, easier to maintain

## Migration Steps

### Phase 1: Testing (Current State)

Both systems run side-by-side. You can test the new system without breaking existing functionality.

**Test the new system:**

```python
# In your UI or tests
from kitchen_erp.bom_generator import BOMGenerator

# Generate BOM for a cabinet
generator = BOMGenerator(cabinet, defaults)
bom_tree = generator.generate()

# Compare with old system
old_result = cabinet.calculate_cost(defaults, waste_factor=1.20)
print(f"Old total: ${old_result.total_cost:.2f}")
print(f"New total: ${bom_tree.cost:.2f}")
```

**Run integration tests:**

```bash
cd kitchen-app && uv run pytest tests/test_integration_bom.py -v
```

### Phase 2: UI Migration

Replace old methods with new ones in `state.py`:

**For single cabinet cost trace:**

```python
# OLD (current)
def open_selected_cabinet_cost_trace(self):
    # Uses cabinet.calculate_cost()
    
# NEW (use this)
def open_selected_cabinet_cost_trace_new(self):
    from kitchen_erp.bom_generator import BOMGenerator
    
    generator = BOMGenerator(cabinet, defaults)
    trace_lines = generator.generate_cost_trace_lines()
    # Convert to UI format...
```

**For project-level cost trace:**

```python
# OLD (current)
def open_project_cost_trace(self):
    # Loops through cabinets calling calculate_cost()
    
# NEW (use this)
def open_project_cost_trace_new(self):
    result = project.generate_project_bom()
    # Use result['aggregated_materials'] and result['aggregated_hardware']
```

**To switch over:**

1. Rename `open_selected_cabinet_cost_trace` → `open_selected_cabinet_cost_trace_old`
2. Rename `open_selected_cabinet_cost_trace_new` → `open_selected_cabinet_cost_trace`
3. Test thoroughly in UI
4. Repeat for project-level method

### Phase 3: Cleanup

Once the new system is proven stable:

1. **Delete old methods:**
   - Remove `Cabinet.calculate_cost()` from `models.py`
   - Remove `*_old()` methods from `state.py`

2. **Update documentation:**
   - Remove references to old system
   - Update examples to use new BOM generator

3. **Celebrate!** 🎉 You now have a professional CAD/CAM-grade BOM system

## Key Differences

### Old System

```python
# Hardcoded logic in Python
result = cabinet.calculate_cost(defaults, waste_factor=1.20)
# Returns flat list of CostTraceLine
```

### New System

```python
# Recipe-driven, tag-based
generator = BOMGenerator(cabinet, defaults)
bom_tree = generator.generate()
# Returns hierarchical BOMAssembly tree
```

## Adding New Cabinet Types

### Old Way (Don't do this anymore)

Edit Python code in multiple places:
- Add to `specs` dict in `state.py`
- Add to `limits` dict in `state.py`
- Add hardcoded logic in `calculate_cost()` in `models.py`

### New Way (Recommended)

Just edit `recipes.json`:

```json
{
  "MY_NEW_CABINET": {
    "name": "My New Cabinet Type",
    "type": "BASE",
    "tags": ["is_base", "has_doors"],
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
      "back_m2": "(height_mm * width_mm) / 1000000"
    }
  }
}
```

No Python code changes needed!

## Troubleshooting

### "Recipe not found" error

Make sure `recipes.json` exists in `kitchen_erp/` directory and contains the cabinet type you're trying to use.

### Costs don't match between old and new

This is expected! The new system is more accurate because:
- It uses purchasing strategies (full sheets, not fractional m²)
- It includes hardware based on tags (more complete BOM)
- It aggregates materials at project level (realistic waste calculation)

The new system should give **higher** costs that are closer to reality.

### Missing hardware in BOM

Check that the recipe has the correct tags. For example:
- `"is_base"` → adds cabinet legs
- `"has_doors"` → adds hinges and bumpers
- `"has_drawers"` → adds drawer slides

See `HARDWARE_RULES` in `kitchen_erp/rules_engine.py` for full list.

## Support

If you encounter issues during migration:

1. Check the integration tests: `uv run pytest tests/test_integration_bom.py -v`
2. Review the architecture docs: `kitchen-app/prompt2.md`
3. Compare old vs new output side-by-side

## Timeline

- **Week 1-2**: Test new system alongside old (Phase 1)
- **Week 3-4**: Migrate UI to use new methods (Phase 2)
- **Week 5**: Remove old code, celebrate (Phase 3)

Take your time! The systems can coexist safely during migration.
