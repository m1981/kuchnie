# Layout Implementation Plan — Claude-Inspired Improvements

## Scope
Apply Claude.ai's polished layout patterns to our warm color scheme while maintaining our feature set.

## Priority 1: Input Area (Most Impact)

### Current State
```css
.composer-box {
    border: 1px solid #dadce0;
    border-radius: 12px;
    background: #fff;
}
```

### Target (Claude-inspired)
```css
.composer-box {
    border: 1px solid transparent;
    border-radius: 20px;
    background: var(--color-panel);
    box-shadow: 
        0 0.25rem 1.25rem rgba(39, 35, 31, 0.08),
        0 0 0 0.5px rgba(222, 214, 202, 0.3);
    transition: box-shadow 0.2s;
}

.composer-box:hover {
    box-shadow: 
        0 0.25rem 1.25rem rgba(39, 35, 31, 0.1),
        0 0 0 0.5px rgba(222, 214, 202, 0.5);
}

.composer-box:focus-within {
    box-shadow: 
        0 0.25rem 1.25rem rgba(39, 35, 31, 0.12),
        0 0 0 0.5px rgba(138, 105, 57, 0.4);
}
```

---

## Priority 2: Header Sticky + Blur

### Current State
```html
<header class="border-b border-line bg-panel/92 px-4 py-3 backdrop-blur md:px-6">
```

### Target (Claude-inspired)
```html
<header class="sticky top-0 z-40 flex w-full items-center border-b border-line bg-panel/80 px-4 py-3 backdrop-blur-md md:px-6">
```

**Key changes:**
- Add `sticky top-0` for sticky behavior
- Add `z-40` for proper layering
- Increase backdrop blur to `blur-md`
- Reduce background opacity to `80%` for more blur effect

---

## Priority 3: Sidebar Transitions

### Current State
```html
<aside class="absolute inset-y-0 left-0 z-30 shrink-0 border-r border-line bg-panel p-4 shadow-lg transition-transform duration-200 lg:relative lg:shadow-[1px_0_0_rgba(38,35,31,0.03)] ...">
```

### Target (Claude-inspired)
```html
<aside class="fixed lg:sticky z-30 h-screen shrink-0 border-r border-line bg-panel p-4 transition-[transform,opacity] duration-35 delay-75 lg:relative ...">
```

**Key changes:**
- Use `fixed` on mobile, `sticky` on desktop
- Use `h-screen` + `100dvh` for proper height
- Faster transition: `35ms` with `75ms` delay
- Add opacity transition for smoother feel

---

## Priority 4: Message Bubbles

### Current User Message
```html
<div class="max-w-[min(760px,88%)] rounded-md bg-ink px-4 py-3 text-white shadow-sm">
```

### Target (Claude-inspired)
```html
<div class="max-w-[85%] rounded-xl bg-ink/5 px-4 py-2.5 text-ink shadow-sm">
```

**Key changes:**
- Larger border radius: `rounded-xl` (12px)
- Lighter background: `bg-ink/5` (5% opacity)
- Text stays dark (our warm scheme)
- Slightly less padding

### Current Assistant Message
```html
<div class="w-full max-w-4xl rounded-md border border-line bg-panel p-4 shadow-sm">
```

### Target (Claude-inspired)
```html
<div class="w-full max-w-3xl rounded-xl border border-line/50 bg-panel/80 p-4 shadow-sm">
```

**Key changes:**
- Max width: `max-w-3xl` (768px) instead of `max-w-4xl`
- Lighter border: `border-line/50`
- Semi-transparent background: `bg-panel/80`

---

## Priority 5: Z-Index Management

### Current Issues
- Inconsistent z-index values
- Some elements overlapping incorrectly

### Target System
```
Background grid:    z-0 (decorative)
Main content:       z-10 (default)
Chat input:         z-20 (sticky bottom)
Sidebar:            z-30 (above content)
Header:             z-40 (above sidebar)
Resize divider:     z-50 (above everything)
Modal overlays:     z-60 (highest)
```

---

## Priority 6: Spacing Constants

### Adopt Claude's Spacing
| Element | Current | Target | Tailwind |
|---------|---------|--------|----------|
| Header height | auto | 48px | `h-12` |
| Sidebar item | varied | 32px | `h-8` |
| Sidebar padding | 16px | 6px 16px | `py-1.5 px-4` |
| Input radius | 12px | 20px | `rounded-[20px]` |
| Input margin | 16px | 14px | `m-3.5` |
| Chat max-width | 1024px | 768px | `max-w-3xl` |

---

## Implementation Order

1. **Input area** — Highest visual impact
2. **Header sticky** — Immediate UX improvement
3. **Z-index cleanup** — Prevents future issues
4. **Message bubbles** — Polish chat appearance
5. **Sidebar transitions** — Smooth animations
6. **Spacing constants** — Consistency pass

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/routes/layout.css` | Add CSS custom properties, update base styles |
| `src/lib/components/ChatComposer.svelte` | Input box styling |
| `src/lib/components/ChatHeader.svelte` | Sticky + blur |
| `src/lib/components/ChatMessageList.svelte` | Message bubbles |
| `src/routes/chat/[id]/+page.svelte` | Z-index, layout structure |
| `src/lib/components/SidebarLayout.svelte` | Sidebar transitions |
