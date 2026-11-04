# Implementation plan

Scope rule: this is a junior-sized portfolio project that one person can build, explain in an interview and run for free. When in doubt, choose the simpler option and write the trade-off in `DECISIONS.md`.

## Phases

### Phase 0: Scaffold (small)
- [ ] Create `backend/` and `frontend/` folders as in `ARCHITECTURE.md`
- [ ] `backend/.venv`, install `requirements.txt`, then pin the versions that worked
- [ ] Get a free Gemini API key and put it in `backend/.env`
- [ ] "Hello graph": a one-node LangGraph that calls Gemini and returns text
- Done when: a script prints a Gemini answer through LangGraph.

### Phase 1: Tools (pattern 1)
- [ ] `tools/market.py`: `get_price_snapshot`, `get_technicals`, `get_fundamentals`, `get_news`
- [ ] `tools/cache.py`: 10-minute TTL cache
- [ ] Tools never raise: they return `{"error": ...}`
- [ ] Unit tests with saved fixture data so tests run offline
- Done when: `pytest` passes and each tool works on AAPL, MSFT and an invalid ticker.

### Phase 2: Plan, workers, writer (patterns 2 and 3)
- [ ] `state.py` with `AgentState`, `Step`, `Finding`, `Critique`
- [ ] Planner with structured output (1 to 6 steps)
- [ ] Orchestrator conditional edge using `Send`
- [ ] Three workers as small tool-calling agents (max 3 tool calls)
- [ ] `collect` and `writer` with the fixed report format
- Done when: "Compare AAPL and MSFT" runs end to end in a script and prints a report.

### Phase 3: Reflection and memory (patterns 4 and 5)
- [ ] Critic with structured output and the revision loop (max 2)
- [ ] `memory/store.py` (SQLite), `load_memory` and `save_memory` nodes
- [ ] Checkpointer for thread memory; window of 6 messages and up to 5 summaries
- [ ] Tests: critic catches a draft with a made-up number; follow-up works within a thread; a new session sees the watchlist
- Done when: a follow-up question works and a deliberately bad draft is sent back by the critic.

### Phase 4: API
- [ ] FastAPI routes from `API_SPEC.md`
- [ ] Graph events to SSE, including tool calls through the stream writer
- [ ] Retry with backoff on Gemini 429, then the `model_busy` error
- [ ] Per-IP limiter, CORS from `ALLOWED_ORIGINS`
- Done when: `curl -N` shows the full event sequence.

### Phase 5: Frontend
- [ ] Vite + React + Tailwind app, `lib/api.ts` with the SSE reader
- [ ] Chat, TracePanel, MemoryPanel, Disclaimer, cold-start message
- [ ] User id in `localStorage`
- Done when: asking a question shows the plan, tool calls and critic verdict live.

### Phase 6: Deploy
- [ ] Push to GitHub (repo name suggestion: `AlphaDesk`)
- [ ] Render from `render.yaml`, then Vercel with root `frontend`
- [ ] Set `ALLOWED_ORIGINS` and `VITE_API_URL`, smoke test the live URL
- Done when: the public site answers a question end to end. Steps are in `DEPLOYMENT.md`.

### Phase 7: Measure, write up, add to portfolio
- [ ] Run `evals/run_demo_set.py` on the 8 questions below and record numbers
- [ ] Medium article (same workflow as the other articles), Sanity card (AI Engineer), CV bullet
- Done when: the README has a "Measured results" table with real numbers.

## Small demo set (measure, do not over-engineer)

Eight questions saved in `evals/questions.md`:

1. Is NVDA overextended right now?
2. Compare AAPL and MSFT for a conservative investor.
3. What changed for TSLA this week?
4. Give me a quick read on AMZN valuation.
5. Is JPM cheap relative to its fundamentals?
6. Technical outlook for META in one paragraph.
7. (follow-up in the same thread as 1) What about its valuation?
8. A ticker that does not exist, to check the error path.

For each run record: number of LLM calls, elapsed seconds, number of critic revisions, and whether the final report contains only numbers present in the findings (checked by a small script that extracts numbers from the report and looks them up in the findings). Report the numbers as measured on one machine with the free tier, nothing more.

## Definition of done

- [ ] All five patterns visible in the trace panel
- [ ] Public Vercel URL calling the public Render URL
- [ ] No API key in the repo or the browser
- [ ] Disclaimer visible, no trade instructions in any report
- [ ] `pytest` passes offline
- [ ] README has measured results and a short "what I would do next" list

## Explicitly not doing

Authentication, payments, real-time quotes or websockets, portfolio optimization, backtesting, Postgres, Kubernetes, multi-model routing, vector databases, a mobile app, Telegram integration (kept in AlphaSwarm).

## Wrap-up templates (fill with measured numbers only)

CV bullet:
- Built AlphaDesk, a LangGraph stock-research agent combining tool use, plan-and-execute, orchestrator/worker, reflection and memory, with a FastAPI streaming backend on Render and a React frontend on Vercel; a critic loop revised N of 8 test answers, with a median of X LLM calls and Y seconds per answer on the Gemini free tier.

Article outline: why basic agents are not enough, the five patterns mapped to the graph, the trace panel, the measured table, what the free tier taught me.
