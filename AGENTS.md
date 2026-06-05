## Project Structure & Development

### Kitchen Agent Application

This repository contains the Kitchen Agent application:

- `kitchen-agent/frontend/` — Svelte 5 frontend (ChatGPT-like UI with content management)
- `kitchen-agent/src/` — FastAPI backend (Python)

### Testing Infrastructure

**IMPORTANT:** Before making changes to frontend components or backend API, read `kitchen-agent/TESTING.md` to understand the testing infrastructure patterns. These patterns are intentional and must not be removed:

- `data-testid` attributes on UI components
- `data-busy-recent` attribute for E2E test timing
- `window.__testHelpers` exposure in dev mode
- `POST /api/_test/seed` endpoint (DEBUG mode only)
- `X-Test-Delay-Ms` middleware (DEBUG mode only)

See `TESTING.md` for full documentation.
