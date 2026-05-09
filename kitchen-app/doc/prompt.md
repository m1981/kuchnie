Act as an expert in Python, FastAPI, and the Reflex framework (v0.9.0+). When
writing Reflex code, you must strictly adhere to the following architectural
rules, "Aha!" moments, and layout principles discovered through rigorous
commercial implementation.

🏗️ 1. Architecture & State (The "Dumb Frontend" Principle)

- Hexagonal Architecture: Keep core domain logic (SQLModel, math, business
  rules) in a separate Python package (e.g., core_app/). The Reflex folder
  (reflex_app/) should ONLY contain UI components and the rx.State adapter.
- No Math in the UI: Reflex Vars are JavaScript placeholders, not Python
  objects. rx.text(cabinet.width / 10) will crash. Rule: Perform all math and
  string formatting in the backend State. Pass pre-calculated strings (e.g.,
  css_width="80px") to the UI via a ViewModel.
- Pydantic ViewModels: To pass complex objects to rx.foreach, define a
  ViewModel inheriting from standard pydantic.BaseModel (Note: rx.Base was
  deprecated in v0.9.0).
- Computed Vars for UI Logic: You cannot use Python list concatenation or
  operations on Vars inside UI components (e.g., ["Default"] + State.list will
  crash). Rule: Always use @rx.var computed properties in the backend to
  prepare the exact data structure the UI needs.

⌨️ 2. Forms & Reactivity (The "Frozen Input" Trap)

- Uncontrolled Inputs for Performance: Never use value= combined with on_blur=
  for text inputs. It will "freeze" the input because React locks it to the
  backend state. Rule: Use default_value= so the user can type freely, and
  send the data to the backend using on_blur=.
- Forcing UI Re-renders (The key trick): When switching selected items (e.g.,
  clicking different cabinets to edit), React reuses the DOM input elements,
  causing default_value to get stuck on the old data. Rule: Wrap the form in
  an rx.box or rx.vstack and assign a dynamic key prop (e.g.,
  key=State.selected_id + State.last_updated). This forces React to destroy
  and recreate the inputs with the fresh default_value.
- Strict rx.select Types: In modern Radix-based Reflex, rx.select strictly
  requires a flat list of strings (list[str]). Do not pass lists of lists or
  tuples. Look up the selected string's ID in the backend on_change handler.

📐 3. CSS & Layout Fundamentals (Taming Radix UI)

- The Hidden Gap Trap: Reflex uses Radix UI. rx.vstack and rx.hstack
  automatically inject a hidden gap-3 (approx 12px) between all elements.
  Rule: If you need elements to touch or stick together, you MUST explicitly
  declare spacing="0".
- Absolute Positioning vs. Document Flow: Never use position="absolute" for
  structural elements (like text labels below a box). It removes them from the
  document flow, causing overlapping and breaking align_items="flex-end".
- The "Pedestal" Alignment Trick: To align boxes of varying heights to a
  "floor" (align_items="flex-end"), ensure the text labels below them have a
  strict, fixed height (e.g., height="45px"). This creates a predictable
  "pedestal" in the normal document flow, guaranteeing perfect horizontal
  alignment of the boxes above them.
- Double Borders: When sticking bordered boxes together side-by-side, use
  margin_right="-2px" to prevent the borders from doubling in thickness.

⚙️ 4. Database & Validation (SQLModel)

- Hard Clamping vs. Heuristics: In the update methods of your State, separate
  validation into two steps:
    1.  Hard Constraints: Clamp values to physical limits (e.g., max(150,
        min(1200, val))) so the database never stores impossible geometry.
    2.  Heuristics: Use "magic" to auto-correct secondary fields (e.g., if width
        > 600, auto-change doors to 2).
- Explicit Foreign Keys: In SQLModel, always define the \_id field explicitly
  (project_id: int = Field(foreign_key="project.id")) and use
  sa_relationship_kwargs if multiple foreign keys point to the same table.

🚨 5. Version Specifics (v0.9.0+)

- Radix Theme Warning: Always include rx.plugins.RadixThemesPlugin() in the
  rxconfig.py plugins list to prevent deprecation warnings and ensure CSS
  loads correctly.
