As a Web Designer focusing on UX/UI and customer conversion, I look at this from the perspective of the end-user (a homeowner or interior designer) and the business goal (selling Krono Swiss materials).

Because our 2.5D engine is incredibly fast and physically accurate, we can design a highly interactive, "app-like" experience rather than a slow, clunky traditional website.

Here are the core **UX Use Cases** we need to build for the customer presentation, categorized by how they drive engagement:

### 1. The Core Interaction: "Point & Click" Material Swapping

- **The Use Case:** The user wants to see what Krono Oak looks like on the lower cabinets and White Marble on the countertop.
- **The UI:** A large, beautiful central image of the kitchen. On the right side, a panel with visual "Swatches" (thumbnails of the actual textures).
- **The UX:** The user clicks a tab called "Countertop", then clicks a Marble swatch. Because our API is so fast, the image updates almost instantly. This creates a "flow state" where the user plays with dozens of combinations without getting frustrated by loading spinners.

### 2. The "Shop the Look" (One-Click Presets)

- **The Use Case:** Users often suffer from "decision paralysis" when faced with 50 different wood grains. They need inspiration.
- **The UI:** A row of buttons at the top: _"Modern Minimalist"_, _"Rustic Farmhouse"_, _"Industrial Dark"_.
- **The UX:** Clicking "Rustic Farmhouse" sends a single JSON payload to our API that changes the Upper, Lower, and Countertop zones all at once. It instantly transforms the entire mood of the room, showing the power of the engine.

### 3. Zone Highlighting (Visual Feedback)

- **The Use Case:** The user needs to know exactly which part of the kitchen they are currently editing.
- **The UI/UX:** When the user selects the "Upper Cabinets" menu, the frontend briefly flashes or outlines the upper cabinets on the image. _(Note: We can actually use the `id_mask.png` on the frontend using an HTML5 Canvas to create perfect hover effects!)_

### 4. The "Details Matter" View (Zooming)

- **The Use Case:** Krono Swiss prides itself on high-quality, realistic wood grains. The user wants to see the physical scaling we worked so hard on.
- **The UI/UX:** A magnifying glass effect or a "Zoom" button. Because our engine renders in high resolution (up to 4K) and respects physical mm scaling, the user can zoom in on the countertop edge and see the realistic shadow blending and the crisp wood texture.

### 5. The Conversion: "Save & Quote"

- **The Use Case:** The user has found their dream kitchen. The business needs to capture this lead.
- **The UI:** A prominent "Download My Kitchen" or "Get a Quote" button.
- **The UX:** The frontend takes the current JSON configuration, downloads the final JPEG from our API, and generates a summary list of the exact Krono Swiss SKUs used (e.g., "Lower Cabinets: Krono Oak #1234").

---

### Proposed Screen Layout for the MVP Prototype

If we build a simple HTML/JS frontend (Option B from earlier), I suggest this layout:

- **Left (70% width):** The live Kitchen Render.
- **Right (30% width):** The Control Panel.
    - **Step 1:** Select Zone (Dropdown or Tabs: Upper, Lower, Countertop).
    - **Step 2:** Select Material (Grid of 4-6 clickable texture thumbnails).
    - **Bottom:** A "Randomize Kitchen" button (for fun/inspiration).
