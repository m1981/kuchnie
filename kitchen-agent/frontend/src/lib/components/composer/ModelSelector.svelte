<script lang="ts">
	/**
	 * ModelSelector
	 * =============
	 * Custom dropdown for picking an LLM model grouped by provider.
	 * Shows bottom sheet on mobile, popover on desktop.
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

	type ModelGroup = {
		providerId: string;
		providerLabel: string;
		models: { id: string; label: string; context_k: number }[];
	};

	const modelGroups: ModelGroup[] = $derived(
		providers.map((p) => ({
			providerId: p.id,
			providerLabel: p.label,
			models: p.models.map((m) => ({ id: m.id, label: m.label, context_k: m.context_k }))
		}))
	);

	const currentModel = $derived(allModels.find((m) => m.id === selectedModel) ?? allModels[0]);

	let isOpen = $state(false);
	let dropdownEl = $state<HTMLDivElement | null>(null);

	function selectModel(model: FlatModel) {
		onproviderchange(model.providerId, model.id);
		isOpen = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			isOpen = false;
		}
	}

	function handleClickOutside(e: MouseEvent) {
		if (dropdownEl && !dropdownEl.contains(e.target as Node)) {
			isOpen = false;
		}
	}
</script>

<svelte:window onclick={handleClickOutside} onkeydown={handleKeydown} />

{#if allModels.length > 0}
	<div class="model-selector" bind:this={dropdownEl}>
		<!-- Trigger button -->
		<button
			type="button"
			class="model-trigger"
			onclick={() => (isOpen = !isOpen)}
			aria-haspopup="listbox"
			aria-expanded={isOpen}
			aria-label="Select model"
		>
			<span class="model-name">{currentModel?.label ?? 'Select model'}</span>
			<svg
				class="chevron"
				class:rotate-180={isOpen}
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<polyline points="6 9 12 15 18 9" />
			</svg>
		</button>

		<!-- Desktop dropdown -->
		{#if isOpen}
			<div class="dropdown" role="listbox" aria-label="Available models">
				{#each modelGroups as group (group.providerId)}
					<div class="group">
						<div class="group-header">{group.providerLabel}</div>
						{#each group.models as model (model.id)}
							<button
								type="button"
								class="model-option"
								class:selected={model.id === currentModel?.id}
								onclick={() =>
									selectModel({
										id: model.id,
										label: model.label,
										providerId: group.providerId,
										providerLabel: group.providerLabel,
										context_k: model.context_k
									})}
								role="option"
								aria-selected={model.id === currentModel?.id}
							>
								<span class="option-label">{model.label}</span>
								<span class="option-context">{(model.context_k / 1000).toFixed(0)}K</span>
							</button>
						{/each}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<!-- Mobile bottom sheet -->
{#if isOpen}
	<div class="mobile-overlay" role="dialog" aria-label="Select model">
		<div
			class="mobile-backdrop"
			onclick={() => (isOpen = false)}
			onkeydown={(e) => e.key === 'Escape' && (isOpen = false)}
			role="button"
			tabindex="-1"
		></div>
		<div class="mobile-sheet">
			<div class="mobile-header">
				<span class="mobile-title">Select Model</span>
				<button type="button" class="mobile-close" onclick={() => (isOpen = false)}>
					<svg
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M18 6L6 18M6 6l12 12" />
					</svg>
				</button>
			</div>
			<div class="mobile-body">
				{#each modelGroups as group (group.providerId)}
					<div class="mobile-group">
						<div class="mobile-group-header">{group.providerLabel}</div>
						{#each group.models as model (model.id)}
							<button
								type="button"
								class="mobile-option"
								class:selected={model.id === currentModel?.id}
								onclick={() =>
									selectModel({
										id: model.id,
										label: model.label,
										providerId: group.providerId,
										providerLabel: group.providerLabel,
										context_k: model.context_k
									})}
							>
								<span class="mobile-option-label">{model.label}</span>
								<span class="mobile-option-context">{(model.context_k / 1000).toFixed(0)}K</span>
								{#if model.id === currentModel?.id}
									<svg
										class="mobile-check"
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
									>
										<polyline points="20 6 9 17 4 12" />
									</svg>
								{/if}
							</button>
						{/each}
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}

<style>
	/* ── Shared font settings ────────────────────────────────────────── */
	/* All elements inherit from body: Inter, system-ui, 15px base       */

	/* ── Trigger button ──────────────────────────────────────────────── */

	.model-selector {
		position: relative;
	}

	.model-trigger {
		display: flex;
		align-items: center;
		gap: 4px;
		height: 36px;
		padding: 0 10px;
		border-radius: 8px;
		border: 1px solid #dadce0;
		background: #fff;
		color: #5f6368;
		font-family: inherit;
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
		max-width: 180px;
	}

	.model-trigger:hover {
		background: #f8f9fa;
		border-color: #bdc1c6;
	}

	.model-name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.chevron {
		width: 14px;
		height: 14px;
		flex-shrink: 0;
		transition: transform 0.2s;
	}

	/* ── Desktop dropdown ────────────────────────────────────────────── */

	.dropdown {
		position: absolute;
		bottom: 100%;
		left: 0;
		min-width: 220px;
		max-height: 320px;
		overflow-y: auto;
		background: #fff;
		border: 1px solid #dadce0;
		border-radius: 12px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		z-index: 50;
		margin-bottom: 4px;
	}

	.group {
		padding: 4px 0;
	}

	.group:not(:last-child) {
		border-bottom: 1px solid #f1f3f4;
	}

	.group-header {
		padding: 8px 12px 4px;
		font-family: inherit;
		font-size: 11px;
		font-weight: 600;
		color: #80868b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.model-option {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 10px 12px;
		border: none;
		background: transparent;
		text-align: left;
		cursor: pointer;
		transition: background 0.1s;
		font-family: inherit;
	}

	.model-option:hover {
		background: #f1f3f4;
	}

	.model-option.selected {
		background: #e8f0fe;
	}

	.option-label {
		font-size: 13px;
		color: #202124;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.option-context {
		font-size: 11px;
		color: #80868b;
		white-space: nowrap;
		flex-shrink: 0;
		margin-left: 8px;
	}

	/* ── Mobile bottom sheet ─────────────────────────────────────────── */

	.mobile-overlay {
		display: none;
	}

	@media (max-width: 1023px) {
		.dropdown {
			display: none;
		}

		.mobile-overlay {
			display: block;
			position: fixed;
			inset: 0;
			z-index: 100;
		}

		.mobile-backdrop {
			position: absolute;
			inset: 0;
			background: rgba(0, 0, 0, 0.4);
		}

		.mobile-sheet {
			position: absolute;
			bottom: 0;
			left: 0;
			right: 0;
			background: #fff;
			border-radius: 16px 16px 0 0;
			max-height: 70vh;
			display: flex;
			flex-direction: column;
			animation: slide-up 0.2s ease-out;
		}

		@keyframes slide-up {
			from {
				transform: translateY(100%);
			}
			to {
				transform: translateY(0);
			}
		}

		.mobile-header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 16px;
			border-bottom: 1px solid #e5e7eb;
		}

		.mobile-title {
			font-family: inherit;
			font-size: 16px;
			font-weight: 600;
			color: #111827;
		}

		.mobile-close {
			display: flex;
			align-items: center;
			justify-content: center;
			width: 32px;
			height: 32px;
			border: none;
			background: #f3f4f6;
			border-radius: 50%;
			color: #6b7280;
			cursor: pointer;
		}

		.mobile-body {
			overflow-y: auto;
			padding: 8px 0;
		}

		.mobile-group {
			padding: 4px 0;
		}

		.mobile-group:not(:last-child) {
			border-bottom: 1px solid #f3f4f6;
		}

		.mobile-group-header {
			padding: 12px 16px 8px;
			font-family: inherit;
			font-size: 11px;
			font-weight: 600;
			color: #6b7280;
			text-transform: uppercase;
			letter-spacing: 0.05em;
		}

		.mobile-option {
			display: flex;
			align-items: center;
			width: 100%;
			padding: 14px 16px;
			min-height: 48px;
			border: none;
			background: transparent;
			text-align: left;
			cursor: pointer;
			transition: background 0.1s;
			font-family: inherit;
			gap: 8px;
		}

		.mobile-option:hover {
			background: #f9fafb;
		}

		.mobile-option.selected {
			background: #eff6ff;
		}

		.mobile-option-label {
			font-size: 15px;
			color: #111827;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
			flex: 1;
			min-width: 0;
		}

		.mobile-option-context {
			font-size: 12px;
			color: #6b7280;
			white-space: nowrap;
			flex-shrink: 0;
		}

		.mobile-check {
			color: #3b82f6;
			flex-shrink: 0;
		}
	}
</style>
