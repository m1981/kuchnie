<script lang="ts">
	/**
	 * +page.svelte — Kitchen Agent
	 * =============================
	 * Pure layout wrapper. All business logic lives elsewhere:
	 *
	 *   $lib/stores/chat.svelte.ts          — chat session, modes, images, append
	 *   $lib/stores/sessions.svelte.ts      — session tree, archive, delete
	 *   $lib/actions/textSelection.ts       — mouseup → popup classification
	 *   $lib/actions/pasteImage.ts          — Ctrl+V image capture
	 *   $lib/hooks/useKeyboardResize.svelte — keyboard-driven sidebar/prompt resize
	 *
	 * This file is responsible only for:
	 *   - Three-column layout (left sidebar / main / right sidebar)
	 *   - Wiring the textSelection action to popup $state variables
	 *   - Wiring keyboard resize handlers to drag-handle buttons
	 *   - Mounting child components with the correct props
	 */

	import { onMount } from 'svelte';

	import { chatStore }      from '$lib/stores/chat.svelte';
	import { sessionStore }   from '$lib/stores/sessions.svelte';
	import { createSidebarResize }    from '$lib/sidebar-resize.svelte';
	import { textSelection }          from '$lib/actions/textSelection';
	import { createKeyboardResize }   from '$lib/hooks/useKeyboardResize.svelte';

	import type { PromptMode, Note }              from '$lib/api';
	import type { ChatSelectionHit, PageSelectionHit } from '$lib/actions/textSelection';

	import ChatHeader       from '$lib/components/ChatHeader.svelte';
	import ChatMessageList  from '$lib/components/ChatMessageList.svelte';
	import ChatComposer     from '$lib/components/ChatComposer.svelte';
	import PromptInspector  from '$lib/components/PromptInspector.svelte';
	import AppendPopup      from '$lib/components/AppendPopup.svelte';
	import SessionTree      from '$lib/components/SessionTree.svelte';
	import ContextSidebar   from '$lib/components/ContextSidebar.svelte';
	import NotePopup        from '$lib/components/NotePopup.svelte';

	// ---------------------------------------------------------------------------
	// Layout resize
	// ---------------------------------------------------------------------------

	const sidebarResize = createSidebarResize();
	const kbResize      = createKeyboardResize(sidebarResize);

	// ---------------------------------------------------------------------------
	// Prompt mode list — fetched once on mount; selectedModeId lives in chatStore
	// ---------------------------------------------------------------------------

	let modes = $state<PromptMode[]>([]);

	// ---------------------------------------------------------------------------
	// Floating popup state — set by the textSelection action callbacks
	// ---------------------------------------------------------------------------

	let notePopup   = $state<ChatSelectionHit | null>(null);
	let appendPopup = $state<PageSelectionHit | null>(null);

	// ---------------------------------------------------------------------------
	// Composer — bind:currentMessage so notes can be injected from the sidebar
	// ---------------------------------------------------------------------------

	let currentMessage = $state('');
	let textareaEl     = $state<HTMLTextAreaElement | null>(null);

	// ---------------------------------------------------------------------------
	// Derived — active mode label / icon resolved from the live modes list
	// ---------------------------------------------------------------------------

	const MODE_ICONS: Record<string, string> = {
		general:  '🔧',
		design:   '📐',
		assembly: '🔨',
	};

	const activeMode = $derived(
		modes.find((m) => m.id === chatStore.selectedModeId) ?? {
			id:      chatStore.selectedModeId,
			label:   chatStore.selectedModeId,
			eyebrow: '',
		}
	);

	// ---------------------------------------------------------------------------
	// Bootstrap
	// ---------------------------------------------------------------------------

	onMount(async () => {
		void sessionStore.refresh();
		void chatStore.loadAppendFiles();

		const fetched = await chatStore.loadModes();
		if (fetched) modes = fetched;
	});

	// ---------------------------------------------------------------------------
	// Notes → Composer injection (called from ContextSidebar)
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

<!--
  use:textSelection wires the entire mouseup + click-away lifecycle.
  Popup state is set reactively via the action callbacks — no inline
  handleMouseUp / popupPosition / nodeElement helpers needed here.
-->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="flex h-screen overflow-hidden bg-surface text-ink"
	use:textSelection={{
		onchatselect: (hit) => { notePopup = hit;   if (hit) appendPopup = null; },
		onpageselect: (hit) => { appendPopup = hit; if (hit) notePopup   = null; },
	}}
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

		<!-- Left sidebar drag handle -->
		<button
			type="button"
			aria-label="Resize conversation sidebar"
			class="absolute top-0 -right-1 z-20 h-full w-2 cursor-col-resize touch-none transition hover:bg-accent/30 focus:bg-accent/30 focus:outline-none"
			onmousedown={sidebarResize.startLeftDrag}
			ondblclick={sidebarResize.resetLeft}
			onkeydown={(e) => kbResize.sidebar(e, 'left')}
			title="Drag to resize. Double-click to reset."
		></button>
	</aside>

	<!-- ===================================================================== -->
	<!-- MAIN AREA                                                              -->
	<!-- ===================================================================== -->
	<main class="flex min-w-0 flex-1 flex-col">

		<ChatHeader
			modeIcon={MODE_ICONS[activeMode.id] ?? '💬'}
			modeLabel={activeMode.label}
			sessionId={chatStore.sessionId}
			showRight={sidebarResize.showRight}
			ontoggleright={() => sidebarResize.toggleRight()}
		/>

		<!-- Chat scroll area -->
		<section class="min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
			<div class="mx-auto max-w-5xl space-y-5">

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
					<div class="flex items-center gap-2 rounded-md border border-accent-soft bg-accent-soft px-3 py-2 text-xs font-medium text-accent">
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

				<ChatMessageList
					messages={chatStore.messages}
					isLoading={chatStore.chatState.status === 'loading'}
					onfork={(i) => chatStore.forkSession(i)}
				/>
			</div>
		</section>

		<ChatComposer
			{modes}
			promptHeight={sidebarResize.promptHeight}
			onStartDrag={sidebarResize.startPromptDrag}
			onDblClickReset={sidebarResize.resetPrompt}
			onResizeKeydown={kbResize.prompt}
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
			<!-- Right sidebar drag handle -->
			<button
				type="button"
				aria-label="Resize context sidebar"
				class="absolute top-0 -left-1 z-20 h-full w-2 cursor-col-resize touch-none transition hover:bg-accent/30 focus:bg-accent/30 focus:outline-none"
				onmousedown={sidebarResize.startRightDrag}
				ondblclick={sidebarResize.resetRight}
				onkeydown={(e) => kbResize.sidebar(e, 'right')}
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
	<!-- FLOATING POPUP — Note (highlight inside a chat bubble)                -->
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
