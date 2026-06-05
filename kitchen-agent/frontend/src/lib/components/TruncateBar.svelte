<script lang="ts">
	/**
	 * TruncateBar
	 * ============
	 * Compact toolbar that lets the user quickly remove the last N turn-pairs
	 * from the conversation without opening a full editor.
	 *
	 * Shown only when there are at least 2 messages (1 complete turn-pair).
	 *
	 * Props:
	 *   totalMessages   — total number of messages in the conversation
	 *   isBusy          — true while a truncate API call is in flight
	 *   errorMessage    — non-empty string shown as an error badge
	 *   ontruncate(n)   — called with the number of pairs to remove
	 */

	import ConfirmDialog from './ConfirmDialog.svelte';

	type Props = {
		totalMessages: number;
		isBusy: boolean;
		errorMessage: string;
		ontruncate: (n: number) => void;
	};

	let { totalMessages, isBusy, errorMessage, ontruncate }: Props = $props();

	// Max pairs we can remove (each pair = user + assistant = 2 messages).
	const maxPairs = $derived(Math.floor(totalMessages / 2));

	// Confirm dialog state
	let pendingN = $state<number | null>(null);

	function handleTruncate(n: number) {
		if (isBusy || n < 1 || n > maxPairs) return;
		pendingN = n;
	}

	function doConfirm() {
		if (pendingN !== null) {
			ontruncate(pendingN);
			pendingN = null;
		}
	}
</script>

{#if maxPairs >= 1}
	<div
		data-testid="truncate-bar"
		class="flex flex-wrap items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-xs"
		role="toolbar"
		aria-label="Conversation management"
	>
		<span class="font-semibold text-muted">Remove last:</span>

		{#each [1, 2, 3, 5] as n (n)}
			{#if n <= maxPairs}
				<button
					onclick={() => handleTruncate(n)}
					disabled={isBusy}
					data-testid="truncate-btn"
					data-n={n}
					class="rounded border border-line px-2 py-0.5 font-medium text-muted transition hover:border-red-300 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
					title="Remove last {n} turn{n > 1 ? '-pairs' : '-pair'} from context"
				>
					{n} turn{n > 1 ? 's' : ''}
				</button>
			{/if}
		{/each}

		{#if maxPairs > 5}
			<button
				onclick={() => handleTruncate(maxPairs)}
				disabled={isBusy}
				data-testid="truncate-btn"
				data-n="all"
				class="rounded border border-line px-2 py-0.5 font-medium text-muted transition hover:border-red-300 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
				title="Remove all {maxPairs} turns"
			>
				All ({maxPairs})
			</button>
		{/if}

		{#if isBusy}
			<span class="ml-2 animate-pulse text-muted">Removing…</span>
		{/if}

		{#if errorMessage}
			<span class="ml-2 text-red-500" role="alert">{errorMessage}</span>
		{/if}
	</div>
{/if}

{#if pendingN !== null}
	<ConfirmDialog
		message={`Remove the last ${pendingN} turn${pendingN > 1 ? 's' : ''} (user + assistant) from this conversation?`}
		onconfirm={doConfirm}
		oncancel={() => (pendingN = null)}
	/>
{/if}
