<script lang="ts">
	/**
	 * +page.svelte — Kitchen Agent
	 * =============================
	 * Pure layout wrapper. All business logic lives elsewhere:
	 *
	 *   $lib/stores/chat.svelte.ts          — chat session, modes, images, message editor,
	 *                                         provider/model selection
	 *   $lib/stores/sessions.svelte.ts      — session tree, archive, delete
	 *   $lib/actions/textSelection.ts       — mouseup → note-popup classification
	 *   $lib/actions/pasteImage.ts          — Ctrl+V image capture
	 *   $lib/hooks/useKeyboardResize.svelte — keyboard-driven sidebar/prompt resize
	 *
	 * This file is responsible only for:
	 *   - Three-column layout (left sidebar / main / right sidebar)
	 *   - Wiring the textSelection action to the note popup $state
	 *   - Wiring keyboard resize handlers to drag-handle buttons
	 *   - Mounting child components with the correct props
	 *   - Wiring the message editor
	 *   - Passing provider/model selection props to ChatHeader
	 */

	import { onMount } from 'svelte';

	import { chatStore }           from '$lib/stores/chat.svelte';
	import { sessionStore }        from '$lib/stores/sessions.svelte';
	import { createSidebarResize } from '$lib/sidebar-resize.svelte';
	import { textSelection }       from '$lib/actions/textSelection';
	import { createKeyboardResize} from '$lib/hooks/useKeyboardResize.svelte';

	import type { PromptMode, Note } from '$lib/api';
	import type { ChatSelectionHit } from '$lib/actions/textSelection';

	import ChatHeader         from '$lib/components/ChatHeader.svelte';
	import ChatMessageList    from '$lib/components/ChatMessageList.svelte';
	import ChatComposer       from '$lib/components/ChatComposer.svelte';
	import PromptInspector    from '$lib/components/PromptInspector.svelte';
	import SessionTree        from '$lib/components/SessionTree.svelte';
	import ContextSidebar     from '$lib/components/ContextSidebar.svelte';
	import NotePopup          from '$lib/components/NotePopup.svelte';
	import TruncateBar        from '$lib/components/TruncateBar.svelte';

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
	// Note popup state — set by the textSelection action callback
	// ---------------------------------------------------------------------------

	let notePopup = $state<ChatSelectionHit | null>(null);

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

	// Derived: true when the session has a non-empty system prompt override.
	const hasSystemPromptOverride = $derived(
		chatStore.sessionSystemPrompt !== null && chatStore.sessionSystemPrompt !== ''
	);

	// Resolved system prompt text for the bubble: override ?? mode default
	const systemPromptText = $derived(
		chatStore.sessionSystemPrompt ?? ''
	);

	// Derived: edit state helpers
	const isEditSaving = $derived(chatStore.editState.status === 'loading');
	const editError    = $derived(
		chatStore.editState.status === 'error' ? chatStore.editState.message : ''
	);
	const isTruncating = $derived(chatStore.editState.status === 'loading');

	// ---------------------------------------------------------------------------
	// Busy-recent indicator — stays true for 300ms after operation completes
	// Allows E2E tests to observe the loading state before optimistic updates
	// ---------------------------------------------------------------------------

	let busyRecent = $state(false);
	let busyTimer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		const isBusy = chatStore.editState.status === 'loading' || chatStore.chatState.status === 'loading';
		if (isBusy) {
			busyRecent = true;
			if (busyTimer) clearTimeout(busyTimer);
		} else if (busyRecent) {
			busyTimer = setTimeout(() => { busyRecent = false; }, 300);
		}
	});

	// ---------------------------------------------------------------------------
	// Bootstrap — load modes and providers in parallel on mount
	// ---------------------------------------------------------------------------

	onMount(async () => {
		void sessionStore.refresh();

		// Expose stores and test helpers on window for browser-based testing (dev mode only)
		if (import.meta.env.DEV) {
			(window as any).__chatStore = chatStore;
			(window as any).__sessionStore = sessionStore;
			(window as any).__testHelpers = {
				autoConfirm: false,
				confirmAll() { (window as any).__testHelpers.autoConfirm = true; },
				confirmNone() { (window as any).__testHelpers.autoConfirm = false; },
			};
		}

		// Fire all three in parallel — none depends on the others.
		const [fetched] = await Promise.all([
			chatStore.loadModes(),
			chatStore.loadProviders(),
			chatStore.loadAppInfo()
		]);
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
	<title>{chatStore.appTitle}</title>
</svelte:head>

<!--
  use:textSelection handles the full mouseup + click-away lifecycle.
  The onchatselect callback is the only wiring needed here.
-->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="flex h-screen overflow-hidden bg-surface text-ink"
	use:textSelection={{ onchatselect: (hit) => (notePopup = hit) }}
>

	<!-- Global busy indicator for browser-based testing -->
	<div
		data-testid="app-busy"
		data-loading={chatStore.editState.status === 'loading' || chatStore.chatState.status === 'loading'}
		data-busy-recent={busyRecent}
		class="hidden"
	></div>

	<!-- ===================================================================== -->
	<!-- LEFT SIDEBAR — session list                                            -->
	<!-- ===================================================================== -->
	<aside
		class="relative hidden shrink-0 border-r border-line bg-panel/86 p-4 shadow-[1px_0_0_rgba(38,35,31,0.03)] lg:flex lg:flex-col"
		style="width: {sidebarResize.leftWidth}px;"
	>
		<div class="mb-5">
			<p class="text-xs font-semibold tracking-[0.18em] text-muted uppercase">{chatStore.appTitle}</p>
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
			appTitle={chatStore.appTitle}
			modeIcon={MODE_ICONS[activeMode.id] ?? '💬'}
			modeLabel={activeMode.label}
			sessionId={chatStore.sessionId}
			showRight={sidebarResize.showRight}
			hasSystemPromptOverride={hasSystemPromptOverride}
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

				<!-- Fork status pill -->
				{#if chatStore.forkStatus}
					<p class="rounded-md border border-line bg-panel px-3 py-2 text-xs text-muted">
						{chatStore.forkStatus}
					</p>
				{/if}

				<!-- Truncate bar — quick turn removal (only shown when there are messages) -->
				{#if chatStore.messages.length >= 2}
					<TruncateBar
						totalMessages={chatStore.messages.length}
						isBusy={isTruncating}
						errorMessage={editError ?? ''}
						ontruncate={(n) => chatStore.truncateMessages(n)}
					/>
				{/if}

				<ChatMessageList
					systemPromptText={systemPromptText}
					systemPromptIsOverride={hasSystemPromptOverride}
					systemPromptModeLabel={activeMode.label}
					systemPromptSaveState={chatStore.systemPromptState}
					systemPromptError={chatStore.systemPromptError}
					onsystemprompsave={(text) => chatStore.saveSystemPrompt(text)}
					onsystempromptreset={() => chatStore.clearSystemPrompt()}
					messages={chatStore.messages}
					isLoading={chatStore.chatState.status === 'loading'}
					isBusy={chatStore.editState.status === 'loading'}
					editingTurnId={chatStore.editingTurnId}
					editDraft={chatStore.editDraft}
					isSavingEdit={isEditSaving}
					editErrorMessage={editError ?? ''}
					onfork={(i) => chatStore.forkSession(i)}
					onedit={(turnId) => chatStore.startEditing(turnId)}
					ondelete={(turnId) => chatStore.deleteMessage(turnId, false)}
					onregenerate={() => chatStore.regenerateMessage()}
					oncopytext={(content) => navigator.clipboard.writeText(content)}
					oncopymarkdown={(content) => navigator.clipboard.writeText(content)}
					onsaveedit={() => chatStore.saveEdit()}
					oncanceledit={() => chatStore.cancelEditing()}
					ondraftchange={(text) => chatStore.setEditDraft(text)}
				/>
			</div>
		</section>

		<ChatComposer
			providers={chatStore.providers}
			selectedProvider={chatStore.selectedProvider}
			selectedModel={chatStore.selectedModel}
			onproviderchange={(p, m) => { chatStore.setProvider(p); chatStore.setModel(m); }}
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
				checkedFiles={chatStore.contextFiles}
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
</div>
