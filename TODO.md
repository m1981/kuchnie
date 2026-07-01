# TODO — Contract Testing Implementation

## Phase 1: Schema Definition
- [x] 1.1 Create Pydantic models for kitchen YAML schema
- [x] 1.2 Write tests for schema validation (valid/invalid inputs)
- [x] 1.3 Verify schema tests pass (31 tests)

## Phase 2: Test Fixtures
- [x] 2.1 Create Blender export fixture (simulated YAML)
- [x] 2.2 Create minimal single-cabinet fixture
- [x] 2.3 Create full kitchen fixture (multiple cabinets)
- [x] 2.4 Verify fixtures load in kuchnie_core

## Phase 3: Contract Tests (Schema → kuchnie_core)
- [x] 3.1 Write test: load_kitchen() succeeds with fixture
- [x] 3.2 Write test: decompose_kitchen() produces panels
- [x] 3.3 Write test: all panels have positive dimensions
- [x] 3.4 Write test: drawer cabinets have runners
- [x] 3.5 Write test: door cabinets have hinges
- [x] 3.6 Verify contract tests pass (20 tests)

## Phase 4: Integration Tests (Full Pipeline)
- [x] 4.1 Write test: BOM has all categories (panel, edge, accessory)
- [x] 4.2 Write test: cut list CSV is valid
- [x] 4.3 Write test: BOM total cost is positive
- [x] 4.4 Verify integration tests pass

## Phase 5: Blender Export Operator (Skeleton)
- [ ] 5.1 Create operator file structure
- [ ] 5.2 Implement _extract_kitchen() skeleton
- [ ] 5.3 Implement _extract_cabinet() skeleton
- [ ] 5.4 Implement _extract_drawers() skeleton
- [ ] 5.5 Write test: operator produces valid YAML

## Phase 6: Documentation
- [x] 6.1 Document schema format (src/kuchnie_core/schema.py)
- [x] 6.2 Document test strategy (this TODO)
- [x] 6.3 Update architecture doc (docs/ARCHITECTURE-kuchnie-core.md)
