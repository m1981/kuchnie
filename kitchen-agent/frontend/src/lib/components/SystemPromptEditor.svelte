<script lang="ts">
	/**
	 * SystemPromptEditor
	 * ===================
	 * Floating panel that lets the user view and edit the session-scoped
	 * system prompt override.
	 *
	 * Design decisions
	 * -----------------
	 * • The panel is a <dialog>-like overlay positioned in the chat scroll area,
	 *   not a true <dialog>, to keep it in the same stacking context as the rest
	 *   of the chat without portal gymnastics.
	 * • It is purely presentational — all state transitions live in chatStore.
	 * • "Clear override" reverts to the PromptManager-resolved prompt for the
	 *   selected mode without deleting the .md file.
	 *
	 * Props:
	 *   draft        — current editable text (bound from chatStore.systemPromptDraft)
	 *   isLoading    — true while loading or saving
	 *   isSaving     — true specifically during the save API call
	 *   errorMessage — non-empty string shows an error row
	 *   hasOverride  — true when a non-empty session override is currently set
	 *   onsave       — user confirmed the edit
	 *   onclear      — user wants to revert to mode default
	 *   onclose      — user dismissed the panel without saving
	 *   ondraftchange — user typed in the textarea
	 */

	type Props = {
		draft: string;
		isLoading: boolean;
		isSaving: boolean;
		errorMessage: string;
		hasOverride: boolean;
		onsave: () => void;
		onclear: () => void;
		onclose: () => void;
		ondraftchange: (text: string) => void;
	};

	let {
		draft,
		isLoading,
		isSaving,
		errorMessage,
		hasOverride,
		onsave,
		onclear,
		onclose,
		ondraftchange
	}: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}

	function handleInput(e: Event) {
		ondraftchange((e.target as HTMLTextAreaElement).value);
	}
</script>

<!-- Backdrop -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
	onclick={onclose}
	onkeydown={handleKeydown}
	role="presentation"
></div>

<!-- Panel -->
<div
	class="fixed inset-x-4 top-1/2 z-50 mx-auto max-w-2xl -translate-y-1/2 rounded-lg border border-line bg-panel shadow-2xl"
	role="dialog"
	aria-modal="true"
	aria-label="Edit session system prompt"
>
	<!-- Header -->
	<div class="flex items-center justify-between border-b border-line px-5 py-4">
		<div>
			<h2 class="text-sm font-semibold text-ink">System Prompt Override</h2>
			<p class="mt-0.5 text-xs text-muted">
				This override applies only to <strong>this session</strong>.
				It does not modify any <code class="font-mono">.md</code> file.
			</p>
		</div>
		<button
			onclick={onclose}
			class="rounded p-1 text-muted transition hover:bg-line hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent"
			aria-label="Close system prompt editor"
		>
			✕
		</button>
	</div>

	<!-- Body -->
	<div class="px-5 py-4 space-y-3">
		{#if isLoading && !isSaving}
			<div class="flex items-center gap-2 text-sm text-muted">
				<span class="h-2 w-2 animate-pulse rounded-full bg-accent"></span>
				Loading current prompt…
			</div>
		{:else}
			{#if hasOverride}
				<div class="flex items-center gap-2 rounded-md border border-accent-soft bg-accent-soft px-3 py-2 text-xs font-medium text-accent">
					⚡ This session has an active prompt override.
				</div>
			{/if}

			<label class="block">
				<span class="mb-1.5 block text-xs font-semibold text-muted uppercase tracking-wide">
					System prompt (Markdown)
				</span>
				<textarea
					value={draft}
					oninput={handleInput}
					disabled={isSaving}
					rows={12}
					class="w-full resize-y rounded-md border border-line bg-surface px-3 py-2 font-mono text-xs leading-5 text-ink placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60"
					placeholder="Enter a custom system prompt for this session…&#10;&#10;Leave empty to use the mode-resolved default."
					spellcheck="false"
				></textarea>
			</label>

			{#if errorMessage}
				<p class="text-xs text-red-500" role="alert">{errorMessage}</p>
			{/if}
		{/if}
	</div>

	<!-- Footer -->
	<div class="flex items-center justify-between border-t border-line px-5 py-3">
		<div class="flex items-center gap-2">
			{#if hasOverride}
				<button
					onclick={onclear}
					disabled={isSaving || isLoading}
					class="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-muted transition hover:border-red-300 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-400 disabled:opacity-50"
					title="Remove override — revert to the mode-resolved default"
				>
					🗑 Clear override
				</button>
			{/if}
		</div>

		<div class="flex items-center gap-2">
			<button
				onclick={onclose}
				disabled={isSaving}
				class="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-muted transition hover:border-accent/60 hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
			>
				Cancel
			</button>
			<button
				onclick={onsave}
				disabled={isSaving || isLoading}
				class="rounded-md bg-accent px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-strong focus:outline-none focus:ring-2 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
			>
				{isSaving ? 'Saving…' : 'Apply to session'}
			</button>
		</div>
	</div>
</div>
