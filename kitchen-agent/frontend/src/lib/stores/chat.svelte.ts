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
 *   - Token counting (session count + live input estimate)
 */

import { api, type Message, type Note } from '$lib/api';
import { PROVIDERS, type ProviderInfo }  from '$lib/providers';
import { sessionStore }                  from '$lib/stores/sessions.svelte';
import type { AsyncState, PastedImage }  from '$lib/types';
import { estimateTokensForText, estimateTokensForImage } from '$lib/token_estimator';

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function createChatStore() {
	// ── Session ───────────────────────────────────────────────────────────────
	let sessionId = $state<string>(crypto.randomUUID());
	let messages  = $state<Message[]>([]);

	// ── Async chat state machine — replaces isLoading boolean ─────────────────
	let chatState = $state<AsyncState<void>>({ status: 'idle' });

	// ── AbortController for cancelling in-flight LLM requests ─────────────────
	let chatAbortController = $state<AbortController | null>(null);

	// ── Pasted images ─────────────────────────────────────────────────────────
	let pastedImages = $state<PastedImage[]>([]);

	// ── Prompt modes ──────────────────────────────────────────────────────────
	let selectedModeId = $state('general');
	let modesState     = $state<AsyncState<void>>({ status: 'idle' });

	// ── Tools toggle ────────────────────────────────────────────────────
	/**
	 * Whether the next message should use the agentic tool-calling loop.
	 * Initialised to true; updated automatically when the user switches mode
	 * (picks up mode.tools_enabled_default); can be flipped manually by the
	 * user via the toggle in ChatComposer at any time.
	 */
	let toolsEnabled = $state<boolean>(true);

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

	// ── Token counting ──────────────────────────────────────────────────────
	/**
	 * Token count for the current session's entire history.
	 * Updated after each send and on session load.
	 * -1 means "not yet fetched".
	 */
	let sessionTokenCount = $state<number>(-1);

	/**
	 * Whether the session token count was fetched using the heuristic
	 * fallback (true) or the exact API (false).
	 */
	let sessionTokenFallback = $state<boolean>(false);

	/**
	 * Cached token estimate for the currently attached context files.
	 * Recalculated when contextFiles changes.
	 */
	let contextFileTokenEstimate = $state<number>(0);

	/**
	 * Cached system prompt text for the currently selected mode.
	 * Used by the client-side input token estimator.
	 */
	let cachedSystemPromptText = $state<string>('');

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
		// ── Derived guards ────────────────────────────────────────────────────────
		/** True when ANY destructive/edit operation is in flight. */
		get isMutating() {
			return editState.status === 'loading' || chatState.status === 'loading';
		},

	// ── Getters ───────────────────────────────────────────────────────────
		get sessionId()           { return sessionId; },
		get messages()            { return messages; },
		get chatState()           { return chatState; },
		get pastedImages()        { return pastedImages; },

		get selectedModeId()      { return selectedModeId; },
		get modesState()          { return modesState; },
		get toolsEnabled()        { return toolsEnabled; },

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

		// Token counting
		get sessionTokenCount()     { return sessionTokenCount; },
		get sessionTokenFallback()  { return sessionTokenFallback; },
		get contextFileTokenEstimate() { return contextFileTokenEstimate; },

		/**
		 * Reactive input token estimate — "what you'll pay when you click Send".
		 * Computed client-side using the chars/4 heuristic for instant feedback.
		 *
		 * Components:
		 *   text        = estimateTokensForText(currentMessage)
		 *   images      = pastedImages.length * 258
		 *   ctx_files   = cached context file token estimate
		 *   sys_prompt  = estimateTokensForText(cachedSystemPromptText)
		 *   history     = sessionTokenCount (last known)
		 *
		 * The `currentMessage` is not in the store (it's in the component)
		 * so we expose a method that takes it as an argument.
		 */
		estimateInputTokensFor(messageText: string): number {
			const textTokens = estimateTokensForText(messageText);
			const imageTokens = pastedImages.length * estimateTokensForImage();
			const systemPromptTokens = estimateTokensForText(cachedSystemPromptText);
			const historyTokens = Math.max(0, sessionTokenCount);

			return textTokens + imageTokens + contextFileTokenEstimate + systemPromptTokens + historyTokens;
		},

		/**
		 * Return the context window size in thousands of tokens for the
		 * currently selected model. Falls back to 1000 (Gemini default).
		 */
		get contextWindowK(): number {
			const provider = providers.find(p => p.id === selectedProvider);
			if (!provider) return 1000;
			const model = provider.models.find(m => m.id === selectedModel);
			return model?.context_k ?? provider.models[0]?.context_k ?? 1000;
		},

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
			sessionTokenCount     = -1;  // Reset — new session has no tokens yet
			sessionTokenFallback  = false;
			contextFileTokenEstimate = 0;
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
				// Auto-fetch session token count
				void this.refreshSessionTokens();
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
			contextFileTokenEstimate = 0;
			chatState    = { status: 'loading' };

			// Create placeholder assistant message for streaming
			const assistantMsg: import('$lib/api').Message = {
				role: 'assistant',
				content: '',
				isStreaming: true,
			};
			messages.push(assistantMsg);
			const assistantIdx = messages.length - 1;

			// Set state to idle so loading indicator hides
			// The isStreaming flag on the message shows the streaming state
			chatState = { status: 'idle' };

			const payload = {
				session_id:    sessionId,
				message:       text,
				mode_id:       selectedModeId,
				images:
					imagesToSend.length > 0
						? imagesToSend.map((i) => ({ mime_type: i.mimeType, data: i.base64 }))
						: null,
				context_files: contextFilesToSend.length > 0 ? contextFilesToSend : null,
				provider: selectedProvider || undefined,
				model:    selectedModel    || undefined,
				tools_enabled: toolsEnabled ? undefined : false
			};

			try {
				// Use streaming API
				for await (const event of api.chatStream(payload)) {
					switch (event.type) {
						case 'text':
						case 'text_delta': {
							// Append text delta to assistant message
							const current = messages[assistantIdx];
							messages[assistantIdx] = {
								...current,
								content: (current.content || '') + event.content,
							};
							break;
						}

						case 'tool_call': {
							// Show tool call in progress
							const current = messages[assistantIdx];
							const tools = [...(current.tools || [])];
							tools.push({
								name: event.name,
								args: event.args,
								id: event.id,
								status: 'calling',
							} as any);
							messages[assistantIdx] = { ...current, tools };
							break;
						}

						case 'tool_result': {
							// Update tool result
							const current = messages[assistantIdx];
							const tools = (current.tools || []).map((t: any) =>
								t.id === event.id ? { ...t, result: event.result, status: 'done' } : t
							);
							messages[assistantIdx] = { ...current, tools };
							break;
						}

						case 'done': {
							// Finalize message
							const current = messages[assistantIdx];
							messages[assistantIdx] = {
								...current,
								isStreaming: false,
								turn_id: event.assistant_turn_id,
								provider: event.provider,
								model: event.model,
							};

							// Update user message with turn_id
							if (event.user_turn_id) {
								const lastUserIdx = assistantIdx - 1;
								if (lastUserIdx >= 0 && messages[lastUserIdx].role === 'user' && !messages[lastUserIdx].turn_id) {
									messages[lastUserIdx] = { ...messages[lastUserIdx], turn_id: event.user_turn_id };
								}
							}
							break;
						}

						case 'error': {
							throw new Error(event.message);
						}
					}
				}

				chatState = { status: 'success', data: undefined };
				await sessionStore.refresh();
				// Auto-refresh session token count after each successful send
				void this.refreshSessionTokens();
			} catch (e) {
				const msg = e instanceof Error ? e.message : 'Unknown error connecting to API.';
				// Update the placeholder message with error
				messages[assistantIdx] = {
					...messages[assistantIdx],
					content: `⚠️ Error: ${msg}`,
					isStreaming: false,
				};
				chatState = { status: 'error', message: msg };
			}
		},

		/**
		 * Regenerate the last assistant response.
		 * Deletes the last assistant message and resends the last user message.
		 */
		async regenerateMessage() {
			if (chatState.status === 'loading') return;

			// Find the last assistant message
			const lastAssistantIdx = messages.length - 1;
			if (lastAssistantIdx < 0 || messages[lastAssistantIdx].role !== 'assistant') return;

			// Find the last user message before it
			let lastUserIdx = -1;
			for (let i = lastAssistantIdx - 1; i >= 0; i--) {
				if (messages[i].role === 'user') {
					lastUserIdx = i;
					break;
				}
			}
			if (lastUserIdx === -1) return;

			const lastUserMessage = messages[lastUserIdx];

			// Optimistic: remove the last assistant message
			const snapshot = [...messages];
			messages = messages.slice(0, lastAssistantIdx);
			chatState = { status: 'loading' };

			try {
				// Resend the last user message to get a new response
				const data = await api.chat({
					session_id: sessionId,
					message: lastUserMessage.content,
					mode_id: selectedModeId,
					images: null,
					context_files: null,
					provider: selectedProvider || undefined,
					model: selectedModel || undefined,
					tools_enabled: toolsEnabled ? undefined : false
				});

				messages.push({
					role: 'assistant',
					content: data.text,
					tools: data.tools_used,
					...(data.assistant_turn_id ? { turn_id: data.assistant_turn_id } : {}),
					...(data.provider ? { provider: data.provider } : {}),
					...(data.model ? { model: data.model } : {})
				});

				chatState = { status: 'success', data: undefined };
				await sessionStore.refresh();
				void this.refreshSessionTokens();
			} catch (e) {
				// Rollback — restore the snapshot
				messages = snapshot;
				const msg = e instanceof Error ? e.message : 'Unknown error connecting to API.';
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
				// Sync toolsEnabled to the selected mode's default from the live list.
				const activeModeData = fetched.find((m) => m.id === selectedModeId);
				if (activeModeData !== undefined) toolsEnabled = activeModeData.tools_enabled_default ?? true;
				// Cache system prompt for token estimation
				void this.refreshCachedSystemPrompt();
				return fetched;
			} catch (e) {
				console.error('Failed to load prompt modes', e);
				modesState = { status: 'error', message: String(e) };
				return [];
			}
		},

		setSelectedModeId(id: string, modes?: import('$lib/api').PromptMode[]) {
			if (id === selectedModeId) return;
			selectedModeId = id;
			// Sync toolsEnabled to the new mode's default when provided.
			if (modes) {
				const mode = modes.find((m) => m.id === id);
				if (mode !== undefined) toolsEnabled = mode.tools_enabled_default ?? true;
			}
			// Invalidate stale prompt detail cache.
			promptDetailContent = null;
			promptDetailState   = { status: 'idle' };
			promptDetailForId   = '';
			// Eagerly re-fetch if the inspector is open.
			if (promptInspectorOpen) void this.loadPromptDetail();
			// Update cached system prompt for token estimation
			void this.refreshCachedSystemPrompt();
		},

		toggleTools() {
			toolsEnabled = !toolsEnabled;
		},

		setToolsEnabled(value: boolean) {
			toolsEnabled = value;
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
			// Recalculate context file token estimate
			void this.refreshContextFileTokens();
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
		 *
		 * Safety features:
		 *  - Auto-cancels any in-progress edit on the same message.
		 *  - Auto-promotes to pair-delete when deleting a user message that has
		 *    a following assistant reply (prevents orphaned assistant messages).
		 *  - Optimistic local update with rollback on failure (no full session reload).
		 */
		async deleteMessage(turnId: string, deletePair = false) {
			if (editState.status === 'loading') return;

			// Auto-cancel edit if deleting the message currently being edited.
			if (editingTurnId === turnId) {
				this.cancelEditing();
			}

			// Auto-promote to pair-delete: deleting a user message that has a
			// following assistant reply would leave an orphaned assistant bubble.
			const idx = messages.findIndex(m => m.turn_id === turnId);
			if (idx !== -1 && messages[idx].role === 'user' && !deletePair) {
				const next = messages[idx + 1];
				if (next?.role === 'assistant') {
					deletePair = true;
				}
			}

			// Snapshot for rollback.
			const snapshot = [...messages];

			// Optimistic local removal — instant UI feedback.
			if (deletePair) {
				// Remove the target and its paired assistant reply.
				messages = messages.filter((m, i) => {
					if (m.turn_id === turnId) return false;
					if (i === idx + 1 && m.role === 'assistant') return false;
					return true;
				});
			} else {
				messages = messages.filter(m => m.turn_id !== turnId);
			}

			editState = { status: 'loading' };
			try {
				await api.deleteMessage(sessionId, turnId, deletePair);
				editState = { status: 'success', data: undefined };
			} catch (e) {
				// Rollback — restore the snapshot.
				messages = snapshot;
				editState = {
					status:  'error',
					message: e instanceof Error ? e.message : 'Delete failed.'
				};
			}
		},

		/**
		 * Truncate the last n turn-pairs from the conversation.
		 * Uses optimistic local update with rollback on failure.
		 */
		async truncateMessages(n: number) {
			if (n < 1 || editState.status === 'loading') return;

			// Snapshot for rollback.
			const snapshot = [...messages];

			// Optimistic local removal — drop the last 2*n messages (n turn-pairs).
			const pairsToRemove = n * 2;
			messages = messages.slice(0, Math.max(0, messages.length - pairsToRemove));

			editState = { status: 'loading' };
			try {
				await api.truncateMessages(sessionId, n);
				editState = { status: 'success', data: undefined };
				await sessionStore.refresh();
				void this.refreshSessionTokens();
			} catch (e) {
				// Rollback — restore the snapshot.
				messages = snapshot;
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
		},

		// ── Token counting ──────────────────────────────────────────────────────

		/**
		 * Fetch the session's token count from the backend API.
		 * Called automatically after each send and on session load.
		 * Gracefully degrades — on error the count stays at its previous value.
		 */
		async refreshSessionTokens() {
			try {
				const data = await api.getSessionTokens(sessionId);
				sessionTokenCount    = data.total_tokens;
				sessionTokenFallback = data.fallback_used;
			} catch {
				// Backend not available — keep previous value
			}
		},

		/**
		 * Refresh the cached context file token estimate.
		 * Called when contextFiles changes.
		 * Reads each file's content and estimates tokens using chars/4.
		 */
		async refreshContextFileTokens() {
			if (contextFiles.length === 0) {
				contextFileTokenEstimate = 0;
				return;
			}
			let total = 0;
			for (const path of contextFiles) {
				try {
					const data = await api.readFile(path);
					total += estimateTokensForText(data.content);
				} catch {
					// Unreadable file — skip
				}
			}
			contextFileTokenEstimate = total;
		},

		/**
		 * Refresh the cached system prompt text for token estimation.
		 * Called when the mode changes.
		 */
		async refreshCachedSystemPrompt() {
			try {
				const detail = await api.getPromptModeDetail(selectedModeId);
				cachedSystemPromptText = detail.content ?? '';
			} catch {
				cachedSystemPromptText = '';
			}
		}
	};
}

// Singleton — one instance for the whole app lifecycle.
export const chatStore = createChatStore();
