<script lang="ts">
	/**
	 * ChatComposer
	 * =============
	 * AI Studio-style composer with:
	 *   - Auto-resize textarea
	 *   - Left: [🔑 API Key] [🧩 Tools]
	 *   - Center: [Model selector ▾]
	 *   - Right: [🎤] [➕] [Run ⌘↵]
	 *
	 * Placeholder buttons (API Key, STT, Add Media) are grayed-out
	 * and show a tooltip "Coming soon" on click.
	 */

	import { chatStore } from '$lib/stores/chat.svelte';
	import { pasteImage } from '$lib/actions/pasteImage';
	import type { ProviderInfo } from '$lib/providers';
	import TokenIndicator from './TokenIndicator.svelte';
	import ComposerActions from './composer/ComposerActions.svelte';

	type Props = {
		providers: ProviderInfo[];
		selectedModel: string;
		onproviderchange: (provider: string, model: string) => void;
		// Streaming state
		isStreaming?: boolean;
		onstop?: () => void;
		// Bindable — parent can push notes into the textarea
		currentMessage?: string;
		textareaEl?: HTMLTextAreaElement | null;
	};

	let {
		providers,
		selectedModel,
		onproviderchange,
		isStreaming = false,
		onstop,
		currentMessage = $bindable(''),
		textareaEl = $bindable(null)
	}: Props = $props();

	// ── Auto-resize textarea ────────────────────────────────────────────────

	function autoResize(el: HTMLTextAreaElement) {
		function resize() {
			el.style.height = 'auto';
			el.style.height = Math.min(el.scrollHeight, 210) + 'px';
		}
		el.addEventListener('input', resize);
		resize();
		return {
			destroy() {
				el.removeEventListener('input', resize);
			}
		};
	}

	// Model selection logic is in ModelSelector.svelte

	// ── Context file display name ──────────────────────────────────────────
	function basename(path: string): string {
		return path.split('/').pop() ?? path;
	}

	// ── Send ──────────────────────────────────────────────────────────────

	function handleSend() {
		if (!currentMessage.trim() || chatStore.chatState.status === 'loading') return;
		const text = currentMessage;
		currentMessage = '';
		chatStore.sendMessage(text);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSend();
		}
	}
</script>

<footer class="composer-footer">
	<div class="composer-container">
		<!-- Pasted image previews -->
		{#if chatStore.pastedImages.length > 0}
			<div class="mb-2 flex flex-wrap gap-2">
				{#each chatStore.pastedImages as img, i (i)}
					<div class="group relative">
						<img
							src={img.dataUrl}
							alt="Pasted image {i + 1}"
							class="h-16 w-16 rounded border border-line object-cover shadow-sm"
						/>
						<button
							onclick={() => chatStore.removeImage(i)}
							class="absolute -top-1.5 -right-1.5 hidden h-4 w-4 items-center justify-center rounded-full bg-ink text-xs text-white group-hover:flex"
							aria-label="Remove image"
						>
							✕
						</button>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Context files strip -->
		{#if chatStore.contextFiles.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 px-3 pt-3 pb-2">
				<span class="text-xs text-muted">📎 Will inject:</span>
				{#each chatStore.contextFiles as path (path)}
					<span
						title={path}
						class="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent"
					>
						{basename(path)}
						<button
							onclick={() => {
								const next = chatStore.contextFiles.filter((p) => p !== path);
								chatStore.setContextFiles(next);
							}}
							aria-label="Remove {basename(path)} from context"
							class="ml-0.5 rounded-full text-accent/60 hover:text-accent">✕</button
						>
					</span>
				{/each}
			</div>
		{/if}

		<!-- Token indicator bar -->
		<TokenIndicator messageText={currentMessage} />

		<!-- Main composer box -->
		<div class="composer-box">
			<!-- Textarea row -->
			<div class="textarea-row">
				<textarea
					bind:this={textareaEl}
					bind:value={currentMessage}
					onkeydown={handleKeydown}
					use:pasteImage={chatStore.addPastedImage}
					use:autoResize
					data-testid="chat-input"
					placeholder="Ask about layouts, materials, fittings, assembly… or paste an image"
					rows="1"
				></textarea>
			</div>

			<!-- Buttons row -->
			<ComposerActions
				{providers}
				{selectedModel}
				{onproviderchange}
				{isStreaming}
				{onstop}
				onsend={handleSend}
				canSend={chatStore.chatState.status !== 'loading' && !!currentMessage.trim()}
			/>
		</div>
	</div>
</footer>

<style>
	/* ── Footer container ─────────────────────────────────────────────── */

	.composer-footer {
		border-top: 1px solid #e5e7eb;
		background: rgba(255, 255, 255, 0.95);
		backdrop-filter: blur(8px);
		padding: 8px 16px 12px;
	}

	.composer-container {
		max-width: 768px;
		margin: 0 auto;
	}

	/* ── Composer box ─────────────────────────────────────────────────── */

	.composer-box {
		border: 1px solid transparent;
		border-radius: 20px;
		background: var(--color-panel);
		box-shadow:
			0 0.25rem 1.25rem rgba(39, 35, 31, 0.08),
			0 0 0 0.5px rgba(222, 214, 202, 0.3);
		transition: box-shadow 0.2s;
	}

	.composer-box:hover {
		box-shadow:
			0 0.25rem 1.25rem rgba(39, 35, 31, 0.1),
			0 0 0 0.5px rgba(222, 214, 202, 0.5);
	}

	.composer-box:focus-within {
		box-shadow:
			0 0.25rem 1.25rem rgba(39, 35, 31, 0.12),
			0 0 0 0.5px rgba(138, 105, 57, 0.4);
	}

	/* ── Textarea row ─────────────────────────────────────────────────── */

	.textarea-row {
		padding: 12px 16px 0;
	}

	.textarea-row textarea {
		width: 100%;
		min-height: 21px;
		max-height: 210px;
		resize: none;
		border: none;
		outline: none;
		background: transparent;
		font-size: 14px;
		line-height: 24px;
		color: #1f1f1f;
		padding: 0;
		font-family: inherit;
	}

	.textarea-row textarea::placeholder {
		color: #80868b;
	}
</style>
