<script lang="ts">
  import { folderStore } from "$lib/stores/folder.svelte";
  import { smartPosition } from "$lib/actions/smartPosition";
  import { focusTrap } from "$lib/actions/focustrap";

  type Props = {
    folderId: string;
    activeId?: string | null;
    onloadsession?: (sessionId: string) => void;
  };

  let { folderId, activeId = null, onloadsession }: Props = $props();

  // Get folder from store reactively
  const folder = $derived(folderStore.getFolderById(folderId)!);
  const isExpanded = $derived(folderStore.isExpanded(folderId));
  const sessions = $derived(folderStore.getSessions(folderId));
  const isLoading = $derived(folderStore.sessionsLoading.get(folderId) ?? false);
  const sessionsError = $derived(folderStore.sessionsError.get(folderId) ?? null);

  let showMenu = $state(false);
  let menuRef = $state<HTMLElement | null>(null);
  let menuTriggerEl = $state<HTMLButtonElement | null>(null);
  let sessionMenuId = $state<string | null>(null);

  // Close menu on outside click
  function handleClickOutside(e: MouseEvent) {
    if (menuRef && !menuRef.contains(e.target as Node)) {
      showMenu = false;
    }
  }

  function closeSessionMenu() {
    sessionMenuId = null;
  }

  $effect(() => {
    if (showMenu || sessionMenuId !== null) {
      document.addEventListener("click", handleClickOutside);
      return () => document.removeEventListener("click", handleClickOutside);
    }
  });

  // Session menu actions
  async function handleUnassign(sessionId: string) {
    closeSessionMenu();
    await folderStore.unassignSession(folderId, sessionId);
  }

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
    { name: "Gray", hex: "#6B7280" },
    { name: "Red", hex: "#EF4444" },
    { name: "Orange", hex: "#F97316" },
    { name: "Yellow", hex: "#EAB308" },
    { name: "Green", hex: "#22C55E" },
    { name: "Blue", hex: "#3B82F6" },
    { name: "Purple", hex: "#A855F7" },
    { name: "Pink", hex: "#EC4899" },
  ];
</script>

<div class="rounded-md transition hover:bg-surface">
  <!-- Folder header row -->
  <div class="group flex items-center gap-1 px-1.5 py-1">
    <!-- Expand/collapse toggle -->
    <button
      type="button"
      onclick={() => folderStore.toggleExpand(folderId)}
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
      onclick={() => folderStore.toggleExpand(folderId)}
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
      bind:this={menuTriggerEl}
      onclick={(e) => {
        e.stopPropagation();
        showMenu = !showMenu;
      }}
      class="flex h-5 w-5 items-center justify-center rounded text-muted opacity-45 transition group-hover:opacity-100 hover:bg-line hover:text-ink focus:opacity-100 focus:outline-none"
      aria-label="Folder options"
    >
      <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
        <circle cx="7" cy="3" r="1.5" />
        <circle cx="7" cy="7" r="1.5" />
        <circle cx="7" cy="11" r="1.5" />
      </svg>
    </button>
  </div>

  <!-- Expanded: show sessions (derived from store — no $effect needed) -->
  {#if isExpanded}
    <div class="ml-1 border-l border-line pb-0.5 pl-1">
      {#if isLoading}
        <div class="space-y-1 py-1">
          {#each [1, 2] as i (i)}
            <div class="h-6 animate-pulse rounded bg-line"></div>
          {/each}
        </div>
      {:else if sessionsError}
        <p class="py-1 text-xs text-red-600">{sessionsError}</p>
      {:else if sessions.length === 0}
        <p class="py-1 text-xs text-muted italic">No sessions in this folder</p>
      {:else}
        <div class="flex flex-col gap-0.5">
          {#each sessions as session (session.id)}
            {@const isPending = folderStore.pendingOps.has(session.id)}
            {@const isActive = session.id === activeId}
            <button
              type="button"
              onclick={() => onloadsession?.(session.id)}
              disabled={isPending}
              class="group flex w-full cursor-pointer items-center gap-1 rounded-md px-2 py-1 text-left
								transition
								{isActive ? 'bg-accent-soft shadow-[inset_3px_0_0_var(--color-accent)]' : 'hover:bg-surface'}
								{isPending ? 'animate-pulse opacity-50' : ''}"
            >
              <!-- Spacer -->
              <span class="w-1 shrink-0" aria-hidden="true"></span>
              <span
                class="min-w-0 flex-1 truncate text-sm
									{isActive ? 'font-semibold text-ink' : 'font-medium text-muted group-hover:text-ink'}"
                title={session.title}
              >
                {session.title}
              </span>
              <!-- Session context menu -->
              <div class="relative">
                <span
                  role="button"
                  tabindex="0"
                  onclick={(e) => {
                    e.stopPropagation();
                    sessionMenuId = sessionMenuId === session.id ? null : session.id;
                  }}
                  onkeydown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.stopPropagation();
                      sessionMenuId = sessionMenuId === session.id ? null : session.id;
                    }
                  }}
                  title="Session options"
                  aria-label="Session options"
                  aria-expanded={sessionMenuId === session.id}
                  class="flex h-5 w-5 items-center justify-center rounded text-muted transition
									       group-hover:opacity-100 hover:bg-line hover:text-ink focus:opacity-100 focus:outline-none
									       {sessionMenuId === session.id ? 'opacity-100' : 'opacity-45'}"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <circle cx="8" cy="3" r="1.4" />
                    <circle cx="8" cy="8" r="1.4" />
                    <circle cx="8" cy="13" r="1.4" />
                  </svg>
                </span>

                {#if sessionMenuId === session.id}
                  <div
                    use:focusTrap
                    class="absolute top-full right-0 z-40 min-w-[160px] rounded-lg border border-line bg-panel
										       py-1 shadow-lg"
                  >
                    <button
                      type="button"
                      onclick={() => {
                        closeSessionMenu();
                        onloadsession?.(session.id);
                      }}
                      class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-ink
											       hover:bg-surface"
                    >
                      <span aria-hidden="true">📂</span> Open
                    </button>

                    <div class="my-1 border-t border-line"></div>

                    <button
                      type="button"
                      onclick={() => {
                        closeSessionMenu();
                        handleUnassign(session.id);
                      }}
                      class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-muted
											       hover:bg-surface hover:text-ink"
                    >
                      <span aria-hidden="true">↩</span> Remove from folder
                    </button>
                  </div>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Context menu dropdown -->
{#if showMenu}
  <div
    bind:this={menuRef}
    use:smartPosition={{ trigger: menuTriggerEl!, placement: "bottom-end" }}
    class="fixed z-50 min-w-[160px] rounded-md border border-line bg-surface py-1 shadow-lg"
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
