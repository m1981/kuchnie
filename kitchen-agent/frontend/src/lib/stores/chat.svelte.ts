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
 *   - Provider / model selection (loaded from /api/providers, falls back to
 *     static PROVIDERS catalog when the endpoint is not yet available)
 *   - Status strings for fork feedback
 *   - In-session message editing / deletion / truncation
 *   - Session-scoped system-prompt override
 */

import { api, type Message, type Note } from '$lib/api';
import { PROVIDERS, type ProviderInfo }  from '$lib/providers';
import { sessionStore }                  from '$lib/stores/sessions.svelte';
import type { AsyncState, PastedImage }  from '$lib/types';

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function createChatStore() {
	// ── Session ───────────────────────────────────────────────────────────────
	let sessionId = $state<string>(crypto.randomUUID());
	let messages  = $state<Message[]>([]);

	// ── Async chat state machine — replaces isLoading boolean ─────────────────
	let chatState = $state<AsyncState<void>>({ status: 'idle' });

	// ── Pasted images ─────────────────────────────────────────────────────────
	let pastedImages = $state<PastedImage[]>([]);

	// ── Prompt modes ──────────────────────────────────────────────────────────
	let selectedModeId = $state('general');
	let modesState     = $state<AsyncState<void>>({ status: 'idle' });

	// ── Prompt inspector ──────────────────────────────────────────────────────
	/**
	 * Stores the detail content keyed by mode ID so switching modes while the
	 * inspector is open immediately updates the displayed content.
	 * `null` means "not yet fetched for selectedModeId".
	 */
	let promptDetailContent = $state<string | null>(null);
	let promptDetailState   = $state<AsyncState<void>>({ status: 'idle' });
	/** ID for which the current promptDetailContent was fetched. */
	let promptDetailForId   = $state('');
	/** Whether the inspector <details> panel is currently open. */
	let promptInspectorOpen = $state(false);

	// ── Fork feedback ─────────────────────────────────────────────────────────
	let forkStatus = $state('');

	// ── Context files ─────────────────────────────────────────────────────────
	let contextFiles = $state<string[]>([]);

	// ── Message editor ────────────────────────────────────────────────────────
	/**
	 * turn_id of the message currently being edited in the inline editor.
	 * null = no edit in progress.
	 * Using turn_id (stable UUID) instead of array index (shifts on delete).
	 */
	let editingTurnId  = $state<string | null>(null);
	/** Draft text while editing a message. */
	let editDraft      = $state<string>('');
	/** Async state for edit/delete/truncate operations. */
	let editState      = $state<AsyncState<void>>({ status: 'idle' });

	// ── System prompt editor ──────────────────────────────────────────────────
	/** The session-scoped system prompt override loaded from the backend. */
	let sessionSystemPrompt     = $state<string | null>(null);
	/** Whether the system prompt editor panel is open. */
	let systemPromptEditorOpen  = $state(false);
	/** Draft while the user edits the system prompt. */
	let systemPromptDraft       = $state<string>('');
	/** Async state for system prompt save. */
	let systemPromptState       = $state<AsyncState<void>>({ status: 'idle' });

	// ── App branding ──────────────────────────────────────────────────────────
	/**
	 * Domain title loaded from GET /api/app-info (APP_TITLE env var).
	 * Generic default used until the network call completes so the UI
	 * always has something sensible to display.
	 */
	let appTitle       = $state('Agentic Workspace');
	let appDescription = $state('');

	// ── Provider / model selection ────────────────────────────────────────────
	/**
	 * The full provider catalog.  Populated by loadProviders() on app mount.
	 * Pre-seeded from the static PROVIDERS catalog so the picker renders
	 * immediately even before the network call completes.
	 */
	let providers        = $state<ProviderInfo[]>(PROVIDERS);
	/**
	 * The user's currently selected provider id.
	 * Empty string = "use server default".
	 * Initialised after loadProviders() fetches /api/providers/active.
	 */
	let selectedProvider = $state<string>('');
	/**
	 * The user's currently selected model id within the active provider.
	 * Empty string = "use provider default".
	 * Reset to provider default whenever the user switches provider.
	 */
	let selectedModel    = $state<string>('');

	// ---------------------------------------------------------------------------
	// Public API
	// ---------------------------------------------------------------------------

	return {
		// ── Getters ───────────────────────────────────────────────────────────
		get sessionId()           { return sessionId; },
		get messages()            { return messages; },
		get chatState()           { return chatState; },
		get pastedImages()        { return pastedImages; },

		get selectedModeId()      { return selectedModeId; },
		get modesState()          { return modesState; },

		get promptDetailContent() { return promptDetailContent; },
		get promptDetailState()   { return promptDetailState; },
		get promptDetailForId()   { return promptDetailForId; },
		get promptInspectorOpen() { return promptInspectorOpen; },

		get forkStatus()          { return forkStatus; },
		get contextFiles()        { return contextFiles; },

		// Message editor
		get editingTurnId()       { return editingTurnId; },
		get editDraft()           { return editDraft; },
		get editState()           { return editState; },

		// System prompt editor
		get sessionSystemPrompt()    { return sessionSystemPrompt; },
		get systemPromptEditorOpen() { return systemPromptEditorOpen; },
		get systemPromptDraft()      { return systemPromptDraft; },
		get systemPromptState()      { return systemPromptState; },

		// App branding
		get appTitle()       { return appTitle; },
		get appDescription() { return appDescription; },

		// Provider / model
		get providers()        { return providers; },
		get selectedProvider() { return selectedProvider; },
		get selectedModel()    { return selectedModel; },

		// ── Session ───────────────────────────────────────────────────────────

		startNewChat() {
			sessionId             = crypto.randomUUID();
			messages              = [];
			pastedImages          = [];
			chatState             = { status: 'idle' };
			editingTurnId         = null;
			editDraft             = '';
			editState             = { status: 'idle' };
			sessionSystemPrompt   = null;
			systemPromptDraft     = '';
			systemPromptEditorOpen = false;
			systemPromptState     = { status: 'idle' };
			// Provider / model selection intentionally kept across new chats —
			// the user's choice should persist until they manually change it.
		},

		async loadSession(id: string) {
			try {
				const data = await api.getSession(id);
				sessionId     = id;
				messages      = data.ui_messages ?? [];
				chatState     = { status: 'idle' };
				editingTurnId = null;
				editDraft     = '';
				editState     = { status: 'idle' };
				// Reset system prompt editor
				systemPromptEditorOpen = false;
				systemPromptDraft      = '';
				sessionSystemPrompt    = null;
				systemPromptState      = { status: 'idle' };
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

			const imagesToSend      = [...pastedImages];
			// Snapshot context files before clearing so the optimistic bubble
			// and the API call both use the same list.
			const contextFilesToSend = [...contextFiles];

			// Optimistic UI — push user message immediately, including the
			// basenames of any attached context files so the bubble renders them
			// straight away without waiting for the API response.
			const optimisticMsg: import('$lib/api').Message = {
				role:   'user',
				content: text,
				images: imagesToSend.map((i) => i.dataUrl),
				...(contextFilesToSend.length > 0
					? { context_files: contextFilesToSend.map((p) => p.split('/').pop() ?? p) }
					: {})
			};
			messages.push(optimisticMsg);
			pastedImages = [];
			// Clear selected context files after snapshot — one-shot injection.
			contextFiles = [];
			chatState    = { status: 'loading' };

			try {
				const data = await api.chat({
					session_id:    sessionId,
					message:       text,
					mode_id:       selectedModeId,
					images:
						imagesToSend.length > 0
							? imagesToSend.map((i) => ({ mime_type: i.mimeType, data: i.base64 }))
							: null,
					context_files: contextFilesToSend.length > 0 ? contextFilesToSend : null,
					// Only include provider/model when the user has made an explicit
					// selection — omitting them lets the server use its configured defaults.
					provider: selectedProvider || undefined,
					model:    selectedModel    || undefined
				});

				messages.push({
					role:  'assistant',
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
				modesState = { status: 'success', data: undefined };
				// Keep selectedModeId when still valid, otherwise fall back to first.
				if (fetched.length > 0 && !fetched.find((m) => m.id === selectedModeId)) {
					selectedModeId = fetched[0].id;
				}
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
			promptDetailState   = { status: 'idle' };
			promptDetailForId   = '';
			// Eagerly re-fetch if the inspector is open.
			if (promptInspectorOpen) void this.loadPromptDetail();
		},

		// ── Prompt inspector ──────────────────────────────────────────────────

		async loadPromptDetail() {
			if (promptDetailState.status === 'loading') return;
			if (promptDetailContent !== null && promptDetailForId === selectedModeId) return;

			promptDetailState   = { status: 'loading' };
			promptDetailContent = null;
			try {
				const detail        = await api.getPromptModeDetail(selectedModeId);
				promptDetailContent = detail.content;
				promptDetailForId   = selectedModeId;
				promptDetailState   = { status: 'success', data: undefined };
			} catch (e) {
				promptDetailState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Failed to load prompt.'
				};
			}
		},

		setPromptInspectorOpen(open: boolean) {
			promptInspectorOpen = open;
			if (open) void this.loadPromptDetail();
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
		},

		// ── Message editor ────────────────────────────────────────────────────

		/**
		 * Open the inline editor for the message identified by turn_id.
		 * Using turn_id instead of array index prevents stale-index bugs after
		 * a delete shifts the array.
		 */
		startEditing(turnId: string) {
			const msg = messages.find(m => m.turn_id === turnId);
			if (!msg) return;
			editingTurnId = turnId;
			editDraft     = msg.content;
			editState     = { status: 'idle' };
		},

		/** Cancel inline edit without saving. */
		cancelEditing() {
			editingTurnId = null;
			editDraft     = '';
			editState     = { status: 'idle' };
		},

		/** Update the draft text while the user types in the inline editor. */
		setEditDraft(text: string) {
			editDraft = text;
		},

		/**
		 * Save the current editDraft to the backend and update local state.
		 * Uses turn_id for the API call — position-independent.
		 * Closes the editor on success.
		 */
		async saveEdit() {
			if (!editingTurnId || !editDraft.trim()) return;
			const turnId = editingTurnId;
			editState = { status: 'loading' };
			try {
				await api.editMessage(sessionId, turnId, editDraft);
				// Optimistic local update — find by turn_id, not by index.
				const idx = messages.findIndex(m => m.turn_id === turnId);
				if (idx !== -1) {
					messages[idx] = { ...messages[idx], content: editDraft };
				}
				editingTurnId = null;
				editDraft     = '';
				editState     = { status: 'success', data: undefined };
			} catch (e) {
				editState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Edit failed.'
				};
			}
		},

		/**
		 * Delete a single message identified by turn_id.
		 * Optionally deletes the paired next message.
		 * Reloads the full session from the backend to stay in sync.
		 */
		async deleteMessage(turnId: string, deletePair = false) {
			editState = { status: 'loading' };
			try {
				await api.deleteMessage(sessionId, turnId, deletePair);
				// Reload messages from backend to get the authoritative state.
				const data = await api.getSession(sessionId);
				messages  = data.ui_messages ?? [];
				editState = { status: 'success', data: undefined };
			} catch (e) {
				editState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Delete failed.'
				};
			}
		},

		/**
		 * Truncate the last n turn-pairs from the conversation.
		 * Reloads the session from the backend after truncation.
		 */
		async truncateMessages(n: number) {
			if (n < 1) return;
			editState = { status: 'loading' };
			try {
				await api.truncateMessages(sessionId, n);
				const data = await api.getSession(sessionId);
				messages  = data.ui_messages ?? [];
				editState = { status: 'success', data: undefined };
				await sessionStore.refresh();
			} catch (e) {
				editState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Truncate failed.'
				};
			}
		},

		// ── System prompt editor ──────────────────────────────────────────────

		/**
		 * Open the system prompt editor panel and load the current value from
		 * the backend (or use the cached value if already loaded).
		 */
		async openSystemPromptEditor() {
			systemPromptEditorOpen = true;
			if (sessionSystemPrompt !== null) {
				// Already loaded — just pre-fill the draft.
				systemPromptDraft = sessionSystemPrompt ?? '';
				return;
			}
			systemPromptState = { status: 'loading' };
			try {
				const data        = await api.getSystemPrompt(sessionId);
				sessionSystemPrompt = data.system_prompt;
				systemPromptDraft   = data.system_prompt ?? '';
				systemPromptState   = { status: 'success', data: undefined };
			} catch (e) {
				systemPromptState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Failed to load system prompt.'
				};
			}
		},

		closeSystemPromptEditor() {
			systemPromptEditorOpen = false;
		},

		setSystemPromptDraft(text: string) {
			systemPromptDraft = text;
		},

		/**
		 * Save the system prompt draft to the backend.
		 * Closes the editor panel on success.
		 */
		async saveSystemPrompt() {
			systemPromptState = { status: 'loading' };
			try {
				await api.updateSystemPrompt(sessionId, systemPromptDraft);
				sessionSystemPrompt    = systemPromptDraft;
				systemPromptEditorOpen = false;
				systemPromptState      = { status: 'success', data: undefined };
			} catch (e) {
				systemPromptState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Failed to save system prompt.'
				};
			}
		},

		/** Clear the session-scoped system prompt override (revert to mode default). */
		async clearSystemPrompt() {
			systemPromptState = { status: 'loading' };
			try {
				await api.updateSystemPrompt(sessionId, '');
				sessionSystemPrompt    = '';
				systemPromptEditorOpen = false;
				systemPromptState      = { status: 'success', data: undefined };
			} catch (e) {
				systemPromptState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Failed to clear system prompt.'
				};
			}
		},

		// ── Provider / model selection ────────────────────────────────────────

		/**
		 * Load domain branding from GET /api/app-info.
		 * Gracefully degrades — on any error the generic defaults are kept.
		 * Call once in onMount alongside loadModes() and loadProviders().
		 */
		async loadAppInfo() {
			try {
				const info   = await api.getAppInfo();
				appTitle       = info.title;
				appDescription = info.description;
			} catch {
				// Backend not yet updated — keep generic defaults.
			}
		},

		/**
		 * Load the provider catalog and the server's active default.
		 *
		 * Strategy (graceful degradation):
		 *   1. Pre-seeded with the static PROVIDERS catalog — picker renders immediately.
		 *   2. On mount, try GET /api/providers to get a live list (may differ from static).
		 *   3. Try GET /api/providers/active to sync the picker with the server default.
		 *   4. If either endpoint 404s / errors (backend not yet updated), swallow the
		 *      error and keep the static catalog + first provider as the selection.
		 *
		 * Call this once in onMount alongside loadModes().
		 */
		async loadProviders() {
			try {
				// Fire both requests in parallel for speed.
				const [providerList, active] = await Promise.all([
					api.getProviders(),
					api.getActiveProvider()
				]);

				// Replace static catalog with the live one from the backend.
				if (providerList.length > 0) {
					providers = providerList;
				}

				// Initialise the picker to match the server default — but only if
				// the user has not already made a manual selection this session.
				if (!selectedProvider) selectedProvider = active.provider;
				if (!selectedModel)    selectedModel    = active.model;
			} catch {
				// Backend endpoints not yet implemented — fall back to static catalog.
				// Initialise to the first provider's default so the picker is usable.
				if (!selectedProvider && providers.length > 0) {
					selectedProvider = providers[0].id;
					selectedModel    = providers[0].default_model;
				}
			}
		},

		/**
		 * Switch to a different provider.
		 * Automatically resets selectedModel to the new provider's default_model
		 * so the model picker never shows a stale value from the old provider.
		 */
		setProvider(id: string) {
			selectedProvider = id;
			const p = providers.find((p) => p.id === id);
			selectedModel = p?.default_model ?? '';
		},

		/** Switch to a different model within the currently selected provider. */
		setModel(id: string) {
			selectedModel = id;
		}
	};
}

// Singleton — one instance for the whole app lifecycle.
export const chatStore = createChatStore();
