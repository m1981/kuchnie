<script lang="ts">
	/**
	 * ChatComposer
	 * =============
	 * The full input area at the bottom of the chat:
	 *   - Drag-to-resize handle
	 *   - Pasted image thumbnail strip
	 *   - Textarea (with paste-image action + Enter-to-send)
	 *   - Send button
	 *   - Mode pill strip (bottom toolbar)
	 *   - "New chat" shortcut pill
	 *   - Context files status strip (names of files queued for injection)
	 *
	 * State it owns:
	 *   - `currentMessage` — the typed text in the textarea
	 *   - ref to the <textarea> element for programmatic focus
	 *
	 * Everything else (modes, pastedImages, chatState) comes from chatStore
	 * or is received as a prop.
	 *
	 * Props:
	 *   promptHeight    — textarea height in px (from sidebarResize store)
	 *   onStartDrag     — mousedown on the resize handle
	 *   onDblClickReset — dblclick on the resize handle
	 *   onResizeKeydown — keydown on the resize handle
	 *   onnewchat       — "New chat" shortcut clicked
	 *
	 * Bindable:
	 *   currentMessage  — so the parent can inject notes into the composer
	 *   textareaEl      — so the parent can focus it programmatically
	 */

	import { chatStore } from '$lib/stores/chat.svelte';
	import { pasteImage } from '$lib/actions/pasteImage';
	import type { PromptMode } from '$lib/api';

	type Props = {
		modes: PromptMode[];
		promptHeight: number;
		onStartDrag: (e: MouseEvent) => void;
		onDblClickReset: () => void;
		onResizeKeydown: (e: KeyboardEvent) => void;
		onnewchat: () => void;
		// Bindable — parent can push notes into the textarea
		currentMessage?: string;
		textareaEl?: HTMLTextAreaElement | null;
	};

	let {
		modes,
		promptHeight,
		onStartDrag,
		onDblClickReset,
		onResizeKeydown,
		onnewchat,
		currentMessage = $bindable(''),
		textareaEl = $bindable(null)
	}: Props = $props();

	// ── Mode icon map ─────────────────────────────────────────────────────────

	const MODE_ICONS: Record<string, string> = {
		general: '🔧',
		design: '📐',
		assembly: '🔨'
	};

	function modeIcon(id: string): string {
		return MODE_ICONS[id] ?? '💬';
	}

	// ── Context file display name ─────────────────────────────────────────────
	/** Extract just the filename from a path for display. */
	function basename(path: string): string {
		return path.split('/').pop() ?? path;
	}

	// ── Send ──────────────────────────────────────────────────────────────────

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

<footer class="border-t border-line bg-panel/95 px-4 py-4 backdrop-blur md:px-6">
	<div class="mx-auto max-w-5xl">

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

		<!-- Composer box -->
		<div class="relative rounded-md border border-line bg-surface shadow-sm">

			<!-- Drag-to-resize handle (top of the box) -->
			<button
				type="button"
				aria-label="Resize prompt area"
				class="absolute -top-1 left-0 z-20 h-2 w-full cursor-row-resize touch-none rounded-t-md transition hover:bg-accent/30 focus:bg-accent/30 focus:outline-none"
				onmousedown={onStartDrag}
				ondblclick={onDblClickReset}
				onkeydown={onResizeKeydown}
				title="Drag to resize. Double-click to reset."
			></button>

			<!-- Context files strip — shown above textarea when files are queued -->
			{#if chatStore.contextFiles.length > 0}
				<div class="flex flex-wrap items-center gap-1.5 border-b border-line px-3 pt-3 pb-2">
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
								class="ml-0.5 rounded-full text-accent/60 hover:text-accent"
							>✕</button>
						</span>
					{/each}
				</div>
			{/if}

			<!-- Textarea + Send button -->
			<div class="flex items-end gap-2 px-2 pt-3 pb-2">
				<label class="sr-only" for="message-input">Message</label>
				<textarea
					id="message-input"
					bind:this={textareaEl}
					bind:value={currentMessage}
					onkeydown={handleKeydown}
					use:pasteImage={chatStore.addPastedImage}
					placeholder="Ask about layouts, materials, fittings, assembly… or paste an image with Ctrl+V"
					class="min-h-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink placeholder:text-muted focus:outline-none"
					style="height: {promptHeight}px;"
					rows="2"
				></textarea>

				<button
					onclick={handleSend}
					disabled={chatStore.chatState.status === 'loading' || !currentMessage.trim()}
					class="h-10 rounded-md bg-accent px-4 text-sm font-semibold text-white transition hover:bg-accent-strong focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-45"
				>
					Send
				</button>
			</div>

			<!-- Mode pill strip -->
			<div
				class="flex items-center gap-1 border-t border-line px-3 py-2"
				role="group"
				aria-label="Prompt mode"
			>
				{#if chatStore.modesState.status === 'loading'}
					<!-- Skeleton shimmer while modes load from the backend -->
					<span class="h-7 w-20 animate-pulse rounded-full bg-line"></span>
					<span class="h-7 w-16 animate-pulse rounded-full bg-line"></span>
					<span class="h-7 w-20 animate-pulse rounded-full bg-line"></span>
				{:else}
					{#each modes as mode (mode.id)}
						<button
							type="button"
							role="radio"
							aria-checked={chatStore.selectedModeId === mode.id}
							title={mode.eyebrow}
							onclick={() => chatStore.setSelectedModeId(mode.id)}
							class="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1
								{chatStore.selectedModeId === mode.id
									? 'border-accent bg-accent text-white shadow-sm'
									: 'border-line bg-transparent text-muted hover:border-accent/60 hover:bg-accent/8 hover:text-ink'}"
						>
							<span aria-hidden="true">{modeIcon(mode.id)}</span>
							{mode.label}
						</button>
					{/each}
				{/if}

				<!-- Spacer pushes "New chat" to the right -->
				<span class="flex-1"></span>

				<button
					onclick={onnewchat}
					class="rounded-full border border-line px-3 py-1 text-xs font-semibold text-muted transition hover:border-accent/60 hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
					title="Start a new conversation"
				>
					+ New chat
				</button>
			</div>
		</div>
	</div>
</footer>
