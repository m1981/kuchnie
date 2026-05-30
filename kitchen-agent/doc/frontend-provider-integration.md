# Frontend Integration Guide: Provider & Model Selection

**Audience:** Frontend developer (SvelteKit + TypeScript)  
**Backend version:** post-provider-refactor (Gemini + Anthropic)  
**Status:** Backend ready · Frontend work required

---

## 1. What changed on the backend

The backend now supports multiple LLM providers. The active provider is
controlled by the server's `LLM_PROVIDER` environment variable (`gemini` |
`anthropic`). However, the **frontend can override the provider and model
per-request** by sending extra fields in the existing `POST /api/chat` payload.

No new endpoints are needed for basic use. Two new endpoints are added to
support the model picker UI (see §4).

---

## 2. API changes — what to send

### 2.1 Updated `ChatRequest` — two new optional fields

```
POST /api/chat
Content-Type: application/json
```

```jsonc
{
    // --- existing fields (unchanged) ---
    "session_id": "uuid",
    "message": "What hinges should I use?",
    "mode_id": "general",
    "system_prompt": null,
    "images": null,
    "context_files": null,

    // --- NEW optional fields ---
    "provider": "anthropic", // "gemini" | "anthropic"  (omit → use server default)
    "model": "claude-sonnet-4-5" // provider-specific model name  (omit → use server default)
}
```

**Priority rules (server-side):**

| Field sent                     | Behaviour                                            |
| ------------------------------ | ---------------------------------------------------- |
| Neither `provider` nor `model` | Server default (`LLM_PROVIDER` + `*_MODEL` env vars) |
| `provider` only                | Switch provider, use that provider's default model   |
| `model` only                   | Keep current provider, override model name           |
| Both                           | Use the specified provider + model                   |

**The `ChatResponse` is unchanged:**

```typescript
type ChatResponse = {
    text: string;
    tools_used: ToolLog[];
};
```

### 2.2 Backward compatibility

All existing fields remain exactly as before. If the frontend sends neither
`provider` nor `model`, behaviour is identical to today. Existing sessions,
fork/export flows, notes — all unaffected.

---

## 3. New API endpoints

### `GET /api/providers`

Returns the list of available providers with their supported models.

```jsonc
// Response — array of ProviderInfo
[
    {
        "id": "gemini",
        "label": "Google Gemini",
        "default_model": "gemini-2.5-flash",
        "models": [
            { "id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "context_k": 1000 },
            { "id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "context_k": 1000 },
            { "id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash", "context_k": 1000 }
        ]
    },
    {
        "id": "anthropic",
        "label": "Anthropic Claude",
        "default_model": "claude-sonnet-4-5",
        "models": [
            { "id": "claude-opus-4-5", "label": "Claude Opus 4.5", "context_k": 200 },
            { "id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5", "context_k": 200 },
            { "id": "claude-haiku-3-5", "label": "Claude Haiku 3.5", "context_k": 200 }
        ]
    }
]
```

### `GET /api/providers/active`

Returns the server's currently configured default.

```jsonc
{
    "provider": "gemini",
    "model": "gemini-2.5-flash"
}
```

Use this on app startup to initialise the picker to match the server default.

---

## 4. Frontend implementation plan

### 4.1 New TypeScript types — add to `src/lib/api.ts`

```typescript
// ── Provider / model picker types ────────────────────────────────────────────

export type ModelInfo = {
    id: string;
    label: string;
    context_k: number; // context window in thousands of tokens
};

export type ProviderInfo = {
    id: string;
    label: string;
    default_model: string;
    models: ModelInfo[];
};

export type ActiveProvider = {
    provider: string;
    model: string;
};

// Updated ChatRequest — add two optional fields
export type ChatRequest = {
    session_id: string;
    message: string;
    mode_id?: string;
    system_prompt?: string | null;
    images?: ChatImagePart[] | null;
    context_files?: string[] | null;
    provider?: string; // NEW
    model?: string; // NEW
};
```

### 4.2 New API methods — add to `src/lib/api.ts`

```typescript
// inside the `api` object:

/**
 * GET /api/providers
 * Returns all available providers and their supported model lists.
 * Call once on app mount; cache the result.
 */
getProviders: (): Promise<ProviderInfo[]> =>
  request<ProviderInfo[]>('/api/providers'),

/**
 * GET /api/providers/active
 * Returns the server's default provider + model.
 * Use to initialise the picker on first load.
 */
getActiveProvider: (): Promise<ActiveProvider> =>
  request<ActiveProvider>('/api/providers/active'),
```

### 4.3 Store changes — `src/lib/stores/chat.svelte.ts`

Add provider + model state next to the existing `selectedModeId`:

```typescript
// ── Provider / model selection ────────────────────────────────────────────────
let providers = $state<ProviderInfo[]>([]);
let selectedProvider = $state(''); // '' means "use server default"
let selectedModel = $state(''); // '' means "use provider default"

// load on init (alongside loadPromptModes)
async function loadProviders() {
    try {
        const [providerList, active] = await Promise.all([
            api.getProviders(),
            api.getActiveProvider()
        ]);
        providers = providerList;
        // pre-select the server default so the UI reflects reality
        if (!selectedProvider) selectedProvider = active.provider;
        if (!selectedModel) selectedModel = active.model;
    } catch {
        // non-fatal — picker shows "server default" label
    }
}
```

Wire it into `sendMessage`:

```typescript
async function sendMessage(text: string) {
  // ... existing code ...

  const payload: ChatRequest = {
    session_id: sessionId,
    message:    text,
    mode_id:    selectedModeId,
    images:     /* existing */,
    context_files: /* existing */,
    // Only include when the user has explicitly chosen something
    provider: selectedProvider || undefined,
    model:    selectedModel    || undefined,
  };

  // ... rest unchanged ...
}
```

Expose via the store's returned object:

```typescript
return {
    // ... existing exports ...
    get providers() {
        return providers;
    },
    get selectedProvider() {
        return selectedProvider;
    },
    get selectedModel() {
        return selectedModel;
    },
    setProvider(id: string) {
        selectedProvider = id;
        // reset model to that provider's default when provider changes
        const p = providers.find((p) => p.id === id);
        selectedModel = p?.default_model ?? '';
    },
    setModel(id: string) {
        selectedModel = id;
    }
};
```

### 4.4 New component — `src/lib/components/ProviderPicker.svelte`

A compact two-level picker: provider dropdown → model dropdown.

```svelte
<script lang="ts">
  import type { ProviderInfo } from '$lib/api';

  type Props = {
    providers: ProviderInfo[];
    selectedProvider: string;
    selectedModel: string;
    onchange: (provider: string, model: string) => void;
  };

  let { providers, selectedProvider, selectedModel, onchange }: Props = $props();

  const activeProvider = $derived(providers.find(p => p.id === selectedProvider));

  function handleProviderChange(e: Event) {
    const pid = (e.target as HTMLSelectElement).value;
    const p   = providers.find(p => p.id === pid);
    onchange(pid, p?.default_model ?? '');
  }

  function handleModelChange(e: Event) {
    onchange(selectedProvider, (e.target as HTMLSelectElement).value);
  }
</script>

<div class="flex items-center gap-2 text-sm">
  <!-- Provider selector -->
  <select
    value={selectedProvider}
    onchange={handleProviderChange}
    class="rounded border border-line bg-surface px-2 py-1 text-xs text-ink"
    aria-label="LLM provider"
  >
    {#each providers as p}
      <option value={p.id}>{p.label}</option>
    {/each}
  </select>

  <!-- Model selector — only shown when provider is selected -->
  {#if activeProvider}
    <select
      value={selectedModel}
      onchange={handleModelChange}
      class="rounded border border-line bg-surface px-2 py-1 text-xs text-ink"
      aria-label="Model"
    >
      {#each activeProvider.models as m}
        <option value={m.id}>
          {m.label} ({m.context_k}k)
        </option>
      {/each}
    </select>
  {/if}
</div>
```

### 4.5 Wire `ProviderPicker` into `ChatHeader.svelte`

`ChatHeader` already receives mode info as props — extend the same pattern:

```svelte
<!-- ChatHeader.svelte — add to Props type -->
type Props = {
  // ... existing props ...
  providers: ProviderInfo[];
  selectedProvider: string;
  selectedModel: string;
  onproviderchange: (provider: string, model: string) => void;
};
```

Render it next to the existing mode label:

```svelte
<!-- inside <header> — after the mode h2 -->
<ProviderPicker
  providers={providers}
  selectedProvider={selectedProvider}
  selectedModel={selectedModel}
  onchange={onproviderchange}
/>
```

### 4.6 Wire into `+page.svelte`

```svelte
<ChatHeader
  modeIcon={chat.modeIcon}
  modeLabel={chat.modeLabel}
  sessionId={chat.sessionId}
  showRight={showRight}
  hasSystemPromptOverride={chat.hasSystemPromptOverride}
  providers={chat.providers}
  selectedProvider={chat.selectedProvider}
  selectedModel={chat.selectedModel}
  ontoggleright={() => (showRight = !showRight)}
  oneditprompt={chat.openSystemPromptEditor}
  onproviderchange={(p, m) => { chat.setProvider(p); chat.setModel(m); }}
/>
```

---

## 5. UX recommendations

### Provider/model scoping

| Scope              | Recommendation                                                              |
| ------------------ | --------------------------------------------------------------------------- |
| **Global default** | Set via server env (`LLM_PROVIDER` / `GEMINI_MODEL` / `ANTHROPIC_MODEL`)    |
| **Per-session**    | Store `provider` + `model` in the session's `ui_history` metadata (future)  |
| **Per-message**    | Already supported — each `ChatRequest` can carry its own `provider`+`model` |

For v1, **per-message** (whatever is selected in the picker at send time) is
the simplest approach and is fully supported today without any DB changes.

### Empty state

Show a "Using server default" label when `selectedProvider === ''`:

```svelte
{#if !selectedProvider}
  <span class="text-xs text-muted">Using server default</span>
{/if}
```

### Error handling

When the user selects a provider for which the server has no API key configured,
the `POST /api/chat` call will return `HTTP 500` with a message like
`"ANTHROPIC_API_KEY not configured"`. Display this as a toast/banner — the
existing error handling in `chat.svelte.ts` already catches and displays
`Error.message` strings.

### Loading state

`getProviders()` should be called **once** at app startup (inside `onMount` or
the store's init function), not on every message send. Cache the result in
`providers` state. The active provider + model from `getActiveProvider()` is
used only to initialise the picker — subsequent changes are driven by the user.

---

## 6. Backend implementation checklist (what still needs to be built)

The following backend work is needed to fully support the above frontend plan.
This is **not** yet merged — the frontend developer should coordinate with the
backend developer.

### 6.1 `POST /api/chat` — accept `provider` and `model`

**File:** `src/schemas.py` — `ChatRequest`

```python
class ChatRequest(BaseModel):
    # ... existing fields ...
    provider: str | None = None   # NEW — overrides settings.llm_provider
    model: str | None = None      # NEW — overrides provider's default model
```

**File:** `src/main.py` — `chat()` handler  
Pass `provider` and `model` down through `ChatService.handle_turn()` →
`agent.process_chat_turn()` → `get_provider()`.

**File:** `src/providers/base.py` — `get_provider()`  
Accept optional `provider_name` and `model` arguments:

```python
def get_provider(
    provider_name: str | None = None,
    model: str | None = None
) -> LLMProvider:
    name = provider_name or _config.settings.llm_provider
    if name == "gemini":
        return GeminiProvider(model_override=model)
    if name == "anthropic":
        return AnthropicProvider(model_override=model)
    raise ValueError(f"Unknown LLM provider: {name}")
```

**File:** `src/providers/gemini.py` and `src/providers/anthropic_provider.py`  
Accept `model_override: str | None = None` in `__init__`; use it instead of
`settings.gemini_model` / `settings.anthropic_model` when provided.

### 6.2 New endpoints

**File:** `src/main.py`

```python
@app.get("/api/providers", response_model=list[ProviderInfo])
def list_providers() -> list[ProviderInfo]:
    """Returns all available providers and their model catalogs."""
    ...

@app.get("/api/providers/active", response_model=ActiveProvider)
def get_active_provider() -> ActiveProvider:
    """Returns the server's currently configured default provider + model."""
    return ActiveProvider(
        provider=settings.llm_provider,
        model=_get_default_model(settings.llm_provider),
    )
```

**File:** `src/schemas.py`

```python
class ModelInfo(BaseModel):
    id: str
    label: str
    context_k: int

class ProviderInfo(BaseModel):
    id: str
    label: str
    default_model: str
    models: list[ModelInfo]

class ActiveProvider(BaseModel):
    provider: str
    model: str
```

The model catalog can be a static dict in `main.py` for now — it changes only
when new models are released, not at runtime.

---

## 7. Minimal implementation path (frontend v1)

If you want to ship the picker before §6 backend work is complete, use this
reduced approach:

1. **Hardcode the provider/model catalog** in the frontend instead of fetching
   from `/api/providers`. Add it to a new file `src/lib/providers.ts`:

```typescript
// src/lib/providers.ts
export type ModelInfo = { id: string; label: string; context_k: number };
export type ProviderInfo = {
    id: string;
    label: string;
    default_model: string;
    models: ModelInfo[];
};

export const PROVIDERS: ProviderInfo[] = [
    {
        id: 'gemini',
        label: 'Google Gemini',
        default_model: 'gemini-2.5-flash',
        models: [
            { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', context_k: 1000 },
            { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', context_k: 1000 },
            { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', context_k: 1000 }
        ]
    },
    {
        id: 'anthropic',
        label: 'Anthropic Claude',
        default_model: 'claude-sonnet-4-5',
        models: [
            { id: 'claude-opus-4-5', label: 'Claude Opus 4.5', context_k: 200 },
            { id: 'claude-sonnet-4-5', label: 'Claude Sonnet 4.5', context_k: 200 },
            { id: 'claude-haiku-3-5', label: 'Claude Haiku 3.5', context_k: 200 }
        ]
    }
];
```

2. **Skip `/api/providers` and `/api/providers/active`** — initialise the
   picker from `PROVIDERS[0].id` and `PROVIDERS[0].default_model`.

3. **Send `provider` + `model` in `ChatRequest`** — the backend `ChatRequest`
   schema uses `extra="ignore"` via pydantic-settings so the extra fields are
   silently dropped today. The request will succeed; the extra fields are just
   ignored until §6.1 is implemented.

> **Important:** Step 3 means the picker renders and sends data but has no
> effect until the backend implements §6.1. This is acceptable for a staged
> rollout — the UI ships first, the backend follows.

---

## 8. File change summary

| File                                       | Change type | Notes                                                                                                                                                      |
| ------------------------------------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/lib/api.ts`                           | Update      | Add `ModelInfo`, `ProviderInfo`, `ActiveProvider` types; add `provider?` + `model?` to `ChatRequest`; add `getProviders()` + `getActiveProvider()` methods |
| `src/lib/providers.ts`                     | **Create**  | Static catalog (v1 hardcoded approach from §7)                                                                                                             |
| `src/lib/stores/chat.svelte.ts`            | Update      | Add `providers`, `selectedProvider`, `selectedModel` state; `loadProviders()`; `setProvider()` / `setModel()`; include in `sendMessage()` payload          |
| `src/lib/components/ProviderPicker.svelte` | **Create**  | Two-level select (§4.4)                                                                                                                                    |
| `src/lib/components/ChatHeader.svelte`     | Update      | Add `providers`, `selectedProvider`, `selectedModel`, `onproviderchange` props; render `<ProviderPicker>`                                                  |
| `src/routes/+page.svelte`                  | Update      | Pass new props to `<ChatHeader>`                                                                                                                           |

---

## 9. Questions / open items

| #   | Question                                                                                                                                   | Decision needed by |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| 1   | Should provider/model be persisted per-session in the DB? (Currently per-message)                                                          | Backend + Product  |
| 2   | Should the picker be hidden when the server has only one provider with API key configured?                                                 | Frontend           |
| 3   | Should the ChatHeader display which model generated the last response? (Requires storing it in `tools_used` or a new `ChatResponse` field) | Backend            |
| 4   | Should switching provider mid-session be allowed, or should it only apply to new sessions?                                                 | Product            |
