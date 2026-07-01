#!/bin/bash
# Documentation Reorganization Script
# Based on evolution analysis and doc noise analysis
# 
# Usage: bash scripts/reorganize_docs.sh [--dry-run]

set -euo pipefail

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=true
  echo "=== DRY RUN MODE ==="
fi

run() {
  if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] $*"
  else
    echo "  [EXEC] $*"
    "$@"
  fi
}

cd "$(dirname "$0")/.."

echo ""
echo "=== Phase 1: Create new directory structure ==="
run mkdir -p docs/vision
run mkdir -p docs/archive
run mkdir -p catalog/docs/archive
run mkdir -p kitchen-app/docs/archive/doc
run mkdir -p kitchen-cad/docs/specs
run mkdir -p kitchen-cad/docs/adr
run mkdir -p kitchen-cad/docs/archive
run mkdir -p kitchen-plugin/docs/specs
run mkdir -p kitchen-plugin/docs/adr
run mkdir -p krono-compositor-mvp/docs/specs
run mkdir -p krono-compositor-mvp/docs/adr
run mkdir -p krono-compositor-mvp/docs/archive

echo ""
echo "=== Phase 2: Move vision docs ==="
run git mv docs/00-brief.md docs/vision/00-mission.md
run git mv docs/00-brief2.md docs/vision/01-user-journeys.md
run git mv docs/02_pattern_mapping.md docs/vision/02-pattern-mapping.md

echo ""
echo "=== Phase 3: Archive stale root docs ==="
for f in docs/COLD-REVIEW-*.md docs/CATALOG_RELOCATION_PLAN.md docs/DATA-FLOW-BLENDER.md docs/ARCHITECTURE-kuchnie-core.md; do
  if [ -f "$f" ]; then
    # Check if tracked by git
    if git ls-files --error-unmatch "$f" &>/dev/null; then
      run git mv "$f" docs/archive/
    else
      run mv "$f" docs/archive/
    fi
  fi
done

# Move archive2 contents to archive
if [ -d docs/archive2 ]; then
  for f in docs/archive2/*; do
    if [ -f "$f" ]; then
      run git mv "$f" docs/archive/
    fi
  done
  run rmdir docs/archive2
fi

echo ""
echo "=== Phase 4: Quarantine kitchen-app ==="
if [ -d kitchen-app/doc ]; then
  for f in kitchen-app/doc/*; do
    if [ -f "$f" ]; then
      run git mv "$f" kitchen-app/docs/archive/doc/
    fi
  done
  run rmdir kitchen-app/doc
fi

echo ""
echo "=== Phase 5: Reorganize kitchen-cad ==="
# Move specs
if [ -f kitchen-cad/docs/LEGRABOX_SPEC.md ]; then
  run git mv kitchen-cad/docs/LEGRABOX_SPEC.md kitchen-cad/docs/specs/legrabox-spec.md
fi
if [ -f kitchen-cad/docs/CABINET-VARIANTS.md ]; then
  run git mv kitchen-cad/docs/CABINET-VARIANTS.md kitchen-cad/docs/specs/cabinet-variants.md
fi
if [ -f kitchen-cad/docs/00-overview.md ]; then
  run git mv kitchen-cad/docs/00-overview.md kitchen-cad/docs/specs/overview.md
fi

# Move stale docs to archive
for f in kitchen-cad/docs/PROJECT_LOG.md kitchen-cad/docs/test-plan.md kitchen-cad/docs/poradnik-kompleksowy.md kitchen-cad/docs/analiza_konfiguratora_formatek.md kitchen-cad/docs/DOCUMENTATION_GUIDELINES.md; do
  if [ -f "$f" ]; then
    run git mv "$f" kitchen-cad/docs/archive/
  fi
done

# Move sessions to archive
if [ -d kitchen-cad/docs/sessions ]; then
  run git mv kitchen-cad/docs/sessions kitchen-cad/docs/archive/
fi

echo ""
echo "=== Phase 6: Reorganize krono-compositor ==="
# Move specs
if [ -f krono-compositor-mvp/docs/PIPELINE_RULES.md ]; then
  run git mv krono-compositor-mvp/docs/PIPELINE_RULES.md krono-compositor-mvp/docs/specs/pipeline-rules.md
fi
if [ -f krono-compositor-mvp/docs/blender-scene-reference.md ]; then
  run git mv krono-compositor-mvp/docs/blender-scene-reference.md krono-compositor-mvp/docs/specs/blender-scene-ref.md
fi

# Move stale docs to archive
for f in krono-compositor-mvp/docs/conflicting_paradigms.md krono-compositor-mvp/docs/prompt_blender.md krono-compositor-mvp/docs/prompt_web.md krono-compositor-mvp/docs/what_next.md krono-compositor-mvp/docs/rendering-improvements.md; do
  if [ -f "$f" ]; then
    run git mv "$f" krono-compositor-mvp/docs/archive/
  fi
done

echo ""
echo "=== Phase 7: Reorganize catalog ==="
if [ -f catalog/docs/03-configurator-design.md ]; then
  run git mv catalog/docs/03-configurator-design.md catalog/docs/architecture/configurator-design.md
fi
for f in catalog/docs/STATE-SYNC-*.md; do
  if [ -f "$f" ]; then
    run git mv "$f" catalog/docs/archive/
  fi
done

echo ""
echo "=== Phase 8: Create README markers ==="

# Root docs README
if [ ! -f docs/README.md ]; then
  cat > /tmp/docs_readme.md << 'EOF'
# Documentation Structure

## Layers

| Layer | Directory | Purpose | Trust Level |
|-------|-----------|---------|-------------|
| Vision | `vision/` | Strategy, mission, roadmap | Aspirational |
| Decisions | `adr/` | Immutable architecture decisions | High |
| Shared | `*.md` | Cross-project docs | Varies |
| Archive | `archive/` | Historical, no longer current | Low |

## Projects

Each project has its own `docs/` directory with:
- `specs/` — contracts and specifications
- `adr/` — project-specific decisions
- `architecture/` — current state documentation
- `archive/` — historical docs

## See Also

- `REORGANIZATION_PLAN.md` — migration details
- Per-project `AGENTS.md` — AI agent guides
EOF
  if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] Create docs/README.md"
  else
    mv /tmp/docs_readme.md docs/README.md
    echo "  [CREATE] docs/README.md"
  fi
fi

echo ""
echo "=== Done ==="
if [ "$DRY_RUN" = true ]; then
  echo "Run without --dry-run to execute."
else
  echo "Review changes with: git status"
  echo "Commit with: git add -A && git commit -m 'docs: reorganize into vision/spec/doc layers'"
fi
