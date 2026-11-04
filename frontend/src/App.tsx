import { useEffect, useRef, useState } from "react";
import Chat, { type Msg } from "./components/Chat";
import Disclaimer from "./components/Disclaimer";
import MemoryPanel from "./components/MemoryPanel";
import TracePanel, { emptyTrace, type Trace } from "./components/TracePanel";
import { newThread, streamChat, waitForServer, type Event } from "./lib/api";

function reduce(t: Trace, e: Event): Trace {
  switch (e.type) {
    case "plan":
      return { ...t, plan: e.data.steps };
    case "worker_start":
      return { ...t, workers: { ...t.workers, [e.data.step_id]: { tools: [], done: false } } };
    case "tool_call": {
      const w = t.workers[e.data.step_id] ?? { tools: [], done: false };
      return { ...t, workers: { ...t.workers, [e.data.step_id]: { ...w, tools: [...w.tools, `${e.data.tool}(${e.data.args.ticker})`] } } };
    }
    case "worker_done":
      return {
        ...t,
        workers: { ...t.workers, [e.data.step_id]: { ...(t.workers[e.data.step_id] ?? { tools: [] }), notes: e.data.notes, done: true } },
      };
    case "draft":
      return { ...t, drafts: t.drafts + 1 };
    case "critique":
      return { ...t, critiques: [...t.critiques, e.data] };
    case "final":
      return { ...t, final: e.data };
    case "error":
      return { ...t, error: e.data.message };
    default:
      return t;
  }
}

export default function App() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [trace, setTrace] = useState<Trace>(emptyTrace);
  const [busy, setBusy] = useState(false);
  const [waking, setWaking] = useState(false);
  const [memKey, setMemKey] = useState(0);
  const thread = useRef(newThread());

  useEffect(() => {
    waitForServer(() => setWaking(true)).then(() => setWaking(false));
  }, []);

  async function send(text: string) {
    setMessages((m) => [...m, { role: "user", text }]);
    setTrace(emptyTrace);
    setBusy(true);
    try {
      await streamChat(thread.current, text, (e) => {
        setTrace((t) => reduce(t, e));
        if (e.type === "final") setMessages((m) => [...m, { role: "assistant", text: e.data.text }]);
        if (e.type === "error") setMessages((m) => [...m, { role: "assistant", text: `**${e.data.message}**` }]);
      });
    } catch {
      setTrace((t) => ({ ...t, error: "Could not reach the server." }));
    } finally {
      setBusy(false);
      setMemKey((k) => k + 1);
    }
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <h1 className="font-semibold">
          AlphaDesk <span className="text-sm font-normal text-slate-500">a small AI research desk for stocks</span>
        </h1>
        <button
          className="text-xs text-slate-400 hover:text-white"
          onClick={() => {
            thread.current = newThread();
            setMessages([]);
            setTrace(emptyTrace);
          }}
        >
          New chat
        </button>
      </header>
      {waking && <div className="bg-amber-950 px-4 py-2 text-center text-sm text-amber-200">Waking the server, about 50 seconds on the free tier...</div>}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <div className="flex min-h-0 flex-1 flex-col md:w-1/2">
          <Chat messages={messages} busy={busy} onSend={send} />
        </div>
        <aside className="flex min-h-0 flex-1 flex-col border-t border-slate-800 md:w-1/2 md:flex-none md:border-l md:border-t-0">
          <div className="min-h-0 flex-1 overflow-y-auto">
            <TracePanel trace={trace} busy={busy} />
          </div>
          <MemoryPanel refreshKey={memKey} />
        </aside>
      </div>
      <Disclaimer />
    </div>
  );
}
