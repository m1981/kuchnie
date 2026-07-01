# Cold Review — 2026-06-29

## Execution Flow Traces

### Flow 1: ConstructionMethod → catalog.py → decompose
**Status: BROKEN**

`catalog.py` still uses `cab.thickness_side_mm` (from `CabinetInstance`) instead of `ConstructionMethod`.

```python
# catalog.py line 66 (current — WRONG):
bottom_w = cab.width_mm - 2 * cab.thickness_side_mm

# Should be:
bottom_w = method.carcass_bottom_width(cab.width_mm)
```

**Impact:** ConstructionMethod exists but is unused. Changing a method won't cascade.

### Flow 2: CabinetInstance → decompose → DecompositionResult → BOM
**Status: WORKING but fragile**

```
CabinetInstance (YAML)
  → decompose(cab)           # catalog.py
    → DecompositionResult     # panels + accessories
      → calculate_bom(result) # bom.py
        → BOM                 # items + total_cost
```

No validation at entry. CabinetInstance accepts width_mm=0.

### Flow 3: DrawerSystemFactory → decompose_drawer_box → Panel[]
**Status: WORKING with gaps**

```
DrawerSystemFactory.get("tandembox_antaro")
  → TandemboxAntaro
    → decompose_drawer_box(kb=600, nl=500, height_code="N")
      → (Panel[], MachiningOp[])
```

**Issue:** No NL validation — accepts nl=999 without error.
**Issue:** `lw(0)` returns -25 (negative).

### Flow 4: HingeFactory → calculate_hinge_count → Accessory
**Status: WORKING**

```
HingeFactory.get("blum_cliptop_110")
  → BlumClipTop110
    → to_accessory(cab_id, door_id, quantity=2)
      → Accessory
```

Clean flow, no issues.

### Flow 5: RecipeSchema → evaluate_formula → PanelRecipe.compute_*
**Status: WORKING**

```
RecipeSchema.from_dict(json)
  → PanelRecipe[]
    → evaluate_formula("width - 2*thickness", ctx)
      → float
```

Safe evaluator (no eval()). Negative results allowed (design choice or issue?).

---

## Type Consistency Review

| Module | Input | Output | Consistent? |
|--------|-------|--------|-------------|
| ConstructionMethod.carcass_bottom_width | int | int | ✅ |
| DrawerSystem.lw | int | int | ✅ |
| DrawerSystem.base_panel_width | int | int | ✅ |
| evaluate_formula | str + dict | float | ✅ |
| HingeFactory.get | str | BlumHinge | ✅ |
| calculate_hinge_count | int | int | ✅ |

---

## Issues Found

### Issue 1: catalog.py doesn't use ConstructionMethod
**Severity:** HIGH
**Location:** `src/kuchnie_core/catalog.py`
**Problem:** All 3 decompose functions use `cab.thickness_side_mm` instead of `ConstructionMethod` methods.
**Fix:** Refactor to accept `ConstructionMethod` parameter.

### Issue 2: No negative dimension validation
**Severity:** MEDIUM
**Location:** `recipe.py`, `construction.py`, `blum_drawers.py`
**Problem:** `evaluate_formula` allows negative results. `lw(0)` returns -25.
**Fix:** Add optional validation in decompose functions.

### Issue 3: DrawerSystem.decompose_drawer_box() doesn't validate NL
**Severity:** MEDIUM
**Location:** `src/kuchnie_core/blum_drawers.py`
**Problem:** Accepts nl=999 without error. Should check `is_valid_combo(height_code, nl)`.
**Fix:** Add validation at entry.

### Issue 4: Recipe evaluator allows negative context values
**Severity:** LOW
**Location:** `src/kuchnie_core/recipe.py`
**Problem:** `evaluate_formula("x", {"x": -5})` returns -5. No check that context values are positive.
**Fix:** Add optional validation flag.

### Issue 5: CabinetInstance has no validation
**Severity:** LOW
**Location:** `src/kuchnie_core/model.py`
**Problem:** Can create `CabinetInstance(width_mm=0, height_mm=-100)`.
**Fix:** Add `__post_init__` validation.

### Issue 6: Edge band material string construction
**Severity:** LOW
**Location:** `src/kuchnie_core/catalog.py` lines 23-34
**Problem:** `_body_eb()` constructs material code as `f"{cab.edge_banding_type}_{cab.body_material}"`. If body_material already contains prefix (e.g. "swiss_krono.U119_VL"), result is "ABS_swiss_krono.U119_VL" — may not match catalog DB.
**Fix:** Document expected format or normalize.
