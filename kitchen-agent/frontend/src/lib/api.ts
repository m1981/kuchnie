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
};

export type FileItem = { path: string; name: string };

export type ChatImagePart = { mime_type: string; data: string };

export type ChatRequest = {
	session_id: string;
	message: string;
	system_prompt?: string | null;
	images?: ChatImagePart[] | null;
	context_files?: string[] | null;
};

export type ChatResponse = {
	text: string;
	tools_used: ToolLog[];
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

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
	// Sessions
	getSessions: () => request<SessionSummary[]>('/api/sessions'),

	getSession: (id: string) =>
		request<{ ui_messages: Message[] }>(`/api/sessions/${id}`),

	exportSession: (id: string) =>
		requestText(`/api/sessions/${id}/export`),

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
		request<ChatResponse>('/api/chat', json(payload))
};
