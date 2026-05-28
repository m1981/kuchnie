<script lang="ts">
	/**
	 * SessionTree
	 * ============
	 * Renders the full session forest from the sessionStore and wires up
	 * all tree-level callbacks (load, archive, unarchive, delete).
	 *
	 * Props:
	 *   activeId    — currently loaded session ID (for highlight).
	 *   onload      — called when user clicks a session title.
	 *   onnewsession — called when user clicks "New chat".
	 */
	import { sessionStore } from '$lib/stores/sessions.svelte';
	import SessionTreeNode from './SessionTreeNode.svelte';

	type Props = {
		activeId: string | null;
		onload: (id: string) => void;
	};

	let { activeId, onload }: Props = $props();

	// ── Error toast for failed operations ────────────────────────────────────
	let opError = $state('');
	let opErrorTimer: ReturnType<typeof setTimeout>;

	function showError(msg: string) {
		clearTimeout(opErrorTimer);
		opError = msg;
		opErrorTimer = setTimeout(() => (opError = ''), 4000);
	}

	// ── Handlers passed to every SessionTreeNode ─────────────────────────────
	async function handleArchive(id: string) {
		try {
			await sessionStore.archive(id);
		} catch (e) {
			showError(`Archive failed: ${e}`);
		}
	}

	async function handleUnarchive(id: string) {
		try {
			await sessionStore.unarchive(id);
		} catch (e) {
			showError(`Restore failed: ${e}`);
		}
	}

	async function handleDelete(id: string) {
		try {
			await sessionStore.delete(id);
		} catch (e) {
			// 409 = has children; surface a clear message.
			const msg = String(e).includes('child')
				? 'Delete children first before deleting this session.'
				: `Delete failed: ${e}`;
			showError(msg);
		}
	}

	// Derived counts for the header badge.
	const total = $derived(sessionStore.flat.length);
	const visibleRoots = $derived(
		sessionStore.tree.filter((n) => n.archived_at === null)
	);
	const archivedCount = $derived(
		sessionStore.flat.filter((n) => n.archived_at !== null).length
	);
</script>

<!-- Header row -->
<div class="mb-2 flex items-center justify-between">
	<h2 class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">History</h2>
	<div class="flex items-center gap-1.5">
		{#if archivedCount > 0}
			<span
				class="rounded-full border border-line bg-surface px-1.5 py-0.5 text-[10px] text-muted"
				title="{archivedCount} archived"
			>
				{archivedCount} archived
			</span>
		{/if}
		<span class="rounded-full bg-surface px-2 py-0.5 text-xs text-muted">
			{total}
		</span>
	</div>
</div>

<!-- Error toast -->
{#if opError}
	<div
		class="mb-2 rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs text-red-700"
		role="alert"
	>
		{opError}
	</div>
{/if}

<!-- Loading state -->
{#if sessionStore.fetchState.status === 'loading'}
	<div class="space-y-1.5">
		{#each [1, 2, 3] as i (i)}
			<div class="h-8 animate-pulse rounded-md bg-line"></div>
		{/each}
	</div>

<!-- Error state -->
{:else if sessionStore.fetchState.status === 'error'}
	<p class="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
		{sessionStore.fetchState.error}
	</p>

<!-- Empty state -->
{:else if sessionStore.tree.length === 0}
	<p class="rounded-md border border-dashed border-line bg-surface p-3 text-sm text-muted">
		No saved conversations yet.
	</p>

<!-- Tree -->
{:else}
	<div class="space-y-0.5 overflow-y-auto pr-1">
		<!-- Active / non-archived roots first, then archived (greyed) roots -->
		{#each sessionStore.tree as root (root.id)}
			<SessionTreeNode
				node={root}
				depth={0}
				{activeId}
				{onload}
				onarchive={handleArchive}
				onunarchive={handleUnarchive}
				ondelete={handleDelete}
			/>
		{/each}
	</div>
{/if}
