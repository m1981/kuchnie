/**
 * src/lib/api.ts
 * ==============
 * Centralised API client for the Kitchen Agent backend.
 *
 * The base URL is read from the Vite env variable VITE_API_BASE so it can be
 * changed without touching component code.  Defaults to http://127.0.0.1:8000.
 *
 * Usage:
 *   import { api } from '$lib/api';
 *   const sessions = await api.getSessions();
 */

export const API_BASE: string =
	(import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000';

// ---------------------------------------------------------------------------
// Types (mirroring Pydantic models on the backend)
// ---------------------------------------------------------------------------

export type SessionSummary = {
	id: string;
	title: string | null;
	updated_at: string | null;
	parent_id: string | null;
	fork_turn_index: number | null;
	root_id: string | null;
	archived_at: string | null;
};

export type SessionNode = SessionSummary & {
	children: SessionNode[];
};

/** Lightweight session state for test verification. */
export type SessionState = {
	session_id: string;
	message_count: number;
	turn_ids: (string | undefined)[];
	roles: string[];
};

export type Note = {
	id: string;
	session_id: string;
	selected_text: string;
	note: string;
	source_role: 'user' | 'assistant';
	created_at: string;
};

export type NoteCreateRequest = {
	selected_text: string;
	source_role: 'user' | 'assistant';
	note?: string;
};

export type ToolLog = {
	name: string;
	args: Record<string, unknown>;
	result: { content?: string; [key: string]: unknown };
};

export type Message = {
	role: 'user' | 'assistant';
	content: string;
	tools?: ToolLog[];
	images?: string[]; // preview data-URLs stored locally; not sent to backend
	/**
	 * Stable UUID stamped by the backend at write time.
	 * Used to identify messages for editing/deleting without relying on array
	 * position.  Always present for messages from the chat API; may be
	 * undefined only for very old sessions created before this feature.
	 */
	turn_id?: string;
	/**
	 * Basenames of context files that were injected into this user message
	 * (e.g. ["kuchnia-kroki.md", "materials.md"]).
	 * Persisted by the backend on the user ui_message entry; undefined when
	 * no files were attached.  Only present on user messages.
	 */
	context_files?: string[];
	/** Provider used for this message (e.g. "gemini", "anthropic"). Only on assistant messages. */
	provider?: string;
	/** Model used for this message (e.g. "gemini-2.5-flash"). Only on assistant messages. */
	model?: string;
};

export type FileItem = { path: string; name: string };

export type ChatImagePart = { mime_type: string; data: string };

// ---------------------------------------------------------------------------
// Provider / model picker types  (mirrors backend ProviderInfo / ModelInfo)
// ---------------------------------------------------------------------------

/**
 * Metadata for a single model within a provider.
 * Matches ModelInfo Pydantic schema on the backend.
 */
export type ModelInfo = {
	id: string;
	label: string;
	context_k: number; // context window in thousands of tokens
};

/**
 * Metadata for one LLM provider, including its available model list.
 * Returned by GET /api/providers.
 */
export type ProviderInfo = {
	id: string;
	label: string;
	default_model: string;
	models: ModelInfo[];
};

/**
 * Server's currently configured default provider + model.
 * Returned by GET /api/providers/active.
 */
export type ActiveProvider = {
	provider: string;
	model: string;
};

/**
 * Domain branding metadata for the running instance.
 * Returned by GET /api/app-info.
 * Driven by APP_TITLE / APP_DESCRIPTION env vars on the server.
 */
export type AppInfo = {
	title: string;
	description: string;
};

// ---------------------------------------------------------------------------
// Chat types
// ---------------------------------------------------------------------------

/**
 * F05 — Updated ChatRequest.
 *
 * `mode_id` is the new primary field (default: "general").
 * `system_prompt` is kept for backward compatibility and takes precedence
 * when provided.
 *
 * `provider` and `model` are optional overrides added in the provider
 * integration pass.  When omitted the server uses its configured defaults.
 * When provided they override the server default for that single request.
 */
export type ChatRequest = {
	session_id: string;
	message: string;
	/** F05: backend prompt mode id. Resolved server-side via PromptManager. */
	mode_id?: string;
	/**
	 * Legacy override.  When set, bypasses mode_id resolution entirely and
	 * passes the raw string directly to the LLM.  Maintained for backward
	 * compatibility with existing frontend code.
	 */
	system_prompt?: string | null;
	images?: ChatImagePart[] | null;
	context_files?: string[] | null;
	/**
	 * Provider override — "gemini" | "anthropic".
	 * Omit to use the server's LLM_PROVIDER environment variable default.
	 */
	provider?: string;
	/**
	 * Model override — provider-specific model id string.
	 * Omit to use the provider's configured default model.
	 */
	model?: string;
	/**
	 * Tool-calling toggle — Option C.
	 * true  → agentic loop (LLM may call file tools). Default.
	 * false → plain LLM call; no tools sent, no agentic loop.
	 * When omitted the server uses the mode's tools_enabled_default.
	 */
	tools_enabled?: boolean;
};

export type ChatResponse = {
	text: string;
	tools_used: ToolLog[];
	user_turn_id?: string;
	assistant_turn_id?: string;
	provider?: string;
	model?: string;
};

// ---------------------------------------------------------------------------
// F05 — Prompt mode types (mirrors PromptModeResponse Pydantic model)
// ---------------------------------------------------------------------------

/**
 * Metadata for one backend-managed prompt mode.
 * Returned by GET /api/prompts/modes.
 * Never includes the full `content` string.
 */
export type PromptMode = {
	id: string;
	label: string;
	eyebrow: string;
	/** When false, this mode defaults to plain LLM chat (no tool-calling loop). */
	tools_enabled_default: boolean;
};

/**
 * Full detail for one prompt mode including the resolved system instruction.
 * Returned by GET /api/prompts/modes/{mode_id}.
 * Fetched lazily only when the user expands the inspector panel.
 */
export type PromptModeDetail = PromptMode & {
	content: string;
};

// ---------------------------------------------------------------------------
// LLM debug export types (mirrors LlmExportResponse Pydantic model)
// ---------------------------------------------------------------------------

export type LlmExportMetadata = {
	session_id: string;
	title: string;
	turn_count: number;
	export_timestamp: string; // ISO 8601 UTC
};

export type LlmExportTurn = {
	role: string;
	parts: Record<string, unknown>[];
};

export type LlmExportResponse = {
	metadata: LlmExportMetadata;
	turns: LlmExportTurn[];
};

// ---------------------------------------------------------------------------
// Message editor types (mirrors message_editor Pydantic models)
// ---------------------------------------------------------------------------

/** Response from PATCH /api/sessions/{id}/messages/{turn_id} */
export type MessageEditResponse = {
	updated: boolean;
	turn_id: string;
};

/** Response from DELETE /api/sessions/{id}/messages/{turn_id} */
export type MessageDeleteResponse = {
	deleted: boolean;
	turn_id: string;
	delete_pair: boolean;
};

/** Response from POST /api/sessions/{id}/messages/truncate */
export type TruncateResponse = {
	truncated: boolean;
	turns_removed: number;
};

/** Response from GET /api/sessions/{id}/system-prompt */
export type SystemPromptResponse = {
	session_id: string;
	system_prompt: string | null;
};

/** Response from PATCH /api/sessions/{id}/system-prompt */
export type SystemPromptUpdateResponse = {
	updated: boolean;
};

// ---------------------------------------------------------------------------
// Token counting types (mirrors SessionTokensResponse / TokenEstimateResponse)
// ---------------------------------------------------------------------------

/** Response from GET /api/sessions/{id}/tokens */
export type SessionTokensResponse = {
	session_id: string;
	text_tokens: number;
	image_tokens: number;
	context_file_tokens: number;
	system_prompt_tokens: number;
	history_tokens: number;
	total_tokens: number;
	fallback_used: boolean;
};

/** Response from POST /api/tokens/estimate */
export type TokenEstimateResponse = {
	text_tokens: number;
	image_tokens: number;
	context_file_tokens: number;
	system_prompt_tokens: number;
	history_tokens: number;
	total_tokens: number;
	fallback_used: boolean;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, init);
	if (!res.ok) {
		const detail = await res.text().catch(() => `HTTP ${res.status}`);
		throw new Error(detail || `HTTP ${res.status}`);
	}
	return res.json() as Promise<T>;
}

async function requestText(path: string, init?: RequestInit): Promise<string> {
	const res = await fetch(`${API_BASE}${path}`, init);
	if (!res.ok) {
		const detail = await res.text().catch(() => `HTTP ${res.status}`);
		throw new Error(detail || `HTTP ${res.status}`);
	}
	return res.text();
}

function json(body: unknown): RequestInit {
	return {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	};
}

function jsonPatch(body: unknown): RequestInit {
	return {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(body)
	};
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
	// Sessions
	getSessions: () => request<SessionSummary[]>('/api/sessions'),

	getSession: (id: string) =>
		request<{ ui_messages: Message[] }>(`/api/sessions/${id}`),

	/**
	 * GET /api/sessions/{id}/state
	 * Lightweight state check for test verification.
	 * Returns message count, turn_ids, and roles without full message content.
	 */
	getSessionState: (id: string) =>
		request<SessionState>(`/api/sessions/${id}/state`),

	/**
	 * GET /api/sessions/{id}/export
	 * Returns the session as a human-readable Markdown string.
	 * Content-Type: text/markdown
	 */
	exportSession: (id: string): Promise<string> =>
		requestText(`/api/sessions/${id}/export`),

	/**
	 * GET /api/sessions/{id}/export/llm
	 * Returns the raw LLM context window as structured JSON.
	 * Useful for debugging multi-turn tool-calling sessions.
	 */
	exportSessionLlm: (id: string): Promise<LlmExportResponse> =>
		request<LlmExportResponse>(`/api/sessions/${id}/export/llm`),

	forkSession: (id: string, turnIndex: number) =>
		request<{ new_session_id: string }>(
			`/api/sessions/${id}/fork`,
			json({ turn_index: turnIndex })
		),

	// Files
	listFiles: () => request<FileItem[]>('/api/files'),

	readFile: (path: string) =>
		request<{ filepath: string; content: string }>(`/api/files/${path}`),

	writeFile: (path: string, content: string) =>
		request<{ success: string }>(`/api/files/${path}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ content })
		}),

	appendToFile: (filepath: string, content: string) =>
		request<{ success: string }>('/api/files/append', json({ filepath, content })),

	// Repo map
	getRepoMap: () => request<{ content: string }>('/api/repo-map'),

	// Session tree, archive, delete
	getSessionTree: (includeArchived = true) =>
		request<SessionNode[]>(`/api/sessions/tree?include_archived=${includeArchived}`),

	archiveSession: (id: string) =>
		request<{ archived: boolean; session_id: string }>(
			`/api/sessions/${id}/archive`,
			{ method: 'PATCH' }
		),

	unarchiveSession: (id: string) =>
		request<{ archived: boolean; session_id: string }>(
			`/api/sessions/${id}/archive`,
			{ method: 'DELETE' }
		),

	deleteSession: (id: string) =>
		fetch(`${API_BASE}/api/sessions/${id}`, { method: 'DELETE' }).then((r) => {
			if (!r.ok && r.status !== 204)
				return r.text().then((t) => { throw new Error(t || `HTTP ${r.status}`); });
		}),

	// Notes
	getNotes: (sessionId: string) =>
		request<Note[]>(`/api/sessions/${sessionId}/notes`),

	createNote: (sessionId: string, body: NoteCreateRequest) =>
		request<Note>(`/api/sessions/${sessionId}/notes`, json(body)),

	deleteNote: (sessionId: string, noteId: string) =>
		fetch(`${API_BASE}/api/sessions/${sessionId}/notes/${noteId}`, { method: 'DELETE' }).then(
			(r) => {
				if (!r.ok && r.status !== 204)
					return r.text().then((t) => { throw new Error(t || `HTTP ${r.status}`); });
			}
		),

	// Chat
	chat: (payload: ChatRequest) =>
		request<ChatResponse>('/api/chat', json(payload)),

	// -------------------------------------------------------------------------
	// F05 — Prompt mode management
	// -------------------------------------------------------------------------

	/**
	 * GET /api/prompts/modes
	 * Returns metadata (id, label, eyebrow) for all backend prompt modes.
	 * Use this to populate the mode switcher instead of hardcoding templates.
	 */
	getPromptModes: (): Promise<PromptMode[]> =>
		request<PromptMode[]>('/api/prompts/modes'),

	/**
	 * GET /api/prompts/modes/{mode_id}
	 * Returns the full resolved system instruction for one mode.
	 * Fetched lazily when the user expands the prompt inspector.
	 * Throws on 404 when the mode_id is not registered.
	 */
	getPromptModeDetail: (modeId: string): Promise<PromptModeDetail> =>
		request<PromptModeDetail>(`/api/prompts/modes/${modeId}`),

	/**
	 * POST /api/prompts/reload
	 * Hot-reloads the prompt Markdown files on the server without restart.
	 * Useful during development when editing prompts/*.md files.
	 */
	reloadPrompts: (): Promise<{ success: boolean }> =>
		request<{ success: boolean }>('/api/prompts/reload', { method: 'POST' }),

	// -------------------------------------------------------------------------
	// Message Editor — in-session message editing/deletion
	// -------------------------------------------------------------------------

	/**
	 * PATCH /api/sessions/{id}/messages/{turn_id}
	 * Replace the text content of a single message identified by its stable turn_id.
	 * Both ui_history and api_history are updated atomically.
	 */
	editMessage: (sessionId: string, turnId: string, newContent: string) =>
		request<MessageEditResponse>(
			`/api/sessions/${sessionId}/messages/${turnId}`,
			jsonPatch({ new_content: newContent })
		),

	/**
	 * DELETE /api/sessions/{id}/messages/{turn_id}
	 * Remove a message from the conversation identified by its stable turn_id.
	 * Pass deletePair=true to also remove the next paired message.
	 */
	deleteMessage: (sessionId: string, turnId: string, deletePair = false) =>
		request<MessageDeleteResponse>(
			`/api/sessions/${sessionId}/messages/${turnId}?delete_pair=${deletePair}`,
			{ method: 'DELETE' }
		),

	/**
	 * POST /api/sessions/{id}/messages/truncate
	 * Remove the last n complete turn-pairs from the conversation.
	 */
	truncateMessages: (sessionId: string, n: number) =>
		request<TruncateResponse>(
			`/api/sessions/${sessionId}/messages/truncate`,
			json({ n })
		),

	/**
	 * GET /api/sessions/{id}/system-prompt
	 * Retrieve the session-scoped system prompt override (or null if unset).
	 */
	getSystemPrompt: (sessionId: string) =>
		request<SystemPromptResponse>(`/api/sessions/${sessionId}/system-prompt`),

	/**
	 * PATCH /api/sessions/{id}/system-prompt
	 * Set or clear the session-scoped system prompt override.
	 * Empty string clears the override (reverts to mode-resolved prompt).
	 */
	updateSystemPrompt: (sessionId: string, systemPrompt: string) =>
		request<SystemPromptUpdateResponse>(
			`/api/sessions/${sessionId}/system-prompt`,
			jsonPatch({ system_prompt: systemPrompt })
		),

	// -------------------------------------------------------------------------
	// Provider / model selection
	// -------------------------------------------------------------------------

	/**
	 * GET /api/providers
	 * Returns all available providers and their supported model lists.
	 * Call once on app mount and cache the result in the store.
	 * Falls back to the static PROVIDERS catalog in src/lib/providers.ts
	 * when the endpoint is not yet available on the backend.
	 */
	getProviders: (): Promise<ProviderInfo[]> =>
		request<ProviderInfo[]>('/api/providers'),

	/**
	 * GET /api/providers/active
	 * Returns the server's default provider + model as configured via env vars.
	 * Use on app startup to initialise the picker to match the server default.
	 */
	getActiveProvider: (): Promise<ActiveProvider> =>
		request<ActiveProvider>('/api/providers/active'),

	/**
	 * GET /api/app-info
	 * Returns domain branding metadata (title, description) from server config.
	 * Call once on app mount to replace hardcoded domain strings in the UI.
	 * Graceful degradation: falls back to generic defaults on error.
	 */
	getAppInfo: (): Promise<AppInfo> =>
		request<AppInfo>('/api/app-info'),

	// -------------------------------------------------------------------------
	// Token counting
	// -------------------------------------------------------------------------

	/**
	 * GET /api/sessions/{id}/tokens
	 * Returns the token count for all turns stored in the session so far.
	 * Uses the exact Gemini count_tokens API on the backend when available,
	 * falling back to a heuristic when the API is unreachable.
	 */
	getSessionTokens: (sessionId: string): Promise<SessionTokensResponse> =>
		request<SessionTokensResponse>(`/api/sessions/${sessionId}/tokens`),

	/**
	 * POST /api/tokens/estimate
	 * Returns a heuristic token estimate for a pending (not-yet-sent) context.
	 * Used for precise on-demand estimates; the client-side estimator is used
	 * for the reactive live indicator.
	 */
	estimateTokens: (payload: {
		user_message: string;
		images?: { mime_type: string; data: string }[] | null;
		context_files?: string[] | null;
		system_prompt?: string | null;
		history_token_count?: number;
	}): Promise<TokenEstimateResponse> =>
		request<TokenEstimateResponse>('/api/tokens/estimate', json(payload))
};
