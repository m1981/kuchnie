<script lang="ts">
	/**
	 * ConfirmDialog
	 * ==============
	 * Accessible modal confirmation dialog.
	 * Replaces native window.confirm() for testability.
	 *
	 * Props:
	 *   message    — the question to display
	 *   onconfirm  — called when user confirms
	 *   oncancel   — called when user cancels
	 */

	type Props = {
		message: string;
		onconfirm: () => void;
		oncancel: () => void;
	};

	let { message, onconfirm, oncancel }: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') oncancel();
		if (e.key === 'Enter') onconfirm();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
	onclick={oncancel}
	onkeydown={handleKeydown}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="mx-4 max-w-sm rounded-lg bg-white p-5 shadow-xl"
		onclick={(e) => e.stopPropagation()}
		onkeydown={(e) => e.stopPropagation()}
		role="alertdialog"
		aria-modal="true"
		aria-label="Confirmation"
		tabindex="-1"
		data-testid="confirm-dialog"
	>
		<p class="text-sm text-ink">{message}</p>

		<div class="mt-4 flex justify-end gap-2">
			<button
				onclick={oncancel}
				data-testid="confirm-cancel"
				class="rounded-md border border-line px-3 py-1.5 text-sm font-medium text-muted transition hover:bg-surface focus:outline-none focus:ring-2 focus:ring-accent"
			>
				Cancel
			</button>
			<button
				onclick={onconfirm}
				data-testid="confirm-ok"
				class="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
			>
				Confirm
			</button>
		</div>
	</div>
</div>
