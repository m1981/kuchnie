<script lang="ts">
	/**
	 * AppendPopup
	 * ============
	 * Floating popup for the "Highlight → Add to Docs" feature.
	 *
	 * Appears at the cursor position when the user selects text anywhere on
	 * the page (outside chat bubbles), allowing them to append it to a
	 * knowledge-base Markdown file.
	 *
	 * Props:
	 *   text       — the selected text to append
	 *   x / y      — absolute position for placement
	 *   files      — list of candidate files to append to
	 *   ondismiss  — called when the popup should close
	 *   onappend   — called with (targetPath) when the user clicks "Add"
	 */

	import type { FileItem } from '$lib/api';

	type Props = {
		text: string;
		x: number;
		y: number;
		files: FileItem[];
		ondismiss: () => void;
		onappend: (target: string) => void;
	};

	let { text, x, y, files, ondismiss, onappend }: Props = $props();

	let appendTarget = $state('');
</script>

<div
	class="append-popup fixed z-50 rounded-md border border-line bg-panel p-3 shadow-lg"
	style="left: {x}px; top: {y}px; min-width: 220px; max-width: 300px;"
>
	<p class="mb-2 text-xs font-semibold text-ink">📋 Add to docs</p>
	<p class="mb-3 line-clamp-2 text-xs italic text-muted">"{text}"</p>

	<div class="flex items-center gap-2">
		<select
			bind:value={appendTarget}
			class="min-w-0 flex-1 rounded border border-line bg-surface px-2 py-1 text-xs text-ink focus:outline-none"
		>
			<option value="">Select file…</option>
			{#each files as file (file.path)}
				<option value={file.path}>{file.name}</option>
			{/each}
		</select>

		<button
			onclick={() => onappend(appendTarget)}
			disabled={!appendTarget}
			class="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-accent-strong disabled:opacity-40"
		>
			Add
		</button>

		<button
			onclick={ondismiss}
			class="rounded px-1.5 py-1 text-xs text-muted transition hover:text-ink"
		>
			✕
		</button>
	</div>
</div>
