<script lang="ts">
	/**
	 * ComposerActions
	 * ===============
	 * Action buttons for the chat composer:
	 *   - Left: API Key placeholder + Tools toggle
	 *   - Center: Model selector
	 *   - Right: Speech-to-text, Add media, Send/Stop
	 */
	import { promptStore } from '$lib/stores/prompt.svelte';
	import type { ProviderInfo } from '$lib/providers';
	import ModelSelector from './ModelSelector.svelte';

	type Props = {
		providers: ProviderInfo[];
		selectedModel: string;
		onproviderchange: (provider: string, model: string) => void;
		isStreaming: boolean;
		onstop?: () => void;
		onsend: () => void;
		canSend: boolean;
	};

	let {
		providers,
		selectedModel,
		onproviderchange,
		isStreaming,
		onstop,
		onsend,
		canSend
	}: Props = $props();

	// ── Placeholder handler ────────────────────────────────────────────────
	let placeholderToast = $state('');

	function showPlaceholder(name: string) {
		placeholderToast = `${name} — coming soon`;
		setTimeout(() => {
			placeholderToast = '';
		}, 2000);
	}
</script>

<div class="buttons-row">
	<!-- Left: placeholder buttons + tools -->
	<div class="buttons-left">
		<!-- API Key placeholder -->
		<button
			type="button"
			class="icon-btn"
			onclick={() => showPlaceholder('API Key')}
			title="API Key"
			aria-label="API Key"
			disabled
		>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
			</svg>
		</button>

		<!-- Tools toggle -->
		<button
			type="button"
			class="tools-btn"
			class:tools-active={promptStore.toolsEnabled}
			onclick={() => promptStore.toggleTools()}
			aria-pressed={promptStore.toolsEnabled}
			title={promptStore.toolsEnabled ? 'Tools ON — LLM can read and edit your knowledge base' : 'Tools OFF — Direct LLM reply, no file access'}
		>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="3" y="3" width="7" height="7" rx="1" />
				<rect x="14" y="3" width="7" height="7" rx="1" />
				<rect x="3" y="14" width="7" height="7" rx="1" />
				<rect x="14" y="14" width="7" height="7" rx="1" />
			</svg>
			<span>{promptStore.toolsEnabled ? 'Tools' : 'Tools'}</span>
		</button>
	</div>

	<!-- Center: model selector -->
	<div class="buttons-center">
		<ModelSelector
			{providers}
			{selectedModel}
			{onproviderchange}
		/>
	</div>
	<div class="buttons-right">
		<!-- Speech-to-text placeholder -->
		<button
			type="button"
			class="icon-btn"
			onclick={() => showPlaceholder('Speech to text')}
			title="Speech to text"
			aria-label="Speech to text"
			disabled
		>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
				<path d="M19 10v2a7 7 0 0 1-14 0v-2" />
				<line x1="12" y1="19" x2="12" y2="23" />
				<line x1="8" y1="23" x2="16" y2="23" />
			</svg>
		</button>

		<!-- Add media placeholder -->
		<button
			type="button"
			class="icon-btn"
			onclick={() => showPlaceholder('Add media')}
			title="Insert images, videos, audio, or files"
			aria-label="Add media"
			disabled
		>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10" />
				<line x1="12" y1="8" x2="12" y2="16" />
				<line x1="8" y1="12" x2="16" y2="12" />
			</svg>
		</button>

		<!-- Send / Stop button -->
		{#if isStreaming}
			<button
				onclick={() => onstop?.()}
				data-testid="stop-btn"
				class="stop-btn"
			>
				<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
					<rect x="6" y="6" width="12" height="12" rx="2" />
				</svg>
				<span class="run-btn-label">Stop</span>
			</button>
		{:else}
			<button
				onclick={onsend}
				disabled={!canSend}
				data-testid="send-btn"
				class="run-btn"
			>
				<span class="run-btn-label">Run</span>
				<span class="run-btn-shortcut">
					<span class="key-icon">⌘</span>
					<span class="key-icon">↵</span>
				</span>
			</button>
		{/if}
	</div>
</div>

<!-- Placeholder toast -->
{#if placeholderToast}
	<div class="placeholder-toast">{placeholderToast}</div>
{/if}

<style>
	/* ── Buttons row ──────────────────────────────────────────────────── */

	.buttons-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 8px 12px;
		gap: 8px;
	}

	.buttons-left,
	.buttons-right {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.buttons-center {
		flex: 1;
		display: flex;
		justify-content: center;
	}

	/* ── Icon buttons (placeholders) ──────────────────────────────────── */

	.icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border-radius: 8px;
		border: none;
		background: transparent;
		color: #80868b;
		cursor: pointer;
		transition: background 0.15s;
	}

	.icon-btn:hover:not(:disabled) {
		background: #f1f3f4;
	}

	.icon-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}

	/* ── Tools button ─────────────────────────────────────────────────── */

	.tools-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		height: 32px;
		padding: 0 12px;
		border-radius: 8px;
		border: 1px solid #dadce0;
		background: #fff;
		color: #5f6368;
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.tools-btn:hover {
		background: #f8f9fa;
		border-color: #bdc1c6;
	}

	.tools-btn.tools-active {
		background: #e8f0fe;
		border-color: #4285f4;
		color: #1a73e8;
	}

	.tools-btn.tools-active:hover {
		background: #d2e3fc;
	}

	/* ── Run button ───────────────────────────────────────────────────── */

	.run-btn,
	.stop-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		height: 36px;
		padding: 0 16px;
		border-radius: 18px;
		border: none;
		background: #1a73e8;
		color: #fff;
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s, box-shadow 0.15s;
	}

	.run-btn:hover:not(:disabled) {
		background: #1557b0;
		box-shadow: 0 1px 3px rgba(26, 115, 232, 0.4);
	}

	.run-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.stop-btn {
		background: #ea4335;
	}

	.stop-btn:hover {
		background: #c5221f;
		box-shadow: 0 1px 3px rgba(234, 67, 53, 0.4);
	}

	.run-btn-label {
		font-weight: 600;
	}

	.run-btn-shortcut {
		display: flex;
		align-items: center;
		gap: 2px;
		opacity: 0.8;
	}

	.key-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		border-radius: 4px;
		background: rgba(255, 255, 255, 0.2);
		font-size: 11px;
		font-weight: 600;
	}

	/* ── Placeholder toast ────────────────────────────────────────────── */

	.placeholder-toast {
		position: fixed;
		bottom: 100px;
		left: 50%;
		transform: translateX(-50%);
		background: #323232;
		color: #fff;
		padding: 8px 16px;
		border-radius: 8px;
		font-size: 13px;
		z-index: 1000;
		animation: toast-in 0.2s ease;
	}

	@keyframes toast-in {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0);
		}
	}
</style>
