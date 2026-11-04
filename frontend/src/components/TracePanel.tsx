import type { ReactNode } from "react";
import type { Final, Step } from "../lib/api";

export type Trace = {
  plan: Step[];
  workers: Record<number, { tools: string[]; notes?: string; done: boolean }>;
  critiques: { verdict: string; issues: string[] }[];
  drafts: number;
  final?: Final;
  error?: string;
};
export const emptyTrace: Trace = { plan: [], workers: {}, critiques: [], drafts: 0 };

const Box = ({ title, children }: { title: string; children: ReactNode }) => (
  <section className="space-y-1">
    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
    {children}
  </section>
);

export default function TracePanel({ trace, busy }: { trace: Trace; busy: boolean }) {
  const idle = !busy && !trace.plan.length && !trace.error && !trace.final;
  return (
    <div className="space-y-5 p-4 text-sm">
      <h2 className="font-semibold">Agent trace</h2>
      {idle && <p className="text-slate-500">Ask a question to see the plan, the tool calls and the critic verdict live.</p>}
      {trace.plan.length > 0 && (
        <Box title="1. Plan">
          {trace.plan.map((s) => {
            const w = trace.workers[s.id];
            return (
              <div key={s.id} className="rounded bg-slate-900 p-2">
                <div>
                  {w?.done ? "✔" : w ? "…" : "○"} {s.worker} · <b>{s.ticker}</b>
                </div>
                <div className="text-xs text-slate-400">{s.goal}</div>
                {w?.tools.map((t, i) => (
                  <div key={i} className="font-mono text-xs text-emerald-400">
                    {t}
                  </div>
                ))}
                {w?.notes && <div className="mt-1 text-xs text-slate-300">{w.notes}</div>}
              </div>
            );
          })}
        </Box>
      )}
      {trace.drafts > 0 && (
        <Box title="2. Writer and critic">
          <div className="text-xs text-slate-400">Drafts written: {trace.drafts}</div>
          {trace.critiques.map((c, i) => (
            <div key={i} className={`rounded p-2 ${c.verdict === "pass" ? "bg-emerald-950" : "bg-amber-950"}`}>
              Critic: <b>{c.verdict}</b>
              {c.issues.map((x, j) => (
                <div key={j} className="text-xs text-slate-300">
                  • {x}
                </div>
              ))}
            </div>
          ))}
        </Box>
      )}
      {trace.final && (
        <Box title="3. Result">
          <div className="text-xs text-slate-300">
            {trace.final.revisions} revision(s) · {trace.final.llm_calls} LLM calls · {(trace.final.elapsed_ms / 1000).toFixed(1)} s
            <br />
            Answered by: {trace.final.models_used.join(", ") || "-"} ({trace.final.models_skipped} skipped)
          </div>
          {trace.final.saved.summary && <div className="text-xs text-slate-400">Memory saved: {trace.final.saved.summary}</div>}
        </Box>
      )}
      {trace.error && <div className="rounded bg-red-950 p-2 text-red-200">{trace.error}</div>}
    </div>
  );
}
