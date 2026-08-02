"""Pinned tests for scripts/session-gates.d/64-reachability.sh (kuchnie-lh2).

Review finding N12 (docs/reviews/architecture-review-round-3-2026-08-02.md
§3): five first-party modules are built, tested and unreachable from the
running application. Under the owner's fidelity-first decision
(docs/reviews/architecture-consolidated-review-2026-08-02.md) the wiring
stays parked, so "built but unreachable" is a STANDING state and must be a
DECLARED one — that is what this gate enforces.

Contract under test:
  * exit 0 = pass, exit 1 = FAIL (session-close.sh reads the exit code)
  * a module unreachable from every entry point and absent from the
    allowlist FAILs
  * an allowlist entry without a bead id FAILs (a declaration with no work
    item is not a declaration)
  * entry points are legitimately unimported
  * vendored trees (.venv/site-packages/node_modules/...) are never swept

Run: .venv/bin/python -m pytest scripts/tests -q
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = "scripts/session-gates.d/64-reachability.sh"
ALLOWLIST = REPO / "docs" / "not-yet-wired.txt"

# The orphan set review round 3 confirmed by hand (§3 evidence table).
REVIEW_ORPHANS = [
    "kitchen-erp/kitchen_erp/core/variant_derivation.py",
    "kitchen-erp/kitchen_erp/core/offers.py",
    "kitchen-erp/kitchen_erp/core/heights.py",
    "kitchen-cam/src/kitchen_cam/machining.py",
    "kitchen-cam/src/kitchen_cam/dxf/panel_dxf.py",
]


def run_gate(**env_overrides: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run(
        ["bash", GATE],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


# ── fixture builder ──────────────────────────────────────────────────
def make_tree(base: Path) -> None:
    """A miniature repo: one entry point, one module it reaches through a
    package __init__ re-export, and one module nothing imports."""
    src = base / "src"
    (src / "pkg").mkdir(parents=True)
    (base / "docs").mkdir()
    (src / "app.py").write_text("from pkg import used\n\nused.go()\n")
    # the re-export leg: __init__ is what makes `used` reachable
    (src / "pkg" / "__init__.py").write_text("from .used import go\n")
    (src / "pkg" / "used.py").write_text("def go():\n    return 1\n")
    (src / "pkg" / "orphan.py").write_text("def never_called():\n    return 2\n")
    (base / "docs" / "allow.txt").write_text("# empty allowlist\n")


FIXTURE_ENV = {
    "REACHABILITY_ROOTS": "src",
    "REACHABILITY_ENTRIES": "src/app.py",
    "REACHABILITY_ALLOWLIST": "docs/allow.txt",
}


def run_fixture(base: Path, **over: str) -> subprocess.CompletedProcess:
    env = dict(FIXTURE_ENV, REACHABILITY_BASE=str(base))
    env.update(over)
    return run_gate(**env)


# ── 1. the current tree passes ───────────────────────────────────────
def test_gate_passes_on_the_current_tree() -> None:
    """With docs/not-yet-wired.txt populated, HEAD is clean (kuchnie-lh2
    acceptance: every current orphan either wired or allowlisted)."""
    proc = run_gate()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "FAIL" not in proc.stdout


def test_allowlist_declares_every_orphan_the_review_confirmed() -> None:
    """The five modules N12's evidence table names must be declared, each
    with a bead id — otherwise the finding has quietly gone unrecorded."""
    text = ALLOWLIST.read_text(encoding="utf-8")
    entries = [ln for ln in text.splitlines()
               if ln.strip() and not ln.lstrip().startswith("#")]
    paths = [ln.split("#")[0].strip() for ln in entries]
    for orphan in REVIEW_ORPHANS:
        assert orphan in paths, f"{orphan} missing from {ALLOWLIST.name}"
    for ln in entries:
        assert "kuchnie-" in ln.split("#", 1)[-1], f"no bead id on: {ln}"


# ── 2. an undeclared orphan FAILs ────────────────────────────────────
def test_undeclared_orphan_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    proc = run_fixture(tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "src/pkg/orphan.py" in proc.stdout
    # the reachable pair must NOT be reported
    assert "src/pkg/used.py" not in proc.stdout
    assert "src/app.py" not in proc.stdout


def test_declared_orphan_passes(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / "docs" / "allow.txt").write_text(
        "# accepted deferrals\n"
        "src/pkg/orphan.py  # kuchnie-lh2 — parked behind the UI\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_allowlist_entry_without_a_bead_id_fails(tmp_path: Path) -> None:
    """A declaration with no work item decays into a forgotten one — the
    whole point of the allowlist (consolidated review, fidelity-first §)."""
    make_tree(tmp_path)
    (tmp_path / "docs" / "allow.txt").write_text(
        "src/pkg/orphan.py  # parked, no bead\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "bead id" in proc.stdout


# ── 3. entry points are legitimately unimported ──────────────────────
def test_entry_point_needs_no_importer(tmp_path: Path) -> None:
    """Nothing imports app.py, and nothing should have to."""
    make_tree(tmp_path)
    proc = run_fixture(tmp_path)
    # the gate ran and found the real orphan, but left the entry point alone
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "src/pkg/orphan.py" in proc.stdout
    assert "src/app.py" not in proc.stdout


def test_declaring_an_orphan_as_an_entry_point_passes(tmp_path: Path) -> None:
    """A CLI or one-shot script is unimported by design — the entry-point
    list, not the allowlist, is where it belongs."""
    make_tree(tmp_path)
    proc = run_fixture(tmp_path,
                       REACHABILITY_ENTRIES="src/app.py:src/pkg/orphan.py")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_entry_points_accept_globs(tmp_path: Path) -> None:
    """Seed scripts are declared by pattern, not one by one."""
    make_tree(tmp_path)
    (tmp_path / "src" / "seed_a.py").write_text("X = 1\n")
    (tmp_path / "src" / "seed_b.py").write_text("X = 2\n")
    proc = run_fixture(tmp_path, REACHABILITY_ENTRIES="src/app.py:src/seed*.py")
    assert "seed_a.py" not in proc.stdout
    assert "seed_b.py" not in proc.stdout
    assert proc.returncode == 1  # orphan.py still undeclared
    assert "src/pkg/orphan.py" in proc.stdout


# ── 4. vendored code is never swept ──────────────────────────────────
def test_vendored_trees_are_excluded(tmp_path: Path) -> None:
    """An earlier hand-run of this analysis swept 400+ vendored files. A
    module under .venv/site-packages/node_modules/__pycache__ is not
    first-party and must not be reported, allowlisted or counted."""
    make_tree(tmp_path)
    vendored = [
        tmp_path / "src" / ".venv" / "lib" / "python3.13" / "site-packages"
        / "vendored_pkg" / "mod.py",
        tmp_path / "src" / "pkg" / "node_modules" / "thing" / "shim.py",
        tmp_path / "src" / "pkg" / "__pycache__" / "cached.py",
        tmp_path / "src" / "venv" / "other.py",
    ]
    for v in vendored:
        v.parent.mkdir(parents=True, exist_ok=True)
        v.write_text("def vendored_thing():\n    return 0\n")
    proc = run_fixture(tmp_path)
    # the gate ran (it still sees the first-party orphan) …
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "src/pkg/orphan.py" in proc.stdout
    # … and swept none of the vendored files
    for v in vendored:
        assert v.name not in proc.stdout, f"{v} was swept"
    assert "vendored_pkg" not in proc.stdout
    assert "node_modules" not in proc.stdout
    # the fixture has exactly 4 first-party modules (app, pkg, used, orphan);
    # the count is the guard against a silently widened sweep
    assert "4 first-party module(s) swept" in proc.stdout, \
        "vendored files inflated the swept count"


def test_test_files_are_not_first_party_sources(tmp_path: Path) -> None:
    """Tests neither count as importers nor need importing — that inversion
    is exactly what let N12 hide behind DARK=0."""
    make_tree(tmp_path)
    tdir = tmp_path / "src" / "tests"
    tdir.mkdir()
    (tdir / "test_orphan.py").write_text(
        "from pkg.orphan import never_called\n")
    (tmp_path / "src" / "pkg" / "test_inline.py").write_text(
        "from pkg.orphan import never_called\n")
    proc = run_fixture(tmp_path)
    # the test importers must not rescue orphan.py, and must not themselves
    # be reported as unreachable modules
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "src/pkg/orphan.py" in proc.stdout
    assert "test_orphan.py" not in proc.stdout
    assert "test_inline.py" not in proc.stdout


# ── 5. the allowlist stays honest ────────────────────────────────────
def test_stale_allowlist_entry_is_reported(tmp_path: Path) -> None:
    """Once a parked module gets wired, its entry must be dropped —
    same 'baseline finding fixed' note 60-arch-smells.sh prints."""
    make_tree(tmp_path)
    (tmp_path / "docs" / "allow.txt").write_text(
        "src/pkg/orphan.py  # kuchnie-lh2 — parked\n"
        "src/pkg/used.py    # kuchnie-lh2 — stale, this one IS reachable\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "src/pkg/used.py" in proc.stdout
    assert "stale" in proc.stdout.lower() or "reachable" in proc.stdout.lower()


def test_allowlist_entry_for_a_missing_file_fails(tmp_path: Path) -> None:
    """A path that no longer exists is a rotted declaration."""
    make_tree(tmp_path)
    (tmp_path / "docs" / "allow.txt").write_text(
        "src/pkg/orphan.py  # kuchnie-lh2 — parked\n"
        "src/pkg/deleted.py # kuchnie-lh2 — file is gone\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "deleted.py" in proc.stdout


# ── 6. symbol-level declarations (the purchasing generators) ─────────
def test_symbol_entry_validates_and_passes(tmp_path: Path) -> None:
    """`path::symbol` declares a sub-module deferral (kuchnie-ubc.1: the
    purchasing order-doc generators live in a module that IS reachable)."""
    make_tree(tmp_path)
    (tmp_path / "src" / "pkg" / "used.py").write_text(
        "def go():\n    return 1\n\n\ndef order_rows():\n    return []\n")
    (tmp_path / "docs" / "allow.txt").write_text(
        "src/pkg/orphan.py            # kuchnie-lh2 — parked\n"
        "src/pkg/used.py::order_rows  # kuchnie-ubc.1 — no caller yet\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_symbol_entry_for_an_absent_symbol_fails(tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / "docs" / "allow.txt").write_text(
        "src/pkg/orphan.py           # kuchnie-lh2 — parked\n"
        "src/pkg/used.py::not_there  # kuchnie-ubc.1 — renamed away\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "not_there" in proc.stdout


def test_symbol_entry_that_gained_a_caller_is_reported_stale(
        tmp_path: Path) -> None:
    make_tree(tmp_path)
    (tmp_path / "src" / "pkg" / "used.py").write_text(
        "def go():\n    return 1\n\n\ndef order_rows():\n    return []\n")
    (tmp_path / "src" / "app.py").write_text(
        "from pkg import used\nfrom pkg.used import order_rows\n\n"
        "used.go()\norder_rows()\n")
    (tmp_path / "docs" / "allow.txt").write_text(
        "src/pkg/orphan.py            # kuchnie-lh2 — parked\n"
        "src/pkg/used.py::order_rows  # kuchnie-ubc.1 — now wired\n")
    proc = run_fixture(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "order_rows" in proc.stdout
