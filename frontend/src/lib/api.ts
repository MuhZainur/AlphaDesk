export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export type Step = { id: number; worker: string; ticker: string; goal: string };
export type Memory = { risk_profile: string; watchlist: string[]; recent_summaries?: { summary: string; tickers: string[] }[] };
export type Final = {
  text: string;
  revisions: number;
  llm_calls: number;
  models_used: string[];
  models_skipped: number;
  elapsed_ms: number;
  saved: { summary?: string; watchlist_added?: string[] };
};
export type Event =
  | { type: "memory"; data: { risk_profile: string; watchlist: string[]; summaries_used: number } }
  | { type: "plan"; data: { steps: Step[] } }
  | { type: "worker_start"; data: { step_id: number; worker: string; ticker: string } }
  | { type: "tool_call"; data: { step_id: number; tool: string; args: Record<string, unknown> } }
  | { type: "worker_done"; data: { step_id: number; notes: string } }
  | { type: "draft"; data: { revision: number; text: string } }
  | { type: "critique"; data: { verdict: "pass" | "revise"; issues: string[] } }
  | { type: "final"; data: Final }
  | { type: "error"; data: { code: string; message: string } };

const uid = () => crypto.randomUUID();

function stored(key: string): string {
  try {
    let v = localStorage.getItem(key);
    if (!v) localStorage.setItem(key, (v = uid()));
    return v;
  } catch {
    return uid(); // storage blocked: the id lasts only for this page load
  }
}
export const userId = stored("alphadesk_user");
export const newThread = uid;

export async function waitForServer(onWaking: () => void): Promise<void> {
  for (;;) {
    try {
      const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) });
      if (r.ok) return;
    } catch {
      /* cold start or offline */
    }
    onWaking();
    await new Promise((r) => setTimeout(r, 5000));
  }
}

export async function streamChat(threadId: string, message: string, onEvent: (e: Event) => void): Promise<void> {
  const res = await fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, thread_id: threadId, message }),
  });
  if (res.status === 429)
    return onEvent({ type: "error", data: { code: "rate_limited", message: "Too many requests from your network. Please try again later." } });
  if (!res.ok || !res.body) return onEvent({ type: "error", data: { code: "bad_request", message: "The server rejected the request." } });
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i);
      buf = buf.slice(i + 2);
      const type = /^event: (.+)$/m.exec(block)?.[1];
      const data = /^data: (.+)$/m.exec(block)?.[1];
      if (type && data) onEvent({ type, data: JSON.parse(data) } as Event);
    }
  }
}

export const getMemory = (): Promise<Memory> => fetch(`${API}/memory/${userId}`).then((r) => r.json());
export const setRisk = (risk_profile: string) =>
  fetch(`${API}/memory/${userId}/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ risk_profile }),
  });
export const clearMemory = () => fetch(`${API}/memory/${userId}`, { method: "DELETE" });
