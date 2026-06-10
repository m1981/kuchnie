<script lang="ts">
	/**
	 * SystemPromptBubble
	 * ===================
	 * Inline bubble that displays the active system prompt for the session.
	 * Supports read-only (collapsed/expanded) and editing states.
	 *
	 * Rendered as the first item in ChatMessageList, above all user messages.
	 */

	import type { AsyncState } from '$lib/types';
	import { tick } from 'svelte';

	type Props = {
		/** Current system prompt text (resolved: override ?? modeDefault). */
		text: string;
		/** Whether the displayed text is a session-specific override. */
		isOverride: boolean;
		/** Current mode label (e.g., "general", "design"). */
		modeLabel: string;
		/** Async state for loading/saving operations. */
		saveState: AsyncState<void>;
		/** Error message from the last operation, or empty. */
		errorMessage: string;
		/** Called when user saves an edited prompt. */
		onsave: (newText: string) => void;
		/** Called when user resets to mode default. */
		onreset: () => void;
	};

	let {
		text,
		isOverride,
		modeLabel,
		saveState,
		errorMessage,
		onsave,
		onreset
	}: Props = $props();

	// ── Local UI state ──────────────────────────────────────────────────
	let isEditing   = $state(false);
	let isExpanded  = $state(false);
	let draft       = $state('');
	let textareaEl  = $state<HTMLTextAreaElement | null>(null);

	// Reset editing state when text changes externally (e.g., after save).
	$effect(() => {
		if (text) {
			isEditing = false;
			draft = '';
		}
	});

	function startEditing() {
		draft = text;
		isEditing = true;
		tick().then(() => textareaEl?.focus());
	}

	function cancelEditing() {
		isEditing = false;
		draft = '';
	}

	function handleSave() {
		if (draft.trim()) {
			onsave(draft.trim());
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
			e.preventDefault();
			handleSave();
		}
		if (e.key === 'Escape') {
			e.preventDefault();
			cancelEditing();
		}
	}

	const isBusy = $derived(saveState.status === 'loading');

	// Truncate long prompts for collapsed view
	const isLong = $derived(text.length > 300);
	const displayText = $derived(isExpanded || !isLong ? text : text.slice(0, 300) + '…');
</script>

<article
	class="rounded-lg border bg-panel/60 shadow-sm {isOverride
		? 'border-l-4 border-l-accent border-line'
		: 'border-l-4 border-l-line border-line'}"
	aria-label="System prompt"
>
	<!-- Header -->
	<div class="flex items-center justify-between gap-2 border-b border-line px-4 py-2.5">
		<div class="flex items-center gap-2 min-w-0">
			<span class="text-xs font-semibold tracking-[0.14em] text-muted uppercase">
				⚙️ System Prompt
			</span>
			{#if isOverride}
				<span
					class="rounded-full border border-accent-soft bg-accent-soft px-2 py-0.5 text-[10px] font-semibold text-accent"
				>
					custom
				</span>
			{/if}
			<span class="text-[10px] text-muted">
				mode: {modeLabel}
			</span>
		</div>

		<div class="flex shrink-0 items-center gap-1.5">
			{#if !isEditing}
				<button
					onclick={startEditing}
					disabled={isBusy}
					class="rounded px-2 py-1 text-xs font-medium text-muted transition hover:bg-line hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
					title="Edit system prompt"
				>
					✏️ Edit
				</button>
				{#if isOverride}
					<button
						onclick={onreset}
						disabled={isBusy}
						class="rounded px-2 py-1 text-xs font-medium text-muted transition hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-400 disabled:opacity-50"
						title="Reset to mode default"
					>
						🔄 Reset
					</button>
				{/if}
			{/if}
		</div>
	</div>

	<!-- Body -->
	<div class="px-4 py-3">
		{#if isEditing}
			<!-- Editing state -->
			<div class="space-y-2">
				<textarea
					bind:this={textareaEl}
					bind:value={draft}
					onkeydown={handleKeydown}
					disabled={isBusy}
					rows={Math.max(4, draft.split('\n').length)}
					class="w-full resize-y rounded-md border border-accent bg-surface px-3 py-2 font-mono text-xs leading-5 text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-60"
					placeholder="Enter a custom system prompt for this session…"
					spellcheck="false"
				></textarea>

				{#if errorMessage}
					<p class="text-xs text-red-500" role="alert">{errorMessage}</p>
				{/if}

				<div class="flex items-center gap-2">
					<button
						onclick={handleSave}
						disabled={isBusy || !draft.trim()}
						class="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-accent-strong focus:outline-none focus:ring-2 focus:ring-accent disabled:cursor-not-allowed disabled:opacity-50"
					>
						{#if isBusy}
							Saving…
						{:else}
							Save <kbd class="ml-1 font-mono opacity-70">⌘↵</kbd>
						{/if}
					</button>
					<button
						onclick={cancelEditing}
						disabled={isBusy}
						class="rounded-md border border-line px-3 py-1.5 text-xs font-semibold text-muted transition hover:border-accent/60 hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
					>
						Cancel <kbd class="ml-1 font-mono opacity-70">Esc</kbd>
					</button>
				</div>
			</div>
		{:else}
			<!-- Read-only state -->
			{#if text}
				<pre
					class="whitespace-pre-wrap break-words font-mono text-xs leading-5 text-ink {isLong && !isExpanded
						? 'max-h-[4.5rem] overflow-hidden'
						: ''}">{displayText}</pre>
				{#if isLong}
					<button
						onclick={() => (isExpanded = !isExpanded)}
						class="mt-1 text-xs font-medium text-accent hover:underline focus:outline-none"
					>
						{isExpanded ? 'Show less' : 'Show more'}
					</button>
				{/if}
			{:else}
				<p class="text-xs italic text-muted">
					No system prompt set for this session.
				</p>
			{/if}
		{/if}
	</div>
</article>
