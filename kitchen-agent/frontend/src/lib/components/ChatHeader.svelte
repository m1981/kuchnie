<script lang="ts">
	/**
	 * ChatHeader
	 * ===========
	 * Top bar showing the session title, active mode badge, and the
	 * context-sidebar toggle button.
	 *
	 * Props:
	 *   modeIcon              — emoji icon for the active mode
	 *   modeLabel             — human-readable label, e.g. "Design"
	 *   sessionId             — current session UUID (first 8 chars displayed)
	 *   title                 — session title from database (null for new sessions)
	 *   showRight             — whether the context sidebar is currently visible
	 *   hasSystemPromptOverride — true when a session-level override is active
	 *   ontoggleright         — callback to toggle the context sidebar
	 *   onsave                — callback when user saves an edited title
	 */

	type Props = {
		modeIcon: string;
		modeLabel: string;
		sessionId: string;
		/** Session title from the database. Falls back to session ID if null. */
		title?: string | null;
		showLeft: boolean;
		showRight: boolean;
		hasSystemPromptOverride: boolean;
		ontoggleleft: () => void;
		ontoggleright: () => void;
		/** Called when user saves an edited title. */
		onsave?: (newTitle: string) => void;
	};

	let {
		modeIcon,
		modeLabel,
		sessionId,
		title = null,
		showLeft,
		showRight,
		hasSystemPromptOverride,
		ontoggleleft,
		ontoggleright,
		onsave
	}: Props = $props();

	/** Display title: use provided title, or fallback to short session ID */
	const displayTitle = $derived(title ?? `Session ${sessionId.substring(0, 8)}`);

	// ── Inline editing state ────────────────────────────────────────────────

	let isEditing = $state(false);
	let draft = $state('');
	let inputEl = $state<HTMLInputElement | null>(null);

	function startEditing() {
		draft = displayTitle;
		isEditing = true;
		// Focus the input after it renders
		requestAnimationFrame(() => {
			inputEl?.focus();
			inputEl?.select();
		});
	}

	function cancelEditing() {
		isEditing = false;
		draft = '';
	}

	function saveEditing() {
		const trimmed = draft.trim();
		if (trimmed && trimmed !== displayTitle) {
			onsave?.(trimmed);
		}
		isEditing = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			saveEditing();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelEditing();
		}
	}
</script>

<header
	class="sticky top-0 z-40 border-b border-line/50 bg-panel/80 px-4 py-3 backdrop-blur-md md:px-6"
>
	<div class="mx-auto flex max-w-5xl items-center justify-between gap-3">
		<!-- ── Left cluster: sidebar toggle + mode title ──────────────────────── -->
		<div class="flex min-w-0 items-center gap-3">
			<!-- Left sidebar toggle -->
			<button
				onclick={ontoggleleft}
				data-testid="sidebar-toggle"
				class="flex shrink-0 items-center justify-center rounded-md p-1.5 text-muted transition hover:bg-surface/80 hover:text-ink"
				title={showLeft ? 'Hide sidebar' : 'Show sidebar'}
				aria-label={showLeft ? 'Hide sidebar' : 'Show sidebar'}
			>
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					{#if showLeft}
						<rect x="3" y="3" width="18" height="18" rx="2" />
						<line x1="9" y1="3" x2="9" y2="21" />
					{:else}
						<rect x="3" y="3" width="18" height="18" rx="2" />
						<line x1="3" y1="3" x2="3" y2="21" />
					{/if}
				</svg>
			</button>

			<div class="min-w-0">
				<div class="flex flex-wrap items-center gap-2">
					{#if isEditing}
						<input
							bind:this={inputEl}
							bind:value={draft}
							onkeydown={handleKeydown}
							onblur={saveEditing}
							class="h-8 rounded-md border border-accent bg-surface px-2 text-xl font-semibold text-ink shadow-sm outline-none focus:ring-2 focus:ring-accent/50 md:text-2xl"
							maxlength="100"
						/>
					{:else}
						<button
							type="button"
							class="cursor-pointer rounded-md px-1 text-left text-xl font-semibold text-ink transition hover:bg-surface/80 md:text-2xl"
							onclick={startEditing}
							title="Click to edit title"
						>
							{displayTitle}
						</button>
					{/if}
					<span
						class="rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted"
					>
						{modeIcon}&nbsp;{modeLabel}
					</span>

					{#if hasSystemPromptOverride}
						<span
							class="rounded-full border border-accent-soft bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent"
							title="This session has a custom system prompt override active"
						>
							⚡ Prompt override
						</span>
					{/if}
				</div>
			</div>
		</div>

		<!-- ── Right cluster: action buttons ──────────────────────────────── -->
		<div class="flex shrink-0 items-center gap-2">
			<!-- Context sidebar toggle -->
			<button
				onclick={ontoggleright}
				class="hidden rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-muted transition hover:border-accent hover:text-ink lg:flex"
				title="Toggle context sidebar"
			>
				{showRight ? '▶ Hide panel' : '◀ Context'}
			</button>
		</div>
	</div>
</header>
