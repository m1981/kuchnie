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

### Generic Tools (in `~/.pi/agent/skills/pi-skills/browser-tools/`)

These are reusable across any project:

```bash
browser-test.js click "[data-testid='delete-btn']"
browser-test.js assert --count 4
browser-wait.js --selector "[data-testid='chat-bubble']" --count 4
browser-eval.js 'document.title'
browser-nav.js http://localhost:5173
browser-screenshot.js
```

### Project-Specific Tools (in `kitchen-agent/scripts/`)

These are specific to Kitchen Agent's API and should NOT be moved to global skills:

```bash
# Create test sessions via /api/_test/seed
scripts/browser-seed.js --pairs 3 --title "My Test"

# Intercept Kitchen Agent API responses
scripts/browser-intercept.js --path '/api/sessions/*/messages/*' --delay 2000
scripts/browser-intercept.js --clear
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

## E2E Tests (Playwright)

### Isolated Environment

E2E tests run on dedicated ports to avoid conflicts with dev servers:

| Service  | Dev Port | E2E Port    |
| -------- | -------- | ----------- |
| Backend  | 8000     | 8001        |
| Frontend | 5173     | 5174        |
| Data dir | `data/`  | `data-e2e/` |

Playwright manages the E2E servers automatically - no need to start them manually.

### Running Tests

```bash
# Run all E2E tests (starts isolated servers automatically)
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run in debug mode (step through)
npm run test:e2e:debug

# View test report
npm run test:e2e:report

# Clean up E2E data
npm run e2e:cleanup
```

### Test Coverage

| Spec File                | Tests | Coverage                                                         |
| ------------------------ | ----- | ---------------------------------------------------------------- |
| `message-delete.spec.ts` | 10    | Single delete, pair delete, auto-promote, cancel, error rollback |
| `truncate.spec.ts`       | 6     | Truncate bar visibility, 1 turn, 2 turns, cancel                 |

### Page Object Model

All page interactions are in `e2e/page-objects/ChatPage.ts`:

```typescript
const chatPage = new ChatPage(page);
await chatPage.goto();
await chatPage.loadSession('Test Session');
await chatPage.deleteMessage(0);
await chatPage.expectMessageCount(3);
```

### Seed Fixtures

Test data is created via `/api/_test/seed`:

```typescript
const session = await seedSession(page, { pairs: 3 });
// session.session_id, session.turn_ids for assertions
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
