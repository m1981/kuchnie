<script lang="ts">
	/**
	 * SessionTree
	 * ============
	 * Renders the full session forest from the sessionStore and wires up
	 * all tree-level callbacks (load, archive, unarchive, delete, export).
	 *
	 * Props:
	 *   activeId — currently loaded session ID (for highlight).
	 *   onload   — called when user clicks a session title.
	 */
	import { api } from '$lib/api';
	import { sessionStore } from '$lib/stores/sessions.svelte';
	import SessionTreeNode from './SessionTreeNode.svelte';

	type Props = {
		activeId: string | null;
		onload: (id: string) => void;
		isStreaming?: boolean;
	};

	let { activeId, onload, isStreaming = false }: Props = $props();

	// ── Error toast for failed operations ────────────────────────────────────
	let opError = $state('');
	let opErrorTimer: ReturnType<typeof setTimeout>;
	let archivedExpanded = $state(false);

	function showError(msg: string) {
		clearTimeout(opErrorTimer);
		opError = msg;
		opErrorTimer = setTimeout(() => (opError = ''), 4000);
	}

	// ── Shared filename helper ────────────────────────────────────────────────
	/**
	 * Derives a safe filesystem filename stem from the session's title.
	 * Strips path-unsafe characters, collapses whitespace, lowercases, caps at 64 chars.
	 * Falls back to the short session ID when no title is set.
	 */
	function safeFilename(id: string): string {
		const node = sessionStore.flat.find((n) => n.id === id);
		const rawTitle = node?.title ?? id.slice(0, 8);
		return rawTitle
			.replace(/[/\\:*?"<>|]/g, '')
			.replace(/\s+/g, '-')
			.slice(0, 64)
			.toLowerCase();
	}

	/** Trigger a browser file download from an in-memory string. */
	function triggerDownload(content: string, filename: string, mimeType: string): void {
		const blob = new Blob([content], { type: mimeType });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
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
			const msg = String(e).includes('child')
				? 'Delete children first before deleting this session.'
				: `Delete failed: ${e}`;
			showError(msg);
		}
	}

	/**
	 * GET /api/sessions/{id}/export
	 * Downloads the human-readable Markdown export (from ui_history_json).
	 * Throws on API error — SessionContextMenu surfaces it inline.
	 */
	async function handleExport(id: string): Promise<void> {
		const markdown = await api.exportSession(id);
		triggerDownload(
			markdown,
			`${safeFilename(id)}.md`,
			'text/markdown;charset=utf-8'
		);
	}

	/**
	 * GET /api/sessions/{id}/export/llm
	 * Downloads the raw LLM context window as a pretty-printed JSON file
	 * (from api_history_json) — every Content turn, Part, function call ID,
	 * and thought_signature hex exactly as Gemini received them.
	 * Throws on API error — SessionContextMenu surfaces it inline.
	 */
	async function handleExportLlm(id: string): Promise<void> {
		const data = await api.exportSessionLlm(id);
		// Pretty-print so the file is immediately human-readable in any text editor.
		const json = JSON.stringify(data, null, 2);
		triggerDownload(
			json,
			`${safeFilename(id)}.llm.json`,
			'application/json;charset=utf-8'
		);
	}

	// Derived counts for the header badges.
	const activeCount = $derived(sessionStore.flat.filter((n) => n.archived_at === null).length);
	const visibleRoots = $derived(sessionStore.tree.filter((n) => n.archived_at === null));
	const archivedRoots = $derived(sessionStore.tree.filter((n) => n.archived_at !== null));
	const archivedCount = $derived(sessionStore.flat.filter((n) => n.archived_at !== null).length);
	const activeArchived = $derived(
		activeId !== null && sessionStore.flat.some((n) => n.id === activeId && n.archived_at !== null)
	);

	$effect(() => {
		if (activeArchived) archivedExpanded = true;
	});
</script>

<!-- Header row -->
<div class="mb-2 flex items-center justify-between">
	<h2 class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">History</h2>
	<div class="flex items-center gap-1.5">
		<span class="rounded-full bg-surface px-2 py-0.5 text-xs text-muted">
			{activeCount}
		</span>
	</div>
</div>

<!-- Streaming lock -->
{#if isStreaming}
	<div
		class="mb-2 rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-700"
		role="status"
	>
		Generating response — sessions locked
	</div>
{/if}

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
	<div class="flex min-h-0 flex-col overflow-y-auto pr-1 {isStreaming ? 'pointer-events-none opacity-50' : ''}">
		<div class="space-y-0.5">
			{#each visibleRoots as root (root.id)}
				<SessionTreeNode
					node={root}
					depth={0}
					{activeId}
					{onload}
					onarchive={handleArchive}
					onunarchive={handleUnarchive}
					ondelete={handleDelete}
					onexport={handleExport}
					onexportllm={handleExportLlm}
				/>
			{/each}
		</div>

		{#if archivedRoots.length > 0}
			<div class="mt-3 border-t border-line pt-2">
				<button
					type="button"
					onclick={() => (archivedExpanded = !archivedExpanded)}
					class="group flex h-8 w-full items-center gap-2 rounded-md px-2 text-left text-xs font-semibold tracking-[0.14em] text-muted uppercase transition hover:bg-surface hover:text-ink focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none"
					aria-expanded={archivedExpanded}
				>
					<svg
						width="10"
						height="10"
						viewBox="0 0 10 10"
						fill="currentColor"
						class="shrink-0 transition-transform {archivedExpanded ? 'rotate-90' : ''}"
						aria-hidden="true"
					>
						<path d="M3 2 L7 5 L3 8 Z" />
					</svg>
					<span class="min-w-0 flex-1 truncate">Archived</span>
					<span
						class="rounded-full border border-line bg-surface px-1.5 py-0.5 text-[10px] font-medium tracking-normal text-muted"
					>
						{archivedCount}
					</span>
				</button>

				{#if archivedExpanded}
					<div class="mt-1 space-y-0.5">
						{#each archivedRoots as root (root.id)}
							<SessionTreeNode
								node={root}
								depth={0}
								{activeId}
								{onload}
								onarchive={handleArchive}
								onunarchive={handleUnarchive}
								ondelete={handleDelete}
								onexport={handleExport}
								onexportllm={handleExportLlm}
							/>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
