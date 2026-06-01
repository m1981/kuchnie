It's a local-first agentic workspace — a chat interface where an LLM autonomously reads, searches, and edits a  
 Markdown knowledge base via tool-calling. It has session branching, message editing, token counting, notes, file  
 CRUD, and a hot-swappable prompt system. The architecture is excellent (Clean Architecture, Protocol-based  
 repositories, TDD). Only 3 thin seams had kitchen-specific vocabulary hardcoded into Python source.

### The refactor: 3 surgical changes + 1 new config file

```
 ┌────────────────────────┬───────────────────────────────────────────────────────────┬──────────────────────────────┐
 │ Change                 │ What changed                                              │ Why                          │
 ├────────────────────────┼───────────────────────────────────────────────────────────┼──────────────────────────────┤
 │ src/prompt_manager.py  │ Removed _MODE_REGISTRY list; now reads modes.json from    │ Zero domain knowledge in     │
 │                        │ prompts_dir. Graceful degradation for missing/malformed   │ Python source                │
 │                        │ JSON, missing keys, wrong types.                          │                              │
 ├────────────────────────┼───────────────────────────────────────────────────────────┼──────────────────────────────┤
 │ src/config.py          │ Added app_title + app_description fields with generic     │ Any domain can brand its own │
 │                        │ defaults, overridable via .env                            │ API without touching code    │
 ├────────────────────────┼───────────────────────────────────────────────────────────┼──────────────────────────────┤
 │ src/main.py            │ FastAPI(title=..., description=...) now uses              │ Consistent use of settings   │
 │                        │ settings.app_title/settings.app_description;              │ as single source of truth    │
 │                        │ get_active_provider reads settings directly               │                              │
 ├────────────────────────┼───────────────────────────────────────────────────────────┼──────────────────────────────┤
 │ src/tools/registry.py  │ Replaced 'Blum|zawias' example with 'keyword1|keyword2'   │ Tool schemas must be         │
 │                        │                                                           │ domain-agnostic (they go to  │
 │                        │                                                           │ the LLM on every request)    │
 ├────────────────────────┼───────────────────────────────────────────────────────────┼──────────────────────────────┤
 │ prompts/modes.json     │ Kitchen domain's mode registry: general/design/assembly   │ Domain config lives next to  │
 │ (new)                  │                                                           │ its .md files, not in Python │
 └────────────────────────┴───────────────────────────────────────────────────────────┴──────────────────────────────┘
```

### To deploy a different domain (e.g. legal)

```
  legal-agent/
    prompts/
      modes.json          ← [{"id":"research","label":"Research",...}, ...]
      base_agent_rules.md ← universal agentic rules
      research.md         ← domain-specific system prompt
      drafting.md
    data/
      case-law/           ← your knowledge base
    .env
      APP_TITLE=Legal Research Agent
      APP_DESCRIPTION=AI assistant for case law research and contract drafting.
```
