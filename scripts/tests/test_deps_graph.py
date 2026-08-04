"""The dependency graph must be evidence, not a drawing.

Four obligations, and they are the reasons this file exists rather than a
"it ran without crashing" smoke test:

  * DETERMINISM — two consecutive builds are byte-identical, or the artifact
    cannot go into git and its diffs cannot be reviewed.
  * NO DARK EXTRACTOR — every extractor reports what it examined, and a zero
    is a FAILURE. This repo has lost three checks to silent zeros in two days
    (a suite "clean" while running 0 tests; a count regex that needed a leading
    character; a `grep -c` matching claim text instead of the status column).
  * PROVENANCE — every edge resolves to a real file and a real line. An edge
    nobody can trace back is a claim, not evidence.
  * THE CROSS-CHECK — a fact known independently of the tool: pre-push-checks.sh
    invokes every gate in session-gates.d EXCEPT 20-exercise-gate.sh, and
    invokes scripts/exercise-gate.sh directly. If the extractor cannot
    reproduce that, the extractor is wrong and the rest of the graph is not
    worth reading.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / "scripts" / "deps-graph.py"

_spec = importlib.util.spec_from_file_location("deps_graph", TOOL)
dg = importlib.util.module_from_spec(_spec)
sys.modules["deps_graph"] = dg
_spec.loader.exec_module(dg)


@pytest.fixture(scope="module")
def built():
    edges, reports, corpus = dg.build(ROOT)
    # A sensor that cannot see its own corpus must scream, never pass empty.
    assert corpus.scope, "the in-scope corpus is empty — the sweep is dark"
    return edges, reports, corpus


# ── the cross-check against an independently known fact ──────────────────
def test_invokes_reproduces_the_pre_push_gate_wiring(built):
    edges, _, _ = built
    gate_dir = ROOT / "scripts" / "session-gates.d"
    on_disk = {f"scripts/session-gates.d/{p.name}"
               for p in gate_dir.glob("*.sh")}
    assert len(on_disk) >= 5, "session-gates.d glob is dark"
    expected = on_disk - {"scripts/session-gates.d/20-exercise-gate.sh"}

    found = {e.dst for e in edges
             if e.kind == "invokes"
             and e.src == "scripts/pre-push-checks.sh"
             and e.dst.startswith("scripts/session-gates.d/")}
    assert found == expected, (
        f"missing {sorted(expected - found)}, spurious {sorted(found - expected)}"
    )
    assert any(e.kind == "invokes"
               and e.src == "scripts/pre-push-checks.sh"
               and e.dst == "scripts/exercise-gate.sh"
               for e in edges), (
        "pre-push-checks.sh runs scripts/exercise-gate.sh directly (section 2) "
        "and the graph does not show it")


# ── no dark extractor ────────────────────────────────────────────────────
def _reports():
    return [r.name for r in dg.build(ROOT)[1]]


def test_every_edge_kind_has_exactly_one_extractor(built):
    """Adding an artifact type must mean adding an extractor, not editing a
    monolith — so no kind may be produced by two of them."""
    edges, _, _ = built
    owner: dict[str, set[str]] = {}
    for e in edges:
        owner.setdefault(e.kind, set()).add(e.extractor)
    multi = {k: v for k, v in owner.items() if len(v) > 1}
    assert not multi, f"edge kind(s) produced by more than one extractor: {multi}"


@pytest.mark.parametrize("name", [
    "invokes", "triggers", "filters", "reads", "imports",
    "cites", "references", "defines", "premise", "watches",
])
def test_extractor_is_not_dark(built, name):
    """The positive control, one per extractor.

    Zero files examined means the corpus selector broke. Zero edges means the
    matcher broke — every one of these kinds is populated in this repo today,
    so a zero cannot be 'nothing to find'.
    """
    _, reports, _ = built
    rep = next((r for r in reports if r.name == name), None)
    assert rep is not None, f"no extractor reports as {name!r}"
    assert rep.files_examined > 0, (
        f"{name} examined 0 files — an extractor that examined nothing is a "
        "FAILURE, never a silent zero")
    assert rep.edges_found > 0, (
        f"{name} found 0 edges over {rep.files_examined} file(s) — this kind "
        "is populated in this repo, so zero means the extractor broke")


# ── provenance ───────────────────────────────────────────────────────────
def test_every_edge_traces_back_to_a_line(built):
    edges, _, corpus = built
    bad = []
    for e in edges:
        if e.file not in corpus.tracked:
            bad.append(f"{e.kind} {e.src}->{e.dst}: file {e.file} not tracked")
        elif e.line < 1:
            bad.append(f"{e.kind} {e.src}->{e.dst}: line {e.line}")
        elif not e.extractor:
            bad.append(f"{e.kind} {e.src}->{e.dst}: no extractor")
    assert not bad, f"{len(bad)} edge(s) without provenance, e.g. {bad[:5]}"


def test_provenance_lines_are_real(built):
    """Spot-check that file:line actually contains the evidence.

    Not every kind can be checked this way (ledger edges point at a JSON
    record), so this checks the token-based kinds, where the destination
    literally has to appear on the cited line.
    """
    edges, _, corpus = built
    checkable = [e for e in edges
                 if e.kind in ("invokes", "triggers", "reads", "references",
                               "filters")]
    assert len(checkable) > 100, "too few checkable edges — sample is dark"
    misses = []
    for e in checkable[::37]:
        line = corpus.text(e.file).splitlines()[e.line - 1]
        if e.dst not in line:
            misses.append(f"{e.file}:{e.line} does not contain {e.dst}")
    assert not misses, misses[:5]


# ── determinism ──────────────────────────────────────────────────────────
def test_two_builds_are_byte_identical(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    for out in (a, b):
        env = dict(os.environ, DEPS_GRAPH_PATH=str(out))
        run = subprocess.run([sys.executable, str(TOOL), "--build"],
                             cwd=ROOT, env=env, capture_output=True,
                             text=True, timeout=300)
        assert run.returncode == 0, run.stdout + run.stderr
    assert a.read_bytes() == b.read_bytes(), (
        "two consecutive builds differ — the artifact is not diffable")
    assert a.read_text().count("\n") > 500


def test_committed_graph_is_current():
    """The committed artifact must be what the extractor produces today.

    A stale graph is worse than none: every query below it answers with
    yesterday's repo while looking exactly as authoritative.
    """
    committed = ROOT / "docs" / "deps-graph.jsonl"
    if not committed.exists():
        pytest.skip("docs/deps-graph.jsonl not built yet")
    edges, _, _ = dg.build(ROOT)
    fresh = "".join(json.dumps(e.as_dict(), sort_keys=True,
                               ensure_ascii=False) + "\n" for e in edges)
    assert fresh == committed.read_text(encoding="utf-8"), (
        "docs/deps-graph.jsonl is stale — run scripts/deps-graph.py --build")


# ── the unknown must be loud ─────────────────────────────────────────────
def test_unclassified_is_computed_from_content_extractors_only(built):
    edges, reports, corpus = built
    unknown = dg.unclassified(reports, corpus)
    assert set(unknown) <= set(corpus.scope)
    # The ledger extractors must NOT be allowed to mark files classified;
    # x_watches nominally 'examines' the whole scope, and counting it would
    # make the unknown set vacuously empty — the exact silent-zero failure
    # this repo keeps hitting.
    ledger = [r for r in reports if not r.classifies]
    assert ledger, "no ledger extractor is marked classifies=False"
    assert any(len(r.examined) > 0 for r in ledger)
    assert unknown, (
        "no in-scope file is unclassified — either every file type is now "
        "parsed (good news, delete this assertion) or the metric went blind")


def test_scope_boundary_is_explicit_and_counts_the_outside(built):
    _, _, corpus = built
    assert dg.in_scope("scripts/pre-push-checks.sh")
    assert dg.in_scope("docs/adr/truth/047-gate-adoption-metrics.md")
    assert dg.in_scope("AGENTS.md")
    assert not dg.in_scope("kuchnie-core/src/kuchnie_core/model.py")
    assert not dg.in_scope("docs/specs/process-coverage.png")
    assert len(corpus.outside) > 100, (
        "the outside-scope count is suspiciously small — the boundary must "
        "COUNT what it excludes, not hide it")


# ── queries ──────────────────────────────────────────────────────────────
def test_walk_depth_and_direction(built):
    edges, _, _ = built
    root = ".beads/hooks/pre-push"
    d1 = dg.walk(edges, root, 1, reverse=False)
    d3 = dg.walk(edges, root, 3, reverse=False)
    assert {e.dst for e in d1} == {"scripts/pre-push-checks.sh"}
    assert len(d3) > len(d1)
    assert any(e.dst.startswith("scripts/session-gates.d/") for e in d3), (
        "depth 3 from the pre-push hook must reach the session gates")
    back = dg.walk(edges, "scripts/exercise-gate.sh", 1, reverse=True)
    assert "scripts/pre-push-checks.sh" in {e.src for e in back}


def test_orphans_are_in_scope_and_unpointed(built):
    edges, _, corpus = built
    orph = dg.orphans(edges, corpus)
    pointed = {e.dst for e in edges}
    assert orph, "orphan query returned nothing — it examined nothing"
    for o in orph:
        assert dg.in_scope(o)
        assert o not in pointed
    assert "scripts/pre-push-checks.sh" not in orph


def test_mermaid_renders_a_subgraph_and_refuses_the_whole_graph(built):
    edges, _, _ = built
    sub = dg.walk(edges, "scripts/pre-push-checks.sh", 1, reverse=False)
    out = dg.render_mermaid(sub)
    assert out.startswith("graph LR")
    assert "scripts/session-gates.d/40-test-health.sh" in out
    assert dg.render_mermaid(edges).startswith("%% refusing"), (
        "a whole-graph poster is not a map — rendering must refuse it")


# ── do not build a second matcher: reconcile with the repo's own verb ────
def test_cites_is_a_superset_of_truth_citations(built):
    """`truth citations` already answers doc->ledger-id over its own scope.

    This extractor is deliberately wider (every in-scope .md, plus file:line),
    but where the two overlap the wider one must CONTAIN the narrower one. A
    miss here means the two matchers have drifted — the ADR-005 failure mode.
    """
    edges, _, _ = built
    mine = {(e.src, e.dst) for e in edges
            if e.kind == "cites" and e.via == "ledger"}
    # `truth citations` sweeps its own default scope (docs/specs/**), so the
    # sample has to be drawn from THAT overlap — asking it about ids cited only
    # in scripts/ would produce an empty answer that proves nothing.
    ids = sorted({d for s, d in mine
                  if s.startswith("docs/specs/") and d.startswith("tr-")})[:60]
    assert ids, "no tr- citation under docs/specs — the control is dark"
    run = subprocess.run([str(ROOT / "scripts" / "truth"), "citations",
                          "--json", *ids],
                         cwd=ROOT, capture_output=True, text=True, timeout=300)
    assert run.returncode in (0, 6), run.stderr[-400:]
    theirs = json.loads(run.stdout or "{}")
    hits = [(f, cid) for cid, files in theirs.items() for f in files]
    assert hits, ("truth citations reported nothing for 60 ids — the "
                  "reconciliation control is dark, not clean")
    missing = [(f, cid) for f, cid in hits
               if dg.in_scope(f) and (f, cid) not in mine]
    assert not missing, (
        f"truth citations sees {len(missing)} in-scope citation(s) this "
        f"extractor does not, e.g. {missing[:5]} — the matchers have drifted")


# ── the declared blind spot, pinned exactly as the gates are ─────────────
def test_tool_declares_its_blind_spot():
    text = TOOL.read_text(encoding="utf-8")
    assert "# BLIND-SPOT:" in text, (
        "deps-graph.py states no blind spot. Every sensor is a fitness "
        "function with an unsound edge; declaring it is the price of being "
        "trusted (doctrine L2).")


def test_declared_blind_spot_still_holds():
    text = TOOL.read_text(encoding="utf-8")
    probe = next((ROOT / ln.split(":", 1)[1].strip()
                  for ln in text.splitlines()
                  if ln.startswith("# BLIND-SPOT-PROBE:")), None)
    assert probe is not None and probe.exists(), f"probe missing: {probe}"
    run = subprocess.run(["bash", str(probe)], cwd=ROOT,
                         capture_output=True, text=True, timeout=300)
    assert run.returncode == 0, (
        "the blind spot deps-graph.py declares is no longer real, so the "
        "declaration is now a lie. Rewrite the BLIND-SPOT line (good news: "
        f"a sensor got stronger).\n{run.stdout}\n{run.stderr}")


# ── lexer units: the parts that decide whether a comment is an edge ──────
@pytest.mark.parametrize("line,want", [
    ("bash scripts/x.sh", "bash scripts/x.sh"),
    ("  # bash scripts/x.sh", "  "),
    ("bash a.sh  # then scripts/x.sh", "bash a.sh  "),
    ('say "count: $# args"', 'say "count: $# args"'),
    ('grep -c "#" f', 'grep -c "#" f'),
    ("echo '# not a comment'", "echo '# not a comment'"),
])
def test_strip_hash_comment(line, want):
    assert dg.strip_hash_comment(line) == want


def test_shell_heredoc_body_is_flagged():
    src = "bash a.sh\npython3 - <<'PY'\nbash b.sh\nPY\nbash c.sh\n"
    got = {ln.no: ln.heredoc for ln in dg.shell_lines(src)}
    assert got == {1: False, 2: False, 3: True, 4: True, 5: False}


def test_yaml_separates_run_steps_from_path_filters():
    src = ("on:\n  push:\n    paths:\n      - scripts/truth\njobs:\n"
           "  a:\n    steps:\n      - run: |\n          bash scripts/x.sh\n")
    lines = {ln.no: (ln.run, ln.paths_filter) for ln in dg.yaml_lines(src)}
    assert lines[4] == (False, True), "a paths: entry is not a command"
    assert lines[9] == (True, False), "a run: body is a command"


def test_path_tokens_require_membership_not_a_guess():
    tracked = frozenset({"scripts/truth", "AGENTS.md"})
    assert dg.path_tokens("see AGENTS.md.", tracked) == ["AGENTS.md"]
    assert dg.path_tokens("`scripts/truth` queue", tracked) == ["scripts/truth"]
    assert dg.path_tokens("scripts/session-gates.d/*.sh", tracked) == []
    assert dg.path_tokens("kuchnie-core is a word", tracked) == []
