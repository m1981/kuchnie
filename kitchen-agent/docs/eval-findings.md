# Evaluation Findings — 2026-06-11

## Summary

Ran golden dataset evaluation against live LLM APIs (Anthropic Claude Sonnet 4, Gemini 3.1 Pro).

---

## Run 1: 5% Tool Budget (Baseline)

**Provider:** Anthropic Claude Sonnet 4
**Duration:** 250 seconds for 15 cases
**Result:** 6/15 passed (40%)

### Failures

| Case     | Root Cause                                 | Impact                                  |
| -------- | ------------------------------------------ | --------------------------------------- |
| eval-003 | Token budget exceeded → synthetic response | Missing Tandembox, Merivobox, citations |
| eval-006 | Token budget exceeded → synthetic response | Missing "montaż"                        |
| eval-007 | Token budget exceeded → synthetic response | Missing "wysokość"                      |
| eval-011 | Token budget exceeded → synthetic response | Missing citations                       |
| eval-015 | Token budget exceeded → synthetic response | Missing "okucia"                        |
| eval-004 | Citations missing                          | Content good, no `[1]` markers          |
| eval-005 | Citation verification failed               | Content good, uncited claims            |
| eval-010 | Budget exceeded before edit_file           | Incomplete workflow                     |
| eval-013 | Citations missing                          | Content good, no citations              |

---

## Run 2: 20% Tool Budget

**Provider:** Anthropic Claude Sonnet 4
**Duration:** 197 seconds for 9 cases (credits exhausted)
**Result:** 5/9 passed (56%)

### Improvements

| Case     | Before   | After    | Change                                      |
| -------- | -------- | -------- | ------------------------------------------- |
| eval-005 | ❌       | ✅       | **Fixed** — agent could read full file      |
| eval-003 | ❌ (0/5) | ❌ (5/6) | **Improved** — only citation_verdict failed |
| eval-004 | ❌ (0/4) | ❌ (4/5) | **Improved** — only citation_verdict failed |

### Remaining Failures

| Case      | Root Cause                      | Notes                                            |
| --------- | ------------------------------- | ------------------------------------------------ |
| eval-003  | Citation format not followed    | Agent produces good content but no `[1]` markers |
| eval-004  | Citation format not followed    | Same — content accurate, citations missing       |
| eval-006  | Broad search exceeds 20% budget | "montaż Merivobox" returns 84K chars             |
| eval-007  | Broad search exceeds 20% budget | "blaty ergonomiczne" returns 86K chars           |
| eval-010+ | API credits exhausted           | Could not complete evaluation                    |

---

## Root Cause Analysis

### Problem 1: Token Budget (FIXED)

**Before:** 5% of context (6,400 tokens at 128K)
**After:** 20% of context (25,600 tokens at 128K)

Search results routinely contain 10-20K tokens. The 5% budget caused:

1. Truncation of search results
2. LLM requesting more tools (didn't get enough info)
3. Budget exceeded → synthetic fallback response
4. Synthetic response lacks domain terms and citations

**Status:** Fixed by increasing budget to 20%.

### Problem 2: Citation Compliance (OPEN)

The system prompt mandates citations:

```
## Citation Format
At the end of your answer, add a `## Źródła` section with numbered references.
Every factual claim from knowledge base must have a [1], [2] etc. inline marker.
```

But the LLM doesn't always follow this instruction. Possible reasons:

1. **Instruction following is probabilistic** — LLMs don't guarantee compliance
2. **Long responses** — citations more likely to be forgotten in long outputs
3. **Tool-heavy turns** — agent focuses on tool execution, forgets formatting
4. **Truncation** — when response is long, citations may be cut off

**Mitigation options:**

1. Add post-processing that detects missing citations and appends a warning
2. Use a second LLM call to verify/enforce citations
3. Accept that citations are "best effort" and use CitationVerifier to flag issues

### Problem 3: Broad Searches (OPEN)

Some queries trigger very broad searches:

- "montaż Merivobox" → 84K chars (21K tokens)
- "blaty ergonomiczne" → 86K chars (21.5K tokens)

Even with 20% budget (25.6K tokens), these get truncated.

**Mitigation options:**

1. Limit `search_knowledge_base` results before they hit the budget
2. Use more specific search queries (prompt engineering)
3. Increase budget further (trade-off with conversation history)

---

## Recommendations

### Immediate

1. ✅ **DONE:** Increase tool budget from 5% to 20%
2. **TODO:** Add `context_lines=1` as default in search tool (reduces output size)
3. **TODO:** Add post-citation check in ChatService (warn if citations missing)

### Short-term

4. Run full evaluation with fresh API credits
5. Tune golden dataset based on findings (some expectations may be too strict)
6. Add `scripts/test_citation_compliance.py` to CI pipeline

### Long-term

7. Implement RAG quality metrics (faithfulness, context relevance)
8. Add provider comparison tests (Gemini vs Anthropic vs MiMo)
9. Build observability dashboard for tracking citation compliance over time

---

## Files Created

| File                                  | Purpose                                     |
| ------------------------------------- | ------------------------------------------- |
| `scripts/test_citation_compliance.py` | Test citation compliance over multiple runs |
| `docs/eval-findings.md`               | This document                               |
