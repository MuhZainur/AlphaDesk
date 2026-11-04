import { useEffect, useState } from "react";
import { clearMemory, getMemory, setRisk, type Memory } from "../lib/api";

export default function MemoryPanel({ refreshKey }: { refreshKey: number }) {
  const [mem, setMem] = useState<Memory | null>(null);
  useEffect(() => {
    getMemory().then(setMem).catch(() => setMem(null));
  }, [refreshKey]);
  if (!mem) return null;
  return (
    <div className="border-t border-slate-800 p-4 text-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Memory</h3>
        <button className="text-xs text-slate-500 hover:text-red-300" onClick={() => clearMemory().then(() => getMemory().then(setMem))}>
          Forget me
        </button>
      </div>
      <label className="flex items-center gap-2">
        Risk profile
        <select
          value={mem.risk_profile}
          onChange={(e) => setRisk(e.target.value).then(() => setMem({ ...mem, risk_profile: e.target.value }))}
          className="rounded bg-slate-900 px-2 py-1 ring-1 ring-slate-700"
        >
          <option value="conservative">conservative</option>
          <option value="balanced">balanced</option>
          <option value="aggressive">aggressive</option>
        </select>
      </label>
      <div className="mt-2 flex flex-wrap gap-1">
        {mem.watchlist.length ? (
          mem.watchlist.map((t) => (
            <span key={t} className="rounded bg-slate-800 px-2 py-0.5 text-xs">
              {t}
            </span>
          ))
        ) : (
          <span className="text-xs text-slate-500">Watchlist is empty.</span>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-600">Memory may reset when the free server restarts.</p>
    </div>
  );
}
