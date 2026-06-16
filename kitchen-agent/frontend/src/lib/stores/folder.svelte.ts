/**
 * src/lib/stores/folder.svelte.ts
 * ================================
 * Class-based rune store for folder organization.
 *
 * Owns:
 *   - the folder list fetched from GET /api/folders
 *   - session cache per folder (moved from FolderItem)
 *   - expanded state per folder (moved from FolderTree)
 *   - drag and drop state for session-to-folder assignment
 *   - CRUD operations with optimistic updates
 *
 * Design decisions:
 *   - Class-based (not closure-based) for reliable $state reactivity
 *   - Session cache co-located here to fix drag-drop refresh bug
 *   - expandedFolders uses SvelteSet for reactive .has()
 */

import { api, type Folder, type FolderCreateRequest, type FolderUpdateRequest } from '$lib/api';
import type { RemoteData, DragPayload, DropTarget, FolderSession } from '$lib/types';
import { SvelteMap, SvelteSet } from 'svelte/reactivity';

// ---------------------------------------------------------------------------
// Store class
// ---------------------------------------------------------------------------

class FolderStore {
	// ── Folder CRUD state ──────────────────────────────────────────────────
	folders = $state<Folder[]>([]);
	fetchState = $state<RemoteData<Folder[]>>({ status: 'idle' });

	// ── Session cache (moved from FolderItem) ──────────────────────────────
	// Using SvelteMap for reactive .has()/.get()/.set()/.delete()
	folderSessions = $state<SvelteMap<string, FolderSession[]>>(new SvelteMap());
	sessionsLoading = $state<SvelteMap<string, boolean>>(new SvelteMap());
	sessionsError = $state<SvelteMap<string, string | null>>(new SvelteMap());

	// ── Expanded state (moved from FolderTree) ─────────────────────────────
	expandedFolders = $state<SvelteSet<string>>(new SvelteSet());

	// ── Drag & drop state ──────────────────────────────────────────────────
	dragPayload = $state<DragPayload | null>(null);
	dropTarget = $state<DropTarget | null>(null);

	// ── Dialog state ───────────────────────────────────────────────────────
	createDialogOpen = $state(false);
	editingFolderId = $state<string | null>(null);

	// ── Error toast ────────────────────────────────────────────────────────
	error = $state<string | null>(null);
	private errorTimer: ReturnType<typeof setTimeout> | null = null;

	// ── Derived ────────────────────────────────────────────────────────────

	get sortedFolders(): Folder[] {
		return [...this.folders].sort((a, b) => a.order_index - b.order_index);
	}

	get folderMap(): Map<string, Folder> {
		return new Map(this.folders.map((f) => [f.id, f]));
	}

	get isDragging(): boolean {
		return this.dragPayload !== null;
	}

	// ── Helpers ────────────────────────────────────────────────────────────

	private showError(msg: string): void {
		if (this.errorTimer) clearTimeout(this.errorTimer);
		this.error = msg;
		this.errorTimer = setTimeout(() => {
			this.error = null;
			this.errorTimer = null;
		}, 4000);
	}

	// ── Folder CRUD ────────────────────────────────────────────────────────

	getFolderById(id: string): Folder | undefined {
		return this.folderMap.get(id);
	}

	async refresh(): Promise<void> {
		this.fetchState = { status: 'loading' };
		try {
			const response = await api.getFolders();
			this.folders = response.folders;
			this.fetchState = { status: 'success', data: this.folders };
		} catch (e) {
			const msg = e instanceof Error ? e.message : String(e);
			this.fetchState = { status: 'error', error: msg };
			this.showError(`Failed to load folders: ${msg}`);
		}
	}

	async createFolder(request: FolderCreateRequest): Promise<Folder | null> {
		try {
			const folder = await api.createFolder(request);
			this.folders = [...this.folders, folder];
			return folder;
		} catch (e) {
			const msg = e instanceof Error ? e.message : String(e);
			this.showError(`Failed to create folder: ${msg}`);
			return null;
		}
	}

	async updateFolder(id: string, request: FolderUpdateRequest): Promise<Folder | null> {
		const previous = this.folders;
		this.folders = this.folders.map((f) =>
			f.id === id ? { ...f, ...request, updated_at: new Date().toISOString() } : f
		);

		try {
			const updated = await api.updateFolder(id, request);
			this.folders = this.folders.map((f) => (f.id === id ? updated : f));
			return updated;
		} catch (e) {
			this.folders = previous;
			const msg = e instanceof Error ? e.message : String(e);
			this.showError(`Failed to update folder: ${msg}`);
			return null;
		}
	}

	async deleteFolder(id: string): Promise<boolean> {
		const previous = this.folders;
		this.folders = this.folders.filter((f) => f.id !== id);

		try {
			await api.deleteFolder(id);
			return true;
		} catch (e) {
			this.folders = previous;
			const msg = e instanceof Error ? e.message : String(e);
			this.showError(`Failed to delete folder: ${msg}`);
			return false;
		}
	}

	// ── Session Assignment ─────────────────────────────────────────────────

	async assignSession(folderId: string, sessionId: string): Promise<boolean> {
		// Optimistic: increment count
		const previous = this.folders;
		this.folders = this.folders.map((f) =>
			f.id === folderId ? { ...f, session_count: f.session_count + 1 } : f
		);

		try {
			await api.assignSessionToFolder(folderId, sessionId);
			// Invalidate cache so expanded folders re-fetch
			this.invalidateSessions(folderId);
			return true;
		} catch (e) {
			// Rollback
			this.folders = previous;
			const msg = e instanceof Error ? e.message : String(e);
			this.showError(`Failed to assign session: ${msg}`);
			return false;
		}
	}

	async unassignSession(folderId: string, sessionId: string): Promise<boolean> {
		// Optimistic: decrement count
		const previous = this.folders;
		this.folders = this.folders.map((f) =>
			f.id === folderId ? { ...f, session_count: Math.max(0, f.session_count - 1) } : f
		);

		try {
			await api.unassignSessionFromFolder(folderId, sessionId);
			this.invalidateSessions(folderId);
			return true;
		} catch (e) {
			// Rollback
			this.folders = previous;
			const msg = e instanceof Error ? e.message : String(e);
			this.showError(`Failed to unassign session: ${msg}`);
			return false;
		}
	}

	// ── Session Cache ──────────────────────────────────────────────────────

	/**
	 * Get sessions for a folder. Returns cached data or empty array.
	 * Triggers async fetch if not cached.
	 */
	getSessions(folderId: string): FolderSession[] {
		if (!this.folderSessions.has(folderId)) {
			// Trigger async fetch (fire-and-forget)
			this.fetchSessions(folderId);
			return [];
		}
		return this.folderSessions.get(folderId) ?? [];
	}

	/**
	 * Fetch sessions for a folder and cache them.
	 * Skips if already loading (prevents duplicate fetches).
	 */
	async fetchSessions(folderId: string): Promise<void> {
		if (this.sessionsLoading.get(folderId)) return;

		// SvelteMap.set() is reactive — no need to reassign the whole map
		this.sessionsLoading.set(folderId, true);
		this.sessionsError.set(folderId, null);

		try {
			const data = await api.getFolderSessions(folderId);
			this.folderSessions.set(folderId, data);
		} catch (e) {
			const msg = e instanceof Error ? e.message : String(e);
			this.sessionsError.set(folderId, msg);
		} finally {
			this.sessionsLoading.set(folderId, false);
		}
	}

	/**
	 * Invalidate sessions cache for a folder.
	 * Triggers re-fetch on next getSessions() call.
	 */
	invalidateSessions(folderId: string): void {
		this.folderSessions.delete(folderId);
	}

	// ── Expand / Collapse ──────────────────────────────────────────────────

	toggleExpand(folderId: string): void {
		if (this.expandedFolders.has(folderId)) {
			this.expandedFolders.delete(folderId);
		} else {
			this.expandedFolders.add(folderId);
		}
	}

	isExpanded(folderId: string): boolean {
		return this.expandedFolders.has(folderId);
	}

	// ── Drag & Drop ────────────────────────────────────────────────────────

	startDrag(payload: DragPayload): void {
		this.dragPayload = payload;
	}

	endDrag(): void {
		this.dragPayload = null;
		this.dropTarget = null;
	}

	setDropTarget(target: DropTarget | null): void {
		this.dropTarget = target;
	}

	async handleDrop(): Promise<void> {
		if (!this.dragPayload || !this.dropTarget) return;

		if (this.dragPayload.type === 'session' && this.dropTarget.type === 'folder') {
			await this.assignSession(this.dropTarget.id, this.dragPayload.id);
		}

		this.endDrag();
	}

	// ── Dialog State ───────────────────────────────────────────────────────

	openCreateDialog(): void {
		this.createDialogOpen = true;
	}

	closeCreateDialog(): void {
		this.createDialogOpen = false;
	}

	startEditing(folderId: string): void {
		this.editingFolderId = folderId;
	}

	stopEditing(): void {
		this.editingFolderId = null;
	}

	// ── Reset (for testing) ────────────────────────────────────────────────

	reset(): void {
		this.folders = [];
		this.fetchState = { status: 'idle' };
		this.folderSessions = new SvelteMap();
		this.sessionsLoading = new SvelteMap();
		this.sessionsError = new SvelteMap();
		this.expandedFolders = new SvelteSet();
		this.dragPayload = null;
		this.dropTarget = null;
		this.createDialogOpen = false;
		this.editingFolderId = null;
		this.error = null;
		if (this.errorTimer) {
			clearTimeout(this.errorTimer);
			this.errorTimer = null;
		}
	}
}

// Singleton
export const folderStore = new FolderStore();
