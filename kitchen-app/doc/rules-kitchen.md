# 🪚 Cabinet Technology & Manufacturing Constraints

**Version:** 1.0
**Context:** European System 32 Cabinetry (Egger, Blum, Hettich standards)
**Purpose:** To instruct LLMs and developers on the physical, material, and hardware realities of cabinet making. Software must act as an expert system that prevents physically impossible or structurally unsound designs.

## 🧠 Core Philosophy: The Carpenter's Mindset

When writing validation logic, generating UI, or calculating costs, you must respect the laws of physics. A cabinet is not just a 3D bounding box; it is a physical object subject to gravity, leverage, and material limitations.

- **Do not silently auto-correct user input** without providing UI feedback.
- **Differentiate between "Hard Clamps"** (physically impossible to manufacture) and **"Soft Warnings"** (physically possible, but structurally risky or impractical).

---

## 🪵 1. Material & Physics Constraints

### 1.1 The "Jumbo Board" Limit (Max Height)

- **Constraint:** Standard European melamine/MDF boards (e.g., Egger, Kronospan) are manufactured at **2800mm x 2070mm**.
- **Reality:** After trimming rough factory edges, the absolute maximum continuous grain height is **~2750mm**.
- **Rule:** If a cabinet height exceeds `2700mm`, issue a **Soft Warning**: _"Exceeds standard 2800mm board size. Requires Jumbo boards; grain matching may be difficult."_

### 1.2 The "Shelf Sag" Limit (Max Width)

- **Constraint:** Standard cabinet carcases use 18mm or 19mm board.
- **Reality:** An unsupported horizontal shelf wider than 900mm will sag (deflect) under the weight of standard kitchen items (plates, cans).
- **Rule:** If a cabinet width exceeds `900mm` and has no vertical partitions/drawers, issue a **Soft Warning**: _"Shelves > 900mm may sag under heavy load. Consider 25mm shelves or a center partition."_

---

## ⚙️ 2. Hardware & Kinematic Constraints

### 2.1 The "Hinge Leverage" Rule (Side-Hinged Doors)

- **Constraint:** A door acts as a lever. The wider the door, the more rotational force it applies to the hinges and the MDF carcase.
- **Reality:** Side-hinged doors wider than 600mm will eventually rip the hinge plates out of the cabinet wall.
- **Rule:** For `BASE` and `TALL` cabinets, if `width > 600mm` and `doors == 1`, apply a **Hard Clamp** to force `doors = 2`. Issue a warning: _"Base/Tall doors > 600mm are too heavy. Forced 2 doors."_

### 2.2 The "Flap Door" Exception (Wall Cabinets)

- **Constraint:** Wall cabinets frequently use top-hinged lift systems (e.g., Blum Aventos) rather than side hinges.
- **Reality:** Lift systems can easily support single wide fronts up to 1200mm.
- **Rule:** For `WALL` cabinets, `doors == 1` is perfectly valid up to `1200mm`. Do not force 2 doors unless `width > 1200mm`.

### 2.3 The "Useless Drawer" Rule (Internal Clearance)

- **Constraint:** Premium under-mount drawer runners (e.g., Blum Legrabox, Hettich AvanTech) require physical space on the sides.
- **Reality:** Runners consume approximately ~38mm per side (76mm total). In a 150mm wide cabinet, the usable internal drawer width is only ~40mm.
- **Rule:** If `drawers > 0` and `width < 300mm`, issue a **Soft Warning**: _"Usable inside drawer width will be very narrow due to hardware clearances."_

---

## 📐 3. Design & Topology Rules

### 3.1 Open Shelving is Valid

- **Constraint:** Not all cabinets have fronts.
- **Reality:** Open shelving (_Regalschränke_) is standard for wine racks, end-caps, and decorative boxes.
- **Rule:** **Never force a cabinet to have > 0 doors or drawers.** `doors == 0` and `drawers == 0` is a valid state.

### 3.2 Drawer & Door Combinations

- **Constraint:** If a cabinet has drawers (usually at the bottom or top), the remaining space is covered by doors.
- **Reality:** You cannot have 3 doors on a standard cabinet that also has drawers (it implies a highly complex, non-standard asymmetrical build).
- **Rule:** If `drawers > 0` and `doors > 2`, apply a **Hard Clamp** to force `doors = 2`.

---

## 🤖 4. Implementation Guide for LLMs

When writing Python/Reflex state logic for cabinet validation, adhere to this structure:

1.  **Forgiving Parsing:** Always strip non-numeric characters (e.g., "600 mm" -> 600) before validation. Do not crash on string inputs.
2.  **Hard Clamps First:** Apply absolute geometric limits based on cabinet type (e.g., Base cabinets cannot be 2000mm tall).
3.  **Heuristics Second:** Apply the Carpenter Rules (Leverage, Sag, Clearances) holistically.
4.  **UX Feedback:** If a Hard Clamp or Heuristic alters the user's input, you MUST populate a UI-visible warning dictionary (e.g., `field_warnings["door_count"] = "..."`). **No silent mutations.**

### Extensibility

_To future LLMs: If asked to add new cabinet types (e.g., "Corner Cabinets" or "Sink Cabinets"), you must append new sections to this document detailing the specific hardware constraints (e.g., Pie-cut hinges, plumbing clearances) before writing the code._
