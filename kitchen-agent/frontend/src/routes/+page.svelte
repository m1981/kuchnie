<script lang="ts">
	/**
	 * +page.svelte — Kitchen Agent
	 * =============================
	 * Pure layout wrapper.  All business logic lives in:
	 *   $lib/stores/chat.svelte.ts   — chat session, modes, images, append
	 *   $lib/stores/sessions.svelte.ts — session tree, archive, delete
	 *
	 * This file is responsible only for:
	 *   - Three-column layout (left sidebar / main / right sidebar)
	 *   - Sidebar resize wiring
	 *   - Mouse-up event for "highlight → popup" UX
	 *   - Mounting child components with the right props
	 */

	import { onMount } from 'svelte';
	import { chatStore } from '$lib/stores/chat.svelte';
	import { sessionStore } from '$lib/stores/sessions.svelte';
	import { createSidebarResize } from '$lib/sidebar-resize.svelte';
	import type { PromptMode, Note } from '$lib/api';
	import type { NotePopupState, AppendPopupState } from '$lib/types';

	import ChatHeader from '$lib/components/ChatHeader.svelte';
	import ChatMessageList from '$lib/components/ChatMessageList.svelte';
	import ChatComposer from '$lib/components/ChatComposer.svelte';
	import PromptInspector from '$lib/components/PromptInspector.svelte';
	import AppendPopup from '$lib/components/AppendPopup.svelte';
	import SessionTree from '$lib/components/SessionTree.svelte';
	import ContextSidebar from '$lib/components/ContextSidebar.svelte';
	import NotePopup from '$lib/components/NotePopup.svelte';

	// ---------------------------------------------------------------------------
	// Layout
	// ---------------------------------------------------------------------------

	const sidebarResize = createSidebarResize();

	// ---------------------------------------------------------------------------
	// Mode list — fetched once, stored locally in this route
	// (chatStore.selectedModeId is the single source of truth for the selection)
	// ---------------------------------------------------------------------------

	let modes = $state<PromptMode[]>([]);

	// ---------------------------------------------------------------------------
	// Floating popup state (UI-only, not business logic)
	// ---------------------------------------------------------------------------

	let notePopup = $state<NotePopupState>(null);
	let appendPopup = $state<AppendPopupState>(null);
	let suppressNextClickAway = $state(false);

	// ---------------------------------------------------------------------------
	// Composer — bidirectionally bound so the parent can inject notes
	// ---------------------------------------------------------------------------

	let currentMessage = $state('');
	let textareaEl = $state<HTMLTextAreaElement | null>(null);

	// ---------------------------------------------------------------------------
	// Derived — active mode resolved from the live list
	// ---------------------------------------------------------------------------

	const MODE_ICONS: Record<string, string> = {
		general: '🔧',
		design: '📐',
		assembly: '🔨'
	};

	function modeIcon(id: string): string {
		return MODE_ICONS[id] ?? '💬';
	}

	const activeMode = $derived(
		modes.find((m) => m.id === chatStore.selectedModeId) ?? {
			id: chatStore.selectedModeId,
			label: chatStore.selectedModeId,
			eyebrow: ''
		}
	);

	// ---------------------------------------------------------------------------
	// Bootstrap on mount
	// ---------------------------------------------------------------------------

	onMount(async () => {
		void sessionStore.refresh();
		void chatStore.loadAppendFiles();

		const fetched = await chatStore.loadModes();
		if (fetched) modes = fetched;
	});

	// ---------------------------------------------------------------------------
	// Mouse-up → floating popup logic
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
		const focusBubble = nodeElement(selection.focusNode)?.closest<HTMLElement>('[data-chat-bubble]');
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
			notePopup = { ...chatSelection, x, y };
			appendPopup = null;
			suppressNextClickAway = true;
			return;
		}

		const text = window.getSelection()?.toString().trim();
		if (!text || text.length < 5) {
			appendPopup = null;
			return;
		}
		const { x, y } = popupPosition(event, 300, 120);
		appendPopup = { text, x, y };
		notePopup = null;
		suppressNextClickAway = true;
	}

	// ---------------------------------------------------------------------------
	// Keyboard resize helpers
	// ---------------------------------------------------------------------------

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

	// ---------------------------------------------------------------------------
	// Notes → Composer injection
	// ---------------------------------------------------------------------------

	function insertNotesIntoComposer(notes: Note[]) {
		const block = chatStore.formatNotesForPrompt(notes);
		currentMessage = currentMessage.trim()
			? `${currentMessage.trimEnd()}\n\n${block}`
			: block;

		requestAnimationFrame(() => {
			textareaEl?.focus();
			textareaEl?.setSelectionRange(currentMessage.length, currentMessage.length);
		});
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
		if (suppressNextClickAway) { suppressNextClickAway = false; return; }
		const t = e.target as HTMLElement;
		if (appendPopup && !t.closest('.append-popup')) appendPopup = null;
		if (notePopup   && !t.closest('.note-popup'))   notePopup   = null;
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
			onclick={() => chatStore.startNewChat()}
			class="mb-5 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-line bg-ink px-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-soft focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none"
		>
			<span aria-hidden="true">+</span>
			New chat
		</button>

		<div class="min-h-0 flex-1 overflow-y-auto">
			<SessionTree
				activeId={chatStore.sessionId}
				onload={(id) => chatStore.loadSession(id)}
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

		<!-- Header -->
		<ChatHeader
			modeIcon={modeIcon(activeMode.id)}
			modeLabel={activeMode.label}
			sessionId={chatStore.sessionId}
			showRight={sidebarResize.showRight}
			ontoggleright={() => sidebarResize.toggleRight()}
		/>

		<!-- Chat scroll area -->
		<section class="min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
			<div class="mx-auto max-w-5xl space-y-5">

				<!-- System prompt inspector -->
				<PromptInspector
					modeLabel={activeMode.label}
					modeEyebrow={activeMode.eyebrow}
					content={chatStore.promptDetailContent}
					isLoading={chatStore.promptDetailState.status === 'loading'}
					error={chatStore.promptDetailState.status === 'error'
						? chatStore.promptDetailState.message
						: ''}
					ontoggle={(open) => chatStore.setPromptInspectorOpen(open)}
				/>

				<!-- Context injection badge -->
				{#if chatStore.contextFiles.length > 0}
					<div
						class="flex items-center gap-2 rounded-md border border-accent-soft bg-accent-soft px-3 py-2 text-xs font-medium text-accent"
					>
						📎 {chatStore.contextFiles.length} file{chatStore.contextFiles.length > 1 ? 's' : ''} will
						be injected into your next message.
					</div>
				{/if}

				<!-- Status pills -->
				{#if chatStore.forkStatus}
					<p class="rounded-md border border-line bg-panel px-3 py-2 text-xs text-muted">
						{chatStore.forkStatus}
					</p>
				{/if}
				{#if chatStore.appendStatus}
					<p class="rounded-md border border-accent-soft bg-accent-soft px-3 py-2 text-xs text-accent">
						{chatStore.appendStatus}
					</p>
				{/if}

				<!-- Messages -->
				<ChatMessageList
					messages={chatStore.messages}
					isLoading={chatStore.chatState.status === 'loading'}
					onfork={(i) => chatStore.forkSession(i)}
				/>
			</div>
		</section>

		<!-- Footer / Composer -->
		<ChatComposer
			{modes}
			promptHeight={sidebarResize.promptHeight}
			onStartDrag={sidebarResize.startPromptDrag}
			onDblClickReset={sidebarResize.resetPrompt}
			onResizeKeydown={handlePromptResizeKeydown}
			onnewchat={() => chatStore.startNewChat()}
			bind:currentMessage
			bind:textareaEl
		/>
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
				oncontextchange={(paths) => chatStore.setContextFiles(paths)}
				oninsertnotes={insertNotesIntoComposer}
				sessionId={chatStore.sessionId}
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
			sessionId={chatStore.sessionId}
			sourceRole={notePopup.sourceRole}
			ondismiss={() => (notePopup = null)}
		/>
	{/if}

	<!-- ===================================================================== -->
	<!-- FLOATING POPUP — Highlight → Add to Docs                             -->
	<!-- ===================================================================== -->
	{#if appendPopup}
		<AppendPopup
			text={appendPopup.text}
			x={appendPopup.x}
			y={appendPopup.y}
			files={chatStore.appendFiles}
			ondismiss={() => (appendPopup = null)}
			onappend={async (target) => {
				if (appendPopup) {
					await chatStore.appendToDoc(target, appendPopup.text);
					appendPopup = null;
				}
			}}
		/>
	{/if}
</div>
