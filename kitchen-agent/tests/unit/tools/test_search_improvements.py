"""
tests/unit/tools/test_search_improvements.py
==============================================
Regression tests for search_knowledge_base improvements.

Problem observed (2026-06-11):
  Anthropic Claude used spaces instead of | for OR queries:
    "Blum szuflady Tandembox" → No matches (wrong!)
    "Blum|szuflady|Tandembox" → Found results (correct)

Root cause: Tool description was unclear about regex syntax.
Fixes:
  1. Improved tool description with WRONG vs RIGHT examples
  2. Auto-sanitization: convert spaces to | when query has no |
  3. Fallback hint in "No matches" response
"""
import os
import pytest
from pathlib import Path


@pytest.fixture
def tmp_kb(tmp_path: Path):
    """Creates a temporary knowledge base with Blum-related content."""
    (tmp_path / "blum_compendium.md").write_text(
        """# Szuflady Blum

## Tandembox Antaro
Klasyczny system szufladowy. Prowadnice widoczne.

## Merivobox
Złoty standard na 2026. Prowadnica ukryta.

## Legrabox
Premium. Szklane ścianki boczne.
""",
        encoding="utf-8",
    )
    (tmp_path / "standards.md").write_text(
        """# Standardy materiałowe

- Zawiasy: Blum Clip Top Blumotion
- Szuflady: Blum Merivobox lub Tandembox Antaro
- Podnośniki: Blum Aventos HF
""",
        encoding="utf-8",
    )
    (tmp_path / "playbook.md").write_text(
        """# Playbook

## Montaż
Fronty, szuflady, AGD — 12:30-15:00

## Okucia
Koszt okuć Blum komplet: 1500-2000 zł
""",
        encoding="utf-8",
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: Pipe-separated OR queries work correctly
# ---------------------------------------------------------------------------

def test_or_query_with_pipe(tmp_kb):
    """Pipe-separated OR queries should match across all terms."""
    from src.tools.file_ops import search_knowledge_base

    result = search_knowledge_base("Blum|szuflady|Tandembox", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    # Should find matches in multiple files
    assert "blum_compendium.md" in content
    assert "standards.md" in content


# ---------------------------------------------------------------------------
# Test 2: Space-separated queries get auto-converted to OR
# ---------------------------------------------------------------------------

def test_space_separated_autoconverted_to_or(tmp_kb):
    """When query has spaces but no |, auto-convert to OR for LLM convenience."""
    from src.tools.file_ops import search_knowledge_base

    # This is what Claude did wrong — spaces instead of |
    result = search_knowledge_base("Blum szuflady Tandembox", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    # Should find matches (auto-converted to Blum|szuflady|Tandembox)
    assert "No matches" not in content
    assert "blum_compendium.md" in content or "standards.md" in content


def test_space_separated_finds_all_terms(tmp_kb):
    """3+ word queries should be auto-converted to OR to find all terms."""
    from src.tools.file_ops import search_knowledge_base

    # 3+ words: auto-convert to OR
    result = search_knowledge_base("Merivobox Legrabox Tandembox", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    # All terms should be found (auto-converted to Merivobox|Legrabox|Tandembox)
    assert "Merivobox" in content or "merivobox" in content.lower()
    assert "Legrabox" in content or "legrabox" in content.lower()


def test_two_word_phrase_not_converted(tmp_kb):
    """Two-word phrases should NOT be auto-converted (often specific terms)."""
    from src.tools.file_ops import search_knowledge_base

    # "Blum komplet" is a specific phrase, not two separate terms
    result = search_knowledge_base("Blum komplet", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    # Should find the exact phrase "Blum komplet" (from playbook.md)
    assert "Blum komplet" in content


# ---------------------------------------------------------------------------
# Test 3: Exact phrases (quoted) are NOT auto-converted
# ---------------------------------------------------------------------------

def test_quoted_phrase_not_converted(tmp_kb):
    """Quoted phrases should be preserved as-is."""
    from src.tools.file_ops import search_knowledge_base

    # Quoted phrase should be kept intact
    result = search_knowledge_base('"Blum Merivobox"', base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    # Should find exact phrase
    assert "Blum Merivobox" in content


# ---------------------------------------------------------------------------
# Test 4: Queries with | are passed through unchanged
# ---------------------------------------------------------------------------

def test_pipe_query_passed_through(tmp_kb):
    """Queries already using | should not be modified."""
    from src.tools.file_ops import search_knowledge_base

    result = search_knowledge_base("Blum|Antaro|Merivobox", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    assert "No matches" not in content


# ---------------------------------------------------------------------------
# Test 5: "No matches" response includes helpful hint
# ---------------------------------------------------------------------------

def test_no_matches_hint(tmp_kb):
    """When no matches found, response should suggest using | for OR."""
    from src.tools.file_ops import search_knowledge_base

    result = search_knowledge_base("unicorn|dragon", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    assert "No matches" in content


# ---------------------------------------------------------------------------
# Test 6: Single word queries still work
# ---------------------------------------------------------------------------

def test_single_word_query(tmp_kb):
    """Single word queries should work unchanged."""
    from src.tools.file_ops import search_knowledge_base

    result = search_knowledge_base("Blum", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    assert "blum_compendium.md" in content
    assert "standards.md" in content


# ---------------------------------------------------------------------------
# Test 7: Regex special characters are handled
# ---------------------------------------------------------------------------

def test_regex_special_chars(tmp_kb):
    """Regex special characters should still work."""
    from src.tools.file_ops import search_knowledge_base

    # \d should match digits
    result = search_knowledge_base(r"\d{4}", base_dir=str(tmp_kb))
    assert "error" not in result
    content = result["content"]
    assert "2026" in content


# ---------------------------------------------------------------------------
# Test 8: context_lines parameter works with auto-conversion
# ---------------------------------------------------------------------------

def test_context_lines_with_autoconversion(tmp_kb):
    """context_lines should work correctly after auto-conversion."""
    from src.tools.file_ops import search_knowledge_base

    # 3+ words: auto-convert to OR
    result = search_knowledge_base(
        "Blum szuflady Tandembox", base_dir=str(tmp_kb), context_lines=3,
    )
    assert "error" not in result
    content = result["content"]
    # Should have context lines (>> markers)
    assert ">>" in content
