<script lang="ts">
	/**
	 * ModelSelector
	 * =============
	 * Optgroup <select> for picking an LLM model grouped by provider.
	 *
	 * Props:
	 *   providers         — list of provider metadata from the API
	 *   selectedModel     — currently selected model ID
	 *   onproviderchange  — called with (providerId, modelId) on change
	 */
	import type { ProviderInfo } from '$lib/providers';

	type Props = {
		providers: ProviderInfo[];
		selectedModel: string;
		onproviderchange: (provider: string, model: string) => void;
	};

	let { providers, selectedModel, onproviderchange }: Props = $props();

	/** Flat list of all models across all providers. */
	type FlatModel = {
		id: string;
		label: string;
		providerId: string;
		providerLabel: string;
		context_k: number;
	};

	const allModels: FlatModel[] = $derived(
		providers.flatMap((p) =>
			p.models.map((m) => ({
				id: m.id,
				label: m.label,
				providerId: p.id,
				providerLabel: p.label,
				context_k: m.context_k
			}))
		)
	);

	/** Group models by provider for optgroup rendering. */
	type ModelGroup = {
		providerId: string;
		providerLabel: string;
		models: { id: string; label: string }[];
	};

	const modelGroups: ModelGroup[] = $derived(
		providers.map((p) => ({
			providerId: p.id,
			providerLabel: p.label,
			models: p.models.map((m) => ({ id: m.id, label: m.label }))
		}))
	);

	/** Currently selected model id. Falls back to first available. */
	const currentModelId = $derived(
		allModels.some((m) => m.id === selectedModel) ? selectedModel : (allModels[0]?.id ?? '')
	);

	function handleChange(e: Event) {
		const modelId = (e.target as HTMLSelectElement).value;
		const flat = allModels.find((m) => m.id === modelId);
		if (flat) {
			onproviderchange(flat.providerId, modelId);
		}
	}
</script>

{#if allModels.length > 0}
	<select value={currentModelId} onchange={handleChange} class="model-select" aria-label="Model">
		{#each modelGroups as group (group.providerId)}
			<optgroup label={group.providerLabel}>
				{#each group.models as m (m.id)}
					<option value={m.id}>{m.label}</option>
				{/each}
			</optgroup>
		{/each}
	</select>
{/if}

<style>
	.model-select {
		height: 32px;
		padding: 0 8px;
		border-radius: 8px;
		border: 1px solid #dadce0;
		background: #fff;
		color: #5f6368;
		font-size: 12px;
		cursor: pointer;
		transition: all 0.15s;
		appearance: none;
		-webkit-appearance: none;
		background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%235f6368' d='M3 4.5L6 8l3-3.5H3z'/%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 6px center;
		padding-right: 22px;
	}

	.model-select:hover {
		background-color: #f8f9fa;
		border-color: #bdc1c6;
	}

	.model-select:focus {
		outline: none;
		border-color: #4285f4;
		box-shadow: 0 0 0 1px #4285f4;
	}
</style>
