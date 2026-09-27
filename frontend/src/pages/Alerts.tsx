import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type AlertRule, type FiredAlert, type StreamUpdate } from "../api";

type Kinds = Record<string, { label: string; unit: string }>;

export function AlertForm({ kinds, symbol, onCreated }: { kinds: Kinds; symbol?: string; onCreated: () => void }) {
  const [form, setForm] = useState({ symbol: symbol ?? "", kind: "day_move_pct", threshold: "", note: "" });
  const [error, setError] = useState<string | null>(null);
  const unit = kinds[form.kind]?.unit ?? "";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createAlert({ symbol: form.symbol, kind: form.kind, threshold: Number(form.threshold), note: form.note || undefined });
      setForm({ ...form, threshold: "", note: "" });
      onCreated();
    } catch (err) {
      const e2 = err as ApiError;
      setError(`${e2.message}${e2.hint ? ` — ${e2.hint}` : ""}`);
    }
  };

  return (
    <>
      <form className="row" onSubmit={submit}>
        {!symbol && <input className="input" placeholder="Symbol" value={form.symbol} required style={{ maxWidth: 110 }}
                           onChange={(e) => setForm({ ...form, symbol: e.target.value })} aria-label="Symbol" />}
        <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })} aria-label="Rule">
          {Object.entries(kinds).map(([k, v]) => <option key={k} value={k}>{v.label.replace("{t}", "…")}</option>)}
        </select>
        <input className="input" type="number" step="any" min="0" required value={form.threshold} style={{ maxWidth: 110 }}
               placeholder={unit === "$" ? "Price $" : unit === "%" ? "Percent" : unit === "x" ? "P/E" : "Days"}
               onChange={(e) => setForm({ ...form, threshold: e.target.value })} aria-label="Threshold" />
        <input className="input" placeholder="Note (optional)" value={form.note}
               onChange={(e) => setForm({ ...form, note: e.target.value })} aria-label="Note" />
        <button className="btn primary">Add alert</button>
      </form>
      {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
    </>
  );
}

export function AlertList({ alerts, onToggle, showSymbol = true }: { alerts: AlertRule[]; onToggle: (a: AlertRule) => void; showSymbol?: boolean }) {
  if (!alerts.length) return <p className="muted">No alerts.</p>;
  return (
    <div className="table-wrap">
      <table>
        <tbody>
          {alerts.map((a) => (
            <tr key={a.id} style={{ cursor: "default", opacity: a.active ? 1 : 0.5 }}>
              {showSymbol && <td><Link to={`/t/${a.symbol}`} className="sym">{a.symbol}</Link></td>}
              <td style={{ textAlign: "left" }}>{a.label}{a.note ? <span className="muted"> · {a.note}</span> : null}</td>
              <td className="small text-2">{a.last_fired ? `last fired ${a.last_fired.session_date}` : "not fired yet"}</td>
              <td><span className={`tag ${a.created_by === "mcp" ? "agent" : ""}`}>{a.created_by === "mcp" ? "Agent" : "You"}</span></td>
              <td><button className="btn ghost" onClick={() => onToggle(a)}>{a.active ? "Turn off" : "Turn on"}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Alerts({ live }: { live: StreamUpdate | null }) {
  const [data, setData] = useState<{ alerts: AlertRule[]; fired: FiredAlert[]; kinds: Kinds } | null>(null);
  const load = useCallback(() => api.alerts(true).then(setData, () => undefined), []);
  useEffect(() => { load(); }, [load]);
  // Reload when the hub reports newly fired alerts.
  const firedCount = live?.alerts_fired?.length ?? 0;
  useEffect(() => { if (firedCount) load(); }, [firedCount, load]);

  if (!data) return <p className="muted">Loading…</p>;
  const toggle = (a: AlertRule) => api.toggleAlert(a.id, !a.active).then(load);

  return (
    <div className="stack">
      <section className="card">
        <h2>New alert <span className="muted small">· fires at most once per trading session; shown here, on the dashboard and in the daily brief</span></h2>
        <AlertForm kinds={data.kinds} onCreated={load} />
      </section>
      <section className="card">
        <h2>Fired since the last session</h2>
        {data.fired.length === 0 ? <p className="muted">None.</p> : (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {data.fired.map((f) => <li key={`${f.alert_id}-${f.session_date}`}>{f.message}{f.note ? <span className="muted"> · {f.note}</span> : null}</li>)}
          </ul>
        )}
      </section>
      <section className="card">
        <h2>Rules <span className="muted">· {data.alerts.length}</span></h2>
        <AlertList alerts={data.alerts} onToggle={toggle} />
      </section>
    </div>
  );
}
