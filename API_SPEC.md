# API specification

Base URL: `http://localhost:8000` locally, the Render URL in production. All bodies are JSON. CORS allows only the origins listed in `ALLOWED_ORIGINS`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check, used by Render and by the frontend to detect a cold start |
| POST | `/chat/stream` | Ask a question, receive progress and the answer as Server-Sent Events |
| GET | `/memory/{user_id}` | Read the stored profile and recent summaries |
| PUT | `/memory/{user_id}/profile` | Set the risk profile |
| DELETE | `/memory/{user_id}` | Forget everything stored for this user |

## `GET /health`

```json
{ "status": "ok", "model": "gemini-3.8-flash" }
```

## `POST /chat/stream`

Request:

```json
{
  "user_id": "b6f1c1c0-6d3e-4c1e-9a54-6d9c2c2a1f10",
  "thread_id": "5a9e0a0c-1b1a-4a3a-8d1c-0c7d3f9a2b11",
  "message": "Compare AAPL and MSFT for a conservative investor"
}
```

Rules: `message` is 1 to 500 characters. `thread_id` groups follow-up questions. Both ids are UUIDs created in the browser.

Response: `text/event-stream`. Each event is `event: <type>` followed by `data: <json>`.

| Event | When | Data |
|---|---|---|
| `memory` | after `load_memory` | `{"risk_profile": "balanced", "watchlist": ["AAPL"], "summaries_used": 2}` |
| `plan` | planner done | `{"steps": [{"id": 1, "worker": "technical", "ticker": "AAPL", "goal": "..."}]}` |
| `worker_start` | a worker begins | `{"step_id": 1, "worker": "technical", "ticker": "AAPL"}` |
| `tool_call` | a worker calls a tool | `{"step_id": 1, "tool": "get_technicals", "args": {"ticker": "AAPL"}}` |
| `worker_done` | a worker finishes | `{"step_id": 1, "notes": "RSI 61, above SMA200 ..."}` |
| `draft` | writer finishes a draft | `{"revision": 0, "text": "..."}` |
| `critique` | critic finishes | `{"verdict": "revise", "issues": ["P/E of 28 is not in the evidence"]}` |
| `final` | graph finished | `{"text": "...", "revisions": 1, "llm_calls": 8, "elapsed_ms": 14200, "saved": {"summary": "...", "watchlist_added": ["MSFT"]}}` |
| `error` | anything failed | `{"code": "model_busy", "message": "The free model is rate limited. Try again in a minute."}` |

Order is always `memory`, `plan`, then for each step `worker_start`, zero or more `tool_call`, `worker_done`, then `draft`, `critique` (repeating as needed), and last `final`. Workers can interleave because they run in parallel.

Error codes:

| Code | HTTP | Meaning |
|---|---|---|
| `bad_request` | 422 | invalid or empty message |
| `rate_limited` | 429 | too many requests from this IP |
| `model_busy` | SSE | Gemini free tier returned 429 after retries |
| `data_unavailable` | SSE | a ticker returned no data from yfinance |
| `internal` | SSE | unexpected failure, details only in server logs |

## Memory endpoints

`GET /memory/{user_id}`:

```json
{
  "risk_profile": "balanced",
  "watchlist": ["AAPL", "MSFT"],
  "recent_summaries": [
    {"created_at": "2026-11-05T09:10:00Z", "tickers": ["AAPL"], "summary": "AAPL trades above its 200-day average with RSI near 61."}
  ]
}
```

`PUT /memory/{user_id}/profile` with `{"risk_profile": "conservative"}`; allowed values are `conservative`, `balanced`, `aggressive`.

`DELETE /memory/{user_id}` returns `{"deleted": true}`.

## Notes for the frontend

- Read the stream with `fetch` and a `ReadableStream` reader, because `EventSource` cannot send a POST body.
- If `/health` does not answer within 3 seconds, show "Waking the server, about 50 seconds on the free tier" and retry every 5 seconds.
- Always render the disclaimer under the chat.
