# Kitchen Design & Manufacturing Software — A Practitioner's View

As someone who straddles both the workshop floor and the developer desk, here's my rundown of the key players in kitchen/cabinet CAD-CAM, with a focus on what actually matters in European production:

---

## 🏆 Tier 1 — Full Design-to-Production Suites

### **HOMAG iX / woodCAD|CAM**

- The gold standard for HOMAG machine owners
- Handles everything: design → cutlists → CNC programs → edgebanding → drilling
- Deep integration with **System32** (32mm hole rows, shelf drilling, hinge boring)
- Direct post-processor to HOMAG machines (saw, CNC, bore)
- _Worth it if you're on HOMAG equipment_

### **ima Kellner: TopSolid'Wood**

- Full parametric 3D CAD/CAM for woodworking
- True manufacturing intelligence — knows about grain, material thickness, tooling
- Generates G-code directly for CNC routers and point-to-point
- Steep learning curve, but incredibly powerful for custom work

### **Palette CAD (now CET by Configura)**

- Very popular in European kitchen studios and showrooms
- Great photorealistic rendering for client presentations
- Good catalog integration with manufacturers (Nobilia, Schüller, etc.)
- Weaker on the CAM/manufacturing side — often needs handoff

### **CARAT by Hettich**

- Strong System32 awareness (makes sense — Hettich is a fitting manufacturer)
- Good for planning with Hettich hardware
- Less common as a standalone solution

---

## 🥈 Tier 2 — Strong Mid-Market

### **KitchenDraw / Winner Flex / CARAT (by Cyncly — formerly Compusoft)**

- **KitchenDraw** — huge in France, Italy, Southern Europe
- **Winner Flex** — popular in Scandinavia, UK
- **CARAT** — German-speaking markets
- All now under **Cyncly** umbrella (merged Compusoft + 2020 + others)
- Good manufacturer catalogs (taps, appliances, worktops)
- Design → quotation → ordering pipeline
- _Manufacturing output varies — some connect to saws/CNC, some don't_

### **SBT / bSolid (by Biesse)**

- Direct machine integration for Biesse equipment
- Solid System32 support
- CAM post-processing for Biesse CNC routers and bore machines
- Similar philosophy to HOMAG iX but for Biesse users

### **IMOS (now part of Hettich Group)**

- Parametric furniture/kitchen design
- Strong database-driven approach
- System32 aware
- Good for medium-to-large manufacturers running batch production
- Generates machine code for various CNC brands

---

## 🥉 Tier 3 — Niche / Emerging

### **FreeCAD + CadQuery / BlenderCAD** (open source)

- For the maker/builder who wants full control
- No System32 intelligence out of the box
- Requires heavy scripting
- Good for custom one-off projects

### **Polyboard / OptiCut**

- **Polyboard** — affordable parametric cabinet design
- **OptiCut** — nesting and cut optimization
- Together they form a budget production pipeline
- Popular with small workshops in France and Eastern Europe

### **Fusion 360 (Autodesk)**

- General-purpose CAD/CAM
- Good for custom components and fixtures
- No kitchen-specific intelligence
- Strong CAM with generic CNC post-processors

### **Mozaik Software**

- Designed specifically for cabinet/kitchen manufacturing
- System32 aware
- Generates cutlists, CNC code, and reports
- Originally US-focused but gaining traction in Europe

---

## 🔧 What Matters for System32 Production

As a cabinet maker who's actually programmed System32 bore cycles:

| Feature                         | Why It Matters                                                      |
| ------------------------------- | ------------------------------------------------------------------- |
| **32mm row awareness**          | Shelf pin holes, hinge boring, drawer runners must land on the grid |
| **Post-processor for your CNC** | Drilling patterns must match your machine's boring block layout     |
| **Material/grain direction**    | Panel saw nesting and edgebanding orientation                       |
| **Edgebanding metadata**        | Which edges get tape — critical for cut-to-size services            |
| **Fitting libraries**           | Blum, Hettich, Hafele — drill patterns vary by fitting              |
| **Export: DXF / CSV / XML**     | Interoperability between design and shop floor                      |

---

## Honest Take

> For a **mid-size European kitchen manufacturer**, the pragmatic choice is usually one of:
>
> - **The software that came with your CNC machine** (HOMAG iX, bSolid, etc.)
> - **IMOS or Cyncly suite** if you're designing + manufacturing
> - **Polyboard + OptiCut** if you're small and budget-conscious
>
> The "sexy" design software (Winner, KitchenDraw) is great for **selling kitchens**, but the real test is whether it can **talk to your boring machine at 6 AM on a Monday**.
