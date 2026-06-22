<script lang="ts">
  import { folderStore } from "$lib/stores/folder.svelte";
  import { droppable } from "$lib/actions/dragdrop";
  import FolderItem from "./FolderItem.svelte";
  import CreateFolderDialog from "./CreateFolderDialog.svelte";
  import type { Snippet } from "svelte";

  type Props = {
    activeId?: string | null;
    children?: Snippet;
    onload?: (sessionId: string) => void;
  };

  let { activeId = null, children, onload }: Props = $props();

  // No local expandedFolders state — it's in the store now
</script>

<!-- Header -->
<div class="mb-2 flex items-center justify-between">
  <h2 class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">Folders</h2>
  <button
    type="button"
    onclick={() => folderStore.openCreateDialog()}
    class="flex h-6 w-6 items-center justify-center rounded-md text-muted transition hover:bg-surface hover:text-ink"
    aria-label="Create folder"
    title="Create folder"
  >
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    >
      <path d="M7 3v8M3 7h8" />
    </svg>
  </button>
</div>

<!-- Error toast -->
{#if folderStore.error}
  <div
    class="mb-2 rounded-md border border-red-200 bg-red-50 px-2.5 py-1.5 text-xs text-red-700"
    role="alert"
  >
    {folderStore.error}
  </div>
{/if}

<!-- Loading state -->
{#if folderStore.fetchState.status === "loading"}
  <div class="space-y-1.5">
    {#each [1, 2, 3] as i (i)}
      <div class="h-8 animate-pulse rounded-md bg-line"></div>
    {/each}
  </div>

  <!-- Error state -->
{:else if folderStore.fetchState.status === "error"}
  <p class="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
    {folderStore.fetchState.message}
  </p>

  <!-- Empty state -->
{:else if folderStore.sortedFolders.length === 0}
  <p class="rounded-md border border-dashed border-line bg-surface p-3 text-sm text-muted">
    No folders yet. Create one to organize your sessions.
  </p>

  <!-- Folder list -->
{:else}
  <div class="flex flex-col gap-0.5">
    {#each folderStore.sortedFolders as folder (folder.id)}
      <div
        use:droppable={{
          target: { type: "folder", id: folder.id },
          acceptTypes: ["session"],
          ondragenter: (target) => folderStore.setDropTarget(target),
          ondragleave: () => {
            // Only clear if THIS zone is still the active target.
            // Prevents race condition: moving from A→B fires dragenter(B) then
            // dragleave(A). Without the guard, dragleave(A) would wipe out B.
            if (folderStore.dropTarget?.id === folder.id) {
              folderStore.setDropTarget(null);
            }
          },
          ondrop: async (payload, target) => {
            console.debug("[DnD] FolderTree.ondrop", {
              sessionId: payload.id,
              from: payload.sourceFolderId ?? "history",
              to: target.id,
            });
            if (payload.type === "session" && target.type === "folder") {
              // Cross-folder move: unassign from source folder first
              if (payload.sourceFolderId && payload.sourceFolderId !== target.id) {
                console.debug("[DnD] cross-folder: unassign from", payload.sourceFolderId);
                await folderStore.unassignSession(payload.sourceFolderId, payload.id);
              }
              // Assign to target folder (skip if already in this folder)
              if (payload.sourceFolderId !== target.id) {
                console.debug("[DnD] assigning to", target.id);
                await folderStore.assignSession(target.id, payload.id);
              } else {
                console.debug("[DnD] same folder, skipped");
              }
            }
            folderStore.endDrag();
          },
        }}
        class="folder-drop-zone"
        class:drag-over={folderStore.dropTarget?.id === folder.id}
      >
        <FolderItem folderId={folder.id} {activeId} onloadsession={onload} />
      </div>
    {/each}
  </div>
{/if}

<!-- Unorganized sessions slot -->
{#if children}
  <div class="mt-3 border-t border-line pt-2">
    <h3 class="mb-1 text-xs font-semibold tracking-[0.14em] text-muted uppercase">Unorganized</h3>
    {@render children()}
  </div>
{/if}

<!-- Create folder dialog -->
{#if folderStore.createDialogOpen}
  <CreateFolderDialog
    onclose={() => folderStore.closeCreateDialog()}
    oncreate={async (request) => {
      await folderStore.createFolder(request);
      folderStore.closeCreateDialog();
    }}
  />
{/if}

<style>
  .folder-drop-zone {
    border-radius: 6px;
    transition: background-color 150ms ease;
  }

  .folder-drop-zone.drag-over {
    background-color: color-mix(in srgb, var(--color-accent) 15%, transparent);
    outline: 2px dashed var(--color-accent);
    outline-offset: -2px;
  }
</style>
