# Decisions

Short records of the choices that shape the project. Format: decision, why, what we gave up.

## D1. New repo, not a change to AlphaSwarm
AlphaSwarm is live on Render with a Telegram bot. AlphaDesk reuses its ideas (yfinance, a stock focus) in a clean repo so the working bot is never at risk. We give up shared history, which is fine because the architecture is different.

## D2. LangGraph for the agent framework
It expresses plan, parallel workers (`Send`), conditional loops (critic) and checkpointed memory directly, and it is the framework employers ask about. We give up the "everything from scratch" story, but the graph code is short and readable.

## D3. Gemini free tier as the LLM
No cost, good structured output, decent tool calling. Free-tier limits (requests per minute and per day) shape the design: at most 6 steps, 2 concurrent workers, retry with backoff, a per-IP limiter and a fallback to `gemini-3.8-flash-lite`. Limits change over time, so check Google AI Studio before relying on a number.

## D4. yfinance for data
No key, covers prices, fundamentals and news. It is unofficial and can fail or lag, so tools return error dictionaries instead of raising, results are cached for 10 minutes, and reports state when data is missing. We give up real-time and licensed data.

## D5. Server-Sent Events, not websockets
One direction (server to browser), plain HTTP, works on Render and Vercel without extra setup. The frontend uses `fetch` with a stream reader because the request needs a POST body.

## D6. SQLite for long-term memory
A watchlist, a risk profile and a few summaries do not need Postgres. On Render's free tier the disk is ephemeral, so memory resets on a redeploy. That is stated in the README and in the UI ("memory may reset"). We give up durability. Moving to a free hosted Postgres is the first upgrade.

## D7. Memory without extra LLM calls
Summaries come from the writer's one-line TL;DR, and the risk profile comes from a UI selector. This keeps each answer within the free-tier budget and keeps memory behaviour predictable.

## D8. Anonymous user id, no login
A UUID in `localStorage` is enough for a demo and avoids collecting personal data. Anyone with the id can read that memory, so nothing sensitive is stored. We give up cross-device memory.

## D9. React + Vite + Tailwind on Vercel, not Streamlit
A real frontend shows the trace panel and streaming well and matches the user's other React projects. We give up Streamlit's speed of building.

## D10. Critic checks evidence, not truth
The critic verifies that every number in the report appears in the collected findings and that the report gives no trade instructions. It cannot verify that yfinance itself is right. That limit is stated in the README.

## D11. Finance guardrails
Every answer carries a "not financial advice" note, the writer is told never to recommend a trade, and the critic rejects drafts that do. No brokerage or trading integration exists.

## D12. Scope
This is a junior-level portfolio project: one backend, one frontend, one small test set, free hosting. Anything that would need a team, a budget or a thesis is out of scope (see "Explicitly not doing" in `IMPLEMENTATION_PLAN.md`).

## D13. LLM chain: OpenRouter free models first, Gemini last
`llm.py` tries the `:free` models in `OPENROUTER_MODELS` in order and moves to the next one on a 429, timeout, empty answer or invalid structured output. Only when all fail does it call Gemini 3.8 Flash (the owner's own key). This replaces the earlier plan of Gemini plus a lite fallback. Free model availability and limits change often, so the list lives in an environment variable and the model that answered is reported in the `final` event. The list was taken from the OpenRouter public models API on 2026-11-04 (12 free models, 11 with tool calling). Models were first ordered by structured-output support and size, then reordered after a live probe the same day (the two Gemma models and xing4.0 were rate limited upstream, the Nemotron models answered); the content-safety model and the 2.6B model were left out. 9Router is optional for local experiments and is not part of the deployed path (D3 context: a public gateway holding personal free-tier accounts risks quota abuse and account bans).
