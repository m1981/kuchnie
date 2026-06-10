/**
 * lib/stores/prompt.svelte.ts
 * =============================
 * Rune-based store for prompt modes and tools toggle.
 *
 * Responsibilities:
 *   - Prompt mode list (loaded from /api/prompts/modes)
 *   - Selected mode ID
 *   - Tools enabled toggle (synced to mode default, user-overridable)
 *
 * Independent — no cross-store dependencies.
 */

import { api, type PromptMode } from '$lib/api';
import type { AsyncState } from '$lib/types';

function createPromptStore() {
	let selectedModeId = $state('general');
	let modesState     = $state<AsyncState<void>>({ status: 'idle' });
	let toolsEnabled   = $state<boolean>(true);

	return {
		get selectedModeId() { return selectedModeId; },
		get modesState()     { return modesState; },
		get toolsEnabled()   { return toolsEnabled; },

		async loadModes(): Promise<PromptMode[]> {
			if (modesState.status === 'loading') return [];
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
				return fetched;
			} catch (e) {
				console.error('Failed to load prompt modes', e);
				modesState = { status: 'error', message: String(e) };
				return [];
			}
		},

		setSelectedModeId(id: string, modes?: PromptMode[]) {
			if (id === selectedModeId) return;
			selectedModeId = id;
			// Sync toolsEnabled to the new mode's default when provided.
			if (modes) {
				const mode = modes.find((m) => m.id === id);
				if (mode !== undefined) toolsEnabled = mode.tools_enabled_default ?? true;
			}
		},

		toggleTools() {
			toolsEnabled = !toolsEnabled;
		},

		setToolsEnabled(value: boolean) {
			toolsEnabled = value;
		},

		/** Reset to defaults. Called on startNewChat. */
		reset() {
			// Mode and tools persist across chats — nothing to reset.
		}
	};
}

export const promptStore = createPromptStore();
