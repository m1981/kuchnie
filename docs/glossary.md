# Ubiquitous Language — Kuchnie Project

> Every term below is used consistently across code, docs, and conversation.
> If a term isn't here, add it. If code uses a different word than the business — fix the code.

---

## Kitchen Layout

| Term         | Definition                                                                                                 | Polish Equivalent  |
| ------------ | ---------------------------------------------------------------------------------------------------------- | ------------------ |
| **Kitchen**  | A complete project for a single customer — the top-level container                                         | Kuchnia            |
| **Row**      | A linear sequence of cabinets sharing a wall. An L-shaped kitchen has 2 rows, a galley kitchen has 2 rows. | Ciąg szafek / Rząd |
| **Layout**   | The full arrangement of rows within a room. Defines geometry, not materials.                               | Układ              |
| **Wall Run** | Synonym for Row in v1 (no islands, no slants)                                                              | Ciąg przyścienny   |

## Cabinets

| Term               | Definition                                                                            | Polish Equivalent       |
| ------------------ | ------------------------------------------------------------------------------------- | ----------------------- |
| **Cabinet**        | A single unit within a row — has a type, width, height, depth, and optional overrides | Szafka                  |
| **Cabinet Type**   | The predefined category of a cabinet (see list below)                                 | Typ szafki              |
| **Base Cabinet**   | Lower kitchen unit, typically 820mm high, sits on plinth                              | Szafka dolna            |
| **Wall Cabinet**   | Upper unit mounted on wall, typically 720mm high                                      | Szafka górna / wisząca  |
| **Tall Cabinet**   | Floor-to-ceiling unit (2000mm+), for oven housing, larder, fridge                     | Szafka wysoka           |
| **Corner Cabinet** | Unit designed for L-junction in a row (L-shape or diagonal front)                     | Szafka narożna          |
| **Oven Housing**   | Tall cabinet specifically sized for built-in oven + microwave                         | Słupek piekarnikowy     |
| **Carcass**        | The structural box of the cabinet (sides, top, bottom, back). Made from MFC.          | Korpus                  |
| **Front**          | The visible door/drawer face of the cabinet. Material defines the look.               | Front / Drzwi           |
| **Plinth**         | The recessed kick board at the bottom of base cabinets (typically 100mm)              | Cokół                   |
| **Counter Top**    | The work surface sitting on base cabinets                                             | Blat roboczy            |
| **Splashback**     | Wall panel behind the counter top, protecting the wall from moisture                  | Panel ścienny / Obudowa |

## Dimensions & System32

| Term               | Definition                                                                                                           | Polish Equivalent    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- | -------------------- |
| **System32**       | European 32mm boring grid standard. All holes land on multiples of 32mm from reference edges.                        | System 32            |
| **Boring Pattern** | The specific arrangement of holes drilled into a panel (shelf pins, hinge cups, dowel holes)                         | Rozwiercanie         |
| **Shelf Pin Hole** | 5mm hole on the System32 grid for adjustable shelf supports                                                          | Otwór na kołek półki |
| **Hinge Boring**   | 35mm cup hole for European concealed hinges (Blum, Hettich)                                                          | Otwór zawiasowy      |
| **Dowel Hole**     | 8mm or 5mm hole for Confirmat or wooden dowel joinery                                                                | Otwór na kołek       |
| **Panel Rabbet**   | Groove cut into the back edge of side panels to receive the 3mm HDF back panel                                       | Wpuszczenie na plecy |
| **Reference Edge** | The edge from which System32 measurements are calculated (typically bottom for base cabinets, top for wall cabinets) | Krawędź odniesienia  |
| **Plinth Height**  | The height of the recessed kick space, typically 100mm                                                               | Wysokość cokołu      |

## Materials & Decors

| Term                 | Definition                                                                                                                  | Polish Equivalent          |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Decor**            | The visual identity of a board — the name/pattern (e.g., "Dąb Szlachetny"). One decor can exist on multiple material types. | Dekor                      |
| **MFC**              | Melamine Faced Chipboard — the standard board for carcasses and basic fronts. 18mm typical.                                 | Płyta laminowana           |
| **MDF Acrylic**      | Premium board with acrylic surface — high-gloss or deep-matt finish for fronts                                              | MDF Akryl                  |
| **HPL**              | High Pressure Laminate — durable surface for worktops and splashbacks                                                       | HPL / Laminat              |
| **Compact Interior** | 100% waterproof solid-core board for splashbacks and wet areas                                                              | Compact / Płyta kompaktowa |
| **HDF**              | High Density Fibreboard — thin 3mm board for cabinet back panels                                                            | HDF / Plecy                |
| **Edgebanding**      | ABS plastic tape applied to exposed cut edges of panels                                                                     | Okleina / Obrzeże ABS      |
| **Price Group**      | Manufacturer's pricing tier — determines material cost. Group 1 = standard, Group 2 = premium.                              | Grupa cenowa               |
| **Kronospan**        | Polish-Austrian board manufacturer — primary material supplier                                                              | Kronospan                  |
| **Egger**            | Austrian board manufacturer — secondary material supplier                                                                   | Egger                      |

## Manufacturing & CAM

| Term                     | Definition                                                                                                   | Polish Equivalent    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ | -------------------- |
| **Cut List**             | The complete list of rectangular panel parts with dimensions, material, edgebanding, and grain direction     | Lista cięcia         |
| **Part**                 | A single rectangular panel to be cut from a board sheet (has width, height, thickness, material, edge sides) | Element / Formatka   |
| **Nesting**              | The process of arranging parts on board sheets to minimize waste                                             | Rozkrój / Nesting    |
| **CNC Company**          | The external workshop that cuts and drills your panels using CNC machines                                    | Firma CNC            |
| **Intermediate Format**  | The JSON/YAML file that is the single source of truth — describes the full kitchen from layout to parts      | Format pośredni      |
| **e-rozrys / e-rozkroj** | Polish online nesting and cut list optimization services                                                     | e-rozrys / e-rozkroj |
| **DXF**                  | Drawing Exchange Format — 2D file format sent to CNC company for cutting and drilling                        | DXF                  |
| **MPR**                  | Machine-specific program file format used by some CNC manufacturers (e.g., HOMAG)                            | MPR                  |

## Rendering & Presentation

| Term            | Definition                                                                                          | Polish Equivalent    |
| --------------- | --------------------------------------------------------------------------------------------------- | -------------------- |
| **Render Pass** | A single layer of the compositing pipeline (base, UV, ID mask, reflection, handle)                  | Warstwa renderowania |
| **2.5D Render** | A high-quality image that looks like a 3D kitchen but is composed from 2D image layers              | Render 2.5D          |
| **Compositor**  | The system that combines render passes with real textures into a final photorealistic image         | Kompozytor           |
| **UV Map**      | An EXR render pass that encodes 3D surface coordinates as pixel colors — used for texture warping   | Mapa UV              |
| **ID Mask**     | A render pass where each cabinet zone is a unique solid color — used to isolate areas for texturing | Maska ID             |
| **Zone**        | A configurable area in the scene that can be assigned a different decor/texture                     | Strefa               |

## Use Case Stages

| Term                  | Definition                                                                             | Polish Equivalent       |
| --------------------- | -------------------------------------------------------------------------------------- | ----------------------- |
| **First Visit**       | Stage 1: Visit customer's flat, measure, show predefined layouts with different decors | Pierwsza wizyta         |
| **Design Session**    | Stage 2: Configure exact cabinet layout, dimensions, and materials in the design tool  | Projektowanie           |
| **CAM Preparation**   | Stage 3: Generate cut lists, drilling data, and DXF files for the CNC company          | Przygotowanie produkcji |
| **Customer Approval** | The moment the customer accepts the design and authorizes production                   | Akceptacja klienta      |
