<script lang="ts">
	/**
	 * TokenIndicator
	 * ==============
	 * Compact token count bar showing two key numbers:
	 *
	 *   📊 Session: 4,271  │  → Input: ~127
	 *
	 * - **Session tokens** — all tokens consumed so far (from backend API)
	 * - **Input tokens** — what you'll pay when you click Send (client-side estimate)
	 * - **Context bar** — visual gauge of context window usage
	 *
	 * State comes entirely from chatStore — this component has no local state.
	 */

	import { chatStore } from '$lib/stores/chat.svelte';
	import { formatTokenCount, contextWindowPercent, contextWindowColor } from '$lib/token_estimator';

	type Props = {
		/** Current message text in the composer (for input token estimation). */
		messageText: string;
	};

	let { messageText }: Props = $props();

	// ── Derived values ──────────────────────────────────────────────────────

	const inputTokens = $derived(
		chatStore.estimateInputTokensFor(messageText)
	);

	const sessionTokens = $derived(
		chatStore.sessionTokenCount >= 0 ? chatStore.sessionTokenCount : 0
	);

	const totalTokens = $derived(sessionTokens + inputTokens);

	const pct = $derived(
		contextWindowPercent(totalTokens, chatStore.contextWindowK)
	);

	const color = $derived(contextWindowColor(pct));

	// ── Color classes for the context bar ───────────────────────────────────

	const barColorClass = $derived(
		color === 'danger'
			? 'bg-red-500'
			: color === 'warn'
				? 'bg-amber-500'
				: 'bg-accent'
	);

	const textColorClass = $derived(
		color === 'danger'
			? 'text-red-600'
			: color === 'warn'
				? 'text-amber-600'
				: 'text-muted'
	);
</script>

<div class="flex items-center gap-3 px-3 py-1.5 text-[11px] leading-none {textColorClass}">
	<!-- Context window gauge -->
	<div class="flex items-center gap-1.5">
		<div
			class="h-1.5 w-20 overflow-hidden rounded-full bg-line"
			role="progressbar"
			aria-valuenow={pct}
			aria-valuemin={0}
			aria-valuemax={100}
			aria-label="Context window usage"
		>
			<div
				class="h-full rounded-full transition-all duration-300 {barColorClass}"
				style="width: {Math.min(100, pct)}%;"
			></div>
		</div>
		<span>{pct}%</span>
	</div>

	<span class="text-line">│</span>

	<!-- Session tokens (already consumed) -->
	<span title="Tokens consumed in this session so far">
		📊 {formatTokenCount(sessionTokens)}
	</span>

	<span class="text-line">│</span>

	<!-- Input tokens (what you'll pay when you click Send) -->
	<span title="Estimated input tokens for the next message">
		→ ~{formatTokenCount(inputTokens)}
	</span>

	<!-- Fallback indicator -->
	{#if chatStore.sessionTokenFallback && chatStore.sessionTokenCount >= 0}
		<span class="text-[10px] text-muted/60" title="Token count is approximate (API fallback)">≈</span>
	{/if}
</div>
