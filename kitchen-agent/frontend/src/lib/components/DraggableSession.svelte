<script lang="ts">
	import { draggable, type DraggableOptions } from '$lib/actions/dragdrop';
	import { folderStore } from '$lib/stores/folder.svelte';
	import type { Snippet } from 'svelte';

	type Props = {
		sessionId: string;
		sessionTitle: string;
		children: Snippet;
	};

	let { sessionId, sessionTitle, children }: Props = $props();

	const dragOptions: DraggableOptions = $derived({
		payload: {
			type: 'session',
			id: sessionId,
			title: sessionTitle
		},
		ondragstart: (payload) => {
			folderStore.startDrag(payload);
		},
		ondragend: () => {
			folderStore.endDrag();
		}
	});
</script>

/** * DraggableSession.svelte * ======================= * Wrapper that makes a session draggable for
folder assignment. * * Usage: * <DraggableSession
	sessionId={session.id}
	sessionTitle={session.title}
>
	* <SessionTreeNode ... />
	*
</DraggableSession>
* * The session can be dragged onto any FolderItem in the sidebar. * Visual feedback is provided via CSS
classes during drag operations. */

<div
	use:draggable={dragOptions}
	class="draggable-session"
	class:is-dragging={folderStore.dragPayload?.id === sessionId}
>
	{@render children()}
</div>

<style>
	.draggable-session {
		cursor: grab;
		transition: opacity 150ms ease;
	}

	.draggable-session:active {
		cursor: grabbing;
	}

	.draggable-session.is-dragging {
		opacity: 0.5;
	}

	:global(.dragging) {
		opacity: 0.5;
	}
</style>
