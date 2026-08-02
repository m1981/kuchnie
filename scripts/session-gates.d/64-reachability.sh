#!/usr/bin/env bash
# Reachability gate (review finding N12, kuchnie-lh2): every first-party
# non-test module must be reachable — by imports, from an application entry
# point — or be DECLARED not-yet-wired in docs/not-yet-wired.txt with a bead
# id. Sibling of 60-arch-smells.sh: that gate asks "what does this module
# depend on?", this one asks the inverse, "what depends on this module?".
# Rounds 0-2 of the 2026-08-02 review could not see N12 for exactly that
# reason, and coverage-audit.py scores the orphans TRACED (DARK=0) because
# tests and specs name them — being named is not being reachable.
#
# FAIL (exit 1) — the declaration has a hole:
#   * a module unreachable from every entry point and absent from the
#     allowlist
#   * an allowlist entry carrying no bead id (a deferral with no work item
#     decays into a forgotten one — that is the whole point of the file)
#   * an allowlist entry whose path, or `::symbol`, no longer exists
# NOTE (exit 0) — the allowlist has shrunk; drop the named entries:
#   * an allowlisted module that is now reachable
#   * an allowlisted symbol that now has a first-party non-test reference
#
# Why FAIL and not WARN (the 60-63 family posture): the owner's fidelity-first
# decision (docs/reviews/architecture-consolidated-review-2026-08-02.md) parks
# the wiring epic, which makes "built but unreachable" a STANDING state. A
# standing state has to be a declared one, so the gate that keeps it declared
# has to bite. Adding the one-line allowlist entry is always the cheap fix.
#
# Reachability, precisely: a module is reachable iff a path of first-party
# non-test imports runs to it from an entry point. Package `__init__.py`
# re-exports are ordinary edges, so a module the package publishes is
# reachable through it. Transitive rooting is what surfaces an *island* —
# kuchnie_core.materials imports itself into a tidy circle that no entry
# point ever enters (finding N14, kuchnie-05p); a plain "has >= 1 importer"
# rule scores every one of its modules as fine.
#
# Entry points are legitimately unimported and are listed, never guessed:
# the Reflex app, the two FastAPI apps, the adapter CLI, and the one-shot
# seed/Blender scripts. Add to ENTRIES below, not to the allowlist, when a
# new one lands.
#
# Corpus: the six component source roots of scripts/code-inventory.py
# (ground truth tr-076ed1ea), minus tests and vendored trees — see EXCLUDE.
#
# Detail run: bash scripts/session-gates.d/64-reachability.sh
# Fixture override (scripts/tests/test_reachability.py): REACHABILITY_BASE,
# REACHABILITY_ROOTS, REACHABILITY_ENTRIES, REACHABILITY_ALLOWLIST.
set -u
cd "$(git rev-parse --show-toplevel)"
python3 - "$@" <<'PY'
import ast
import os
import re
from pathlib import Path

BASE = Path(os.environ.get("REACHABILITY_BASE") or Path.cwd()).resolve()

# (root, strip) — `strip` is the prefix removed to form the dotted name the
# rest of the repo imports the module by, exactly as code-inventory.py does.
DEFAULT_ROOTS: list[tuple[str, str]] = [
    ("kuchnie-core/src", "kuchnie-core/src"),
    ("kitchen-cam/src", "kitchen-cam/src"),
    ("kitchen-erp/kitchen_erp", "kitchen-erp"),
    ("home-builder-adapter/src", "home-builder-adapter"),
    ("catalog", ""),  # imported as catalog.*
    ("krono-compositor-mvp/src", "krono-compositor-mvp/src"),
]

# Application entry points: nothing imports these, and nothing should.
# Judgement calls are recorded next to each.
DEFAULT_ENTRIES = [
    "kitchen-erp/kitchen_erp/kitchen_erp.py",   # Reflex app (rxconfig app_name)
    "catalog/api/main.py",                      # FastAPI app (uvicorn target)
    "home-builder-adapter/src/cli.py",          # Blender-driven CLI
    "krono-compositor-mvp/main.py",             # FastAPI app, outside src/
    "krono-compositor-mvp/gen_kitchen.py",      # one-shot Blender generator
    "catalog/scripts/seed*.py",                 # one-shot catalog seeders
    "home-builder-adapter/scripts/*.py",        # one-shot Blender utilities
]

# Vendored, generated and test trees are not first-party source. Getting
# this wrong is not academic: a hand-run of this analysis once swept 400+
# vendored files and buried the finding.
EXCLUDE = {"__pycache__", "tests", "test", "node_modules", ".venv", "venv",
           ".tox", "site-packages", "build", "dist", ".web", ".git",
           "attic", "archive", "public", "data", ".mypy_cache",
           ".pytest_cache", ".ruff_cache"}
BEAD_RE = re.compile(r"\bkuchnie-[0-9a-z]+(?:\.[0-9]+)*\b")


def is_test(rel: Path) -> bool:
    n = rel.name
    return (n.startswith("test_") or n.endswith("_test.py")
            or n == "conftest.py")


def first_party(rel: Path) -> bool:
    return not (any(p in EXCLUDE or p.endswith(".egg-info") for p in rel.parts)
                or is_test(rel))


def env_list(var: str) -> list[str] | None:
    raw = os.environ.get(var)
    if raw is None:
        return None
    return [p for p in raw.split(":") if p.strip()]


roots_env = env_list("REACHABILITY_ROOTS")
# a fixture root strips itself, so dotted names come out root-relative
ROOTS = [(r, r) for r in roots_env] if roots_env is not None else DEFAULT_ROOTS
ENTRIES = env_list("REACHABILITY_ENTRIES")
if ENTRIES is None:
    ENTRIES = DEFAULT_ENTRIES
ALLOWLIST_REL = os.environ.get("REACHABILITY_ALLOWLIST") or "docs/not-yet-wired.txt"
ALLOWLIST = BASE / ALLOWLIST_REL


def dotted_for(rel: Path, strip: str) -> tuple[str, str]:
    """(module dotted name, containing package dotted name)."""
    s = str(rel)
    d = s[len(strip):].lstrip("/") if strip else s
    d = d[:-3].replace("/", ".")
    if d.endswith(".__init__"):
        return d[: -len(".__init__")], d[: -len(".__init__")]
    return d, (d.rsplit(".", 1)[0] if "." in d else "")


# ── 1. enumerate the first-party non-test corpus ──────────────────────
mods: dict[str, dict] = {}
for root, strip in ROOTS:
    base = BASE / root
    if not base.is_dir():
        continue
    for f in sorted(base.rglob("*.py")):
        rel = f.relative_to(BASE)
        if not first_party(rel):
            continue
        d, pkg = dotted_for(rel, strip)
        mods.setdefault(str(rel), {"dotted": d, "pkg": pkg, "path": f})

# Entry points outside the enumerated roots (krono's main.py, the Blender
# scripts) are not modules to judge, but their imports are real edges.
entry_paths: set[str] = set()
for pat in ENTRIES:
    matches = (sorted(BASE.glob(pat)) if any(c in pat for c in "*?[")
               else [BASE / pat])
    for f in matches:
        if not f.is_file():
            continue
        rel = f.relative_to(BASE)
        entry_paths.add(str(rel))
        if str(rel) not in mods:
            mods[str(rel)] = {"dotted": "\0entry:" + str(rel), "pkg": "",
                              "path": f, "outside": True}

by_dotted = {v["dotted"]: k for k, v in mods.items()}


# ── 2. import graph ───────────────────────────────────────────────────
def imports_of(rel: str, info: dict) -> set[str]:
    try:
        tree = ast.parse(info["path"].read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    targets: set[str] = set()

    def add_prefixes(name: str) -> None:
        parts = name.split(".")
        for i in range(1, len(parts) + 1):
            targets.add(".".join(parts[:i]))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                add_prefixes(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base_mod = node.module or ""
            else:
                # `from .x import y` / `from ..core.x import y`
                up = info["pkg"].split(".") if info["pkg"] else []
                if node.level > 1:
                    up = up[: len(up) - (node.level - 1)]
                base_mod = ".".join(up + ([node.module] if node.module else []))
            if not base_mod:
                continue
            add_prefixes(base_mod)
            # `from pkg import submodule` — the alias is the module
            for a in node.names:
                targets.add(base_mod + "." + a.name)
    return {by_dotted[t] for t in targets
            if t in by_dotted and by_dotted[t] != rel}


graph = {rel: imports_of(rel, info) for rel, info in mods.items()}

# ── 3. transitive closure from the entry points ───────────────────────
reachable: set[str] = set()
stack = [e for e in entry_paths if e in graph]
while stack:
    n = stack.pop()
    if n in reachable:
        continue
    reachable.add(n)
    stack.extend(graph.get(n, ()))

judged = {rel for rel, i in mods.items() if not i.get("outside")}
unreachable = sorted(judged - reachable)

# ── 4. read the allowlist ─────────────────────────────────────────────
declared_mods: dict[str, str] = {}
declared_syms: dict[tuple[str, str], str] = {}
failures: list[str] = []
notes: list[str] = []

if ALLOWLIST.exists():
    for lineno, raw in enumerate(
            ALLOWLIST.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entry, _, comment = line.partition("#")
        entry = entry.strip()
        if not entry:
            continue
        if not BEAD_RE.search(comment):
            failures.append(
                f"no bead id   {ALLOWLIST.name}:{lineno} '{entry}' — every "
                f"entry needs a trailing '# kuchnie-<id> — why'")
            continue
        path, sep, symbol = entry.partition("::")
        if sep:
            declared_syms[(path, symbol)] = comment.strip()
        else:
            declared_mods[path] = comment.strip()
elif unreachable:
    failures.append(
        f"missing      {ALLOWLIST_REL} does not exist — create it to "
        f"declare the modules below")

# ── 5. judge modules ──────────────────────────────────────────────────
undeclared = [m for m in unreachable if m not in declared_mods]
for m in undeclared:
    failures.append(f"unreachable  {m} ({mods[m]['dotted']}) — no import path "
                    f"from any entry point")

for path in sorted(declared_mods):
    if not (BASE / path).is_file():
        failures.append(f"stale path   {ALLOWLIST.name} declares {path}, "
                        f"which does not exist — drop or correct the entry")
    elif path not in unreachable:
        notes.append(f"{path} is now reachable — drop its allowlist entry")

# ── 6. judge symbol declarations (sub-module deferrals) ───────────────
# A symbol entry is DECLARED, not discovered: the gate does not hunt for
# uncalled functions (that is a dead-code linter's job, and it reports 130
# here). It keeps a review-named deferral honest — kuchnie-ubc.1's
# purchasing order-doc generators live in a module that IS reachable.
if declared_syms:
    corpus = {}
    for root, _ in ROOTS:
        base = BASE / root
        if base.is_dir():
            for f in base.rglob("*.py"):
                if first_party(f.relative_to(BASE)):
                    corpus[str(f.relative_to(BASE))] = f.read_text(
                        encoding="utf-8", errors="ignore")
    for (path, symbol) in sorted(declared_syms):
        f = BASE / path
        if not f.is_file():
            failures.append(f"stale path   {ALLOWLIST.name} declares "
                            f"{path}::{symbol}, but {path} does not exist")
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            tree = None
        names = {n.name for n in (tree.body if tree else [])
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef))}
        if symbol not in names:
            failures.append(
                f"stale symbol {ALLOWLIST.name} declares {path}::{symbol}, "
                f"which is not a top-level def/class there — drop or rename "
                f"the entry")
            continue
        refs = [p for p, t in corpus.items() if p != path and symbol in t]
        if refs:
            notes.append(f"{path}::{symbol} is now referenced by "
                         f"{refs[0]}{' (+%d more)' % (len(refs) - 1) if len(refs) > 1 else ''}"
                         f" — drop its allowlist entry")

# ── 7. report ─────────────────────────────────────────────────────────
n_declared = len(declared_mods) + len(declared_syms)
if failures:
    print(f"reachability: FAIL {len(failures)} finding(s) "
          f"({len(judged)} first-party module(s) swept, "
          f"{n_declared} declared not-yet-wired):")
    for f in failures:
        print(f"  FAIL  {f}")
    if undeclared:
        print(f"  wire it, or declare it in {ALLOWLIST_REL} — one line each:")
        for m in undeclared:
            print(f"    {m}  # kuchnie-<id> — why it is parked")
else:
    print(f"reachability: {len(judged)} first-party module(s) swept, all "
          f"reachable from an entry point or declared "
          f"({n_declared} not-yet-wired)")
for n in notes:
    print(f"  note: {n}")
raise SystemExit(1 if failures else 0)
PY
