<script lang="ts">
	/**
	 * ProviderPicker
	 * ==============
	 * Compact two-level selector: provider dropdown → model dropdown.
	 *
	 * When no providers are loaded yet the component renders nothing —
	 * the parent pre-seeds the store with the static PROVIDERS catalog so
	 * this empty-state should never be visible in practice.
	 *
	 * When selectedProvider is empty ('') a "Server default" placeholder is
	 * shown instead of the dropdowns so the user understands they are using
	 * whatever the backend is configured with.
	 *
	 * Props:
	 *   providers        — full list of ProviderInfo entries (from store)
	 *   selectedProvider — currently active provider id, '' = server default
	 *   selectedModel    — currently active model id, '' = provider default
	 *   onchange         — called with (providerId, modelId) on any change
	 */

	import type { ProviderInfo } from '$lib/providers';

	type Props = {
		providers: ProviderInfo[];
		selectedProvider: string;
		selectedModel: string;
		onchange: (provider: string, model: string) => void;
	};

	let { providers, selectedProvider, selectedModel, onchange }: Props = $props();

	// The ProviderInfo entry that matches the current selection.
	const activeProvider = $derived(providers.find((p) => p.id === selectedProvider));

	// Label shown on the model option that is the provider's default.
	function modelLabel(m: { id: string; label: string; context_k: number }, isDefault: boolean) {
		return `${m.label} (${m.context_k}k)${isDefault ? ' ★' : ''}`;
	}

	function handleProviderChange(e: Event) {
		const pid = (e.target as HTMLSelectElement).value;
		const p   = providers.find((p) => p.id === pid);
		// Always reset to the provider's default_model on provider switch.
		onchange(pid, p?.default_model ?? '');
	}

	function handleModelChange(e: Event) {
		onchange(selectedProvider, (e.target as HTMLSelectElement).value);
	}
</script>

{#if providers.length === 0}
	<!-- Nothing to render until catalog loads — pre-seeded so this is instant -->
{:else if !selectedProvider}
	<!-- Empty-state: user hasn't selected anything, server default is active -->
	<span
		class="rounded border border-line bg-surface px-2 py-1 text-xs text-muted"
		title="The server's configured LLM_PROVIDER and model will be used"
	>
		Server default
	</span>
{:else}
	<div class="flex items-center gap-1.5" role="group" aria-label="LLM provider and model">

		<!-- ── Provider selector ──────────────────────────────────────────── -->
		<select
			value={selectedProvider}
			onchange={handleProviderChange}
			class="
				rounded border border-line bg-surface
				px-2 py-1 text-xs text-ink
				transition hover:border-accent focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent
				cursor-pointer
			"
			aria-label="LLM provider"
			title="Select LLM provider"
		>
			{#each providers as p (p.id)}
				<option value={p.id}>{p.label}</option>
			{/each}
		</select>

		<!-- ── Model selector — only shown when a provider is resolved ────── -->
		{#if activeProvider}
			<select
				value={selectedModel}
				onchange={handleModelChange}
				class="
					rounded border border-line bg-surface
					px-2 py-1 text-xs text-ink
					transition hover:border-accent focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent
					cursor-pointer
				"
				aria-label="Model"
				title="Select model for {activeProvider.label}"
			>
				{#each activeProvider.models as m (m.id)}
					<option value={m.id}>
						{modelLabel(m, m.id === activeProvider.default_model)}
					</option>
				{/each}
			</select>
		{/if}

	</div>
{/if}
