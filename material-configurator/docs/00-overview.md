
# Technical Specification: Smart Material Configurator (Rule Engine)

## 1. Core Idea & Concept
The goal of this project is to build a **Smart Material Configurator** designed for furniture technologists and interior designers. 

Designing a custom kitchen requires balancing aesthetics (matching colors) with strict physical and technological constraints (moisture resistance, heat resistance, structural integrity). The core idea is to create a **Rule Engine** that acts as an intelligent assistant:
*   **Guides the user** through a logical flow (Fronts -> Carcass -> Worktop -> Splashback).
*   **Suggests matching materials** based on the manufacturer's matching matrix.
*   **Blocks technological errors** (e.g., preventing the use of standard melamine boards for worktops or forcing waterproof PUR glue for kitchen fronts).

## 2. Kronospan Catalog Structure
The system is based on the product taxonomy and matching matrices of major board manufacturers like Kronospan. The catalog is structured as follows:

*   **Base Decors:** The primary visual identifier (e.g., *K003 Gold Craft Oak*).
*   **Core Technologies:** A single decor can be manufactured on different core materials:
    *   **MFC (Melamine Faced Chipboard):** Standard 18mm board for carcasses and basic fronts.
    *   **MDF Acrylic / PET:** Premium high-gloss or deep-matt boards for fronts.
    *   **HPL (High Pressure Laminate):** Highly durable surface for worktops.
    *   **Compact Interior:** 100% waterproof, thin, solid core boards.
*   **Matching Accessories (The Matrix):** For every decor, the catalog defines exact or recommended matches for:
    *   **Edgebanding (ABS):** Plastic tape to seal cut edges.
    *   **HDF (High Density Fibreboard):** Thin 3mm boards for cabinet back panels.

## 3. Data Architecture (JSON Schema)
To ensure scalability and the Open/Closed Principle, the data is strictly separated into **Technological Rules** (physics/manufacturing constraints) and the **Catalog Matrix** (product availability).

```json
{
  "technologicalRules": {
    "materials": {
      "MFC": { "waterResistant": false, "allowedGlues": ["EVA", "PUR"] },
      "HPL": { "waterResistant": true, "allowedGlues": ["PUR"] },
      "COMPACT": { "waterResistant": true, "allowedGlues": [] },
      "ACRYLIC": { "waterResistant": false, "allowedGlues": ["PUR", "LASER"] }
    },
    "zones": {
      "FRONT": { "allowedMaterials": ["MFC", "ACRYLIC"], "forcedGlue": "PUR" },
      "KORPUS": { "allowedMaterials": ["MFC"], "defaultGlue": "EVA" },
      "WORKTOP": { "allowedMaterials": ["HPL", "COMPACT"] },
      "SPLASHBACK": { "allowedMaterials": ["HPL", "COMPACT"] }
    }
  },
  "catalogMatrix": {
    "K003": {
      "name": "Gold Craft Oak",
      "availableMaterials": ["MFC", "COMPACT"],
      "matches": {
        "edgeband": { "code": "K-0003/1-PW", "isDigitalPrint": false },
        "hdf": null,
        "worktopHPL": "K003 FP"
      }
    }
  }
}
```

## 4. Implementation Logic & User Flow
The UI and JavaScript logic follow a specific Use Case flow, utilizing the Rule Engine to filter options and generate a Bill of Materials (BOM).

### Step 1: FRONT (Customer's Choice)
*   **Action:** User selects the main decor for the kitchen fronts.
*   **Logic:** System filters `catalogMatrix` to show decors available in `MFC` or `ACRYLIC` (based on `zones.FRONT.allowedMaterials`).
*   **Assertion:** System automatically assigns `PUR` glue to the BOM, overriding standard glue options to ensure moisture resistance.

### Step 2: KORPUS (Cabinet Carcass)
*   **Action:** User selects the internal cabinet material.
*   **Smart Suggestion:** If the Front decor is available in `MFC`, the system prompts a 1-click button: *"Match Carcass to Front"*.
*   **Automation:** System automatically looks up `matches.hdf` to assign the correct 3mm back panel. If `null`, it defaults to standard white HDF.

### Step 3: WORKTOP (Working Surface)
*   **Action:** User selects the countertop.
*   **Strict Constraint:** The system completely blocks `MFC` from this dropdown. Only `HPL` or `COMPACT` are allowed.
*   **Smart Suggestion:** If the chosen Front decor has a dedicated worktop (`matches.worktopHPL !== null`), the system highlights this as the recommended choice.

### Step 4: SPLASHBACK (Wall Panel)
*   **Action:** User selects the wall finish.
*   **Smart Suggestion:** The system offers two primary 1-click suggestions:
    1.  Match the Worktop (using HPL).
    2.  Match the Front (ONLY IF the front decor is available as a waterproof `COMPACT` board).

## 5. Edge Cases Handled
*   **Digital Print Edgebands:** If `matches.edgeband.isDigitalPrint` is `true`, the UI triggers a warning alert advising the designer to check abrasion resistance, as digital prints behave differently than mass-dyed ABS plastics.
*   **Missing Exact Matches:** The system gracefully handles `null` values in the matching matrix (e.g., missing HDF) by providing safe industry defaults (e.g., White 0101 HDF).




*****

Here is the Markdown explanation detailing the matching rules, their importance in furniture design, and the transcribed matching table.

***

# Product Matching Rules in Furniture Design

## 1. What is the Matching Matrix?
In the furniture industry, a single visual decor (e.g., a specific shade of oak or a solid grey color) must be applied across entirely different physical materials to build a complete kitchen. 

The **Matching Matrix** is a manufacturer's specification that dictates exactly which accessory components (edgebands, back panels, laminates) are chemically, visually, and structurally designed to pair with a specific base board (MFC).

## 2. Why Matching Rules Matter

Ignoring the matching matrix leads to severe aesthetic and technological failures in a project:

### A. Edgebanding (ABS) Matching
*   **The Problem:** When a board is cut, the raw particleboard core is exposed. It must be sealed with an ABS plastic tape. If you use a generic "grey" tape on a specific "Anthracite" board, the color difference will be glaringly obvious under kitchen lighting. Furthermore, the texture (e.g., smooth vs. pearl) will clash.
*   **The Rule:** The matrix provides a specific code (e.g., `K-0164-PE`) from a certified supplier (like Schilsner). This guarantees a 1:1 match in both **color** and **surface structure** (e.g., PE = Pearl).

### B. HDF (Back Panel) Matching
*   **The Problem:** The back of a cabinet (the "plecy") is made of a thin 3mm HDF board. If you build a premium dark wood cabinet but use a standard white HDF back, the interior will look cheap and unfinished when the customer opens the door.
*   **The Rule:** The matrix indicates if a 1:1 matching HDF exists (e.g., `0101 1:1`). If it doesn't, the designer knows they must either accept a default color or use a thicker, matching MFC board for the back (which changes the cabinet's structural design).

### C. Cross-Technology Matching (Compact, Acrylic, HPL)
*   **The Problem:** A customer wants a seamless "monoblock" kitchen where the fronts, the worktop, and the wall splashback are the exact same color. However, you cannot use standard MFC for the worktop or the wet wall area.
*   **The Rule:** The "Matching of other products" column tells the technologist if that specific decor is manufactured in high-performance materials. For example, if a decor is available in `Compact Interior (BS)`, the designer knows they can safely use that exact color for the waterproof splashback behind the sink.

---

## 3. Matching Table (Excerpt from Kronospan Global Collection 2026)

Below is a transcribed excerpt of the matching matrix (from page 27 of the catalog), demonstrating how base decors map to their required accessories and alternative technologies.

| Lp. | Laminates (HPL)<br>0.8 x 3050 x 1320 mm | HDF Match<br>Decor | HDF Match<br>1:1 / Recommended | Matching of other products | ABS Edgeband<br>(Schilsner) | Notes (Recommended color matches)** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | express HPL warehouse | - | - | - | K-0110-SM | NCS S 0500-N, RAL 9016 |
| 2 | express HPL warehouse | **0101** | **1:1** | Compact Interior (BS), KA | K-0101-PE | NCS S 0502-G50Y, RAL 9010 |
| 3 | available in PU in BS | - | - | AG, AM, MG, CI (BS) | K-8685-SM/BS/PD | NCS S 0500-N, RAL 9016 |
| 4 | express HPL warehouse | **0112** | **1:1** | AG, AM, KA, CI (BS) | K-0112-PE | NCS S 2000-N, RAL 7047 |
| 5 | express HPL warehouse | - | - | KA, CI (BS) | K-0162-PE | NCS S 6500-N, RAL 7015 |
| 6 | express HPL warehouse | **0164** | **1:1** | AG, AM, KA, CI (BS) | K-0164-PE/PD | NCS S 7502-G, RAL 7043 |
| 7 | express HPL warehouse | - | - | Compact Interior (BS) | K-0166-BS | NCS S 7500-N, RAL 7022 |
| 9 | express HPL warehouse | **0190** | **1:1** | AG, AM, MG, KA, CI (BS) | K-0190-PE/PD | NCS S 8502-B, RAL 9004 |
| 18 | express HPL warehouse | **5981** | **1:1** | MG, KA, CI (BS) | K-5981-BS/PD | NCS S 2005-Y60R |
| 24 | express HPL warehouse | - | - | KA, Compact Interior (BS) | K-8681-SU/SM | NCS S 0505-R70B |

### Legend for "Matching of other products":
*   **AG:** Acrylic Gloss (Premium high-gloss MDF)
*   **AM:** Acrylic Matt (Premium anti-fingerprint MDF)
*   **MG:** Mirror Gloss
*   **CI:** Compact Interior (100% waterproof solid core board)
*   **KA:** Kronoart (Exterior/Architectural panels)
*   **(BS), (PE), (SM):** Surface texture codes (e.g., BS = Bureau Structure, PE = Pearl, SM = Smooth).