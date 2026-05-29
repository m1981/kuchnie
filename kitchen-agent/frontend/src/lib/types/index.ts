/**
 * lib/types/index.ts
 * ===================
 * Local-only types that are not part of the API contract.
 *
 * API types (Message, Note, PromptMode, …) live in $lib/api.ts.
 * These types describe UI-only shapes used inside the frontend stores
 * and components.
 */

export type { AsyncState } from './states';

/** An image the user pasted with Ctrl+V, held in memory until the message is sent. */
export type PastedImage = {
	/** data-URL used for the in-UI thumbnail preview (never sent to the backend). */
	dataUrl: string;
	/** MIME type extracted from the data-URL header, e.g. "image/png". */
	mimeType: string;
	/** Raw base64 string (no header), sent to the API in the ChatRequest. */
	base64: string;
};

/** Floating note popup state — null means the popup is hidden. */
export type NotePopupState = {
	text: string;
	x: number;
	y: number;
	sourceRole: 'user' | 'assistant';
} | null;

/** Floating append-to-docs popup state — null means the popup is hidden. */
export type AppendPopupState = {
	text: string;
	x: number;
	y: number;
} | null;
