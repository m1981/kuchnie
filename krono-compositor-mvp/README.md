# Krono Compositor MVP

A **2.5D image compositing engine** for real-time kitchen interior visualization. Users interactively swap materials (wood, marble, stone) on pre-rendered 3D kitchen scenes and see photorealistic results in ~500ms.

## How It Works

The system splits the work into two phases:

1. **Offline (Blender)** — A headless Blender script generates 5 render passes from a JSON kitchen layout: base lighting, UV coordinates, ID masks, reflections, and handle shadows.
2. **Real-time (OpenCV)** — A FastAPI server reads those passes and composites new textures on-the-fly using UV warping, masking, and blend modes — no 3D re-rendering needed.

The frontend is a lightweight Alpine.js SPA that sends zone/material selections to the API and displays the result with mouse-zoom.

## Quick Start

```bash
# Install dependencies
uv sync

# Run the server (serves frontend at http://localhost:8000)
uv run python main.py

# Run tests
uv run pytest -v
```

### Regenerating Scene Assets

If you have Blender installed, regenerate the 3D passes from `layout.json`:

```bash
blender -b -P gen_kitchen.py
```

## Project Structure

```
src/compositor/
├── domain/          # Protocol interfaces (no dependencies)
├── infrastructure/  # OpenCV implementations
├── application/     # SceneCompositor orchestration
└── presentation/    # FastAPI routes, Pydantic schemas, catalog

gen_kitchen.py       # Headless Blender script (5-pass renderer)
static/index.html    # Alpine.js + Tailwind frontend
layout.json          # Kitchen scene definition (cabinets, countertop, zones)
assets/              # Textures and rendered scene passes
```

## Architecture

Built with **Clean Architecture** and **Domain-Driven Design**. The core compositor logic is decoupled from OpenCV via Protocol interfaces (Interface Segregation Principle), making it possible to swap the infrastructure layer without touching business rules.

Key design decisions:

- **Physical UV Scaling** — 1.0 UV unit = 1000mm. Textures repeat based on real-world dimensions, not arbitrary scale factors.
- **Synchronous FastAPI routes** — OpenCV is CPU-bound; `async` would block the event loop. FastAPI routes `def` (not `async def`) to a thread pool automatically.
- **Strict 500 errors** — Missing textures raise errors instead of falling back to defaults. Silent failures hide configuration problems.

## Documentation

| Document                                              | Description                                                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [Architecture](doc/architecture.md)                   | Architectural decisions, layered design, and key implementation choices               |
| [Pipeline Rules](doc/PIPELINE_RULES.md)               | Strict rules for separating Art passes from Math passes in the 3D→2D pipeline         |
| [Conflicting Paradigms](doc/conflicting_paradigms.md) | Why Blender's visual approximation and OpenCV's exact math require careful separation |
| [Production Roadmap](doc/what_next.md)                | Next steps for scaling to production (caching, database, cloud storage)               |

### Reference Materials

| Document                                       | Description                                                                       |
| ---------------------------------------------- | --------------------------------------------------------------------------------- |
| [Blender Script Prompt](doc/prompt_blender.md) | Prompt used to generate `gen_kitchen.py` — useful for understanding design intent |
| [Frontend UX Spec](doc/prompt_web.md)          | UX requirements and layout that drove the Alpine.js frontend                      |

## Tech Stack

- **Backend**: Python 3.11, FastAPI, OpenCV, NumPy
- **Frontend**: Alpine.js, Tailwind CSS (CDN, zero build steps)
- **3D Pipeline**: Blender (headless, `bpy` Python API)
- **Testing**: pytest, pytest-cov

## License

MIT
