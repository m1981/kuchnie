<script lang="ts">
	import type { Folder } from '$lib/api';
	import { folderStore } from '$lib/stores/folder.svelte';

	type Props = {
		folder: Folder;
		isExpanded: boolean;
		ontoggle: () => void;
	};

	let { folder, isExpanded, ontoggle }: Props = $props();

	let showMenu = $state(false);
	let menuRef = $state<HTMLElement | null>(null);

	// Close menu on outside click
	function handleClickOutside(e: MouseEvent) {
		if (menuRef && !menuRef.contains(e.target as Node)) {
			showMenu = false;
		}
	}

	$effect(() => {
		if (showMenu) {
			document.addEventListener('click', handleClickOutside);
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});

	// Menu actions
	function handleRename() {
		showMenu = false;
		folderStore.startEditing(folder.id);
	}

	async function handleDelete() {
		showMenu = false;
		if (confirm(`Delete folder "${folder.name}"? Sessions will be unassigned but not deleted.`)) {
			await folderStore.deleteFolder(folder.id);
		}
	}

	function handleColorChange(color: string) {
		showMenu = false;
		folderStore.updateFolder(folder.id, { color });
	}

	// Color palette
	const colors = [
		{ name: 'Gray', hex: '#6B7280' },
		{ name: 'Red', hex: '#EF4444' },
		{ name: 'Orange', hex: '#F97316' },
		{ name: 'Yellow', hex: '#EAB308' },
		{ name: 'Green', hex: '#22C55E' },
		{ name: 'Blue', hex: '#3B82F6' },
		{ name: 'Purple', hex: '#A855F7' },
		{ name: 'Pink', hex: '#EC4899' }
	];
</script>

/** * FolderItem.svelte * ================= * Single folder in the sidebar tree. * * Features: * -
Expand/collapse toggle * - Color dot indicator * - Session count badge * - Context menu (rename,
change color, delete) * - Drop target highlight */

<div class="group flex items-center gap-1.5 rounded-md px-2 py-1.5 transition hover:bg-surface">
	<!-- Expand/collapse toggle -->
	<button
		type="button"
		onclick={ontoggle}
		class="flex h-4 w-4 shrink-0 items-center justify-center text-muted transition-transform"
		aria-expanded={isExpanded}
		aria-label="{isExpanded ? 'Collapse' : 'Expand'} {folder.name}"
	>
		<svg
			width="10"
			height="10"
			viewBox="0 0 10 10"
			fill="currentColor"
			class="transition-transform {isExpanded ? 'rotate-90' : ''}"
		>
			<path d="M3 2 L7 5 L3 8 Z" />
		</svg>
	</button>

	<!-- Color dot -->
	<span
		class="h-3 w-3 shrink-0 rounded-full"
		style="background-color: {folder.color}"
		aria-hidden="true"
	></span>

	<!-- Folder name -->
	<button
		type="button"
		onclick={ontoggle}
		class="min-w-0 flex-1 truncate text-left text-sm text-ink"
	>
		{folder.icon}
		{folder.name}
	</button>

	<!-- Session count badge -->
	{#if folder.session_count > 0}
		<span
			class="rounded-full border border-line bg-surface px-1.5 py-0.5 text-[10px] font-medium text-muted"
		>
			{folder.session_count}
		</span>
	{/if}

	<!-- Context menu button -->
	<button
		type="button"
		onclick|stopPropagation={() => (showMenu = !showMenu)}
		class="flex h-6 w-6 items-center justify-center rounded-md text-muted opacity-0 transition group-hover:opacity-100 hover:bg-surface hover:text-ink"
		aria-label="Folder options"
	>
		<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
			<circle cx="7" cy="3" r="1.5" />
			<circle cx="7" cy="7" r="1.5" />
			<circle cx="7" cy="11" r="1.5" />
		</svg>
	</button>
</div>

<!-- Context menu dropdown -->
{#if showMenu}
	<div
		bind:this={menuRef}
		class="absolute right-2 z-50 mt-1 min-w-[160px] rounded-md border border-line bg-surface py-1 shadow-lg"
		role="menu"
	>
		<button
			type="button"
			onclick={handleRename}
			class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-ink hover:bg-surface"
			role="menuitem"
		>
			✏️ Rename
		</button>

		<!-- Color submenu -->
		<div class="border-t border-line px-3 py-1.5">
			<p class="mb-1 text-[10px] font-semibold text-muted uppercase">Color</p>
			<div class="flex gap-1">
				{#each colors as color (color.hex)}
					<button
						type="button"
						onclick={() => handleColorChange(color.hex)}
						class="h-5 w-5 rounded-full transition-transform hover:scale-110 {folder.color ===
						color.hex
							? 'ring-2 ring-accent ring-offset-1'
							: ''}"
						style="background-color: {color.hex}"
						aria-label={color.name}
						title={color.name}
					></button>
				{/each}
			</div>
		</div>

		<div class="border-t border-line">
			<button
				type="button"
				onclick={handleDelete}
				class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm text-red-600 hover:bg-red-50"
				role="menuitem"
			>
				🗑️ Delete
			</button>
		</div>
	</div>
{/if}
