/**
 * lib/stores/provider.svelte.ts
 * ===============================
 * Rune-based store for provider/model selection and app branding.
 *
 * Responsibilities:
 *   - Provider catalog (live from API, fallback to static PROVIDERS)
 *   - Selected provider + model
 *   - App branding (title, description from /api/app-info)
 *
 * Independent — no cross-store dependencies.
 */

import { api }          from '$lib/api';
import { PROVIDERS, type ProviderInfo } from '$lib/providers';

function createProviderStore() {
	let providers        = $state<ProviderInfo[]>(PROVIDERS);
	let selectedProvider = $state<string>('');
	let selectedModel    = $state<string>('');
	let appTitle         = $state('Agentic Workspace');
	let appDescription   = $state('');

	return {
		get providers()        { return providers; },
		get selectedProvider() { return selectedProvider; },
		get selectedModel()    { return selectedModel; },
		get appTitle()         { return appTitle; },
		get appDescription()   { return appDescription; },

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

		async loadAppInfo() {
			try {
				const info = await api.getAppInfo();
				appTitle       = info.title;
				appDescription = info.description;
			} catch {
				// Backend not yet updated — keep generic defaults.
			}
		},

		async loadProviders() {
			try {
				const [providerList, active] = await Promise.all([
					api.getProviders(),
					api.getActiveProvider()
				]);

				if (providerList.length > 0) {
					providers = providerList;
				}

				if (!selectedProvider) selectedProvider = active.provider;
				if (!selectedModel)    selectedModel    = active.model;
			} catch {
				if (!selectedProvider && providers.length > 0) {
					selectedProvider = providers[0].id;
					selectedModel    = providers[0].default_model;
				}
			}
		},

		setProvider(id: string) {
			selectedProvider = id;
			const p = providers.find((p) => p.id === id);
			selectedModel = p?.default_model ?? '';
		},

		setModel(id: string) {
			selectedModel = id;
		},

		/**
		 * Sync picker to the provider/model from an assistant message.
		 * Called after session load and after each chat response.
		 */
		syncFromMessage(provider?: string, model?: string) {
			if (provider) selectedProvider = provider;
			if (model)    selectedModel    = model;
		},

		/**
		 * Reset to server defaults. Called on startNewChat.
		 * Provider/model selection intentionally kept — user's choice persists.
		 */
		resetSelection() {
			// Intentionally a no-op — provider selection persists across chats.
		}
	};
}

export const providerStore = createProviderStore();
