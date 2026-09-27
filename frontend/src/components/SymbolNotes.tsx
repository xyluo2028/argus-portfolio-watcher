import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type AlertRule, type NoteItem } from "../api";
import { AlertForm, AlertList } from "../pages/Alerts";

/** Thesis, notes and alerts for one symbol (ticker page). */
export function SymbolNotes({ symbol }: { symbol: string }) {
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [alerts, setAlerts] = useState<AlertRule[]>([]);
  const [kinds, setKinds] = useState<Record<string, { label: string; unit: string }>>({});
  const [draft, setDraft] = useState({ text: "", kind: "thesis" as "thesis" | "note", review_on: "" });
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.notes(symbol).then(setNotes, () => undefined);
    api.alerts(true).then((d) => { setAlerts(d.alerts.filter((a) => a.symbol === symbol)); setKinds(d.kinds); }, () => undefined);
  }, [symbol]);
  useEffect(() => { load(); }, [load]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.addNote({ symbol, text: draft.text, kind: draft.kind, review_on: draft.review_on || undefined });
      setDraft({ text: "", kind: "note", review_on: "" });
      load();
    } catch (err) {
      setError((err as ApiError).message);
    }
  };

  const hasThesis = notes.some((n) => n.kind === "thesis");
  return (
    <section className="grid-2">
      <div className="card">
        <h2>Thesis &amp; notes</h2>
        {notes.map((n) => (
          <div key={n.id} style={{ borderLeft: `3px solid ${n.kind === "thesis" ? "var(--series-1)" : "var(--axis)"}`, padding: "2px 10px", marginBottom: 10 }}>
            <div className="small muted">
              {n.kind === "thesis" ? "Thesis" : "Note"} · {n.created_at.slice(0, 10)}{n.created_by === "mcp" ? " · by agent" : ""}
              {n.review_on && <> · review {n.review_on}</>}
              <button className="btn ghost small" onClick={() => api.updateNote(n.id, { archived: true }).then(load)}>archive</button>
            </div>
            <div style={{ whiteSpace: "pre-wrap" }}>{n.text}</div>
          </div>
        ))}
        <form className="stack" style={{ gap: 8 }} onSubmit={save}>
          <textarea className="input" rows={3} required value={draft.text} aria-label="Note text"
                    placeholder={hasThesis ? "Add a note…" : "Why do you own it? What would change your mind?"}
                    onChange={(e) => setDraft({ ...draft, text: e.target.value })} />
          <div className="row">
            <select value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as "thesis" | "note" })} aria-label="Kind">
              <option value="thesis">Thesis</option><option value="note">Note</option>
            </select>
            <label className="small text-2 row" style={{ gap: 6 }}>Review on
              <input className="input" type="date" value={draft.review_on} onChange={(e) => setDraft({ ...draft, review_on: e.target.value })} />
            </label>
            <button className="btn primary">Save</button>
          </div>
        </form>
        {error && <div className="error" style={{ marginTop: 8 }}>{error}</div>}
      </div>
      <div className="card">
        <h2>Alerts</h2>
        <AlertList alerts={alerts} showSymbol={false} onToggle={(a) => api.toggleAlert(a.id, !a.active).then(load)} />
        {Object.keys(kinds).length > 0 && <div style={{ marginTop: 10 }}><AlertForm kinds={kinds} symbol={symbol} onCreated={load} /></div>}
      </div>
    </section>
  );
}
