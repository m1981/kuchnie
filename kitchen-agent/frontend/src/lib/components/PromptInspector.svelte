<script lang="ts">
	/**
	 * PromptInspector
	 * ================
	 * Collapsible <details> panel that shows the resolved system prompt for
	 * the currently selected mode.
	 *
	 * All state transitions are driven by the parent (chatStore) — this
	 * component is purely presentational and fires a callback on toggle.
	 *
	 * Props:
	 *   modeLabel      — human label of the active mode, e.g. "Design"
	 *   modeEyebrow    — sub-label, e.g. "Kitchen layout assistant"
	 *   content        — resolved prompt string (null = not yet loaded)
	 *   isLoading      — show loading spinner
	 *   error          — non-empty string = show error message
	 *   ontoggle       — called with (open: boolean) when the panel is toggled
	 */

	type Props = {
		modeLabel: string;
		modeEyebrow: string;
		content: string | null;
		isLoading: boolean;
		error: string;
		ontoggle: (open: boolean) => void;
	};

	let { modeLabel, modeEyebrow, content, isLoading, error, ontoggle }: Props = $props();

	function handleToggle(e: Event) {
		ontoggle((e.target as HTMLDetailsElement).open);
	}
</script>

<details
	class="group rounded-md border border-line bg-panel shadow-sm"
	ontoggle={handleToggle}
>
	<summary
		class="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm"
	>
		<span>
			<span class="font-semibold text-ink">System prompt</span>
			<span class="ml-2 text-muted">{modeLabel} · {modeEyebrow}</span>
		</span>
		<span class="text-xs font-medium text-accent group-open:hidden">Expand</span>
		<span class="hidden text-xs font-medium text-accent group-open:inline">Collapse</span>
	</summary>

	<div class="border-t border-line bg-surface px-4 py-3">
		{#if isLoading}
			<p class="text-sm text-muted">Loading…</p>
		{:else if error}
			<p class="text-sm text-red-500">{error}</p>
		{:else if content}
			<pre class="whitespace-pre-wrap text-sm leading-6 text-ink">{content}</pre>
		{:else}
			<p class="text-sm text-muted">Open to inspect the active system prompt.</p>
		{/if}
	</div>
</details>
