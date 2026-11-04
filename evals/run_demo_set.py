"""Run the 8-question demo set through the real graph and record what happened.

Usage (from backend/):  python ../evals/run_demo_set.py [first_n]
Writes evals/results.json and evals/results.md. Numbers come from one machine on free models.
"""
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from langchain_core.messages import HumanMessage  # noqa: E402

from app import config, llm  # noqa: E402
from app.graph import checks  # noqa: E402
from app.graph.build import build_graph  # noqa: E402

QUESTIONS = [
    ("q1", "Is NVDA overextended right now?", "t1"),
    ("q2", "Compare AAPL and MSFT for a conservative investor.", "t2"),
    ("q3", "What changed for TSLA this week?", "t3"),
    ("q4", "Give me a quick read on AMZN valuation.", "t4"),
    ("q5", "Is JPM cheap relative to its fundamentals?", "t5"),
    ("q6", "Technical outlook for META in one paragraph.", "t6"),
    ("q7", "What about its valuation?", "t1"),  # follow-up in the same thread as q1
    ("q8", "Tell me about the stock ZZZZQ.", "t8"),  # invalid ticker, checks the error path
]


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(QUESTIONS)
    config.DB_PATH = str(Path(__file__).parent / "eval.db")
    Path(config.DB_PATH).unlink(missing_ok=True)
    graph, user, rows = build_graph(), "eval-" + uuid.uuid4().hex[:8], []
    for qid, question, thread in QUESTIONS[:n]:
        stats, t0 = llm.Stats(), time.time()
        cfg = {"configurable": {"thread_id": f"{user}-{thread}", "stats": stats}, "max_concurrency": config.MAX_CONCURRENCY}
        row = {"id": qid, "question": question}
        try:
            out = graph.invoke({"messages": [HumanMessage(content=question)], "user_id": user}, cfg)
            row |= {
                "ok": True, "llm_calls": stats.calls, "seconds": round(time.time() - t0, 1), "revisions": out["revisions"],
                "steps": len(out["plan"]), "models": list(dict.fromkeys(stats.models)), "skipped": len(stats.skipped),
                "ungrounded_numbers": len(checks.ungrounded_numbers(out["final"], out["findings"])),
                "verified": out["critique"].verdict == "pass", "report": out["final"],
            }
        except Exception as e:  # noqa: BLE001
            row |= {"ok": False, "error": repr(e)[:200], "seconds": round(time.time() - t0, 1), "skipped": len(stats.skipped)}
        rows.append(row)
        print(qid, {k: v for k, v in row.items() if k != "report"}, flush=True)

    here = Path(__file__).parent
    (here / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = ["| # | Question | OK | LLM calls | Seconds | Revisions | Ungrounded numbers | Models that answered |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['question']} | {r['ok']} | {r.get('llm_calls', '-')} | {r['seconds']} | {r.get('revisions', '-')} | {r.get('ungrounded_numbers', '-')} | {', '.join(r.get('models', [])) or '-'} |")
    (here / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
