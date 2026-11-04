# AlphaDesk: a small AI research desk for stocks

AlphaDesk answers questions about stocks the way a junior research desk would. It makes a plan, sends specialist workers to gather technicals, fundamentals and news, writes a short report, has a critic check that report against the evidence, and remembers your watchlist and risk profile between sessions.

It is the next generation of AlphaSwarm, rebuilt around the five agent design patterns that separate a demo from an agent worth shipping.

> Not financial advice. AlphaDesk reads public data and writes research notes. It never places trades.

## Live demo

| | URL |
|---|---|
| Frontend (Vercel) | https://alpha-desk-seven.vercel.app/ |
| Backend API (Render) | https://alphadesk-qgap.onrender.com/ |
| Health check | https://alphadesk-qgap.onrender.com/health |

The backend runs on Render's free plan, so the first request after a quiet period can take about 50 seconds while the server wakes up. Memory is stored in SQLite on an ephemeral disk and may reset when the server restarts.

## The five patterns

| # | Pattern | Where it lives in AlphaDesk |
|---|---|---|
| 1 | Tool use / function calling | Four tools over yfinance: price snapshot, technicals, fundamentals, news |
| 2 | Plan and execute | A planner turns the question into a short list of typed steps |
| 3 | Orchestrator / worker | The orchestrator fans steps out to a Technical, a Fundamental and a News worker |
| 4 | Reflection | A critic checks the draft against the collected evidence and sends it back for at most two revisions |
| 5 | Memory and context management | Conversation memory per thread, a small long-term store (watchlist, risk profile, past summaries), and a trimmed context window |

## What you can do with it

- "Is NVDA overextended right now?"
- "Compare AAPL and MSFT for a conservative investor."
- "What changed for TSLA this week?" followed by "and what about its valuation?"
- Watch the agent work: the right-hand panel shows the plan, each worker's tool calls, the critic's verdict and what was saved to memory.

## Stack

| Layer | Choice |
|---|---|
| Agent framework | LangGraph |
| LLM | OpenRouter free models first (tried in order), Gemini 3.8 Flash (`gemini-3.8-flash`) as the last fallback |
| Market data | yfinance (no API key) |
| Backend | FastAPI, streaming progress over Server-Sent Events, deployed on Render |
| Frontend | React + Vite + Tailwind CSS 3, deployed on Vercel |
| Memory | LangGraph in-memory checkpointer for threads, SQLite for the long-term store |

## Repository layout

```
AlphaDesk/
├── README.md
├── ARCHITECTURE.md        graph, state, workers, diagrams
├── API_SPEC.md            endpoints and the SSE event contract
├── IMPLEMENTATION_PLAN.md phases, tasks, definition of done
├── DECISIONS.md           why LangGraph, Gemini, SSE, SQLite, and what is out of scope
├── DEPLOYMENT.md          Render + Vercel steps
├── CLAUDE.md              working rules for AI assistants in this repo
├── render.yaml            Render blueprint for the backend
├── .env.example
├── backend/
│   ├── requirements.txt
│   └── app/               graph, tools, memory, api (see ARCHITECTURE.md)
└── frontend/
    ├── .env.example
    └── src/               chat, trace panel, memory panel
```

## Run it locally (once built)

```bash
# backend
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env        # add OPENROUTER_API_KEY and GOOGLE_API_KEY
uvicorn app.main:app --reload
pytest                           # offline tests

# frontend (another terminal)
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Free keys: openrouter.ai/keys (OpenRouter) and Google AI Studio (Gemini). The agent tries the free OpenRouter models in `OPENROUTER_MODELS` in order and only falls back to Gemini when all of them fail.

## Measured results

Eight demo questions run through the real graph by `evals/run_demo_set.py` on 2026-11-04, one machine, free OpenRouter models, no Gemini fallback needed. Numbers are from that single run and will vary, because free models are shared and rate limited.

| # | Question | OK | LLM calls | Seconds | Revisions | Ungrounded numbers | Models that answered |
|---|---|---|---|---|---|---|---|
| q1 | Is NVDA overextended right now? | True | 11 | 92.7 | 1 | 0 | nvidia/nemotron-3.5-super-vl:free |
| q2 | Compare AAPL and MSFT for a conservative investor. | True | 15 | 82.7 | 0 | 0 | nvidia/nemotron-3.5-super-vl:free |
| q3 | What changed for TSLA this week? | True | 5 | 74.4 | 0 | 0 | nvidia/nemotron-3.5-super-vl:free |
| q4 | Give me a quick read on AMZN valuation. | True | 5 | 27.9 | 0 | 0 | nvidia/nemotron-3.5-super-vl:free |
| q5 | Is JPM cheap relative to its fundamentals? | True | 5 | 85.7 | 0 | 0 | nvidia/nemotron-3-ultra-550b-a55b:free |
| q6 | Technical outlook for META in one paragraph. | True | 5 | 72.2 | 0 | 0 | nvidia/nemotron-3-ultra-550b-a55b:free |
| q7 | What about its valuation? | True | 7 | 66.5 | 1 | 0 | nvidia/nemotron-3.5-super-vl:free |
| q8 | Tell me about the stock ZZZZQ. | True | 9 | 34.3 | 0 | 0 | nvidia/nemotron-3.5-super-vl:free |

- 8 of 8 questions produced a report. The invalid ticker (q8) ended with a plain "no data available" note instead of an error.
- Median 6 LLM calls and about 73 seconds per answer (range 5 to 15 calls, 28 to 93 seconds).
- The critic sent 2 of 8 first drafts back for one revision (q1, q7).
- "Ungrounded numbers" counts numbers in the final report that are missing from the tool evidence, checked by a script. It was 0 for all 8. This checks the report against collected data, not against the truth of Yahoo Finance's data.
- Not measured: answer quality against an expert, accuracy of the free models over time, behaviour under many concurrent users.

## Known limitation

On the free Render plan, Yahoo Finance rejects fundamentals requests (`YFRateLimitError` for P/E, margins and statements) because the server shares a cloud IP. Prices, technical indicators and news work. When fundamentals are blocked, the report says the data was unavailable instead of guessing. Running the backend locally returns fundamentals normally. A different data source for fundamentals is the next fix.

## What I would do next

Move memory to a free hosted Postgres so it survives redeploys, add a small expert-labelled answer set, cache news across users, and add auth if it ever stops being a demo.

## Status

Backend, frontend and tests are built. See `evals/results.md` for the measured demo set and `DEPLOYMENT.md` for the Render and Vercel steps.
