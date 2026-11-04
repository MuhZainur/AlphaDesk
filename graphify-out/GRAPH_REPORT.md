# Graph Report - AlphaDesk  (2026-11-04)

## Corpus Check
- 45 files · ~13,625 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: .example 2, (none) 1, .css 1)

## Summary
- 347 nodes · 604 edges · 23 communities (17 shown, 6 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `60030f71`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- nodes.py
- llm.py
- package.json
- App.tsx
- main.py
- market.py
- test_tools_memory_checks.py
- Decisions
- services
- compilerOptions
- Architecture
- Phases
- config.py
- AlphaDesk: a small AI research desk for stocks
- Deployment: Render (backend) and Vercel (frontend)
- Working rules for AI assistants in this repo
- API specification
- questions.md

## God Nodes (most connected - your core abstractions)
1. `AgentState` - 15 edges
2. `build_graph()` - 14 edges
3. `Decisions` - 14 edges
4. `run()` - 13 edges
5. `Architecture` - 13 edges
6. `_run_worker()` - 11 edges
7. `compilerOptions` - 11 edges
8. `planner()` - 10 edges
9. `critic()` - 10 edges
10. `App()` - 10 edges

## Surprising Connections (you probably didn't know these)
- ``POST /chat/stream`` --references--> `load_memory()`  [INFERRED]
  API_SPEC.md → backend/app/graph/nodes.py
- `2. The agent graph` --references--> `load_memory()`  [INFERRED]
  ARCHITECTURE.md → backend/app/graph/nodes.py
- `Phase 3: Reflection and memory (patterns 4 and 5)` --references--> `load_memory()`  [INFERRED]
  IMPLEMENTATION_PLAN.md → backend/app/graph/nodes.py
- `2. The agent graph` --references--> `save_memory()`  [INFERRED]
  ARCHITECTURE.md → backend/app/graph/nodes.py
- `Phase 3: Reflection and memory (patterns 4 and 5)` --references--> `save_memory()`  [INFERRED]
  IMPLEMENTATION_PLAN.md → backend/app/graph/nodes.py

## Import Cycles
- None detected.

## Communities (23 total, 6 thin omitted)

### Community 0 - "nodes.py"
Cohesion: 0.10
Nodes (26): 2. The agent graph, build_graph(), after_critic(), critic(), _evidence(), fundamental(), _history(), load_memory() (+18 more)

### Community 1 - "llm.py"
Cohesion: 0.08
Nodes (12): RateLimiter, run_chat(), sse(), LLMUnavailable, _post(), _providers(), run(), Stats (+4 more)

### Community 2 - "package.json"
Cohesion: 0.08
Nodes (33): dependencies, react@^18.3.1, react-dom@^18.3.1, react-markdown@^9.1.0, devDependencies, autoprefixer@^10.6.2, postcss@^8.5.32, tailwindcss@^3.4.19 (+25 more)

### Community 3 - "App.tsx"
Cohesion: 0.12
Nodes (27): App(), send(), reduce(), Chat(), EXAMPLES, Msg, Disclaimer(), MemoryPanel() (+19 more)

### Community 4 - "main.py"
Cohesion: 0.13
Nodes (16): chat_stream(), ChatIn, delete_memory(), get_memory(), health(), ProfileIn, put_profile(), add_watch() (+8 more)

### Community 5 - "market.py"
Cohesion: 0.15
Nodes (13): 5. Workers (pattern 3), cached(), compute_technicals(), get_fundamentals(), get_news(), get_price_snapshot(), get_technicals(), _history() (+5 more)

### Community 6 - "test_tools_memory_checks.py"
Cohesion: 0.18
Nodes (7): numbers(), rule_issues(), ungrounded_numbers(), call(), test_critic_rules_catch_made_up_number_and_trade_advice(), test_tool_never_raises(), test_unknown_tool()

### Community 7 - "Decisions"
Cohesion: 0.13
Nodes (14): D10. Critic checks evidence, not truth, D11. Finance guardrails, D12. Scope, D13. LLM chain: OpenRouter free models first, Gemini last, D1. New repo, not a change to AlphaSwarm, D2. LangGraph for the agent framework, D3. Gemini free tier as the LLM, D4. yfinance for data (+6 more)

### Community 8 - "services"
Cohesion: 0.14
Nodes (13): key, sync, value, services, buildCommand, envVars, healthCheckPath, name (+5 more)

### Community 9 - "compilerOptions"
Cohesion: 0.15
Nodes (12): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, skipLibCheck (+4 more)

### Community 10 - "Architecture"
Cohesion: 0.17
Nodes (11): 10. Frontend layout, 11. Limits that keep it free and calm, 12. LLM layer (`graph/llm.py`), 1. System view, 3. State, 4. Tools (pattern 1), 6. Reflection loop (pattern 4), 7. Memory and context (pattern 5) (+3 more)

### Community 11 - "Phases"
Cohesion: 0.17
Nodes (11): Definition of done, Explicitly not doing, Implementation plan, Phase 0: Scaffold (small), Phase 4: API, Phase 5: Frontend, Phase 6: Deploy, Phase 7: Measure, write up, add to portfolio (+3 more)

### Community 12 - "config.py"
Cohesion: 0.24
Nodes (3): _list(), prices(), tmp_db()

### Community 13 - "AlphaDesk: a small AI research desk for stocks"
Cohesion: 0.20
Nodes (9): AlphaDesk: a small AI research desk for stocks, Measured results, Repository layout, Run it locally (once built), Stack, Status, The five patterns, What I would do next (+1 more)

### Community 14 - "Deployment: Render (backend) and Vercel (frontend)"
Cohesion: 0.22
Nodes (8): 0. Before you start, 1. Backend on Render, 2. Frontend on Vercel, 3. Connect them, 4. Smoke test checklist, 5. Environment variables, 6. Troubleshooting, Deployment: Render (backend) and Vercel (frontend)

### Community 15 - "Working rules for AI assistants in this repo"
Cohesion: 0.25
Nodes (7): Code rules, Honesty rules, Publishing flow (after the app works), Scope and size, Secrets and setup, Stack (fixed), Working rules for AI assistants in this repo

### Community 16 - "API specification"
Cohesion: 0.29
Nodes (6): API specification, Endpoints, `GET /health`, Memory endpoints, Notes for the frontend, `POST /chat/stream`

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Architecture` connect `Architecture` to `nodes.py`, `market.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `AgentState` (e.g. with `build_graph()` and `after_critic()`) actually correct?**
  _`AgentState` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `nodes.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09990749306197964 - nodes in this community are weakly interconnected._
- **Why does `Phases` connect `Phases` to `nodes.py`, `market.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `build_graph()` (e.g. with `critic()` and `fundamental()`) actually correct?**
  _`build_graph()` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `llm.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07804878048780488 - nodes in this community are weakly interconnected._
- **Why does `load_memory()` connect `nodes.py` to `API specification`, `main.py`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._