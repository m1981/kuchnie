# F07 — Token Counting & Context-Size Indicators

## Problem

Users had no visibility into how many tokens they were consuming. Two
distinct questions had no answer:

1. **"How large is my session so far?"** — knowing the accumulated history
   size lets users decide when to fork, truncate, or start a new session
   before hitting the model's context limit.

2. **"How many tokens am I _about to send_?"** — when a user attaches a
   context file or pastes an image, they have no idea whether they are adding
   200 tokens or 20 000. An indicator shown _before_ Send prevents
   accidental quota burns.

---

## Goals

- Expose the current session token count via a REST endpoint so the frontend
  can display it in the session header or sidebar.
- Expose a fast heuristic estimate for a _pending_ context (message + images
    - files) so the frontend can update a live indicator as the user composes
      their next message — with zero latency and no API call.
- Provide a detailed breakdown (text / images / files / system prompt /
  history) so the UI can render a tooltip with component detail.
- Degrade gracefully when the Gemini API is unavailable: fall back to a local
  heuristic and signal the approximation with `fallback_used: true`.

---

## Solution

### Two-mode architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     src/token_counter.py                         │
│                                                                  │
│  TokenEstimate (Pydantic)                                        │
│    text_tokens, image_tokens, context_file_tokens,              │
│    system_prompt_tokens, history_tokens, total_tokens,          │
│    fallback_used                                                 │
│                                                                  │
│  ── Heuristics (offline, instant) ─────────────────────────── │
│  estimate_tokens_for_text(text)        → ceil(len / 4)          │
│  estimate_tokens_for_image(b64, mime)  → Gemini tile model      │
│  estimate_tokens_for_context_files(paths) → sum of text est.    │
│                                                                  │
│  build_pending_context_estimate(...)   → TokenEstimate          │
│    always fallback_used = True  (no API call)                   │
│                                                                  │
│  ── Exact API path (network) ──────────────────────────────── │
│  count_session_tokens(api_json, system_prompt, model)           │
│    → calls _client.models.count_tokens()                        │
│    → graceful degradation to heuristic + fallback_used = True   │
└──────────────────────────────────────────────────────────────────┘
```

| Mode          | Endpoint                        | Gemini API call      | Use case                                                        |
| ------------- | ------------------------------- | -------------------- | --------------------------------------------------------------- |
| **Exact**     | `GET /api/sessions/{id}/tokens` | Yes — `count_tokens` | "How many tokens is this session so far?"                       |
| **Heuristic** | `POST /api/tokens/estimate`     | No                   | Live indicator shown as user attaches files/images, before Send |

### Heuristic rules

| Component           | Rule                                                                                  |
| ------------------- | ------------------------------------------------------------------------------------- |
| **Text**            | `ceil(len(text) / 4)` — Gemini SentencePiece averages ~4 chars/token for Latin/Polish |
| **Image < 50 KB**   | 1 tile × 258 tokens = **258 tokens**                                                  |
| **Image 50–200 KB** | 2 tiles × 258 tokens = **516 tokens**                                                 |
| **Image > 200 KB**  | 4 tiles × 258 tokens = **1 032 tokens**                                               |
| **Context files**   | Text heuristic applied to each file's content, summed                                 |
| **System prompt**   | Text heuristic                                                                        |
| **History**         | Passed in by caller (from prior `count_session_tokens` call or cached)                |

The 258-token tile cost comes from Gemini's published vision pricing
(one 512 × 512 tile). Byte-size is used as a proxy for pixel count because
decoding image dimensions from raw bytes is expensive and unnecessary for an
order-of-magnitude estimate.

---

## API

### `GET /api/sessions/{session_id}/tokens`

Returns the authoritative token count for all turns stored in the session by
calling `client.models.count_tokens()`.

**Response — `SessionTokensResponse`**

```json
{
    "session_id": "abc-123",
    "text_tokens": 3847,
    "image_tokens": 0,
    "context_file_tokens": 0,
    "system_prompt_tokens": 0,
    "history_tokens": 0,
    "total_tokens": 3847,
    "fallback_used": false
}
```

Notes:

- An empty session returns `total_tokens: 0` without making any API call.
- An unknown `session_id` returns `total_tokens: 0` (consistent with the
  existing `GET /api/sessions/{id}` which returns 200 + empty for unknown
  IDs rather than 404).
- When the Gemini API is unavailable `fallback_used` is `true` and the count
  is a heuristic approximation.

---

### `POST /api/tokens/estimate`

Returns a heuristic breakdown for a context that has **not yet been sent**.
No Gemini API call is made. `fallback_used` is always `true`.

**Request — `TokenEstimateRequest`**

```json
{
    "user_message": "How thick should the shelf be?",
    "images": [{ "mime_type": "image/png", "data": "<base64>" }],
    "context_files": ["kuchnia-kroki.md"],
    "system_prompt": "You are an expert kitchen cabinet designer.",
    "history_token_count": 1200
}
```

All fields except `user_message` are optional. `history_token_count`
defaults to `0`.

**Response — `TokenEstimateResponse`**

```json
{
    "text_tokens": 9,
    "image_tokens": 258,
    "context_file_tokens": 412,
    "system_prompt_tokens": 11,
    "history_tokens": 1200,
    "total_tokens": 1890,
    "fallback_used": true
}
```

`total_tokens` is always the exact sum of the five component fields.

---

## Files Changed

| File                          | Change                                                                                              |
| ----------------------------- | --------------------------------------------------------------------------------------------------- |
| `src/token_counter.py`        | **New** — `TokenEstimate`, all heuristics, `build_pending_context_estimate`, `count_session_tokens` |
| `src/schemas.py`              | **Extended** — `TokenEstimateRequest`, `TokenEstimateResponse`, `SessionTokensResponse`             |
| `src/main.py`                 | **Extended** — two new route handlers + updated imports                                             |
| `tests/test_token_counter.py` | **New** — 27 TDD unit tests                                                                         |
| `tests/test_token_routes.py`  | **New** — 13 FastAPI integration tests                                                              |

---

## Design Decisions

| Decision                                                 | Rationale                                                                                                                                                                                                     |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`_client` module-level singleton**                     | Mirrors `agent.py` pattern — trivially patchable in tests with a single `patch("src.token_counter._client")` call; no DI ceremony needed                                                                      |
| **Two separate endpoints**                               | Exact and heuristic have different latency profiles and different callers; a single endpoint with a `?mode=` switch would force the UI to handle two async behaviours from one URL                            |
| **`build_pending_context_estimate` reads context files** | Uses the same `read_file()` tool the agent uses, so the token estimate for a file is based on the actual content the agent would inject — not a filename length guess                                         |
| **Image tile heuristic uses decoded byte-size**          | Decoding image dimensions (PNG IHDR, EXIF, etc.) adds code complexity and library dependencies; byte-size gives the same order-of-magnitude tile bucket at near-zero cost                                     |
| **`fallback_used` boolean on every response**            | Lets the frontend render `~1 890 tokens` (tilde = heuristic) vs `1 890 tokens` (exact) without duplicating the display logic                                                                                  |
| **`count_session_tokens` re-hydrates history**           | Passes proper `Content` objects (not raw JSON strings) to `count_tokens` — the same way `agent.py` passes them to `generate_content`, ensuring the API sees the exact same structure                          |
| **`system_prompt` forwarded in `CountTokensConfig`**     | The system instruction is part of the context window; omitting it would undercount by hundreds of tokens for long prompts                                                                                     |
| **Unknown session returns 200 + zero, not 404**          | Consistent with `GET /api/sessions/{id}` which returns 200 + empty for unknown IDs; the repository's `load_session` returns `("[]", "[]", None)` for missing rows by design                                   |
| **`history_token_count` supplied by caller**             | The estimate endpoint does not query the DB; caller passes the cached session token count from a prior `/tokens` call, keeping the endpoint stateless and fast                                                |
| **Graceful API degradation**                             | Network failures must never break the chat flow; `count_session_tokens` catches all exceptions, logs a warning, and returns a heuristic result so the UI degrades to approximate display rather than an error |

---

## Call Flow

```
── Exact path (session header) ──────────────────────────────────────

GET /api/sessions/{id}/tokens
  └── get_session_token_count()
        ├── session_repo.load_session()      — returns api_json, system_prompt
        └── count_session_tokens()
              ├── hydrate_history()           — JSON → Content objects
              ├── _client.models.count_tokens()  — Gemini API call
              │     └── on failure → heuristic sum over items
              └── TokenEstimate  →  SessionTokensResponse

── Heuristic path (live compose indicator) ──────────────────────────

POST /api/tokens/estimate
  └── estimate_pending_tokens()
        ├── _resolve_context_file_paths()    — bare names → absolute paths
        └── build_pending_context_estimate()
              ├── estimate_tokens_for_text()
              ├── estimate_tokens_for_image() × N
              ├── estimate_tokens_for_context_files()
              │     └── read_file() × M
              └── TokenEstimate  →  TokenEstimateResponse
```

---

## Test Coverage — 40 tests across 7 classes

| Class                               | Tests | What is covered                                                                                                                                                             |
| ----------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TestTokenEstimateModel`            | 3     | Field presence, default `fallback_used`, int type                                                                                                                           |
| `TestEstimateTokensForText`         | 5     | Empty string, proportional estimate, int return, monotonic, whitespace                                                                                                      |
| `TestEstimateTokensForImage`        | 4     | Small PNG tile, large > small, unknown MIME, invalid base64                                                                                                                 |
| `TestEstimateTokensForContextFiles` | 4     | Empty list, single readable, unreadable skipped, multiple summed                                                                                                            |
| `TestBuildPendingContextEstimate`   | 6     | Plain message, +images, +files, all combined, system prompt delta, history forwarded                                                                                        |
| `TestCountSessionTokens`            | 5     | API success, API error fallback, empty history no-call, system prompt forwarded, model param forwarded                                                                      |
| `TestSessionTokensRoute`            | 5     | 200 with fields, positive count, API called once, unknown session zero, empty session zero                                                                                  |
| `TestTokensEstimateRoute`           | 8     | Plain message, +image increases total, +files increases total, +prompt increases total, history forwarded, total = sum of parts, all optional absent, missing message → 422 |
