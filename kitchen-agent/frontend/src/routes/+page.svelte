<script lang="ts">
	import { api, type FileItem, type Message, type Note, type PromptMode, type PromptModeDetail, type ToolLog } from '$lib/api';
	import Markdown from '$lib/components/Markdown.svelte';
	import ContextSidebar from '$lib/components/ContextSidebar.svelte';
	import SessionTree from '$lib/components/SessionTree.svelte';
	import NotePopup from '$lib/components/NotePopup.svelte';
	import { createSidebarResize } from '$lib/sidebar-resize.svelte';
	import { sessionStore } from '$lib/stores/sessions.svelte';

	// ---------------------------------------------------------------------------
	// Local-only types
	// ---------------------------------------------------------------------------

	type PastedImage = {
		dataUrl: string;  // for in-UI preview only
		mimeType: string;
		base64: string;   // raw base64 sent to the API
	};

	type NotePopupState = {
		text: string;
		x: number;
		y: number;
		sourceRole: 'user' | 'assistant';
	} | null;

	// ---------------------------------------------------------------------------
	// State
	// ---------------------------------------------------------------------------

	let sessionId      = $state(crypto.randomUUID());
	let currentMessage = $state('');
	let messageInput   = $state<HTMLTextAreaElement | null>(null);
	let messages       = $state<Message[]>([]);
	let isLoading      = $state(false);

	// F05 — prompt modes fetched from the backend; no hardcoded strings here
	let modes          = $state<PromptMode[]>([]);
	let modesLoading   = $state(true);
	let selectedModeId = $state('general');

	// Prompt inspector — lazy-loaded full content, fetched on first expand.
	// BUG FIX: promptDetail is now invalidated reactively via $effect whenever
	// selectedModeId changes, so the inspector always shows the correct prompt
	// regardless of whether the <details> element is open or closed.
	let promptDetail        = $state<PromptModeDetail | null>(null);
	let promptDetailLoading = $state(false);
	let promptDetailError   = $state('');
	let promptDetailForId   = $state('');

	// Inspector open/close — tracked in JS so we can force-refresh content
	// when the mode changes while the panel is already open.
	let promptInspectorOpen = $state(false);

	// Layout
	const sidebarResize = createSidebarResize();
	let contextFiles = $state<string[]>([]);

	// Pasted images
	let pastedImages = $state<PastedImage[]>([]);

	// Highlight → Append to docs
	let appendTarget          = $state('');
	let appendFiles           = $state<FileItem[]>([]);
	let appendPopup           = $state<{ text: string; x: number; y: number } | null>(null);
	let appendStatus          = $state('');
	let suppressNextClickAway = $state(false);

	// Highlight → Note popup
	let notePopup = $state<NotePopupState>(null);

	// Fork
	let forkStatus = $state('');

	// ---------------------------------------------------------------------------
	// Mode icon map — purely presentational, resolved client-side
	// ---------------------------------------------------------------------------

	const MODE_ICONS: Record<string, string> = {
		general:  '🔧',
		design:   '📐',
		assembly: '🔨',
	};

	function modeIcon(id: string): string {
		return MODE_ICONS[id] ?? '💬';
	}

	// ---------------------------------------------------------------------------
	// Derived — resolved from the live backend modes list
	// ---------------------------------------------------------------------------

	const activeMode = $derived(
		modes.find((m) => m.id === selectedModeId)
			?? { id: selectedModeId, label: selectedModeId, eyebrow: '' }
	);

	// ---------------------------------------------------------------------------
	// Lifecycle — runs once on mount; no $state reads so no re-runs
	// ---------------------------------------------------------------------------

	$effect(() => {
		void sessionStore.refresh();
		void fetchFileList();
		void loadModes();
	});

	// ---------------------------------------------------------------------------
	// BUG FIX — invalidate prompt inspector cache when mode changes.
	//
	// The old code relied solely on the <details> ontoggle event to fetch
	// prompt content. If the panel was already open when the user switched
	// mode, ontoggle never fired, so the panel kept showing the previous
	// mode's content — making it look like the selection had no effect.
	//
	// This $effect reads selectedModeId (tracked) and promptDetailForId
	// (tracked). Whenever selectedModeId differs from what we last fetched,
	// we clear the stale cache. If the inspector is currently open we
	// immediately kick off a fresh fetch so the content updates in place.
	// ---------------------------------------------------------------------------

	$effect(() => {
		const current = selectedModeId;           // tracked
		if (promptDetailForId === current) return; // already correct — nothing to do

		// Invalidate stale cache
		promptDetail      = null;
		promptDetailError = '';
		promptDetailForId = '';

		// Re-fetch immediately only when the inspector panel is open
		if (promptInspectorOpen) {
			void loadPromptDetail();
		}
	});

	// ---------------------------------------------------------------------------
	// Prompt mode loading (list + detail)
	// ---------------------------------------------------------------------------

	async function loadModes() {
		modesLoading = true;
		try {
			const fetched = await api.getPromptModes();
			modes = fetched;
			// keep selectedModeId when still valid, otherwise fall back to first mode
			if (fetched.length > 0 && !fetched.find((m) => m.id === selectedModeId)) {
				selectedModeId = fetched[0].id;
			}
		} catch (e) {
			console.error('Failed to load prompt modes', e);
		} finally {
			modesLoading = false;
		}
	}

	/**
	 * Fetches the full prompt content for selectedModeId.
	 * Guards against concurrent calls and skips when already loaded
	 * for the current mode.
	 */
	async function loadPromptDetail() {
		if (promptDetailLoading) return;
		if (promptDetail && promptDetailForId === selectedModeId) return;

		promptDetailLoading = true;
		promptDetailError   = '';
		promptDetail        = null;
		try {
			promptDetail      = await api.getPromptModeDetail(selectedModeId);
			promptDetailForId = selectedModeId;
		} catch (e) {
			promptDetailError = e instanceof Error ? e.message : 'Failed to load prompt.';
		} finally {
			promptDetailLoading = false;
		}
	}

	/**
	 * Called by the <details> ontoggle handler.
	 * Syncs promptInspectorOpen so the $effect above knows when to
	 * eagerly re-fetch after a mode switch while the panel is open.
	 */
	function handleInspectorToggle(e: Event) {
		promptInspectorOpen = (e.target as HTMLDetailsElement).open;
		if (promptInspectorOpen) void loadPromptDetail();
	}

	async function fetchFileList() {
		try {
			appendFiles = await api.listFiles();
		} catch (e) {
			console.error('Failed to fetch file list', e);
		}
	}

	// ---------------------------------------------------------------------------
	// Session management
	// ---------------------------------------------------------------------------

	async function loadSession(id: string) {
		try {
			const data = await api.getSession(id);
			sessionId = id as ReturnType<typeof crypto.randomUUID>;
			messages  = data.ui_messages || [];
		} catch (e) {
			console.error('Failed to load session', e);
		}
	}

	function startNewChat() {
		sessionId      = crypto.randomUUID();
		messages       = [];
		currentMessage = '';
		pastedImages   = [];
	}

	async function forkSession(turnIndex: number) {
		forkStatus = '';
		try {
			const data = await api.forkSession(sessionId, turnIndex);
			await loadSession(data.new_session_id);
			await sessionStore.refresh();
			forkStatus = `Forked at turn ${turnIndex}`;
		} catch (e) {
			forkStatus = `Fork failed: ${e}`;
		}
	}

	// ---------------------------------------------------------------------------
	// Helpers
	// ---------------------------------------------------------------------------

	function formatToolResult(tool: ToolLog): string {
		return (tool.result.content as string | undefined) ?? JSON.stringify(tool.result, null, 2);
	}

	function handleContextChange(paths: string[]) {
		contextFiles = paths;
	}

	function formatNotesForPrompt(notes: Note[]): string {
		const lines = notes.map((note, index) => {
			const annotation = note.note.trim()
				? `\nComment: ${note.note.trim()}`
				: '';
			return [
				`### Note ${index + 1} (${note.source_role})`,
				`Selected text:`,
				`> ${note.selected_text.replace(/\n/g, '\n> ')}`,
				annotation
			].join('\n');
		});

		return [
			'Here are my selected notes with comments. Please comment and explain.',
			'',
			'## Selected notes',
			'',
			lines.join('\n\n')
		].join('\n');
	}

	function insertNotesIntoComposer(notes: Note[]) {
		const block = formatNotesForPrompt(notes);
		currentMessage = currentMessage.trim()
			? `${currentMessage.trimEnd()}\n\n${block}`
			: block;

		requestAnimationFrame(() => {
			messageInput?.focus();
			messageInput?.setSelectionRange(currentMessage.length, currentMessage.length);
		});
	}

	// ---------------------------------------------------------------------------
	// Image paste (Ctrl+V)
	// ---------------------------------------------------------------------------

	function handlePaste(event: ClipboardEvent) {
		const items = event.clipboardData?.items;
		if (!items) return;
		for (const item of Array.from(items)) {
			if (!item.type.startsWith('image/')) continue;
			event.preventDefault();
			const file = item.getAsFile();
			if (!file) continue;
			const reader = new FileReader();
			reader.onload = (e) => {
				const dataUrl          = e.target?.result as string;
				const [header, base64] = dataUrl.split(',');
				const mimeType         = header.split(':')[1].split(';')[0];
				pastedImages = [...pastedImages, { dataUrl, mimeType, base64 }];
			};
			reader.readAsDataURL(file);
		}
	}

	function removeImage(index: number) {
		pastedImages = pastedImages.filter((_, i) => i !== index);
	}

	// ---------------------------------------------------------------------------
	// Highlight → Add to Docs
	// ---------------------------------------------------------------------------

	function popupPosition(event: MouseEvent, width = 288, height = 220) {
		const gap = 12;
		return {
			x: Math.min(Math.max(event.clientX, gap), window.innerWidth - width - gap),
			y: Math.min(Math.max(event.clientY - 48, gap), window.innerHeight - height - gap)
		};
	}

	function nodeElement(node: Node | null): HTMLElement | null {
		if (!node) return null;
		return node instanceof HTMLElement ? node : node.parentElement;
	}

	function selectedChatText(): { text: string; sourceRole: 'user' | 'assistant' } | null {
		const selection = window.getSelection();
		const text = selection?.toString().trim();
		if (!selection || selection.rangeCount === 0 || !text || text.length < 5) return null;

		const anchorBubble = nodeElement(selection.anchorNode)?.closest<HTMLElement>('[data-chat-bubble]');
		const focusBubble  = nodeElement(selection.focusNode)?.closest<HTMLElement>('[data-chat-bubble]');
		const bubble = anchorBubble ?? focusBubble;
		if (!bubble || (anchorBubble && focusBubble && anchorBubble !== focusBubble)) return null;

		const role = bubble.dataset.chatBubble;
		if (role !== 'user' && role !== 'assistant') return null;
		return { text, sourceRole: role };
	}

	function handleMouseUp(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (target.closest('button, input, textarea, select, .note-popup, .append-popup')) return;

		const chatSelection = selectedChatText();
		if (chatSelection) {
			const { x, y } = popupPosition(event);
			notePopup   = { ...chatSelection, x, y };
			appendPopup = null;
			suppressNextClickAway = true;
			return;
		}

		const text = window.getSelection()?.toString().trim();
		if (!text || text.length < 5) { appendPopup = null; return; }
		const { x, y } = popupPosition(event, 300, 120);
		appendPopup = { text, x, y };
		notePopup   = null;
		suppressNextClickAway = true;
	}

	function dismissAppendPopup() { appendPopup = null; }
	function dismissNotePopup()   { notePopup   = null; }

	async function appendToDoc() {
		if (!appendPopup || !appendTarget) return;
		const snippet = `\n## Snippet (from chat)\n\n${appendPopup.text}\n`;
		appendStatus = '';
		try {
			await api.appendToFile(appendTarget, snippet);
			appendStatus = `✓ Added to ${appendTarget}`;
			appendPopup  = null;
			setTimeout(() => (appendStatus = ''), 3000);
		} catch (e) {
			appendStatus = `Failed: ${e}`;
		}
	}

	// ---------------------------------------------------------------------------
	// Send message — F05: sends mode_id; backend resolves it to full prompt
	// ---------------------------------------------------------------------------

	async function sendMessage() {
		if (!currentMessage.trim() || isLoading) return;

		const promptToSend = currentMessage.trim();
		const imagesToSend = [...pastedImages];

		messages.push({
			role:    'user',
			content: promptToSend,
			images:  imagesToSend.map((i) => i.dataUrl)
		});
		currentMessage = '';
		pastedImages   = [];
		isLoading      = true;

		try {
			const data = await api.chat({
				session_id:    sessionId,
				message:       promptToSend,
				mode_id:       selectedModeId,
				images:
					imagesToSend.length > 0
						? imagesToSend.map((i) => ({ mime_type: i.mimeType, data: i.base64 }))
						: null,
				context_files: contextFiles.length > 0 ? contextFiles : null
			});

			messages.push({
				role:    'assistant',
				content: data.text,
				tools:   data.tools_used
			});

			await sessionStore.refresh();
		} catch (error) {
			const msg =
				error instanceof Error ? error.message : 'Unknown error connecting to API.';
			messages.push({ role: 'assistant', content: `⚠️ Error: ${msg}` });
		} finally {
			isLoading = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}

	function handleSidebarResizeKeydown(event: KeyboardEvent, side: 'left' | 'right') {
		if (!['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) return;
		event.preventDefault();
		const step = event.shiftKey ? 40 : 16;

		if (event.key === 'Home') {
			side === 'left' ? sidebarResize.resetLeft() : sidebarResize.resetRight();
			return;
		}
		const direction = event.key === 'ArrowRight' ? 1 : -1;
		if (side === 'left') {
			sidebarResize.resizeLeftBy(direction * step);
		} else {
			sidebarResize.resizeRightBy(direction * -step);
		}
	}

	function handlePromptResizeKeydown(event: KeyboardEvent) {
		if (!['ArrowUp', 'ArrowDown', 'Home'].includes(event.key)) return;
		event.preventDefault();
		const step = event.shiftKey ? 40 : 16;

		if (event.key === 'Home') {
			sidebarResize.resetPrompt();
			return;
		}
		sidebarResize.resizePromptBy(event.key === 'ArrowUp' ? step : -step);
	}
</script>

<svelte:head>
	<title>Kitchen Agent</title>
</svelte:head>

<!-- Dismiss popups on click-away -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="flex h-screen overflow-hidden bg-surface text-ink"
	onclick={(e) => {
		if (suppressNextClickAway) {
			suppressNextClickAway = false;
			return;
		}
		const t = e.target as HTMLElement;
		if (appendPopup && !t.closest('.append-popup')) dismissAppendPopup();
		if (notePopup   && !t.closest('.note-popup'))   dismissNotePopup();
	}}
	onmouseup={handleMouseUp}
>
	<!-- ===================================================================== -->
	<!-- LEFT SIDEBAR — session list                                            -->
	<!-- ===================================================================== -->
	<aside
		class="relative hidden shrink-0 border-r border-line bg-panel/86 p-4 shadow-[1px_0_0_rgba(38,35,31,0.03)] lg:flex lg:flex-col"
		style="width: {sidebarResize.leftWidth}px;"
	>
		<div class="mb-5">
			<p class="text-xs font-semibold tracking-[0.18em] text-muted uppercase">Kitchen Agent</p>
			<h1 class="mt-2 text-xl font-semibold text-ink">Project conversations</h1>
		</div>

		<button
			onclick={startNewChat}
			class="mb-5 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-line bg-ink px-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-soft focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none"
		>
			<span aria-hidden="true">+</span>
			New chat
		</button>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<SessionTree
				activeId={sessionId}
				onload={loadSession}
			/>
		</div>

		<button
			type="button"
			aria-label="Resize conversation sidebar"
			class="absolute top-0 -right-1 z-20 h-full w-2 cursor-col-resize touch-none transition hover:bg-accent/30 focus:bg-accent/30 focus:outline-none"
			onmousedown={sidebarResize.startLeftDrag}
			ondblclick={sidebarResize.resetLeft}
			onkeydown={(event) => handleSidebarResizeKeydown(event, 'left')}
			title="Drag to resize. Double-click to reset."
		></button>
	</aside>

	<!-- ===================================================================== -->
	<!-- MAIN AREA                                                              -->
	<!-- ===================================================================== -->
	<main class="flex min-w-0 flex-1 flex-col">

		<!-- ================================================================= -->
		<!-- Header — title + session badge + context toggle only.             -->
		<!-- Mode switcher removed from here; it now lives in the footer.      -->
		<!-- ================================================================= -->
		<header class="border-b border-line bg-panel/92 px-4 py-3 backdrop-blur md:px-6">
			<div class="mx-auto flex max-w-5xl items-center justify-between gap-3">
				<div>
					<p class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">
						Kitchen Cabinet Assistant
					</p>
					<div class="mt-1 flex flex-wrap items-center gap-2">
						<!-- Active mode label reflects selectedModeId live -->
						<h2 class="text-xl font-semibold text-ink md:text-2xl">
							{modeIcon(activeMode.id)}&nbsp;{activeMode.label} mode
						</h2>
						<span class="rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted">
							Session {sessionId.substring(0, 8)}
						</span>
					</div>
				</div>

				<!-- Context sidebar toggle (unchanged) -->
				<button
					onclick={sidebarResize.toggleRight}
					class="hidden rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-muted transition hover:border-accent hover:text-ink lg:flex"
					title="Toggle context sidebar"
				>
					{sidebarResize.showRight ? '▶ Hide panel' : '◀ Context'}
				</button>
			</div>
		</header>

		<!-- Chat area -->
		<section class="min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
			<div class="mx-auto max-w-5xl space-y-5">

				<!--
					System prompt inspector.
					BUG FIX: handleInspectorToggle() now syncs promptInspectorOpen
					so the $effect above can eagerly re-fetch when the user switches
					modes while this panel is already open.
				-->
				<details
					class="group rounded-md border border-line bg-panel shadow-sm"
					ontoggle={handleInspectorToggle}
				>
					<summary class="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm">
						<span>
							<span class="font-semibold text-ink">System prompt</span>
							<span class="ml-2 text-muted">{activeMode.label} · {activeMode.eyebrow}</span>
						</span>
						<span class="text-xs font-medium text-accent group-open:hidden">Expand</span>
						<span class="hidden text-xs font-medium text-accent group-open:inline">Collapse</span>
					</summary>

					<div class="border-t border-line bg-surface px-4 py-3">
						{#if promptDetailLoading}
							<p class="text-sm text-muted">Loading…</p>
						{:else if promptDetailError}
							<p class="text-sm text-red-500">{promptDetailError}</p>
						{:else if promptDetail}
							<pre class="whitespace-pre-wrap text-sm leading-6 text-ink">{promptDetail.content}</pre>
						{:else}
							<p class="text-sm text-muted">Open to inspect the active system prompt.</p>
						{/if}
					</div>
				</details>

				<!-- Context injection status -->
				{#if contextFiles.length > 0}
					<div class="flex items-center gap-2 rounded-md border border-accent-soft bg-accent-soft px-3 py-2 text-xs font-medium text-accent">
						📎 {contextFiles.length} file{contextFiles.length > 1 ? 's' : ''} will be injected into
						your next message.
					</div>
				{/if}

				<!-- Status pills -->
				{#if forkStatus}
					<p class="rounded-md border border-line bg-panel px-3 py-2 text-xs text-muted">
						{forkStatus}
					</p>
				{/if}
				{#if appendStatus}
					<p class="rounded-md border border-accent-soft bg-accent-soft px-3 py-2 text-xs text-accent">
						{appendStatus}
					</p>
				{/if}

				<!-- Messages -->
				<div class="space-y-5">
					{#each messages as msg, messageIndex (`${msg.role}-${messageIndex}`)}
						<article
							data-chat-bubble={msg.role}
							class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}"
							aria-label={msg.role === 'user' ? 'User message' : 'Assistant message'}
						>
							<div
								class={msg.role === 'user'
									? 'max-w-[min(760px,88%)] rounded-md bg-ink px-4 py-3 text-white shadow-sm'
									: 'w-full max-w-4xl rounded-md border border-line bg-panel p-4 shadow-sm'}
							>
								<!-- Role label + badges -->
								<div class="mb-2 flex items-center justify-between gap-3">
									<p
										class={msg.role === 'user'
											? 'text-xs font-semibold tracking-[0.14em] text-white/70 uppercase'
											: 'text-xs font-semibold tracking-[0.14em] text-muted uppercase'}
									>
										{msg.role === 'user' ? 'You' : 'Assistant'}
									</p>

									<div class="flex items-center gap-2">
										{#if msg.role === 'assistant' && msg.tools && msg.tools.length > 0}
											<span class="rounded-full border border-line bg-surface px-2 py-0.5 text-xs font-medium text-muted">
												{msg.tools.length} tools
											</span>
										{/if}
										<button
											onclick={() => forkSession(messageIndex)}
											title="Fork conversation from this turn"
											class="rounded px-1.5 py-0.5 text-xs text-muted transition hover:bg-line hover:text-ink"
										>
											⎇ Fork
										</button>
									</div>
								</div>

								<!-- User image previews -->
								{#if msg.role === 'user' && msg.images && msg.images.length > 0}
									<div class="mb-2 flex flex-wrap gap-2">
										{#each msg.images as imgUrl, i (i)}
											<img
												src={imgUrl}
												alt="Attached image {i + 1}"
												class="h-20 w-20 rounded border border-white/20 object-cover"
											/>
										{/each}
									</div>
								{/if}

								<Markdown content={msg.content} variant={msg.role} />

								<!-- Tool logs -->
								{#if msg.role === 'assistant' && msg.tools && msg.tools.length > 0}
									<div class="mt-4 space-y-2 border-t border-line pt-3">
										<p class="text-xs font-semibold tracking-[0.14em] text-muted uppercase">
											Tools used
										</p>

										{#each msg.tools as tool, toolIndex (`${tool.name}-${toolIndex}`)}
											<details class="group rounded-md border border-line bg-surface">
												<summary class="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-sm">
													<span class="min-w-0">
														<span class="font-semibold text-ink">{tool.name}</span>
														<span class="ml-2 text-xs text-muted">Args and result</span>
													</span>
													<span class="text-xs font-medium text-accent group-open:hidden">View</span>
													<span class="hidden text-xs font-medium text-accent group-open:inline">Hide</span>
												</summary>
												<div class="space-y-3 border-t border-line px-3 py-3">
													<div>
														<p class="mb-1 text-xs font-semibold text-muted uppercase">Args</p>
														<pre class="overflow-x-auto rounded bg-code px-3 py-2 text-xs leading-5 text-code-ink">{JSON.stringify(tool.args, null, 2)}</pre>
													</div>
													<div>
														<p class="mb-1 text-xs font-semibold text-muted uppercase">Result</p>
														<pre class="max-h-72 overflow-auto rounded bg-code px-3 py-2 text-xs leading-5 text-code-ink">{formatToolResult(tool)}</pre>
													</div>
												</div>
											</details>
										{/each}
									</div>
								{/if}
							</div>
						</article>
					{/each}

					{#if isLoading}
						<article class="flex justify-start">
							<div class="w-full max-w-4xl rounded-md border border-line bg-panel p-4 shadow-sm">
								<p class="text-xs font-semibold tracking-[0.14em] text-muted uppercase">Assistant</p>
								<div class="mt-3 flex items-center gap-3 text-sm text-muted">
									<span class="h-2 w-2 animate-pulse rounded-full bg-accent"></span>
									Thinking, reading files, and preparing the answer…
								</div>
							</div>
						</article>
					{/if}
				</div>
			</div>
		</section>

		<!-- ================================================================= -->
		<!-- Footer / input area                                                -->
		<!-- ================================================================= -->
		<footer class="border-t border-line bg-panel/95 px-4 py-4 backdrop-blur md:px-6">
			<div class="mx-auto max-w-5xl">

				<!-- Pasted image previews -->
				{#if pastedImages.length > 0}
					<div class="mb-2 flex flex-wrap gap-2">
						{#each pastedImages as img, i (i)}
							<div class="group relative">
								<img
									src={img.dataUrl}
									alt="Pasted image {i + 1}"
									class="h-16 w-16 rounded border border-line object-cover shadow-sm"
								/>
								<button
									onclick={() => removeImage(i)}
									class="absolute -top-1.5 -right-1.5 hidden h-4 w-4 items-center justify-center rounded-full bg-ink text-xs text-white group-hover:flex"
									aria-label="Remove image"
								>
									✕
								</button>
							</div>
						{/each}
					</div>
				{/if}

				<!-- ============================================================= -->
				<!-- Composer box — resize handle + mode pills + textarea + send   -->
				<!-- ============================================================= -->
				<div class="relative rounded-md border border-line bg-surface shadow-sm">

					<!-- Drag-to-resize handle (sits at the very top of the box) -->
					<button
						type="button"
						aria-label="Resize prompt area"
						class="absolute -top-1 left-0 z-20 h-2 w-full cursor-row-resize touch-none rounded-t-md transition hover:bg-accent/30 focus:bg-accent/30 focus:outline-none"
						onmousedown={sidebarResize.startPromptDrag}
						ondblclick={sidebarResize.resetPrompt}
						onkeydown={handlePromptResizeKeydown}
						title="Drag to resize. Double-click to reset."
					></button>

					<!-- Textarea -->
					<div class="flex items-end gap-2 px-2 pt-3 pb-2">
						<label class="sr-only" for="message-input">Message</label>
						<textarea
							id="message-input"
							bind:this={messageInput}
							bind:value={currentMessage}
							onkeydown={handleKeydown}
							onpaste={handlePaste}
							placeholder="Ask about layouts, materials, fittings, assembly… or paste an image with Ctrl+V"
							class="min-h-0 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink placeholder:text-muted focus:outline-none"
							style="height: {sidebarResize.promptHeight}px;"
							rows="2"
						></textarea>
						<button
							onclick={sendMessage}
							disabled={isLoading || !currentMessage.trim()}
							class="h-10 rounded-md bg-accent px-4 text-sm font-semibold text-white transition hover:bg-accent-strong focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-45"
						>
							Send
						</button>
					</div>

					<!-- =========================================================== -->
					<!-- Mode pill strip — the new bottom toolbar                     -->
					<!--                                                               -->
					<!-- Sits inside the composer box, visually separated by a thin   -->
					<!-- top border, matching the pattern used in Claude / ChatGPT.   -->
					<!-- Each pill is a toggle button: active = accent fill,          -->
					<!-- inactive = ghost with hover state.                           -->
					<!-- Keyboard: Tab between pills, Space/Enter to activate.        -->
					<!-- =========================================================== -->
					<div
						class="flex items-center gap-1 border-t border-line px-3 py-2"
						role="group"
						aria-label="Prompt mode"
					>
						{#if modesLoading}
							<!-- Skeleton shimmer while modes load from the backend -->
							<span class="h-7 w-20 animate-pulse rounded-full bg-line"></span>
							<span class="h-7 w-16 animate-pulse rounded-full bg-line"></span>
							<span class="h-7 w-20 animate-pulse rounded-full bg-line"></span>
						{:else}
							{#each modes as mode (mode.id)}
								<button
									type="button"
									role="radio"
									aria-checked={selectedModeId === mode.id}
									title={mode.eyebrow}
									onclick={() => (selectedModeId = mode.id)}
									class="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1
										{selectedModeId === mode.id
											? 'border-accent bg-accent text-white shadow-sm'
											: 'border-line bg-transparent text-muted hover:border-accent/60 hover:bg-accent/8 hover:text-ink'}"
								>
									<span aria-hidden="true">{modeIcon(mode.id)}</span>
									{mode.label}
								</button>
							{/each}
						{/if}

						<!-- Spacer pushes the "New chat" shortcut to the right -->
						<span class="flex-1"></span>

						<button
							onclick={startNewChat}
							class="rounded-full border border-line px-3 py-1 text-xs font-semibold text-muted transition hover:border-accent/60 hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1"
							title="Start a new conversation"
						>
							+ New chat
						</button>
					</div>
				</div>

				<!-- Tiny status line below the composer — context files count -->
				{#if contextFiles.length > 0}
					<p class="mt-1.5 px-1 text-xs text-muted">
						📎
						<span class="text-accent font-medium">
							{contextFiles.length} context file{contextFiles.length > 1 ? 's' : ''}
						</span>
						will be injected into your next message.
					</p>
				{/if}
			</div>
		</footer>
	</main>

	<!-- ===================================================================== -->
	<!-- RIGHT SIDEBAR — context injection + notes                             -->
	<!-- ===================================================================== -->
	{#if sidebarResize.showRight}
		<div
			class="relative hidden h-full shrink-0 lg:block"
			style="width: {sidebarResize.rightWidth}px;"
		>
			<button
				type="button"
				aria-label="Resize context sidebar"
				class="absolute top-0 -left-1 z-20 h-full w-2 cursor-col-resize touch-none transition hover:bg-accent/30 focus:bg-accent/30 focus:outline-none"
				onmousedown={sidebarResize.startRightDrag}
				ondblclick={sidebarResize.resetRight}
				onkeydown={(event) => handleSidebarResizeKeydown(event, 'right')}
				title="Drag to resize. Double-click to reset."
			></button>
			<ContextSidebar
				oncontextchange={handleContextChange}
				oninsertnotes={insertNotesIntoComposer}
				{sessionId}
			/>
		</div>
	{/if}

	<!-- ===================================================================== -->
	<!-- FLOATING POPUP — Note (highlight inside chat bubble)                  -->
	<!-- ===================================================================== -->
	{#if notePopup}
		<NotePopup
			selectedText={notePopup.text}
			x={notePopup.x}
			y={notePopup.y}
			{sessionId}
			sourceRole={notePopup.sourceRole}
			ondismiss={dismissNotePopup}
		/>
	{/if}

	<!-- ===================================================================== -->
	<!-- FLOATING POPUP — Highlight → Add to Docs                              -->
	<!-- ===================================================================== -->
	{#if appendPopup}
		<div
			class="append-popup fixed z-50 rounded-md border border-line bg-panel p-3 shadow-lg"
			style="left: {appendPopup.x}px; top: {appendPopup.y}px; min-width: 220px; max-width: 300px;"
		>
			<p class="mb-2 text-xs font-semibold text-ink">📋 Add to docs</p>
			<p class="mb-3 line-clamp-2 text-xs italic text-muted">"{appendPopup.text}"</p>
			<div class="flex items-center gap-2">
				<select
					bind:value={appendTarget}
					class="min-w-0 flex-1 rounded border border-line bg-surface px-2 py-1 text-xs text-ink focus:outline-none"
				>
					<option value="">Select file…</option>
					{#each appendFiles as file (file.path)}
						<option value={file.path}>{file.name}</option>
					{/each}
				</select>
				<button
					onclick={appendToDoc}
					disabled={!appendTarget}
					class="rounded bg-accent px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-accent-strong disabled:opacity-40"
				>
					Add
				</button>
				<button
					onclick={dismissAppendPopup}
					class="rounded px-1.5 py-1 text-xs text-muted transition hover:text-ink"
				>
					✕
				</button>
			</div>
		</div>
	{/if}
</div>
