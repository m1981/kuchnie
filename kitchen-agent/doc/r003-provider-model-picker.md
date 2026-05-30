# R003 — Provider & Model Picker: Design & Implementation Decisions

**Feature:** LLM provider and model selection UI  
**Scope:** Frontend only (staged rollout — backend endpoints pending)  
**Status:** Implemented · `svelte-check` clean · 0 errors / 0 warnings  
**Files touched:** 6 (2 new, 4 updated)

---

## 1. Context

The backend was refactored to support multiple LLM providers (Gemini, Anthropic).
The integration guide (`doc/frontend-provider-integration.md`) specified two
implementation paths:

- **§4 "full" path** — fetch provider catalog from `/api/providers` + active
  default from `/api/providers/active` at startup.
- **§7 "minimal" path** — hardcode the catalog in the frontend, skip backend
  endpoints until they are implemented.

We implemented the **full path architecture with §7 as the runtime fallback**:
the live API is attempted; if it fails (endpoints not yet deployed) the static
catalog silently takes over. Both code paths use identical types and component
contracts, so no frontend changes are required when the backend catches up.

---

## 2. File map

| File                                       | Role                                                              |
| ------------------------------------------ | ----------------------------------------------------------------- |
| `src/lib/providers.ts`                     | Static catalog (seed + fallback)                                  |
| `src/lib/api.ts`                           | Types + API methods for provider endpoints                        |
| `src/lib/stores/chat.svelte.ts`            | State ownership, `loadProviders()`, `setProvider()`, `setModel()` |
| `src/lib/components/ProviderPicker.svelte` | Two-level `<select>` UI widget                                    |
| `src/lib/components/ChatHeader.svelte`     | Mounts ProviderPicker; routes `onproviderchange`                  |
| `src/routes/+page.svelte`                  | Wires store → header; parallel-loads on mount                     |

---

## 3. Key decisions

### D1 — Static catalog as seed, not as fallback-only

**Decision:** `providers` rune state is initialised directly from `PROVIDERS`
(the static catalog) before any network call fires.

```typescript
// chat.svelte.ts
let providers = $state<ProviderInfo[]>(PROVIDERS); // ← seeded immediately
```

**Why:** The picker renders on the very first paint with no spinner and no
layout shift. `loadProviders()` may later overwrite `providers` with the live
API response, but from the user's perspective the picker is always interactive
from frame one.

**Alternative considered:** Start with `[]` and show a loading skeleton.
Rejected — adds visual noise for a non-critical piece of chrome; the static
catalog is good enough for almost all practical sessions.

---

### D2 — `loadProviders()` is silent on failure

```typescript
async loadProviders() {
    try {
        const [providerList, active] = await Promise.all([
            api.getProviders(),
            api.getActiveProvider()
        ]);
        if (providerList.length > 0) providers = providerList;
        if (!selectedProvider) selectedProvider = active.provider;
        if (!selectedModel)    selectedModel    = active.model;
    } catch {
        // Backend not yet updated — fall back to static catalog + first provider.
        if (!selectedProvider && providers.length > 0) {
            selectedProvider = providers[0].id;
            selectedModel    = providers[0].default_model;
        }
    }
}
```

**Why:** During the backend-pending window every app load would produce a
console error or an error toast for something that is not the user's fault and
has no impact on their workflow. The static catalog is a complete functional
fallback — silence is the right UX here.

**Tradeoff accepted:** If the API _does_ exist but returns a transient 500,
we silently swallow it and fall back to static. This is acceptable for a
non-critical picker; it is not acceptable for the main chat endpoint (which
does surface errors).

---

### D3 — Types are defined in two places (`providers.ts` and `api.ts`), intentionally

`src/lib/providers.ts` exports `ModelInfo` and `ProviderInfo` for use by
the static catalog and the `ProviderPicker` component (which only needs the
shape, not the API layer).

`src/lib/api.ts` also exports `ModelInfo`, `ProviderInfo`, and the additional
`ActiveProvider` type that mirrors the backend Pydantic schema.

**Why:** The component tree (`ProviderPicker`, `ChatHeader`) imports from
`$lib/providers` — the type-only layer. This avoids dragging the full API
client into components that have no business touching it. When the backend
goes live and we want to lift to a single source of truth, the types in
`api.ts` become canonical and `providers.ts` imports from them instead.

**Current duplication:** `ModelInfo` and `ProviderInfo` are structurally
identical in both files. This is intentional and tracked — see §5 Future Work.

---

### D4 — `provider` and `model` are omitted from `ChatRequest` when empty

```typescript
// chat.svelte.ts — sendMessage()
provider: selectedProvider || undefined,
model:    selectedModel    || undefined,
```

**Why:** The backend contract says "omit → use server default". Sending `""`
is not the same as omitting the field in JSON serialisation — some Pydantic
validators would reject it or treat it as an explicit empty override. Using
`|| undefined` ensures the field is dropped from the JSON payload entirely
(`JSON.stringify` skips `undefined` values in objects).

---

### D5 — Provider selection persists across `startNewChat()`

`startNewChat()` resets session, messages, images, and editor state — but
deliberately does **not** reset `selectedProvider` or `selectedModel`.

**Why:** The user's provider/model choice is a workspace preference, not a
per-session setting. If I switch to Claude Opus for heavier reasoning, I expect
every subsequent new chat to also use Claude Opus until I change it manually.
This matches how mode selection works (`selectedModeId` is also preserved).

**Contrast:** `loadSession()` also does not reset provider/model — loading an
old session should not silently switch your provider back to the server default.
Per-session provider persistence (storing provider in `ui_history` metadata) is
an open item tracked in the integration guide §9 Q1.

---

### D6 — `setProvider()` auto-resets model to `default_model`

```typescript
setProvider(id: string) {
    selectedProvider = id;
    const p = providers.find((p) => p.id === id);
    selectedModel = p?.default_model ?? '';
},
```

**Why:** When the user switches from Gemini to Anthropic, keeping the previous
model id (e.g. `gemini-2.5-pro`) in `selectedModel` would send a nonsensical
payload to the backend. Auto-resetting to `default_model` is always safe and
matches the mental model: "I picked a new provider, use its recommended model."
The user can immediately override the model in the second dropdown if needed.

---

### D7 — `ProviderPicker` has three render states, not two

```svelte
{#if providers.length === 0}
    <!-- render nothing -->
{:else if !selectedProvider}
    <span>Server default</span>  <!-- empty-state badge -->
{:else}
    <div>...</div>               <!-- two <select> elements -->
{/if}
```

**Why:** Three distinct situations need distinct UI:

1. **No catalog yet** (`providers.length === 0`) — should never happen since
   the store is pre-seeded, but is guarded defensively to avoid rendering a
   broken empty `<select>`.
2. **Catalog loaded, no selection** (`selectedProvider === ''`) — the user is
   on the server default. A read-only badge communicates this without offering
   a confusing empty dropdown.
3. **Active selection** — both dropdowns are shown.

The empty-string convention for "server default" was chosen over `null` because
`''` is falsy in TypeScript and integrates cleanly with `|| undefined` in the
payload construction (D4).

---

### D8 — Responsive layout: inline on `md+`, row below title on mobile

```svelte
<!-- ChatHeader.svelte -->
<!-- Desktop: inline in the right action cluster -->
<div class="hidden md:flex">
    <ProviderPicker ... />
</div>

<!-- Mobile: dedicated row below the h2 -->
<div class="mt-2 flex md:hidden">
    <ProviderPicker ... />
</div>
```

**Why:** The header right cluster already contains two buttons (Prompt, Context).
On small screens adding two more `<select>` elements would overflow or wrap
badly. The mobile row solution keeps the title line clean and gives the picker
full width below it — consistent with how the prompt-override badge wraps below
the h2.

---

### D9 — `loadModes()` and `loadProviders()` run in parallel on mount

```typescript
// +page.svelte
onMount(async () => {
    void sessionStore.refresh();

    const [fetched] = await Promise.all([chatStore.loadModes(), chatStore.loadProviders()]);
    if (fetched) modes = fetched;
});
```

**Why:** The two calls are completely independent. Running them sequentially
would add unnecessary latency on cold start. `Promise.all` fires both
immediately and the page becomes interactive as soon as the slower of the two
resolves (in practice `loadModes()` since it fetches actual markdown content).

---

### D10 — `onchange` on `ProviderPicker` always passes both `(provider, model)`

```typescript
type Props = {
    onchange: (provider: string, model: string) => void;
};
```

**Why:** Provider and model are always changed as a pair from the component's
perspective — even a model-only change still needs to pass the current provider
so the parent can call `chatStore.setProvider(p)` + `chatStore.setModel(m)`
atomically. A single callback avoids the race condition that would exist if
provider and model had separate `onproviderchange` / `onmodelchange` callbacks
(the store could briefly hold `provider=anthropic, model=gemini-2.5-pro`
between two separate setter calls).

---

## 4. Data flow summary

```
Static PROVIDERS catalog
        │ (seed on module load)
        ▼
chatStore.providers ($state)
        │
        │ loadProviders() on mount
        │   → Promise.all([api.getProviders(), api.getActiveProvider()])
        │   → on success: overwrite providers, set selectedProvider, selectedModel
        │   → on failure: fall back to PROVIDERS[0].id / default_model
        ▼
chatStore.selectedProvider ($state)   chatStore.selectedModel ($state)
        │                                       │
        └───────────────┬───────────────────────┘
                        │ (props flow down)
                   ChatHeader
                        │
                  ProviderPicker
                        │ onchange(provider, model)
                        │ (events flow up)
                   +page.svelte
                        │ chatStore.setProvider(p); chatStore.setModel(m)
                        ▼
                  chatStore.sendMessage()
                        │ payload includes:
                        │   provider: selectedProvider || undefined
                        │   model:    selectedModel    || undefined
                        ▼
                  POST /api/chat
```

---

## 5. Future work / open items

| #   | Item                                                                                                                                   | When                                                                         |
| --- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 1   | Remove type duplication: make `ProviderPicker` import `ProviderInfo` from `$lib/api` once backend types are stable                     | When `/api/providers` ships                                                  |
| 2   | Per-session provider persistence: store `provider` + `model` in `ui_history` metadata so reloading a session restores the picker state | Post-backend §6.1                                                            |
| 3   | Display active model on assistant message bubble (e.g. small badge showing "claude-sonnet-4-5")                                        | Requires backend to echo model in `ChatResponse`                             |
| 4   | Hide picker when only one provider has a configured API key                                                                            | Requires `/api/providers/active` to return `available: boolean` per provider |
| 5   | Keyboard shortcut to focus the provider picker                                                                                         | Nice-to-have UX polish                                                       |
