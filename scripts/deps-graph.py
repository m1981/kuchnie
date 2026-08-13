#!/usr/bin/env python3
"""deps-graph — the governance machinery as a graph, emitted as DATA.

WHY THIS EXISTS. This repo carries interlocking machinery — shell gates, a
Python ledger package, git hooks, CI workflows, ADRs, specs, baselines, a
question bank, an issue tracker — and the questions people actually ask about
it ("what invokes this?", "what prose goes false if I delete this file?",
"which checks does no scheduled root reach?") were answered by hand-grepping,
one grep per question, no record. A hand-grep is not evidence and does not
survive the session that produced it.

THE OUTPUT IS A DIFFABLE ARTIFACT, NOT A PICTURE. `docs/deps-graph.jsonl` is
one JSON object per edge, sorted deterministically: two consecutive runs
produce byte-identical files, so the graph goes into git and CHANGES to it are
reviewable. Mermaid rendering is a consumer of that file and is only ever
offered for a SUBGRAPH a query selected — a 4,000-edge poster is useless.

EVERY EDGE CARRIES PROVENANCE. src, dst, kind, the file:line the edge was found
on, and the extractor that produced it. An edge nobody can trace back to a line
is not evidence, it is a claim.

ONE EXTRACTOR PER EDGE KIND, and each reports what it EXAMINED. An extractor
that examined zero files is a FAILURE here, never a silent zero — that exact
rule has caught three real bugs in this repo in two days (a suite reported
"clean" while running 0 tests; a grep reported a gate dark because its count
regex needed a leading character; a `grep -c` matched claim text instead of the
status column). Same reasoning: an extractor that found zero EDGES is also a
failure, because every kind below is populated in this repo today, so zero can
only mean the extractor broke.

DO NOT BUILD A SECOND MATCHER (ADR-005). Where the repo already computes
something, this consumes its output rather than re-deriving it:
  * path -> claim              `scripts/truth impact --json -- <paths>`
  * issue -> premise claim     `scripts/truth issues --json` + the ledger's own
                               kind=premise records
Bead ids are deliberately NOT validated against `bd`: `cites` records the id
as the doc wrote it, so a citation of a bead that never existed stays visible
rather than being silently dropped by a lookup.
Re-implementing their matching is how two copies drift apart, and this repo has
a live example: the two directions of `truth impact` already disagree about
what "watched" means (see scripts/tests/probes/impact-check-blind.sh).

SCOPE IS THE MACHINERY, NOT THE KITCHEN DOMAIN. See `in_scope()` — it is one
function, deliberately, so widening it is a one-line change. Everything outside
is COUNTED, not silently dropped.

Usage:
  scripts/deps-graph.py --build              rebuild docs/deps-graph.jsonl
  scripts/deps-graph.py --stats              extractor report + unknown files
  scripts/deps-graph.py --of <artifact> [--depth N]
  scripts/deps-graph.py --to <artifact> [--depth N]
  scripts/deps-graph.py --kind <edge-kind>
  scripts/deps-graph.py --orphans
  scripts/deps-graph.py --of X --render mermaid
  scripts/deps-graph.py --of X --json

Exit codes: 0 ok / 1 query found nothing / 2 an extractor went dark.

# BLIND-SPOT: every edge here is a STATIC, LITERAL edge, so the graph is a
#   lower bound on coupling and silence never means "not coupled".
#   Specifically it cannot see: (a) a command whose target is a shell variable
#   or built from a string — `run_gate` in pre-push-checks.sh dispatches through
#   `bash "$path"`, and this file only sees the literal path tokens at its CALL
#   sites, so a gate invoked through a computed name is invisible; (b) a
#   directory glob — `for g in scripts/session-gates.d/*.sh` yields no edge at
#   all, which is precisely why that hook needs its own hand-written reconcile
#   loop; (c) prose that describes a file without naming its path ("the
#   dashboard script", "the flagship exercise"), which is the dominant form of
#   coupling in a review document; (d) anything untracked by git, since the
#   corpus is `git ls-files`; (e) `watches` edges of a claim that is already
#   stale or retracted, because `truth impact` reports only claims a change
#   could still ENDANGER, so a dead claim's dependencies vanish from the graph
#   rather than showing as dead; (f) runtime coupling of every kind — a script
#   reading a path assembled at run time, a Python import behind a registry or
#   entry-point table, an HTTP call.
# BLIND-SPOT-PROBE: scripts/tests/probes/deps-graph-blind.sh
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# DEPS_GRAPH_PATH exists so a test or a probe can build into a scratch file
# instead of asserting against a possibly-stale committed graph.
GRAPH_PATH = Path(os.environ.get("DEPS_GRAPH_PATH")
                  or ROOT / "docs" / "deps-graph.jsonl")

# ── scope ────────────────────────────────────────────────────────────────
# THE BOUNDARY, in one function so widening it is a one-line change. The
# domain components (kuchnie-core/, catalog/, kitchen-*/, krono-*/,
# home-builder-adapter/, exercises/) have their own tooling and are OUT; they
# are counted, never silently dropped (see `--stats`, "outside scope").
SCOPE_PREFIXES = (
    "scripts/",
    "truthlib/",
    ".beads/hooks/",
    ".githooks/",
    ".husky/",
    ".github/workflows/",
    ".truth/",
)
SCOPE_EXACT = frozenset({"AGENTS.md", "CLAUDE.md", "STATUS.md",
                         "README.md", "CHANGELOG.md"})


def in_scope(rel: str) -> bool:
    """True iff `rel` is governance machinery. Widen HERE, nowhere else."""
    if rel in SCOPE_EXACT:
        return True
    if rel.startswith("docs/") and rel.endswith(".md"):
        return True
    return rel.startswith(SCOPE_PREFIXES)


# ── the edge ─────────────────────────────────────────────────────────────
@dataclass(frozen=True, order=True)
class Edge:
    kind: str
    src: str
    dst: str
    file: str
    line: int
    extractor: str
    via: str = ""

    def as_dict(self) -> dict:
        return {"kind": self.kind, "src": self.src, "dst": self.dst,
                "file": self.file, "line": self.line,
                "extractor": self.extractor, "via": self.via}


@dataclass
class Report:
    """What an extractor examined. A zero here is a FAILURE, not a pass.

    `examined` is the SET, not a count, because the honest "unknown" number is
    scope minus the union of what the content extractors could read — and a
    count cannot be unioned. `classifies` marks the extractors that read repo
    FILES; the two ledger extractors read the ledger and classify nothing, so
    counting their corpus would make the unknown set vacuously empty.
    """
    name: str
    examined: set[str] = field(default_factory=set)
    edges_found: int = 0
    classifies: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def files_examined(self) -> int:
        return len(self.examined)

    def saw(self, rel: str) -> None:
        self.examined.add(rel)


# ── lexing helpers ───────────────────────────────────────────────────────
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
_TOKEN = re.compile(r"[A-Za-z0-9_.][A-Za-z0-9_./+-]*")
_TRIM = ".,:;)/-"


def strip_hash_comment(line: str) -> str:
    """Drop a `#` comment, quote-aware. `$#` and `${#v}` are not comments."""
    out: list[str] = []
    quote: str | None = None
    esc = False
    for ch in line:
        if esc:
            out.append(ch)
            esc = False
            continue
        if ch == "\\" and quote != "'":
            out.append(ch)
            esc = True
            continue
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "'\"":
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (not out or out[-1] in " \t"):
            break
        out.append(ch)
    return "".join(out)


@dataclass
class Line:
    no: int
    text: str
    heredoc: bool = False   # inside a shell heredoc body (another language)
    run: bool = False       # inside a YAML `run:` block (a real command)
    paths_filter: bool = False   # inside a YAML `paths:` list


def shell_lines(text: str) -> list[Line]:
    """Comment-stripped shell lines, flagged for heredoc bodies."""
    out: list[Line] = []
    delim: str | None = None
    for no, raw in enumerate(text.splitlines(), 1):
        if delim is not None:
            if raw.strip() == delim:
                delim = None
                out.append(Line(no, "", heredoc=True))
                continue
            out.append(Line(no, strip_hash_comment(raw), heredoc=True))
            continue
        code = strip_hash_comment(raw)
        out.append(Line(no, code))
        m = _HEREDOC.search(code)
        if m:
            delim = m.group(2)
    return out


def python_lines(text: str) -> list[Line]:
    """Comment-stripped Python, with DOCSTRINGS blanked.

    A module docstring is prose, exactly like a `#` comment, and reading it as
    code manufactures edges that are simply false: scripts/truth's docstring
    names scripts/truth-canary.sh as the suite that acceptance-tests it, which
    an earlier version of this file reported as `scripts/truth INVOKES
    scripts/truth-canary.sh` — the arrow pointing the wrong way round.
    Only `Expr(Constant(str))` statements are blanked; a path passed to
    subprocess is an ordinary string expression and survives.
    """
    lines = [Line(no, strip_hash_comment(raw))
             for no, raw in enumerate(text.splitlines(), 1)]
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return lines
    for node in ast.walk(tree):
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            for no in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                if 1 <= no <= len(lines):
                    lines[no - 1] = Line(no, "")
    return lines


def yaml_lines(text: str) -> list[Line]:
    """YAML lines flagged by block: a `run:` script vs a `paths:` filter.

    A workflow's `paths:` list is a TRIGGER CONDITION, not a command — reading
    it as an invocation would have manufactured three false `triggers` edges
    from truth-gate.yml (to scripts/truth and scripts/check-truth.sh, neither
    of which it runs).
    """
    out: list[Line] = []
    run_indent: int | None = None
    paths_indent: int | None = None
    for no, raw in enumerate(text.splitlines(), 1):
        stripped = raw.lstrip()
        indent = len(raw) - len(stripped)
        if stripped and not stripped.startswith("#"):
            if run_indent is not None and indent <= run_indent:
                run_indent = None
            if paths_indent is not None and indent <= paths_indent:
                paths_indent = None
            if re.match(r"-?\s*run:\s*", stripped):
                run_indent = indent
            elif re.match(r"paths(-ignore)?:\s*$", stripped):
                paths_indent = indent
        code = raw if run_indent is not None else strip_hash_comment(raw)
        out.append(Line(no, code,
                        run=run_indent is not None,
                        paths_filter=paths_indent is not None))
    return out


def path_tokens(text: str, tracked: frozenset[str]) -> list[str]:
    """Tokens on a line that name a tracked repo file. Membership, not guess."""
    hits: list[str] = []
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        if tok.startswith("./"):
            tok = tok[2:]
        for cand in (tok, tok.rstrip(_TRIM)):
            if cand in tracked:
                hits.append(cand)
                break
    return hits


# ── corpus ───────────────────────────────────────────────────────────────
class Corpus:
    """Every extractor gets this and nothing else."""

    def __init__(self, root: Path):
        self.root = root
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root,
                             capture_output=True, text=True, check=True)
        self.tracked = frozenset(p for p in out.stdout.split("\0") if p)
        self.scope = sorted(p for p in self.tracked if in_scope(p))
        self.outside = sorted(p for p in self.tracked if not in_scope(p))
        self._text: dict[str, str] = {}
        self._roles: dict[str, set[str]] = {}
        self._classify()

    def text(self, rel: str) -> str:
        if rel not in self._text:
            try:
                self._text[rel] = (self.root / rel).read_text(
                    encoding="utf-8", errors="replace")
            except (OSError, IsADirectoryError):
                self._text[rel] = ""
        return self._text[rel]

    def _classify(self) -> None:
        for rel in self.scope:
            roles: set[str] = set()
            head = self.text(rel)[:200].splitlines()
            shebang = head[0] if head and head[0].startswith("#!") else ""
            if rel.endswith(".sh") or "sh" in shebang.split("/")[-1:]:
                pass
            if rel.endswith(".sh") or re.search(r"\b(ba)?sh\b", shebang):
                roles.add("shell")
            if rel.endswith(".py") or "python" in shebang:
                roles.add("python")
            if rel.endswith((".yml", ".yaml")) and rel.startswith(
                    ".github/workflows/"):
                roles.add("workflow")
            if rel.startswith((".beads/hooks/", ".githooks/", ".husky/")):
                if "/_/" not in rel and not rel.endswith(".md"):
                    roles.add("hook")
            if rel.endswith(".md"):
                roles.add("doc")
            if not roles:
                roles.add("data")
            self._roles[rel] = roles

    def role(self, rel: str, name: str) -> bool:
        return name in self._roles.get(rel, ())

    def with_role(self, *names: str) -> list[str]:
        return [r for r in self.scope
                if self._roles.get(r, set()) & set(names)]

    def is_runnable(self, rel: str) -> bool:
        """Something you can invoke: a script, not a data file."""
        return bool(self._roles.get(rel, set()) & {"shell", "python"})

    # -- ledger access, always through the repo's own verbs ---------------
    def truth(self, *args: str) -> tuple[int, str]:
        p = subprocess.run([str(self.root / "scripts" / "truth"), *args],
                           cwd=self.root, capture_output=True, text=True,
                           timeout=300)
        return p.returncode, p.stdout

    def ledger_lines(self) -> dict[str, int]:
        """id -> first line in .truth/claims.jsonl. Provenance, not matching."""
        if not hasattr(self, "_ledger"):
            self._ledger: dict[str, int] = {}
            self._ledger_records: list[tuple[int, dict]] = []
            path = self.root / ".truth" / "claims.jsonl"
            if path.exists():
                for no, raw in enumerate(
                        path.read_text(encoding="utf-8").splitlines(), 1):
                    if not raw.strip():
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    self._ledger_records.append((no, rec))
                    self._ledger.setdefault(rec.get("id", ""), no)
        return self._ledger

    def ledger_records(self) -> list[tuple[int, dict]]:
        self.ledger_lines()
        return self._ledger_records


LEDGER_REL = ".truth/claims.jsonl"

# ── extractors ───────────────────────────────────────────────────────────
# One per edge kind. Adding an artifact type means adding one of these, never
# editing a monolith. Each returns (edges, report); a report with a zero in it
# aborts the build.

EXTRACTORS: list = []


def extractor(fn):
    EXTRACTORS.append(fn)
    return fn


@extractor
def x_invokes(c: Corpus) -> tuple[list[Edge], Report]:
    """A script runs another script.

    Literal path tokens on comment-stripped, heredoc-free code lines. Heredoc
    bodies are excluded because they are another language embedded in the
    shell, and the paths in them are things that language READS.
    """
    rep = Report("invokes")
    edges: list[Edge] = []
    corpus = [r for r in c.with_role("shell", "python")
              if not c.role(r, "hook")]
    for rel in corpus:
        rep.saw(rel)
        lines = (shell_lines(c.text(rel)) if c.role(rel, "shell")
                 else python_lines(c.text(rel)))
        for ln in lines:
            if ln.heredoc:
                continue
            for tok in path_tokens(ln.text, c.tracked):
                if tok == rel or not c.is_runnable(tok):
                    continue
                edges.append(Edge("invokes", rel, tok, rel, ln.no,
                                  "x_invokes"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_triggers(c: Corpus) -> tuple[list[Edge], Report]:
    """A git hook or CI workflow invokes a root.

    Same literal-token rule as `invokes`, but the SOURCE is a scheduled root:
    a hook under .beads/hooks / .githooks / .husky, or a `run:` step in a
    workflow. YAML `paths:` filters are deliberately not read here (see
    `x_filters`).
    """
    rep = Report("triggers")
    edges: list[Edge] = []
    for rel in c.with_role("hook", "workflow"):
        rep.saw(rel)
        if c.role(rel, "workflow"):
            lines = [ln for ln in yaml_lines(c.text(rel)) if ln.run]
        else:
            lines = [ln for ln in shell_lines(c.text(rel)) if not ln.heredoc]
        for ln in lines:
            for tok in path_tokens(ln.text, c.tracked):
                if tok == rel or not c.is_runnable(tok):
                    continue
                edges.append(Edge("triggers", rel, tok, rel, ln.no,
                                  "x_triggers"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_filters(c: Corpus) -> tuple[list[Edge], Report]:
    """A CI workflow only fires when these paths change.

    NOT in the original edge-kind list; the data forced it. truth-gate.yml
    names scripts/truth and scripts/check-truth.sh under `on: ... paths:`. It
    does not RUN them — it wakes up when they change. Folding that into
    `triggers` would have been three edges that say the opposite of the truth.
    """
    rep = Report("filters")
    edges: list[Edge] = []
    for rel in c.with_role("workflow"):
        rep.saw(rel)
        for ln in yaml_lines(c.text(rel)):
            if not ln.paths_filter:
                continue
            for tok in path_tokens(ln.text, c.tracked):
                if tok != rel:
                    edges.append(Edge("filters", rel, tok, rel, ln.no,
                                      "x_filters"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_reads(c: Corpus) -> tuple[list[Edge], Report]:
    """A script reads a data file: a baseline, an allowlist, a golden, a
    manifest.

    Complement of `invokes` over the same token stream: a literal tracked path
    that is NOT runnable is data being consumed. Heredoc bodies COUNT here —
    `64-reachability.sh` names docs/not-yet-wired.txt only inside its embedded
    Python.
    """
    rep = Report("reads")
    edges: list[Edge] = []
    for rel in c.with_role("shell", "python", "hook", "workflow"):
        rep.saw(rel)
        if c.role(rel, "workflow"):
            lines = [ln for ln in yaml_lines(c.text(rel))
                     if not ln.paths_filter]
        elif c.role(rel, "shell") or c.role(rel, "hook"):
            lines = shell_lines(c.text(rel))
        else:
            lines = python_lines(c.text(rel))
        for ln in lines:
            for tok in path_tokens(ln.text, c.tracked):
                if tok == rel or c.is_runnable(tok):
                    continue
                edges.append(Edge("reads", rel, tok, rel, ln.no, "x_reads"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_imports(c: Corpus) -> tuple[list[Edge], Report]:
    """A Python module imports another first-party module.

    First-party = the in-scope Python corpus itself, indexed by the dotted name
    the rest of the repo imports it by (`truthlib.cli`) and by bare basename
    (scripts/*.py are run, not packaged). Third-party and stdlib names simply
    do not resolve and are dropped.
    """
    rep = Report("imports")
    edges: list[Edge] = []
    pys = c.with_role("python")
    index: dict[str, str] = {}
    for rel in pys:
        dotted = rel[:-3].replace("/", ".") if rel.endswith(".py") else rel
        if dotted.endswith(".__init__"):
            dotted = dotted[: -len(".__init__")]
        index.setdefault(dotted, rel)
        index.setdefault(dotted.rsplit(".", 1)[-1], rel)
    for rel in pys:
        rep.saw(rel)
        try:
            tree = ast.parse(c.text(rel))
        except SyntaxError:
            rep.notes.append(f"unparsed: {rel}")
            continue
        pkg = rel.rsplit("/", 1)[0].replace("/", ".") if "/" in rel else ""
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    up = pkg.split(".") if pkg else []
                    if node.level > 1:
                        up = up[: len(up) - (node.level - 1)]
                    base = ".".join(up + ([node.module] if node.module else []))
                if not base:
                    continue
                names = [base] + [f"{base}.{a.name}" for a in node.names]
            for name in names:
                parts = name.split(".")
                for i in range(len(parts), 0, -1):
                    tgt = index.get(".".join(parts[:i]))
                    if tgt and tgt != rel:
                        edges.append(Edge("imports", rel, tgt, rel,
                                          node.lineno, "x_imports", name))
                        break
    rep.edges_found = len(edges)
    return edges, rep


_LEDGER_ID = re.compile(r"\b(tr|wk)-[0-9a-f]{8}\b")
_BEAD_ID = re.compile(r"\bkuchnie-[0-9a-z]{2,}(?:\.[0-9]+)*\b")
_ADR_ID = re.compile(r"\bADR-([0-9]{3})\b")
_QB_ID = re.compile(r"\bQB-([0-9]{3})\b")


@extractor
def x_cites(c: Corpus) -> tuple[list[Edge], Report]:
    """An artifact names a ledger id, a bead id, an ADR number or a QB number.

    Docs AND code. The brief said "a doc", and the data said otherwise: the
    most consequential citations in this repo are in gate headers, not prose —
    pre-push-checks.sh justifies its advisory posture with ADR-014 and ADR-047,
    64-reachability.sh keys its allowlist on bead ids. Restricting this to .md
    would have answered "which artifacts cite a retracted claim?" while leaving
    out the artifacts that ACT on the citation.

    A bead-shaped token that is also a tracked directory prefix (`kuchnie-core`)
    is a PATH, not a bead, and is dropped here — it belongs to `references`.
    Comments are NOT stripped: a citation in a comment is still a citation, and
    that is where a gate records the decision it obeys.
    """
    rep = Report("cites")
    edges: list[Edge] = []
    dirs = {p.split("/", 1)[0] for p in c.tracked if "/" in p}
    for rel in c.with_role("doc", "shell", "python", "workflow", "hook"):
        rep.saw(rel)
        for no, raw in enumerate(c.text(rel).splitlines(), 1):
            for m in _LEDGER_ID.finditer(raw):
                edges.append(Edge("cites", rel, m.group(0), rel, no,
                                  "x_cites", "ledger"))
            for m in _BEAD_ID.finditer(raw):
                if m.group(0) in dirs:
                    continue
                edges.append(Edge("cites", rel, m.group(0), rel, no,
                                  "x_cites", "bead"))
            for m in _ADR_ID.finditer(raw):
                edges.append(Edge("cites", rel, f"ADR-{m.group(1)}", rel, no,
                                  "x_cites", "adr"))
            for m in _QB_ID.finditer(raw):
                edges.append(Edge("cites", rel, f"QB-{m.group(1)}", rel, no,
                                  "x_cites", "qb"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_references(c: Corpus) -> tuple[list[Edge], Report]:
    """A doc names a repo file path.

    This is the edge that answers "what prose goes false if I delete this
    file?" — `--to <path> --kind references`.
    """
    rep = Report("references")
    edges: list[Edge] = []
    for rel in c.with_role("doc"):
        rep.saw(rel)
        for no, raw in enumerate(c.text(rel).splitlines(), 1):
            for tok in path_tokens(raw, c.tracked):
                if tok != rel:
                    edges.append(Edge("references", rel, tok, rel, no,
                                      "x_references"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_defines(c: Corpus) -> tuple[list[Edge], Report]:
    """Which file DEFINES a cited symbolic id (ADR-NNN, QB-NNN).

    NOT in the original list; added because `cites` alone cannot tell a live
    citation from a dangling one, and because this repo runs TWO ADR
    numberings — docs/adr/NNN and docs/adr/truth/NNN — so an "ADR-014" in prose
    can resolve to two different decisions. Emitting the definition as an edge
    makes both the dangle and the ambiguity queryable (`--to ADR-014`).
    """
    rep = Report("defines")
    edges: list[Edge] = []
    for rel in c.with_role("doc"):
        rep.saw(rel)
        m = re.match(r"docs/adr/(?:truth/)?([0-9]{3})-", rel)
        if m:
            edges.append(Edge("defines", rel, f"ADR-{m.group(1)}", rel, 1,
                              "x_defines", "adr file"))
        if rel == "docs/question-bank.md":
            for no, raw in enumerate(c.text(rel).splitlines(), 1):
                qm = re.match(r"#+\s*QB-([0-9]{3})\b", raw)
                if qm:
                    edges.append(Edge("defines", rel, f"QB-{qm.group(1)}",
                                      rel, no, "x_defines", "qb section"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_premise(c: Corpus) -> tuple[list[Edge], Report]:
    """A ledger/tracker issue stands on a ledger claim.

    Consumes `scripts/truth issues --json` for the native work kernel (it has
    already applied ADR-013 premise-supersede), and the ledger's own
    kind=premise records for issues the kernel does not own — the Beads twins.
    Nothing here re-derives premise validity.
    """
    rep = Report("premise", classifies=False)
    edges: list[Edge] = []
    lines = c.ledger_lines()
    rc, out = c.truth("issues", "--json")
    if rc != 0:
        raise SystemExit(f"deps-graph: 'truth issues --json' exited {rc}; "
                         "the premise extractor examined nothing")
    issues = json.loads(out or "[]")
    seen: set[tuple[str, str]] = set()
    for iss in issues:
        src = iss["id"]
        rep.saw(src)          # the "corpus" here is issue records, not files
        for pid in iss.get("premises") or []:
            if (src, pid) in seen:
                continue
            seen.add((src, pid))
            edges.append(Edge("premise", src, pid, LEDGER_REL,
                              lines.get(src, 0), "x_premise", "work kernel"))
        for dep in iss.get("deps") or []:
            edges.append(Edge("depends", src, dep, LEDGER_REL,
                              lines.get(src, 0), "x_premise", "issue dep"))
    for no, rec in c.ledger_records():
        if rec.get("kind") != "premise":
            continue
        pay = rec.get("payload") or {}
        src, dst = pay.get("issue"), pay.get("claim")
        if not src or not dst or (src, dst) in seen:
            continue
        seen.add((src, dst))
        edges.append(Edge("premise", src, dst, LEDGER_REL, no, "x_premise",
                          "premise record"))
    rep.edges_found = len(edges)
    return edges, rep


@extractor
def x_watches(c: Corpus) -> tuple[list[Edge], Report]:
    """A ledger claim watches paths (evidence_paths).

    Consumes `scripts/truth impact --json -- <in-scope paths>` — the repo's own
    path/glob matcher, ADR-005. This file does NOT expand a single glob itself.
    Consequence, declared: `truth impact` answers "what could this change still
    endanger?", so a claim that is already stale or retracted contributes no
    edges. The graph shows live coupling, not historical coupling.

    EPHEMERAL (ADR-052). Because the edge set keys on claim STATUS, it turns
    over at the rate of the invalidation scan, not the rate of commits:
    measured on this repo over 36 days, 46.1 status transitions per day of
    path-carrying claims against 13.9 commits, a ratio of 3.3 to 1. These 73
    edges are 1.3% of the graph and caused most of its rebuilds. They are
    therefore NOT written to the committed artifact; the query path recomputes
    them live, which costs one fold (~43ms, well under the FS-3 gate). Nothing
    queried them from the file: `truth impact` -- the one verb asking exactly
    this question -- folds the ledger directly and never reads this graph.
    """
    rep = Report("watches", classifies=False)
    edges: list[Edge] = []
    lines = c.ledger_lines()
    rc, out = c.truth("impact", "--json", "--", *c.scope)
    if rc not in (0, 3):
        raise SystemExit(f"deps-graph: 'truth impact --json' exited {rc}; "
                         "the watches extractor examined nothing")
    rows = json.loads(out or "[]")
    rep.examined = set(c.scope)
    for row in rows:
        cid = row["claim"]
        for p in row.get("watched") or []:
            edges.append(Edge("watches", cid, p, LEDGER_REL,
                              lines.get(cid, 0), "x_watches",
                              row.get("status", "")))
    rep.edges_found = len(edges)
    return edges, rep


# ADR-052: extractors whose edge set keys on LEDGER STATUS rather than on
# repository content. They turn over with the invalidation scan, so freezing
# them in a committed artifact makes the whole file inherit the churn of its
# fastest-moving component -- and the committed copy then lies for most of
# the day. Excluded from `--build`, recomputed on every query.
EPHEMERAL_EXTRACTORS = (x_watches,)


# ── build ────────────────────────────────────────────────────────────────
def build(root: Path, verbose: bool = True,
          skip_ephemeral: bool = False) -> tuple[list[Edge], list[Report],
                                                 Corpus]:
    c = Corpus(root)
    edges: list[Edge] = []
    reports: list[Report] = []
    for fn in EXTRACTORS:
        if skip_ephemeral and fn in EPHEMERAL_EXTRACTORS:
            continue
        e, rep = fn(c)
        edges.extend(e)
        reports.append(rep)
    edges = sorted(set(edges))
    return edges, reports, c


def unclassified(reports: list[Report], c: Corpus) -> list[str]:
    """In-scope files that NO content extractor could read.

    Not "produced no edges" — a gate that invokes nothing is a legitimate leaf.
    This is the set nothing knows how to parse, which is the number that has to
    stay visible: future-proofing is not anticipating every file type, it is
    making the unread ones loud.
    """
    seen: set[str] = set()
    for rep in reports:
        if rep.classifies:
            seen |= rep.examined
    return sorted(set(c.scope) - seen)


def write_graph(edges: list[Edge], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for e in edges:
            fh.write(json.dumps(e.as_dict(), sort_keys=True,
                                ensure_ascii=False) + "\n")


def load_graph(path: Path) -> list[Edge]:
    if not path.exists():
        raise SystemExit(f"deps-graph: {path} does not exist — run --build")
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            d = json.loads(raw)
            out.append(Edge(d["kind"], d["src"], d["dst"], d["file"],
                            d["line"], d["extractor"], d.get("via", "")))
    return out


# ── reporting ────────────────────────────────────────────────────────────
def print_stats(edges: list[Edge], reports: list[Report], c: Corpus) -> int:
    dark = 0
    print("deps-graph: extractor report (an extractor that examined nothing "
          "is a FAILURE)")
    for rep in sorted(reports, key=lambda r: r.name):
        flag = ""
        if rep.files_examined == 0:
            flag, dark = "  <-- DARK: examined 0 files", dark + 1
        elif rep.edges_found == 0:
            flag, dark = "  <-- DARK: found 0 edges", dark + 1
        print(f"  {rep.name:<12} examined {rep.files_examined:>5} "
              f"file(s), {rep.edges_found:>6} edge(s){flag}")
        for n in rep.notes:
            print(f"      note: {n}")

    by_kind: dict[str, int] = defaultdict(int)
    for e in edges:
        by_kind[e.kind] += 1
    print(f"\n  edges by kind ({len(edges)} total, deduplicated):")
    for k in sorted(by_kind):
        print(f"    {k:<12} {by_kind[k]:>6}")

    unknown = unclassified(reports, c)
    print(f"\n  corpus: {len(c.scope)} in-scope file(s), "
          f"{len(c.outside)} outside scope (domain components, not read here)")
    print(f"  UNCLASSIFIED: {len(unknown)} in-scope file(s) that no extractor "
          f"examined —")
    print("    future-proofing is not anticipating every file type, it is "
          "making these visible")
    for u in unknown[:40]:
        print(f"    {u}")
    if len(unknown) > 40:
        print(f"    ... and {len(unknown) - 40} more")
    if dark:
        print(f"\ndeps-graph: {dark} extractor(s) DARK — the graph is not "
              "trustworthy")
    return dark


# ── queries ──────────────────────────────────────────────────────────────
def walk(edges: list[Edge], start: str, depth: int,
         reverse: bool) -> list[Edge]:
    adj: dict[str, list[Edge]] = defaultdict(list)
    for e in edges:
        adj[e.dst if reverse else e.src].append(e)
    out: list[Edge] = []
    seen_nodes = {start}
    q = deque([(start, 0)])
    while q:
        node, d = q.popleft()
        if d >= depth:
            continue
        for e in adj.get(node, ()):
            out.append(e)
            nxt = e.src if reverse else e.dst
            if nxt not in seen_nodes:
                seen_nodes.add(nxt)
                q.append((nxt, d + 1))
    return sorted(set(out))


def orphans(edges: list[Edge], c: Corpus) -> list[str]:
    """Artifacts nothing points at: in scope, and the target of zero edges."""
    pointed = {e.dst for e in edges}
    return sorted(p for p in c.scope if p not in pointed)


def render_mermaid(edges: list[Edge]) -> str:
    if len(edges) > 300:
        return (f"%% refusing to render {len(edges)} edges — narrow the query "
                "with --depth or --kind; a whole-graph poster is not a map")
    ids: dict[str, str] = {}

    def nid(name: str) -> str:
        if name not in ids:
            ids[name] = f"n{len(ids)}"
        return ids[name]

    # Collapse to one arrow per (src, kind, dst): the JSONL keeps every call
    # site with its line, a picture must not repeat the same arrow ten times.
    lines = ["graph LR"]
    sites: dict[tuple[str, str, str], int] = defaultdict(int)
    for e in edges:
        sites[(e.src, e.kind, e.dst)] += 1
    for (src, kind, dst), n in sorted(sites.items()):
        label = kind if n == 1 else f"{kind} x{n}"
        lines.append(f'  {nid(src)}["{src}"] -->|{label}| {nid(dst)}["{dst}"]')
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="dependency graph of the governance machinery")
    ap.add_argument("--build", action="store_true",
                    help="rebuild the graph file")
    ap.add_argument("--stats", action="store_true",
                    help="extractor report + unclassified count")
    ap.add_argument("--of", metavar="ARTIFACT", help="outgoing edges")
    ap.add_argument("--to", metavar="ARTIFACT", help="incoming edges")
    ap.add_argument("--depth", type=int, default=1)
    ap.add_argument("--kind", action="append", default=[])
    ap.add_argument("--orphans", action="store_true")
    ap.add_argument("--render", choices=["mermaid"])
    ap.add_argument("--no-live", action="store_true",
                    help="ADR-052: do not recompute the ephemeral "
                         "(ledger-status) edges; answer from the committed "
                         "artifact alone -- for reproducing a query offline")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    need_build = args.build or args.stats or args.orphans
    if need_build:
        edges, reports, c = build(ROOT, skip_ephemeral=args.build)
        if args.build:
            write_graph(edges, GRAPH_PATH)
            print(f"deps-graph: wrote {GRAPH_PATH} "
                  f"({len(edges)} edges)")
        if args.stats or args.build:
            if print_stats(edges, reports, c):
                return 2
        if args.orphans:
            names = orphans(edges, c)
            if args.json:
                print(json.dumps(names, indent=2))
            else:
                print(f"deps-graph: {len(names)} in-scope artifact(s) that "
                      f"nothing points at (of {len(c.scope)} examined):")
                for n in names:
                    print(f"  {n}")
            return 0 if names else 1
        return 0

    edges = load_graph(GRAPH_PATH)
    # ADR-052: the committed artifact holds only content-derived edges. The
    # ephemeral ones key on ledger STATUS, so they are recomputed here, on
    # every query, from the live fold -- the file can no longer be stale
    # about them because it no longer claims to know them.
    if not args.no_live:
        c = Corpus(ROOT)
        for fn in EPHEMERAL_EXTRACTORS:
            try:
                live, _rep = fn(c)
                edges.extend(live)
            except SystemExit as e:
                # The extractor fails LOUD when it examined nothing (F1):
                # surface that on stderr and answer from the file rather
                # than silently returning a graph missing a whole kind.
                print(f"deps-graph: live edges unavailable -- {e}",
                      file=sys.stderr)
    if args.kind:
        edges = [e for e in edges if e.kind in args.kind]
    if args.of:
        edges = walk(edges, args.of, args.depth, reverse=False)
    elif args.to:
        edges = walk(edges, args.to, args.depth, reverse=True)

    if args.render == "mermaid":
        print(render_mermaid(edges))
    elif args.json:
        print(json.dumps([e.as_dict() for e in edges], indent=2))
    else:
        for e in edges:
            via = f" [{e.via}]" if e.via else ""
            print(f"{e.kind:<11} {e.src}  ->  {e.dst}"
                  f"   ({e.file}:{e.line}, {e.extractor}){via}")
        print(f"-- {len(edges)} edge(s)")
    return 0 if edges else 1


if __name__ == "__main__":
    sys.exit(main())
