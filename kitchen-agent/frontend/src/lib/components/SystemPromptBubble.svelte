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
				<!-- Gear SVG icon -->
				<svg class="inline-block h-3.5 w-3.5 mr-1 -mt-px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="12" r="3" />
					<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
				</svg>
				System Prompt
			</span>
			{#if isOverride}
				<span
					class="rounded-full border border-accent-soft bg-accent-soft px-2 py-0.5 text-[10px] font-medium text-accent"
				>
					custom
				</span>
			{/if}
			<span
				class="rounded-full border border-line bg-surface px-2 py-0.5 text-[10px] font-medium text-muted"
			>
				{modeLabel}
			</span>
		</div>

		<div class="flex shrink-0 items-center gap-1">
			{#if !isEditing}
				<button
					onclick={startEditing}
					disabled={isBusy}
					class="action-btn action-btn-assistant"
					title="Edit system prompt"
					aria-label="Edit system prompt"
				>
					<!-- Pencil SVG icon -->
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
						<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
					</svg>
				</button>
				{#if isOverride}
					<button
						onclick={onreset}
						disabled={isBusy}
						class="action-btn action-btn-assistant"
						title="Reset to mode default"
						aria-label="Reset to mode default"
					>
						<!-- Refresh/undo SVG icon -->
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
							<path d="M3 3v5h5" />
						</svg>
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

<style>
	.action-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 6px;
		transition: all 0.15s ease;
	}

	.action-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.action-btn-assistant {
		color: var(--color-muted, #6b7280);
	}

	.action-btn-assistant:hover:not(:disabled) {
		background: var(--color-line, #e5e7eb);
		color: var(--color-ink, #111827);
	}
</style>
