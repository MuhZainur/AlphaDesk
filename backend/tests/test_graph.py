"""End-to-end graph test with a scripted fake LLM and fake tools (offline)."""
import json

from app import llm
from app.api.stream import run_chat
from app.graph.build import build_graph
from app.tools import market

PLAN = {"steps": [{"id": 1, "worker": "technical", "ticker": "aapl", "goal": "trend"}]}


def fake_factory(drafts):
    drafts = iter(drafts)

    def fake_run(messages, stats, tools=None, accept=None):
        text = messages[-1]["content"] if messages[-1]["role"] != "tool" else "TOOL"
        if "ROLE: PLANNER" in text:
            msg = {"content": json.dumps(PLAN), "tool_calls": None}
        elif "WORKER. Goal" in text:
            msg = {"content": "", "tool_calls": [{"id": "1", "function": {"name": "get_technicals", "arguments": "{}"}}]}
        elif messages[-1]["role"] == "tool":
            msg = {"content": "RSI looks neutral.", "tool_calls": None}
        elif "ROLE: WRITER" in text:
            msg = {"content": next(drafts), "tool_calls": None}
        else:  # critic
            msg = {"content": '{"verdict": "pass", "issues": []}', "tool_calls": None}
        out = accept(msg) if accept else msg
        stats.ok("fake")
        return out

    return fake_run


def events(chunks):
    out = []
    for c in chunks:
        kind = c.split("\n")[0].removeprefix("event: ")
        out.append((kind, json.loads(c.split("data: ", 1)[1])))
    return out


def test_reflection_loop_and_memory(monkeypatch):
    monkeypatch.setattr(market, "get_technicals", lambda t: {"ticker": t, "rsi14": 61.2})
    monkeypatch.setitem(market.REGISTRY, "get_technicals", (market.get_technicals, market.REGISTRY["get_technicals"][1]))
    bad = "## Summary\nAAPL P/E is 28.4.\n## Risks\nVolatility.\nTL;DR: cheap."
    good = "## Summary\nAAPL RSI is 61.2.\n## Risks\nVolatility.\nTL;DR: AAPL looks neutral."
    monkeypatch.setattr(llm, "run", fake_factory([bad, good]))
    g = build_graph()

    ev = events(run_chat(g, "user-0001", "thread-001", "Is AAPL overextended?"))
    kinds = [k for k, _ in ev]
    assert kinds[:2] == ["memory", "plan"] and kinds[-1] == "final"
    assert [d["verdict"] for k, d in ev if k == "critique"] == ["revise", "pass"]  # bad draft sent back once
    final = ev[-1][1]
    assert final["revisions"] == 1 and "28.4" not in final["text"]
    assert final["saved"]["watchlist_added"] == ["AAPL"]

    # follow-up in the same thread keeps working, and the watchlist is remembered
    monkeypatch.setattr(llm, "run", fake_factory([good]))
    ev2 = events(run_chat(g, "user-0001", "thread-001", "and now?"))
    assert ev2[0][1]["watchlist"] == ["AAPL"] and ev2[-1][0] == "final"
