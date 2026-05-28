<script lang="ts">
	/**
	 * SessionContextMenu
	 * ==================
	 * A ⋯ button that opens a small popover with per-session actions:
	 *   Archive / Restore / Delete (with confirm step).
	 *
	 * State machine: 'closed' | 'open' | 'confirming-delete'
	 * No boolean flags — impossible states are unrepresentable.
	 */
	import { focusTrap } from '$lib/actions/focustrap';
	import type { SessionNode } from '$lib/api';

	type MenuState = 'closed' | 'open' | 'confirming-delete';

	type Props = {
		node: SessionNode;
		onarchive: (id: string) => void;
		onunarchive: (id: string) => void;
		ondelete: (id: string) => void;
	};

	let { node, onarchive, onunarchive, ondelete }: Props = $props();

	let menuState = $state<MenuState>('closed');
	let errorMsg = $state('');

	const isArchived = $derived(node.archived_at !== null);

	function open(e: MouseEvent) {
		e.stopPropagation();
		menuState = menuState === 'open' ? 'closed' : 'open';
		errorMsg = '';
	}

	function close() {
		menuState = 'closed';
		errorMsg = '';
	}

	function handleArchive(e: MouseEvent) {
		e.stopPropagation();
		close();
		if (isArchived) {
			onunarchive(node.id);
		} else {
			onarchive(node.id);
		}
	}

	function startDelete(e: MouseEvent) {
		e.stopPropagation();
		menuState = 'confirming-delete';
	}

	function confirmDelete(e: MouseEvent) {
		e.stopPropagation();
		close();
		ondelete(node.id);
	}

	function cancelDelete(e: MouseEvent) {
		e.stopPropagation();
		menuState = 'open';
	}
</script>

<!-- Click-outside backdrop (invisible, closes menu) -->
{#if menuState !== 'closed'}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-30" onclick={close}></div>
{/if}

<div class="relative">
	<button
		onclick={open}
		title="Session options"
		aria-label="Session options"
		aria-expanded={menuState !== 'closed'}
		class="flex h-5 w-5 items-center justify-center rounded text-muted opacity-0 transition
		       group-hover:opacity-100 hover:bg-line hover:text-ink focus:opacity-100 focus:outline-none
		       {menuState !== 'closed' ? 'opacity-100' : ''}"
	>
		<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
			<circle cx="8" cy="3" r="1.4" />
			<circle cx="8" cy="8" r="1.4" />
			<circle cx="8" cy="13" r="1.4" />
		</svg>
	</button>

	{#if menuState === 'open'}
		<div
			use:focusTrap
			class="absolute right-0 top-6 z-40 min-w-[148px] rounded-lg border border-line bg-panel
			       py-1 shadow-lg"
		>
			<button
				onclick={handleArchive}
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-ink
				       hover:bg-surface"
			>
				{#if isArchived}
					<span aria-hidden="true">↩</span> Restore
				{:else}
					<span aria-hidden="true">📁</span> Archive
				{/if}
			</button>

			<div class="my-1 border-t border-line"></div>

			<button
				onclick={startDelete}
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-red-600
				       hover:bg-red-50"
			>
				<span aria-hidden="true">🗑</span> Delete…
			</button>
		</div>
	{/if}

	{#if menuState === 'confirming-delete'}
		<div
			use:focusTrap
			class="absolute right-0 top-6 z-40 w-52 rounded-lg border border-red-200 bg-panel
			       p-3 shadow-lg"
		>
			<p class="mb-2 text-xs font-semibold text-ink">Delete this session?</p>
			<p class="mb-3 text-xs leading-4 text-muted">
				This is permanent. Children must be deleted first.
			</p>
			{#if errorMsg}
				<p class="mb-2 text-xs text-red-600">{errorMsg}</p>
			{/if}
			<div class="flex gap-2">
				<button
					onclick={confirmDelete}
					class="flex-1 rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white
					       hover:bg-red-700"
				>
					Delete
				</button>
				<button
					onclick={cancelDelete}
					class="flex-1 rounded border border-line px-2 py-1 text-xs text-muted
					       hover:text-ink"
				>
					Cancel
				</button>
			</div>
		</div>
	{/if}
</div>
