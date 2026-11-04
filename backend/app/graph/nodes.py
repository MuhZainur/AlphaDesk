import json
import re

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Send

from app import config as cfg, llm
from app.graph import checks, prompts
from app.graph.state import AgentState, Critique, Finding, Plan, Step
from app.memory import store
from app.tools import market

WORKER_TOOLS = {
    "technical": ["get_price_snapshot", "get_technicals"],
    "fundamental": ["get_fundamentals", "get_price_snapshot"],
    "news": ["get_news"],
}


def _stats(config) -> llm.Stats:
    return config["configurable"]["stats"]


def _question(state: AgentState) -> str:
    return next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")


def _history(state: AgentState) -> str:
    """Context management: only the last few messages, each truncated, excluding the current question."""
    msgs = state["messages"][:-1][-cfg.HISTORY_MESSAGES :]
    return "\n".join(f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content[:400]}" for m in msgs) or "(none)"


def _evidence(findings: list) -> str:
    return "\n".join(f"[{f.worker} {f.ticker}] {json.dumps(f.evidence, default=str)}\nreading: {f.notes}" for f in findings) or "(none)"


# --- memory (pattern 5) ---------------------------------------------------------------
def load_memory(state: AgentState, config, writer) -> dict:
    uid = state["user_id"]
    profile, summaries = store.get_profile(uid), store.recent(uid)
    writer({"event": "memory", "data": {**profile, "summaries_used": len(summaries)}})
    return {"profile": profile, "summaries": summaries, "findings": "reset", "revisions": 0, "critique": None, "draft": ""}


def save_memory(state: AgentState, config, writer) -> dict:
    tickers = list(dict.fromkeys(f.ticker for f in state["findings"] if "error" not in f.evidence))
    m = re.search(r"TL;DR:\s*(.+)", state["draft"])
    summary = (m.group(1) if m else state["draft"][:200]).strip()
    added = store.add_watch(state["user_id"], tickers)
    store.log_analysis(state["user_id"], tickers, _question(state), summary)
    final = state["draft"]
    if state.get("critique") and state["critique"].verdict == "revise":
        final += "\n\n> Note: some figures in this note could not be fully verified against the data."
    _stats(config).saved = {"summary": summary, "watchlist_added": added}
    return {"final": final, "messages": [AIMessage(content=final)]}


# --- plan and execute (pattern 2) ------------------------------------------------------
def planner(state: AgentState, config, writer) -> dict:
    prompt = prompts.PLANNER.format(
        history=_history(state), watchlist=state["profile"]["watchlist"], question=_question(state)
    )
    plan = llm.run([{"role": "user", "content": prompt}], _stats(config), accept=lambda m: Plan(**llm.parse_json(m["content"])))
    steps = [s.model_copy(update={"id": i + 1}) for i, s in enumerate(plan.steps)]
    writer({"event": "plan", "data": {"steps": [s.model_dump() for s in steps]}})
    return {"plan": steps}


# --- orchestrator / worker (pattern 3) --------------------------------------------------
def orchestrate(state: AgentState):
    if not state["plan"]:
        return "writer"
    return [Send(s.worker, {"step": s, "messages": []}) for s in state["plan"]]


# --- tool use (pattern 1) ---------------------------------------------------------------
def _run_worker(kind: str, state: dict, config, writer) -> dict:
    step: Step = state["step"]
    writer({"event": "worker_start", "data": {"step_id": step.id, "worker": kind, "ticker": step.ticker}})
    messages = [{"role": "user", "content": prompts.WORKER.format(kind=kind, goal=step.goal, ticker=step.ticker)}]
    names = WORKER_TOOLS[kind]
    evidence: dict = {}
    notes = ""
    for used in range(cfg.MAX_TOOL_CALLS + 1):
        tools = market.specs(names) if used < cfg.MAX_TOOL_CALLS else None
        msg = llm.run(messages, _stats(config), tools=tools)
        if not msg["tool_calls"]:
            notes = msg["content"]
            break
        messages.append({k: v for k, v in msg.items() if v})
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            args["ticker"] = step.ticker  # the worker only researches its own ticker
            writer({"event": "tool_call", "data": {"step_id": step.id, "tool": name, "args": args}})
            result = market.call(name, args)
            evidence[name] = result
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, default=str)})
    if not evidence:
        evidence = {"error": "no tool was called"}
    writer({"event": "worker_done", "data": {"step_id": step.id, "notes": notes[:400]}})
    return {"findings": [Finding(step_id=step.id, worker=kind, ticker=step.ticker, evidence=evidence, notes=notes)]}


def technical(state, config, writer):
    return _run_worker("technical", state, config, writer)


def fundamental(state, config, writer):
    return _run_worker("fundamental", state, config, writer)


def news(state, config, writer):
    return _run_worker("news", state, config, writer)


# --- writer and critic (pattern 4: reflection) --------------------------------------------
def writer_node(state: AgentState, config, writer) -> dict:
    crit = state.get("critique")
    revising = bool(crit and crit.verdict == "revise")
    revision = prompts.REVISION.format(draft=state["draft"], issues="\n".join(f"- {i}" for i in crit.issues)) if revising else ""
    summaries = "\n".join(f"- {s['summary']}" for s in state["summaries"]) or "(none)"
    prompt = prompts.WRITER.format(
        risk=state["profile"]["risk_profile"], question=_question(state), history=_history(state),
        summaries=summaries, evidence=_evidence(state["findings"]), revision=revision,
    )

    def accept(m):
        if len(m["content"]) < 40:
            raise ValueError("too short")
        return m["content"]

    text = llm.run([{"role": "user", "content": prompt}], _stats(config), accept=accept)
    if checks.DISCLAIMER not in text.lower():
        text += "\n\n*Not financial advice. This is a research note built from public data.*"
    revisions = state.get("revisions", 0) + (1 if revising else 0)
    writer({"event": "draft", "data": {"revision": revisions, "text": text}})
    return {"draft": text, "revisions": revisions}


def critic(state: AgentState, config, writer) -> dict:
    issues = checks.rule_issues(state["draft"], state["findings"])
    prompt = prompts.CRITIC.format(evidence=_evidence(state["findings"]), draft=state["draft"])
    try:
        llm_c = llm.run([{"role": "user", "content": prompt}], _stats(config), accept=lambda m: Critique(**llm.parse_json(m["content"])))
        issues += llm_c.issues if llm_c.verdict == "revise" else []
    except llm.LLMUnavailable:
        pass  # rule checks alone still decide
    crit = Critique(verdict="revise" if issues else "pass", issues=issues[:5])
    writer({"event": "critique", "data": crit.model_dump()})
    return {"critique": crit}


def after_critic(state: AgentState) -> str:
    return "writer" if state["critique"].verdict == "revise" and state["revisions"] < cfg.MAX_REVISIONS else "save_memory"
