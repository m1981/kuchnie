# Domain Map — Subdomains & Bounded Contexts

## 1. Subdomain Classification

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          KUCHNIE SYSTEM                                 │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐     │
│  │   CORE DOMAIN    │  │   CORE DOMAIN    │  │   CORE DOMAIN     │     │
│  │                  │  │                  │  │                   │     │
│  │  Kitchen Layout  │  │ Cabinet Config   │  │  CAM Generation   │     │
│  │  (Rows & Grid)   │  │ & Costing        │  │  (Cut Lists &     │     │
│  │                  │  │                  │  │   Drilling)        │     │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘     │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐     │
│  │   SUPPORTING     │  │   SUPPORTING     │  │   SUPPORTING      │     │
│  │                  │  │                  │  │                   │     │
│  │  Material Catalog│  │  Rendering       │  │  Customer         │     │
│  │  (Decors, Rules, │  │  (Compositor +   │  │  Presentation     │     │
│  │   Matching)      │  │   Blender)       │  │  (Sales Tool)     │     │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘     │
│                                                                         │
│  ┌──────────────────┐                                                   │
│  │   GENERIC        │                                                   │
│  │                  │                                                   │
│  │  File I/O,       │                                                   │
│  │  Image Utils,    │                                                   │
│  │  HTTP Transport  │                                                   │
│  └──────────────────┘                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Subdomain Details

### 🟡 CORE: Kitchen Layout

**What it does:** Defines where cabinets sit in physical space. Rows, corners, L-shapes, U-shapes.

**Domain Expert says:** _"Mam ciąg przy ścianie, dwa rzędy w literę L, pierwszy rząd 240cm, drugi 180cm."_

**Key concepts:** Row, Layout, Wall Run, room dimensions, obstacle avoidance (pipes, windows, radiators).

**v1 constraint:** No islands, no slanted walls, no angled corners.

**This is where your money is.** Every error here cascades into wrong cut lists and wasted material.

---

### 🟡 CORE: Cabinet Configuration & Costing

**What it does:** Defines what's inside each cabinet — type, dimensions, internal shelves, drawer stacks, hardware. Calculates cost in real-time.

**Domain Expert says:** _"Ta szafka ma 600mm, trzy półki, prowadnice Blum Tandem, i front z Dębu Szlachetnego."_

**Key concepts:** Cabinet, Cabinet Type, dimensions (width/height/depth), overrides, shelf count, drawer stack, hinge type, runner type, handle type, material assignment per zone (front, carcass, countertop).

**Costing rules:** Material cost (per m², by price group) + accessory cost (hinges, runners, handles, edgebanding per meter) + labour estimate.

---

### 🟡 CORE: CAM Generation

**What it does:** Transforms the intermediate format into files a CNC company can execute.

**Domain Expert says:** _"Potrzebuję listę cięcia w CSV dla e-rozroju, i plik DXF z wierceniami."_

**Key concepts:** Cut List, Part, Panel, Edgebanding assignment (which edges get tape), grain direction, System32 drilling (shelf pins, hinge cups, dowels, rabbets), DXF export, CSV export.

**Critical rule:** The CNC company requires **you** to provide the material. Their pricing is labour-only. So cost estimation must be done **before** sending files.

---

### 🔵 SUPPORTING: Material Catalog & Matching

**What it does:** Stores the Kronospan/Egger product catalog — decors, material types, price groups, matching matrix (which edgebanding, HDF, HPL worktop matches each decor).

**Domain Expert says:** _"K003 Gold Craft Oak jest w grupie cenowej 1, obrzeże K-0003/1-PW, dostępny jako MFC i Compact Interior."_

**Key concepts:** Decor, Material Type (MFC/MDF Acrylic/HPL/Compact), Price Group, Edgebanding Code, HDF Match, Allowed Zone (front/carcass/worktop/splashback), Matching Matrix.

**Why Supporting, not Core:** This is data you type in once from a catalog PDF. The rules are important but stable — they change only when Kronospan publishes a new collection.

---

### 🔵 SUPPORTING: Rendering Pipeline

**What it does:** Takes a kitchen layout + material assignments → produces photorealistic 2.5D images using Blender render passes + OpenCV compositing.

**Key concepts:** Render Pass (base, UV, ID mask, reflection, handle), Compositor, Zone, Texture Tiling, Physical UV Scaling, Screen Blending, Alpha Compositing.

**Current state:** Working MVP in `krono-compositor-mvp/`. Reads `layout.json`, generates Blender scenes, composites with OpenCV.

**Why Supporting:** This sells the kitchen, but it doesn't build it. A bad render won't waste a single sheet of MFC.

---

### 🔵 SUPPORTING: Customer Presentation (Sales Tool)

**What it does:** The web app for the first visit — predefined layouts, decor picker, screenshot generation.

**Key concepts:** Predefined Layout Template, Decor Browser, 2.5D Preview, Screenshot Export.

**Why Supporting:** It accelerates the sales conversation. The output is a "yes, we like option B" — not engineering data.

---

### ⚪ GENERIC: File I/O, Image Utils, HTTP Transport

**What it does:** OpenCV image reading/writing, file format conversion, web server (FastAPI), CORS, error handling.

**Not domain-specific.** Replaceable libraries. Don't over-engineer.

---

## 3. Bounded Context Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ┌─────────────────────┐    intermediate     ┌──────────────────────┐     │
│   │  SALES CONTEXT      │    format (JSON)    │  DESIGN CONTEXT      │     │
│   │  kitchen-app        │ ──────────────────► │  kitchen-plugin      │     │
│   │                     │                     │                      │     │
│   │  • Predefined       │                     │  • Row editor        │     │
│   │    Layouts          │                     │  • Cabinet config    │     │
│   │  • Decor picker     │                     │  • Cost estimation   │     │
│   │  • 2.5D preview     │                     │  • Intermediate fmt  │     │
│   │                     │                     │                      │     │
│   └─────────────────────┘                     └──────────┬───────────┘     │
│                                                          │                  │
│                                                    intermediate             │
│                                                    format (JSON)           │
│                                                          │                  │
│           ┌──────────────────────────────────────────────┼──────────┐       │
│           │                                              ▼          │       │
│           │   ┌──────────────────────┐    ┌──────────────────────┐  │       │
│           │   │  RENDERING CONTEXT   │    │  CAM CONTEXT         │  │       │
│           │   │  blender-service     │    │  kitchen-cam (CLI)   │  │       │
│           │   │                      │    │                      │  │       │
│           │   │  • Blender scene gen │    │  • Cut list CSV      │  │       │
│           │   │  • Render passes     │    │  • System32 drilling │  │       │
│           │   │  • OpenCV composite  │    │  • DXF export        │  │       │
│           │   │  • Texture tiling    │    │  • Cost refinement   │  │       │
│           │   │                      │    │                      │  │       │
│           │   └──────────┬───────────┘    └──────────┬───────────┘  │       │
│           │              │                           │              │       │
│           └──────────────┼───────────────────────────┼──────────────┘       │
│                          │                           │                      │
│                          ▼                           ▼                      │
│              ┌──────────────────────┐    ┌──────────────────────┐           │
│              │  MATERIAL CATALOG    │    │  EXTERNAL SYSTEMS    │           │
│              │  (shared kernel)     │    │                      │           │
│              │                      │    │  • e-rozrys          │           │
│              │  • Decors            │    │  • e-rozkroj         │           │
│              │  • Price groups      │    │  • CNC shop (DXF)    │           │
│              │  • Matching matrix   │    │  • Kronospan catalog │           │
│              │  • Texture files     │    │  • Egger catalog     │           │
│              │                      │    │                      │           │
│              └──────────────────────┘    └──────────────────────┘           │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                     INTERMEDIATE FORMAT (hub)                       │   │
│   │                                                                     │   │
│   │   The single source of truth shared between Design, Rendering,      │   │
│   │   and CAM contexts. Defined once. Read by all.                      │   │
│   │                                                                     │   │
│   │   kitchen-plugin WRITES it → blender-service READS it              │   │
│   │   kitchen-plugin WRITES it → kitchen-cam READS it                  │   │
│   │   Manual tweaks in the file → kitchen-cam READS the tweaks         │   │
│   │                                                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Context Relationships

| From             | To                | Type                   | Description                                                                                      |
| ---------------- | ----------------- | ---------------------- | ------------------------------------------------------------------------------------------------ |
| Sales Context    | Design Context    | **Customer-Supplier**  | Sales provides the initial layout concept. Design refines it.                                    |
| Design Context   | Rendering Context | **Customer-Supplier**  | Design provides the intermediate format. Rendering produces images from it.                      |
| Design Context   | CAM Context       | **Customer-Supplier**  | Design provides the intermediate format. CAM produces production files from it.                  |
| Material Catalog | All Contexts      | **Shared Kernel**      | Every context needs decors and material info. Shared read-only data.                             |
| CAM Context      | External Systems  | **Conformist**         | You adapt to e-rozrys CSV format and CNC company DXF requirements. You don't control their APIs. |
| Sales Context    | Rendering Context | **Published Language** | Sales sends scene_id + zone assignments. Rendering returns JPEG.                                 |

---

## 5. Recommended Project Structure

```
kuchnie/
│
├── docs/
│   ├── 00-brief.md
│   ├── 00-brief-understanding.md
│   ├── glossary.md               ← Ubiquitous Language (this file)
│   ├── domain-map.md             ← Subdomains & Contexts (this file)
│   └── kitchen-design-software-overview.md
│
├── shared/                       ← Shared Kernel: Material Catalog + Intermediate Format
│   ├── catalog/                  ← Decor database, price groups, matching matrix
│   │   ├── kronospan.json
│   │   ├── egger.json
│   │   └── catalog_service.py
│   ├── intermediate/             ← Schema & validators for the intermediate format
│   │   ├── schema.json
│   │   ├── models.py
│   │   └── example.json
│   └── textures/                 ← Texture image files (referenced by decor ID)
│
├── kitchen-app/                  ← Sales Context (web app)
│   ├── layouts/                  ← Predefined 2.5D layout templates
│   ├── app.py                    ← FastAPI or lightweight server
│   └── static/
│
├── kitchen-plugin/               ← Design Context (web app)
│   ├── editor/                   ← 2D row editor
│   ├── cabinet-library/          ← Standard cabinet types
│   ├── cost-calculator/          ← Live pricing engine
│   └── app.py
│
├── blender-service/              ← Rendering Context
│   ├── scene-generator/          ← JSON → Blender scene (gen_kitchen.py evolved)
│   ├── compositor/               ← OpenCV compositing pipeline
│   └── api.py                    ← FastAPI endpoint
│
├── kitchen-cam/                  ← CAM Context (CLI tools)
│   ├── cutlist.py                → CSV for e-rozrys / e-rozkroj
│   ├── drilling.py               → System32 boring data → DXF
│   ├── dxf_export.py             → DXF file generation
│   └── cost_report.py            → Final cost with nesting
│
└── krono-compositor-mvp/         ← Existing MVP (to be refactored into above structure)
```

---

## 6. Where to Spend Your Effort

| Priority | Context                   | Effort % | Why                                                                                            |
| -------- | ------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| 🥇       | **CAM Generation**        | 35%      | Wrong cut lists = wasted material = lost money. This is where precision matters most.          |
| 🥈       | **Cabinet Configuration** | 30%      | The intermediate format is the backbone. Get this right and everything flows.                  |
| 🥉       | **Kitchen Layout**        | 15%      | Important but v1 is simple (rectangular rows, no islands). Build it clean but don't overdo it. |
| 4        | **Rendering**             | 10%      | You already have a working MVP. Polish it, don't rebuild it.                                   |
| 5        | **Material Catalog**      | 5%       | Data entry from catalog PDF. Tedious but not architecturally complex.                          |
| 6        | **Sales Tool**            | 5%       | A simple web page with predefined layouts. Minimal logic.                                      |

---

## 7. What NOT to Build

| Thing               | Why                    | Buy/Use Instead                                   |
| ------------------- | ---------------------- | ------------------------------------------------- |
| Authentication      | You're the only user   | None needed                                       |
| Invoicing           | Out of scope           | Use a Polish accounting app (Fakturownia, inFakt) |
| Customer CRM        | Not your core domain   | Spreadsheet or Firma.pl                           |
| 3D modeling GUI     | Too expensive to build | Blender handles this                              |
| Nesting optimizer   | Solved problem         | e-rozrys / e-rozkroj                              |
| General-purpose CAD | Way out of scope       | Your intermediate format is enough                |
