"""kitchen-erp: BOM · cost · purchasing · rules admin · ops UI.

Package layout (per ADR-011 Commit B.ii):

  kitchen_erp/
  ├── kitchen_erp.py  ← Reflex entry (rxconfig app_name = "kitchen_erp")
  ├── ui/             ← Reflex pages + state (was kitchen_app/)
  └── core/           ← business logic: models, BOM, purchasing, recipes
                       (was the inner kitchen_erp/ package)

Downstream consumer of ``kuchnie_core`` for domain computations.
Sales-tool role explicitly reassigned to ``krono-compositor-mvp``
per ADR-011.
"""
