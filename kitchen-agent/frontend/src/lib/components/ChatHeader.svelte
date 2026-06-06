<script lang="ts">
	/**
	 * ChatHeader
	 * ===========
	 * Top bar showing the active mode label, session badge, and the
	 * context-sidebar toggle button.
	 *
	 * Also exposes a "Edit system prompt" button so the user can open the
	 * session-scoped system prompt editor without having to touch the .md files.
	 *
	 * Props:
	 *   modeIcon              — emoji icon for the active mode
	 *   modeLabel             — human-readable label, e.g. "Design"
	 *   sessionId             — current session UUID (first 8 chars displayed)
	 *   showRight             — whether the context sidebar is currently visible
	 *   hasSystemPromptOverride — true when a session-level override is active
	 *   ontoggleright         — callback to toggle the context sidebar
	 *   oneditprompt          — callback to open the system prompt editor
	 */

	type Props = {
		appTitle: string;
		modeIcon: string;
		modeLabel: string;
		sessionId: string;
		showRight: boolean;
		hasSystemPromptOverride: boolean;
		ontoggleright: () => void;
		oneditprompt: () => void;
	};

	let {
		appTitle,
		modeIcon,
		modeLabel,
		sessionId,
		showRight,
		hasSystemPromptOverride,
		ontoggleright,
		oneditprompt
	}: Props = $props();
</script>

<header class="border-b border-line bg-panel/92 px-4 py-3 backdrop-blur md:px-6">
	<div class="mx-auto flex max-w-5xl items-center justify-between gap-3">

		<!-- ── Left cluster: mode title + badges ──────────────────────────── -->
		<div class="min-w-0">
			<p class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">
				{appTitle}
			</p>
			<div class="mt-1 flex flex-wrap items-center gap-2">
				<h2 class="text-xl font-semibold text-ink md:text-2xl">
					{modeIcon}&nbsp;{modeLabel} mode
				</h2>
				<span
					class="rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted"
				>
					Session {sessionId.substring(0, 8)}
				</span>

				<!-- Prompt override indicator badge -->
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

		<!-- ── Right cluster: action buttons ──────────────────────────────── -->
		<div class="flex shrink-0 items-center gap-2">

			<!-- Edit system prompt button -->
			<button
				onclick={oneditprompt}
				class="hidden rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-muted transition hover:border-accent hover:text-ink lg:flex"
				title="Edit the system prompt for this session (temporary override)"
				aria-label="Edit session system prompt"
			>
				⚙️ Prompt
			</button>

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
