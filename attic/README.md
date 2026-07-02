# attic/

Holding pen for files removed during the **2026-07 freeze rescue** (see
`docs/freeze/`). Nothing here is deleted — kept in-tree so a future maintainer
can decide whether to purge or restore.

## Contents

### `all-signatures.md`
Regenerable auto-dump of all Python function signatures across the monorepo
(top-level, 57 KB). Was untracked at freeze. Moved out because it is a build
artifact, not source.

### `evidence-01-tree.txt`
Regenerable `tree`-style listing of the repo produced during some prior audit
(40 KB). Was untracked at freeze.

### `kitchen-plugin/`
**Flag: resurrected duplicate, suspected session accident.**

`kitchen-plugin/docs/wall-centric-model.md` was found untracked at freeze time,
byte-identical to the tracked `home-builder-adapter/docs/archive/wall-centric-model.md`
(proof: `diff` returned no output, exit 0).

History (`git log --follow`) shows the file's canonical path is
`home-builder-adapter/docs/archive/wall-centric-model.md` — the component was
renamed `kitchen-plugin/` → `home-builder-adapter/` per ADR-009 (see AGENTS.md
component roster). The archived copy was **also deleted from disk** in the
uncommitted working tree at freeze time.

The freeze rescue restored the archive copy (`git restore …`) and moved this
resurrected `kitchen-plugin/` tree here rather than delete it, in case the
deletion+recreation was intentional. If nobody claims it by the next thaw, it
can be removed.
