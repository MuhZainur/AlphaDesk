import json
import time
from collections import defaultdict, deque

from langchain_core.messages import HumanMessage

from app import config, llm


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def run_chat(graph, user_id: str, thread_id: str, message: str):
    """Run the graph and yield SSE strings: custom node events, then `final` (or `error`)."""
    stats = llm.Stats()
    cfg = {"configurable": {"thread_id": thread_id, "stats": stats}, "max_concurrency": config.MAX_CONCURRENCY}
    start, last = time.time(), None
    try:
        for mode, chunk in graph.stream(
            {"messages": [HumanMessage(content=message)], "user_id": user_id}, cfg, stream_mode=["custom", "values"]
        ):
            if mode == "custom":
                yield sse(chunk["event"], chunk["data"])
            else:
                last = chunk
        yield sse("final", {
            "text": last["final"], "revisions": last["revisions"], "llm_calls": stats.calls,
            "models_used": list(dict.fromkeys(stats.models)), "models_skipped": len(stats.skipped),
            "elapsed_ms": int((time.time() - start) * 1000), "saved": stats.saved,
        })
    except llm.LLMUnavailable:
        yield sse("error", {"code": "model_busy", "message": "The free models are busy right now. Try again in a minute."})
    except Exception as e:  # noqa: BLE001
        print("chat failed:", repr(e))  # details stay in server logs only
        yield sse("error", {"code": "internal", "message": "Something went wrong. Please try again."})


class RateLimiter:
    """Per-IP sliding window. shortcut: in-memory, so it resets on restart and is per instance."""

    def __init__(self, per_hour: int) -> None:
        self.per_hour, self.hits = per_hour, defaultdict(deque)

    def allow(self, ip: str) -> bool:
        q, now = self.hits[ip], time.time()
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= self.per_hour:
            return False
        q.append(now)
        return True
