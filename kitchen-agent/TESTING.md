# Testing Infrastructure Guide

## Overview

This document describes the cross-cutting testing infrastructure that enables reliable E2E (end-to-end) browser testing. **These patterns are intentional — do not remove them even if they appear unused in production code.**

---

## Frontend Testing Patterns

### `data-testid` Attributes

All interactive elements have `data-testid` attributes for reliable E2E selectors:

| Component         | Attributes                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| `ChatMessageList` | `data-testid="chat-bubble"`, `edit-btn`, `delete-btn`, `delete-pair-btn`, `fork-btn`, `loading-indicator` |
| `ChatComposer`    | `data-testid="chat-input"`, `send-btn`                                                                    |
| `TruncateBar`     | `data-testid="truncate-bar"`, `truncate-btn` (with `data-n`)                                              |
| `ConfirmDialog`   | `data-testid="confirm-dialog"`, `confirm-ok`, `confirm-cancel`                                            |

**Why:** `aria-label` and CSS classes change for styling. `data-testid` is stable for testing.

**DO NOT** remove these attributes. They are not used in production code but are essential for E2E tests.

---

### Global Busy Indicator

```svelte
<!-- +page.svelte -->
<div
  data-testid="app-busy"
  data-loading={isBusy}
  data-busy-recent={busyRecent}
  class="hidden"
/>
```

- `data-loading` — `true` while any async operation is in progress
- `data-busy-recent` — `true` during operation + 300ms after completion

**Why:** Optimistic UI updates are instant. The 300ms grace period gives E2E tests time to observe the loading state before it disappears.

**DO NOT** remove `data-busy-recent` as "redundant." It solves a real timing problem in browser automation.

---

### Test Helpers on `window`

In dev mode (`import.meta.env.DEV`), the following are exposed on `window`:

```javascript
window.__chatStore; // Full chat store for state inspection
window.__sessionStore; // Session store
window.__testHelpers.autoConfirm // Test automation helpers // Boolean — auto-accept ConfirmDialog
    .confirmAll() // Enable auto-confirm
    .confirmNone(); // Disable auto-confirm
```

**Why:** E2E tests need to inspect store state and control dialog behavior without native `confirm()`.

**DO NOT** remove this exposure thinking it's a security risk. It only exists in dev mode (`import.meta.env.DEV`).

---

### ConfirmDialog Auto-Confirm

`ConfirmDialog.svelte` checks `window.__testHelpers.autoConfirm` on mount. When true, it automatically calls `onconfirm()`.

**Why:** Native `confirm()` blocks automation and cannot be styled. The custom dialog is testable.

---

## Backend Testing Patterns

### `DEBUG` Configuration

```python
# src/config.py
debug: bool = False  # Set via DEBUG=true in .env
```

Enables test-only endpoints and middleware. **Never active in production.**

---

### `X-Test-Delay-Ms` Middleware

```python
# src/main.py — TestDelayMiddleware
# Adds artificial delay when header is present (DEBUG mode only)
```

**Why:** Allows E2E tests to slow down API responses to test loading states and button disabled behavior.

**Usage:**

```bash
curl -H "X-Test-Delay-Ms: 2000" http://localhost:8000/api/sessions/...
```

---

### Seed Endpoint

```
POST /api/_test/seed
{
  "pairs": 3,           # Number of user+assistant turn-pairs
  "title": "Test Session"  # Optional session title
}
```

Returns:

```json
{
  "session_id": "uuid",
  "message_count": 6,
  "turn_ids": [{"user": "uuid", "assistant": "uuid"}, ...]
}
```

**Why:** E2E tests need deterministic data. Depending on existing sessions is fragile.

**Only available when `DEBUG=true`.**

---

### Session State Endpoint

```
GET /api/sessions/{id}/state
```

Returns lightweight state without full message content:

```json
{
  "session_id": "uuid",
  "message_count": 4,
  "turn_ids": ["uuid1", "uuid2", ...],
  "roles": ["user", "assistant", ...]
}
```

**Why:** Faster than fetching full messages when you only need to verify state.

---

## Browser Test Tools

### `browser-test.js`

Unified test helper with declarative commands:

```bash
browser-test.js click "[data-testid='delete-btn']"
browser-test.js query "[data-testid='chat-bubble']" --count
browser-test.js assert --count 4           # Exit 0 = pass, 1 = fail
browser-test.js confirm                     # Click confirm-ok button
browser-test.js --auto-confirm click ...    # Auto-accept all dialogs
```

---

### `browser-wait.js`

Wait for DOM conditions instead of `sleep`:

```bash
browser-wait.js --selector "[data-testid='chat-bubble']" --count 4
browser-wait.js --selector "[data-testid='app-busy'][data-busy-recent='false']"
browser-wait.js --selector "[data-testid='loading-indicator']" --absent
```

**Why:** `sleep` is brittle. DOM-based waits are reliable.

---

### `browser-seed.js`

Create test sessions and navigate to them:

```bash
browser-seed.js --pairs 3 --title "My Test"
```

---

### `browser-intercept.js`

Control network responses for testing:

```bash
browser-intercept.js --path '/api/sessions/*/messages/*' --delay 2000
browser-intercept.js --path '/api/chat' --status 500 --error "Server error"
browser-intercept.js --clear
```

---

## Anti-Patterns to Avoid

| Anti-Pattern                               | Why It's Wrong                                               |
| ------------------------------------------ | ------------------------------------------------------------ |
| Removing `data-testid` attributes          | They look unused but are essential for E2E tests             |
| Removing `__testHelpers` from window       | It's dev-mode only and needed for test automation            |
| Removing `data-busy-recent`                | It's not redundant — it solves timing issues in automation   |
| Deleting seed endpoint                     | It looks like dead code but is critical for test determinism |
| Using `sleep` instead of `browser-wait.js` | Sleep is brittle; DOM waits are reliable                     |
| Using native `confirm()`                   | It blocks automation; use `ConfirmDialog` component          |

---

## Running E2E Tests

```bash
# 1. Start backend with DEBUG=true
DEBUG=true python -m uvicorn src.main:app --port 8000

# 2. Start frontend
cd frontend && npm run dev

# 3. Start Chrome with remote debugging
browser-start.js

# 4. Run tests
browser-seed.js --pairs 3
browser-test.js --auto-confirm assert --count 6
browser-test.js click "[data-testid='delete-btn']"
browser-wait.js --selector "[data-testid='app-busy'][data-busy-recent='false']"
browser-test.js assert --count 5
```

---

## Related Files

- `frontend/src/routes/+page.svelte` — Global busy indicator, test helpers exposure
- `frontend/src/lib/components/ConfirmDialog.svelte` — Auto-confirm support
- `frontend/src/lib/components/ChatMessageList.svelte` — data-testid on messages
- `frontend/src/lib/components/ChatComposer.svelte` — data-testid on input/buttons
- `frontend/src/lib/components/TruncateBar.svelte` — data-testid on truncation buttons
- `src/main.py` — TestDelayMiddleware registration
- `src/config.py` — DEBUG setting
- `src/api/test_helpers.py` — Seed endpoint
- `src/api/sessions.py` — Session state endpoint
