/**
 * lib/stores/chat.svelte.ts
 * ==========================
 * Thin facade that composes the focused sub-stores.
 *
 * This preserves the public API so +page.svelte and all components
 * continue to work without changes.  Each concern lives in its own
 * store for independent testing and lower cognitive load.
 *
 * Sub-stores:
 *   providerStore  — provider/model selection, app branding
 *   promptStore    — prompt modes, tools toggle, inspector
 *   editorStore    — message editing, system prompt editing
 *   tokenStore     — token counting, context file tokens
 *
 * This file owns only:
 *   - Session lifecycle (new, load, fork)
 *   - Messaging (send, regenerate, streaming)
 *   - Pasted image queue
 *   - Context files
 *   - Cross-store coordination on state transitions
 */

import { api, type Message, type Note } from '$lib/api';
import { sessionStore }   from '$lib/stores/sessions.svelte';
import { providerStore }  from '$lib/stores/provider.svelte';
import { promptStore }    from '$lib/stores/prompt.svelte';
import { editorStore }    from '$lib/stores/editor.svelte';
import { tokenStore }     from '$lib/stores/token.svelte';
import type { AsyncState, PastedImage } from '$lib/types';

// Re-export sub-stores for direct access (gradual migration path)
export { providerStore, promptStore, editorStore, tokenStore };

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function createChatStore() {
	// ── Core session state ───────────────────────────────────────────────────
	let sessionId = $state<string>(crypto.randomUUID());
	let messages  = $state<Message[]>([]);
	let chatState = $state<AsyncState<void>>({ status: 'idle' });

	// ── Pasted images ────────────────────────────────────────────────────────
	let pastedImages = $state<PastedImage[]>([]);

	// ── Context files ────────────────────────────────────────────────────────
	let contextFiles = $state<string[]>([]);

	// ── Fork feedback ────────────────────────────────────────────────────────
	let forkStatus = $state('');

	return {
		// ── Derived guards ────────────────────────────────────────────────────────
		get isMutating() {
			return editorStore.editState.status === 'loading' || chatState.status === 'loading';
		},

		// ── Core session ──────────────────────────────────────────────────────────
		get sessionId()    { return sessionId; },
		get messages()     { return messages; },
		get chatState()    { return chatState; },
		get pastedImages() { return pastedImages; },
		get contextFiles() { return contextFiles; },
		get forkStatus()   { return forkStatus; },

		// ── Delegated getters (providerStore) ─────────────────────────────────────
		get providers()        { return providerStore.providers; },
		get selectedProvider() { return providerStore.selectedProvider; },
		get selectedModel()    { return providerStore.selectedModel; },
		get appTitle()         { return providerStore.appTitle; },
		get appDescription()   { return providerStore.appDescription; },
		get contextWindowK()   { return providerStore.contextWindowK; },

		// ── Delegated getters (promptStore) ───────────────────────────────────────
		get selectedModeId()      { return promptStore.selectedModeId; },
		get modesState()          { return promptStore.modesState; },
		get toolsEnabled()        { return promptStore.toolsEnabled; },
		get promptDetailContent() { return promptStore.promptDetailContent; },
		get promptDetailState()   { return promptStore.promptDetailState; },
		get promptDetailForId()   { return promptStore.promptDetailForId; },
		get promptInspectorOpen() { return promptStore.promptInspectorOpen; },

		// ── Delegated getters (editorStore) ───────────────────────────────────────
		get editingTurnId()       { return editorStore.editingTurnId; },
		get editDraft()           { return editorStore.editDraft; },
		get editState()           { return editorStore.editState; },
		get sessionSystemPrompt()    { return editorStore.sessionSystemPrompt; },
		get systemPromptDraft()      { return editorStore.systemPromptDraft; },
		get systemPromptState()      { return editorStore.systemPromptState; },
		get systemPromptError()      { return editorStore.systemPromptError; },

		// ── Delegated getters (tokenStore) ────────────────────────────────────────
		get sessionTokenCount()      { return tokenStore.sessionTokenCount; },
		get sessionTokenFallback()   { return tokenStore.sessionTokenFallback; },
		get contextFileTokenEstimate() { return tokenStore.contextFileTokenEstimate; },

		estimateInputTokensFor(messageText: string): number {
			return tokenStore.estimateInputTokensFor(
				messageText,
				pastedImages.length,
				tokenStore.contextFileTokenEstimate
			);
		},

		// ── Delegated methods (providerStore) ─────────────────────────────────────

		async loadProviders() { return providerStore.loadProviders(); },
		async loadAppInfo()   { return providerStore.loadAppInfo(); },
		setProvider(id: string) { providerStore.setProvider(id); },
		setModel(id: string)    { providerStore.setModel(id); },

		// ── Delegated methods (promptStore) ───────────────────────────────────────

		async loadModes() { return promptStore.loadModes(); },

		setSelectedModeId(id: string, modes?: import('$lib/api').PromptMode[]) {
			promptStore.setSelectedModeId(id, modes);
			// Update cached system prompt for token estimation
			void tokenStore.refreshCachedSystemPrompt(promptStore.selectedModeId);
		},

		toggleTools()               { promptStore.toggleTools(); },
		setToolsEnabled(v: boolean) { promptStore.setToolsEnabled(v); },

		setPromptInspectorOpen(open: boolean) { promptStore.setPromptInspectorOpen(open); },

		// ── Delegated methods (editorStore) ───────────────────────────────────────

		startEditing(turnId: string) {
			editorStore.startEditing(turnId, messages);
		},

		cancelEditing()  { editorStore.cancelEditing(); },
		setEditDraft(t: string) { editorStore.setEditDraft(t); },

		async saveEdit() {
			await editorStore.saveEdit(sessionId, messages, (idx, updated) => {
				messages[idx] = updated;
			});
		},

		async deleteMessage(turnId: string, deletePair: boolean) {
			await editorStore.deleteMessage(sessionId, messages, turnId, deletePair, (newMsgs) => {
				messages = newMsgs;
			});
		},

		async truncateMessages(n: number) {
			await editorStore.truncateMessages(sessionId, messages, n, (newMsgs) => {
				messages = newMsgs;
			}, async () => {
				await sessionStore.refresh();
				void tokenStore.refreshSessionTokens(sessionId);
			});
		},

		async loadSystemPrompt()    { return editorStore.loadSystemPrompt(sessionId); },
		async saveSystemPrompt(text: string) { return editorStore.saveSystemPrompt(sessionId, text); },
		async clearSystemPrompt()   { return editorStore.clearSystemPrompt(sessionId); },

		// ── Delegated methods (tokenStore) ─────────────────────────────────────────

		async refreshSessionTokens() { return tokenStore.refreshSessionTokens(sessionId); },

		// ── Context files ─────────────────────────────────────────────────────────

		setContextFiles(paths: string[]) {
			contextFiles = paths;
			void tokenStore.refreshContextFileTokens(paths);
		},

		// ── Images ────────────────────────────────────────────────────────────────

		addPastedImage(img: PastedImage) {
			pastedImages = [...pastedImages, img];
		},

		removeImage(index: number) {
			pastedImages = pastedImages.filter((_, i) => i !== index);
		},

		// ── Notes helper ──────────────────────────────────────────────────────────

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

		// ── Session lifecycle ─────────────────────────────────────────────────────

		startNewChat() {
			sessionId    = crypto.randomUUID();
			messages     = [];
			pastedImages = [];
			chatState    = { status: 'idle' };
			contextFiles = [];
			forkStatus   = '';

			editorStore.reset();
			tokenStore.reset();

			// Provider / model selection intentionally kept across new chats.
		},

		async loadSession(id: string) {
			try {
				const data = await api.getSession(id);
				sessionId    = id;
				messages     = data.ui_messages ?? [];
				chatState    = { status: 'idle' };
				contextFiles = [];
				forkStatus   = '';

				editorStore.reset();

				// Load session's system prompt override (if any).
				void editorStore.loadSystemPrompt(id);

				// Restore provider/model picker from the last assistant message.
				for (let i = messages.length - 1; i >= 0; i--) {
					const m = messages[i];
					if (m.role === 'assistant' && m.provider) {
						providerStore.syncFromMessage(m.provider, m.model);
						break;
					}
				}

				void tokenStore.refreshSessionTokens(id);
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

		// ── Messaging ─────────────────────────────────────────────────────────────

		async sendMessage(text: string) {
			if (!text.trim() || chatState.status === 'loading') return;

			const imagesToSend       = [...pastedImages];
			const contextFilesToSend = [...contextFiles];

			// Optimistic UI — push user message immediately.
			const optimisticMsg: Message = {
				role:   'user',
				content: text,
				images: imagesToSend.map((i) => i.dataUrl),
				...(contextFilesToSend.length > 0
					? { context_files: contextFilesToSend.map((p) => p.split('/').pop() ?? p) }
					: {})
			};
			messages.push(optimisticMsg);
			pastedImages = [];
			contextFiles = [];
			tokenStore.refreshContextFileTokens([]);
			chatState = { status: 'loading' };

			// Create placeholder assistant message for streaming.
			const assistantMsg: Message = {
				role: 'assistant',
				content: '',
				isStreaming: true,
			};
			messages.push(assistantMsg);
			const assistantIdx = messages.length - 1;

			chatState = { status: 'idle' };

			const payload = {
				session_id:    sessionId,
				message:       text,
				mode_id:       promptStore.selectedModeId,
				images:
					imagesToSend.length > 0
						? imagesToSend.map((i) => ({ mime_type: i.mimeType, data: i.base64 }))
						: null,
				context_files: contextFilesToSend.length > 0 ? contextFilesToSend : null,
				provider: providerStore.selectedProvider || undefined,
				model:    providerStore.selectedModel    || undefined,
				tools_enabled: promptStore.toolsEnabled ? undefined : false
			};

			try {
				for await (const event of api.chatStream(payload)) {
					switch (event.type) {
						case 'text':
						case 'text_delta': {
							const current = messages[assistantIdx];
							messages[assistantIdx] = {
								...current,
								content: (current.content || '') + event.content,
							};
							break;
						}

						case 'tool_call': {
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
							const current = messages[assistantIdx];
							const tools = (current.tools || []).map((t: any) =>
								t.id === event.id ? { ...t, result: event.result, status: 'done' } : t
							);
							messages[assistantIdx] = { ...current, tools };
							break;
						}

						case 'done': {
							const current = messages[assistantIdx];
							messages[assistantIdx] = {
								...current,
								isStreaming: false,
								turn_id: event.assistant_turn_id,
								provider: event.provider,
								model: event.model,
							};

							// Sync picker to the provider that actually responded.
							providerStore.syncFromMessage(event.provider, event.model);

							// Update user message with turn_id.
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
				void tokenStore.refreshSessionTokens(sessionId);
			} catch (e) {
				const msg = e instanceof Error ? e.message : 'Unknown error connecting to API.';
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
		 */
		async regenerateMessage() {
			if (chatState.status === 'loading') return;

			const lastAssistantIdx = messages.length - 1;
			if (lastAssistantIdx < 0 || messages[lastAssistantIdx].role !== 'assistant') return;

			let lastUserIdx = -1;
			for (let i = lastAssistantIdx - 1; i >= 0; i--) {
				if (messages[i].role === 'user') {
					lastUserIdx = i;
					break;
				}
			}
			if (lastUserIdx === -1) return;

			const lastUserMessage = messages[lastUserIdx];
			const snapshot = [...messages];
			messages = messages.slice(0, lastAssistantIdx);
			chatState = { status: 'loading' };

			try {
				const data = await api.chat({
					session_id: sessionId,
					message: lastUserMessage.content,
					mode_id: promptStore.selectedModeId,
					images: null,
					context_files: null,
					provider: providerStore.selectedProvider || undefined,
					model: providerStore.selectedModel || undefined,
					tools_enabled: promptStore.toolsEnabled ? undefined : false
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
				void tokenStore.refreshSessionTokens(sessionId);
			} catch (e) {
				messages = snapshot;
				const msg = e instanceof Error ? e.message : 'Unknown error connecting to API.';
				chatState = { status: 'error', message: msg };
			}
		}
	};
}

// Singleton — one instance for the whole app lifecycle.
export const chatStore = createChatStore();
