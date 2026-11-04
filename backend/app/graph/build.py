from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph import nodes
from app.graph.state import AgentState


def build_graph():
    g = StateGraph(AgentState)
    for name, fn in [
        ("load_memory", nodes.load_memory), ("planner", nodes.planner),
        ("technical", nodes.technical), ("fundamental", nodes.fundamental), ("news", nodes.news),
        ("writer", nodes.writer_node), ("critic", nodes.critic), ("save_memory", nodes.save_memory),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "load_memory")
    g.add_edge("load_memory", "planner")
    g.add_conditional_edges("planner", nodes.orchestrate, ["technical", "fundamental", "news", "writer"])
    for w in ("technical", "fundamental", "news"):
        g.add_edge(w, "writer")  # fan-in: writer runs once after all parallel workers finish
    g.add_edge("writer", "critic")
    g.add_conditional_edges("critic", nodes.after_critic, ["writer", "save_memory"])
    g.add_edge("save_memory", END)
    # shortcut: thread memory lives in RAM and resets on restart; upgrade to a SQLite/Postgres saver if needed
    return g.compile(checkpointer=InMemorySaver())
