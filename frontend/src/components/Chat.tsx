import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

export type Msg = { role: "user" | "assistant"; text: string };

const EXAMPLES = ["Is NVDA overextended right now?", "Compare AAPL and MSFT for a conservative investor", "What changed for TSLA this week?"];

export default function Chat({ messages, busy, onSend }: { messages: Msg[]; busy: boolean; onSend: (t: string) => void }) {
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);
  const send = (t: string) => {
    if (t.trim() && !busy) {
      onSend(t.trim());
      setText("");
    }
  };
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="space-y-2 text-sm text-slate-400">
            <p>Ask about a stock. A planner splits the question, workers fetch the data, and a critic checks the note.</p>
            {EXAMPLES.map((e) => (
              <button key={e} onClick={() => send(e)} className="block rounded border border-slate-700 px-3 py-1.5 text-left hover:bg-slate-800">
                {e}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-auto max-w-[85%] rounded-lg bg-indigo-600 px-3 py-2 text-sm">
              {m.text}
            </div>
          ) : (
            <div key={i} className="prose prose-invert prose-sm max-w-none rounded-lg bg-slate-900 p-4">
              <ReactMarkdown>{m.text}</ReactMarkdown>
            </div>
          ),
        )}
        {busy && <p className="animate-pulse text-sm text-slate-400">Working... watch the trace panel.</p>}
        <div ref={end} />
      </div>
      <form
        className="flex gap-2 border-t border-slate-800 p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(text);
        }}
      >
        <input
          value={text}
          maxLength={500}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask about a stock..."
          className="flex-1 rounded bg-slate-900 px-3 py-2 text-sm outline-none ring-1 ring-slate-700 focus:ring-indigo-500"
        />
        <button disabled={busy || !text.trim()} className="rounded bg-indigo-600 px-4 text-sm font-medium disabled:opacity-40">
          Send
        </button>
      </form>
    </div>
  );
}
