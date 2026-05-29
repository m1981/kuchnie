/**
 * lib/stores/chat.svelte.ts
 * ==========================
 * Rune-based store that owns ALL chat session state and async operations.
 *
 * Extracted from +page.svelte to follow the "rune-based store" pattern:
 *   - Pure TypeScript — zero Svelte template syntax.
 *   - Fully unit-testable without mounting any HTML.
 *   - +page.svelte becomes a thin layout wrapper that only renders HTML.
 *
 * Responsibilities:
 *   - Session lifecycle (new, load, fork)
 *   - Sending messages (with optimistic UI update)
 *   - Pasted image queue
 *   - Prompt mode list + detail (lazy-loaded, invalidated on mode change)
 *   - Append-to-docs (highlight → file)
 *   - Status strings for fork / append feedback
 */

import { api, type Message, type FileItem, type Note } from '$lib/api';
import { sessionStore } from '$lib/stores/sessions.svelte';
import type { AsyncState, PastedImage } from '$lib/types';

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function createChatStore() {
	// ── Session ───────────────────────────────────────────────────────────────
	let sessionId = $state<string>(crypto.randomUUID());
	let messages = $state<Message[]>([]);

	// ── Async chat state machine — replaces isLoading boolean ─────────────────
	let chatState = $state<AsyncState<void>>({ status: 'idle' });

	// ── Pasted images ─────────────────────────────────────────────────────────
	let pastedImages = $state<PastedImage[]>([]);

	// ── Prompt modes ──────────────────────────────────────────────────────────
	let selectedModeId = $state('general');
	let modesState = $state<AsyncState<void>>({ status: 'idle' });

	// ── Prompt inspector ──────────────────────────────────────────────────────
	/**
	 * Stores the detail content keyed by mode ID so switching modes while the
	 * inspector is open immediately updates the displayed content.
	 *
	 * `null` means "not yet fetched for selectedModeId".
	 */
	let promptDetailContent = $state<string | null>(null);
	let promptDetailState = $state<AsyncState<void>>({ status: 'idle' });
	/** ID for which the current promptDetailContent was fetched. */
	let promptDetailForId = $state('');
	/** Whether the inspector <details> panel is currently open. */
	let promptInspectorOpen = $state(false);

	// ── Append-to-docs ────────────────────────────────────────────────────────
	let appendFiles = $state<FileItem[]>([]);
	let appendStatus = $state('');
	let appendStatusTimer: ReturnType<typeof setTimeout> | undefined;

	// ── Fork feedback ─────────────────────────────────────────────────────────
	let forkStatus = $state('');

	// ── Context files ─────────────────────────────────────────────────────────
	let contextFiles = $state<string[]>([]);

	// ---------------------------------------------------------------------------
	// Internal helpers
	// ---------------------------------------------------------------------------

	function clearAppendStatus() {
		clearTimeout(appendStatusTimer);
		appendStatusTimer = undefined;
	}

	// ---------------------------------------------------------------------------
	// Public API
	// ---------------------------------------------------------------------------

	return {
		// ── Getters ───────────────────────────────────────────────────────────
		get sessionId() { return sessionId; },
		get messages() { return messages; },
		get chatState() { return chatState; },
		get pastedImages() { return pastedImages; },

		get selectedModeId() { return selectedModeId; },
		get modesState() { return modesState; },

		get promptDetailContent() { return promptDetailContent; },
		get promptDetailState() { return promptDetailState; },
		get promptDetailForId() { return promptDetailForId; },
		get promptInspectorOpen() { return promptInspectorOpen; },

		get appendFiles() { return appendFiles; },
		get appendStatus() { return appendStatus; },
		get forkStatus() { return forkStatus; },
		get contextFiles() { return contextFiles; },

		// ── Session ───────────────────────────────────────────────────────────

		startNewChat() {
			sessionId = crypto.randomUUID();
			messages = [];
			pastedImages = [];
			chatState = { status: 'idle' };
		},

		async loadSession(id: string) {
			try {
				const data = await api.getSession(id);
				sessionId = id;
				messages = data.ui_messages ?? [];
				chatState = { status: 'idle' };
			} catch (e) {
				console.error('Failed to load session', e);
			}
		},

		async forkSession(turnIndex: number) {
			forkStatus = '';
			try {
				const data = await api.forkSession(sessionId, turnIndex);
				await this.loadSession(data.new_session_id);
				await sessionStore.refresh();
				forkStatus = `Forked at turn ${turnIndex}`;
			} catch (e) {
				forkStatus = `Fork failed: ${e}`;
			}
		},

		// ── Messaging ─────────────────────────────────────────────────────────

		async sendMessage(text: string) {
			if (!text.trim() || chatState.status === 'loading') return;

			const imagesToSend = [...pastedImages];

			// Optimistic UI — push user message immediately
			messages.push({
				role: 'user',
				content: text,
				images: imagesToSend.map((i) => i.dataUrl)
			});
			pastedImages = [];
			chatState = { status: 'loading' };

			try {
				const data = await api.chat({
					session_id: sessionId,
					message: text,
					mode_id: selectedModeId,
					images:
						imagesToSend.length > 0
							? imagesToSend.map((i) => ({ mime_type: i.mimeType, data: i.base64 }))
							: null,
					context_files: contextFiles.length > 0 ? contextFiles : null
				});

				messages.push({
					role: 'assistant',
					content: data.text,
					tools: data.tools_used
				});

				chatState = { status: 'success', data: undefined };
				await sessionStore.refresh();
			} catch (e) {
				const msg = e instanceof Error ? e.message : 'Unknown error connecting to API.';
				messages.push({ role: 'assistant', content: `⚠️ Error: ${msg}` });
				chatState = { status: 'error', message: msg };
			}
		},

		// ── Images ────────────────────────────────────────────────────────────

		addPastedImage(img: PastedImage) {
			pastedImages = [...pastedImages, img];
		},

		removeImage(index: number) {
			pastedImages = pastedImages.filter((_, i) => i !== index);
		},

		// ── Prompt modes ──────────────────────────────────────────────────────

		async loadModes() {
			if (modesState.status === 'loading') return;
			modesState = { status: 'loading' };
			try {
				const fetched = await api.getPromptModes();
				// Re-export modes via the store so components can read them.
				// We store them as a success payload.
				modesState = { status: 'success', data: undefined };
				// Keep selectedModeId when still valid, otherwise fall back to first.
				if (fetched.length > 0 && !fetched.find((m) => m.id === selectedModeId)) {
					selectedModeId = fetched[0].id;
				}
				// Return for consumers that need the list.
				return fetched;
			} catch (e) {
				console.error('Failed to load prompt modes', e);
				modesState = { status: 'error', message: String(e) };
				return [];
			}
		},

		setSelectedModeId(id: string) {
			if (id === selectedModeId) return;
			selectedModeId = id;
			// Invalidate stale prompt detail cache.
			promptDetailContent = null;
			promptDetailState = { status: 'idle' };
			promptDetailForId = '';
			// Eagerly re-fetch if the inspector is open.
			if (promptInspectorOpen) {
				void this.loadPromptDetail();
			}
		},

		// ── Prompt inspector ──────────────────────────────────────────────────

		async loadPromptDetail() {
			if (promptDetailState.status === 'loading') return;
			if (promptDetailContent !== null && promptDetailForId === selectedModeId) return;

			promptDetailState = { status: 'loading' };
			promptDetailContent = null;
			try {
				const detail = await api.getPromptModeDetail(selectedModeId);
				promptDetailContent = detail.content;
				promptDetailForId = selectedModeId;
				promptDetailState = { status: 'success', data: undefined };
			} catch (e) {
				promptDetailState = {
					status: 'error',
					message: e instanceof Error ? e.message : 'Failed to load prompt.'
				};
			}
		},

		setPromptInspectorOpen(open: boolean) {
			promptInspectorOpen = open;
			if (open) void this.loadPromptDetail();
		},

		// ── Append-to-docs ────────────────────────────────────────────────────

		async loadAppendFiles() {
			try {
				appendFiles = await api.listFiles();
			} catch (e) {
				console.error('Failed to fetch file list', e);
			}
		},

		async appendToDoc(target: string, text: string) {
			if (!target || !text) return;
			const snippet = `\n## Snippet (from chat)\n\n${text}\n`;
			clearAppendStatus();
			try {
				await api.appendToFile(target, snippet);
				appendStatus = `✓ Added to ${target}`;
				appendStatusTimer = setTimeout(() => (appendStatus = ''), 3000);
			} catch (e) {
				appendStatus = `Failed: ${e}`;
			}
		},

		// ── Context files ─────────────────────────────────────────────────────

		setContextFiles(paths: string[]) {
			contextFiles = paths;
		},

		// ── Notes helper ──────────────────────────────────────────────────────

		formatNotesForPrompt(notes: Note[]): string {
			const lines = notes.map((note, index) => {
				const annotation = note.note.trim()
					? `\nComment: ${note.note.trim()}`
					: '';
				return [
					`### Note ${index + 1} (${note.source_role})`,
					`Selected text:`,
					`> ${note.selected_text.replace(/\n/g, '\n> ')}`,
					annotation
				].join('\n');
			});

			return [
				'Here are my selected notes with comments. Please comment and explain.',
				'',
				'## Selected notes',
				'',
				lines.join('\n\n')
			].join('\n');
		}
	};
}

// Singleton — one instance for the whole app lifecycle.
export const chatStore = createChatStore();
