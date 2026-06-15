/**
 * src/lib/stores/folder.svelte.ts
 * ================================
 * Rune-based store for folder organization.
 *
 * Owns:
 *   - the folder list fetched from GET /api/folders
 *   - drag and drop state for session-to-folder assignment
 *   - CRUD operations with optimistic updates
 *
 * Drag & Drop design:
 *   - Sessions can be dragged onto folders in the sidebar
 *   - Folders can be reordered by dragging
 *   - Visual feedback via CSS classes during drag
 */

import { api, type Folder, type FolderCreateRequest, type FolderUpdateRequest } from '$lib/api';

// ---------------------------------------------------------------------------
// RemoteData state machine
// ---------------------------------------------------------------------------

type RemoteData<T> =
	| { status: 'idle' }
	| { status: 'loading' }
	| { status: 'error'; error: string }
	| { status: 'success'; data: T };

// ---------------------------------------------------------------------------
// Drag & Drop types
// ---------------------------------------------------------------------------

export type DragPayload = {
	type: 'session' | 'folder';
	id: string;
	title: string;
};

export type DropTarget = {
	type: 'folder';
	id: string;
};

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function createFolderStore() {
	// ── State ──────────────────────────────────────────────────────────────────
	let folders = $state<Folder[]>([]);
	let fetchState = $state<RemoteData<Folder[]>>({ status: 'idle' });

	// Drag & drop state
	let dragPayload = $state<DragPayload | null>(null);
	let dropTarget = $state<DropTarget | null>(null);
	const isDragging = $derived(dragPayload !== null);

	// Dialog state
	let createDialogOpen = $state(false);
	let editingFolderId = $state<string | null>(null);

	// Error toast
	let error = $state<string | null>(null);
	let errorTimer = $state<ReturnType<typeof setTimeout> | null>(null);

	// ── Derived ────────────────────────────────────────────────────────────────
	const sortedFolders = $derived([...folders].sort((a, b) => a.order_index - b.order_index));

	const folderMap = $derived(new Map(folders.map((f) => [f.id, f])));

	// ── Helpers ────────────────────────────────────────────────────────────────

	function showError(msg: string) {
		if (errorTimer) clearTimeout(errorTimer);
		error = msg;
		errorTimer = setTimeout(() => {
			error = null;
			errorTimer = null;
		}, 4000);
	}

	// ── Public API ─────────────────────────────────────────────────────────────

	return {
		// ── Reads ──────────────────────────────────────────────────────────────
		get folders() {
			return folders;
		},
		get sortedFolders() {
			return sortedFolders;
		},
		get fetchState() {
			return fetchState;
		},
		get isDragging() {
			return isDragging;
		},
		get dragPayload() {
			return dragPayload;
		},
		get dropTarget() {
			return dropTarget;
		},
		get createDialogOpen() {
			return createDialogOpen;
		},
		get editingFolderId() {
			return editingFolderId;
		},
		get error() {
			return error;
		},

		getFolderById(id: string): Folder | undefined {
			return folderMap.get(id);
		},

		// ── Fetch ──────────────────────────────────────────────────────────────

		async refresh() {
			fetchState = { status: 'loading' };
			try {
				const response = await api.getFolders();
				folders = response.folders;
				fetchState = { status: 'success', data: folders };
			} catch (e) {
				const msg = e instanceof Error ? e.message : String(e);
				fetchState = { status: 'error', error: msg };
				showError(`Failed to load folders: ${msg}`);
			}
		},

		// ── CRUD ───────────────────────────────────────────────────────────────

		async createFolder(request: FolderCreateRequest): Promise<Folder | null> {
			try {
				const folder = await api.createFolder(request);
				// Optimistic: add to local state
				folders = [...folders, folder];
				return folder;
			} catch (e) {
				const msg = e instanceof Error ? e.message : String(e);
				showError(`Failed to create folder: ${msg}`);
				return null;
			}
		},

		async updateFolder(id: string, request: FolderUpdateRequest): Promise<Folder | null> {
			// Optimistic: update local state
			const previous = folders;
			folders = folders.map((f) =>
				f.id === id ? { ...f, ...request, updated_at: new Date().toISOString() } : f
			);

			try {
				const updated = await api.updateFolder(id, request);
				// Replace with server response (has correct timestamps)
				folders = folders.map((f) => (f.id === id ? updated : f));
				return updated;
			} catch (e) {
				// Rollback
				folders = previous;
				const msg = e instanceof Error ? e.message : String(e);
				showError(`Failed to update folder: ${msg}`);
				return null;
			}
		},

		async deleteFolder(id: string): Promise<boolean> {
			// Optimistic: remove from local state
			const previous = folders;
			folders = folders.filter((f) => f.id !== id);

			try {
				await api.deleteFolder(id);
				return true;
			} catch (e) {
				// Rollback
				folders = previous;
				const msg = e instanceof Error ? e.message : String(e);
				showError(`Failed to delete folder: ${msg}`);
				return false;
			}
		},

		// ── Session Assignment ─────────────────────────────────────────────────

		async assignSession(folderId: string, sessionId: string): Promise<boolean> {
			// Optimistic: increment count
			const previous = folders;
			folders = folders.map((f) =>
				f.id === folderId ? { ...f, session_count: f.session_count + 1 } : f
			);

			try {
				await api.assignSessionToFolder(folderId, sessionId);
				return true;
			} catch (e) {
				// Rollback
				folders = previous;
				const msg = e instanceof Error ? e.message : String(e);
				showError(`Failed to assign session: ${msg}`);
				return false;
			}
		},

		async unassignSession(folderId: string, sessionId: string): Promise<boolean> {
			// Optimistic: decrement count
			const previous = folders;
			folders = folders.map((f) =>
				f.id === folderId ? { ...f, session_count: Math.max(0, f.session_count - 1) } : f
			);

			try {
				await api.unassignSessionFromFolder(folderId, sessionId);
				return true;
			} catch (e) {
				// Rollback
				folders = previous;
				const msg = e instanceof Error ? e.message : String(e);
				showError(`Failed to unassign session: ${msg}`);
				return false;
			}
		},

		// ── Drag & Drop ────────────────────────────────────────────────────────

		startDrag(payload: DragPayload) {
			dragPayload = payload;
		},

		endDrag() {
			dragPayload = null;
			dropTarget = null;
		},

		setDropTarget(target: DropTarget | null) {
			dropTarget = target;
		},

		/**
		 * Complete a drop operation.
		 * If dragging a session onto a folder, assign it.
		 * If dragging a folder onto a folder (reorder), update order_index.
		 */
		async handleDrop() {
			if (!dragPayload || !dropTarget) return;

			if (dragPayload.type === 'session' && dropTarget.type === 'folder') {
				await this.assignSession(dropTarget.id, dragPayload.id);
			}

			// Clear drag state
			this.endDrag();
		},

		// ── Dialog State ───────────────────────────────────────────────────────

		openCreateDialog() {
			createDialogOpen = true;
		},

		closeCreateDialog() {
			createDialogOpen = false;
		},

		startEditing(folderId: string) {
			editingFolderId = folderId;
		},

		stopEditing() {
			editingFolderId = null;
		}
	};
}

// Singleton
export const folderStore = createFolderStore();
