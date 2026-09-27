import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, api, type Txn, type TxnDraft, type TxnResult } from "../api";
import { money, price } from "../format";

const TYPES = ["BUY", "SELL", "DIVIDEND", "SPLIT", "FEE"] as const;
const SOURCE_LABEL: Record<string, string> = { ui: "You (web)", cli: "You (CLI)", mcp: "Agent", import: "Import" };

const empty = { type: "BUY", symbol: "", qty: "", price: "", fee: "", amount: "", date: "", note: "" };

export function Transactions({ portfolio }: { portfolio: string }) {
  const [txns, setTxns] = useState<Txn[] | null>(null);
  const [filter, setFilter] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  const [form, setForm] = useState(empty);
  const [preview, setPreview] = useState<TxnResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [key, setKey] = useState(() => crypto.randomUUID());

  const load = useCallback(() => api.transactions(portfolio, showDeleted).then(setTxns, (e: ApiError) => setError(e.message)),
    [portfolio, showDeleted]);
  useEffect(() => { load(); }, [load]);

  const cash = form.type === "DIVIDEND" || form.type === "FEE";
  const draft = (dryRun: boolean): TxnDraft => ({
    type: form.type, symbol: form.symbol.trim(), note: form.note || undefined, date: form.date || undefined,
    qty: cash ? 0 : Number(form.qty || 0), price: cash || form.type === "SPLIT" ? 0 : Number(form.price || 0),
    fee: Number(form.fee || 0), amount: cash ? Number(form.amount || 0) : 0,
    idempotency_key: key, dry_run: dryRun,
  });

  const submit = async (dryRun: boolean) => {
    setError(null);
    try {
      const r = await api.addTransaction(portfolio, draft(dryRun));
      if (dryRun) {
        setPreview(r);
      } else {
        setPreview(null);
        setForm(empty);
        setKey(crypto.randomUUID()); // next entry gets a new idempotency key
        load();
      }
    } catch (e) {
      setPreview(null);
      const err = e as ApiError;
      setError(`${err.message}${err.hint ? ` — ${err.hint}` : ""}`);
    }
  };

  const remove = async (t: Txn) => {
    setError(null);
    try {
      await api.deleteTransaction(t.id, true); // checks that later trades don't depend on it
      if (!window.confirm(`Delete ${t.type} ${t.qty || ""} ${t.symbol} on ${t.ts.slice(0, 10)}? It stays in the audit log.`)) return;
      await api.deleteTransaction(t.id, false);
      load();
    } catch (e) {
      setError((e as ApiError).message);
    }
  };

  const rows = useMemo(() => {
    const f = filter.trim().toUpperCase();
    return (txns ?? []).filter((t) => !f || t.symbol.includes(f)).reverse(); // newest first
  }, [txns, filter]);

  const set = (k: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm({ ...form, [k]: e.target.value });
    setPreview(null);
  };

  return (
    <div className="stack">
      <section className="card">
        <h2>Record a transaction <span className="muted small">· this records a trade you made; it never places an order</span></h2>
        <form className="row" onSubmit={(e) => { e.preventDefault(); submit(true); }}>
          <select value={form.type} onChange={set("type")} aria-label="Type">{TYPES.map((t) => <option key={t}>{t}</option>)}</select>
          <input className="input" placeholder="Symbol" value={form.symbol} onChange={set("symbol")} aria-label="Symbol" required style={{ maxWidth: 110 }} />
          {!cash && <input className="input" type="number" step="any" min="0" placeholder={form.type === "SPLIT" ? "Ratio (e.g. 4)" : "Shares"}
                           value={form.qty} onChange={set("qty")} aria-label="Quantity" required style={{ maxWidth: 130 }} />}
          {!cash && form.type !== "SPLIT" && <input className="input" type="number" step="any" min="0" placeholder="Price"
                           value={form.price} onChange={set("price")} aria-label="Price" required style={{ maxWidth: 120 }} />}
          {cash && <input className="input" type="number" step="any" min="0" placeholder="Amount $" value={form.amount}
                          onChange={set("amount")} aria-label="Amount" required style={{ maxWidth: 130 }} />}
          {(form.type === "BUY" || form.type === "SELL") && <input className="input" type="number" step="any" min="0" placeholder="Fee"
                          value={form.fee} onChange={set("fee")} aria-label="Fee" style={{ maxWidth: 90 }} />}
          <input className="input" type="date" value={form.date} onChange={set("date")} aria-label="Date (default now)" style={{ maxWidth: 160 }} />
          <input className="input" placeholder="Note" value={form.note} onChange={set("note")} aria-label="Note" />
          <button className="btn">Preview</button>
        </form>
        {preview && (
          <div className="preview">
            {preview.positions.map(({ before: b, after: a }) => (
              <div key={a.symbol} className="num">
                <strong>{a.symbol}</strong>: {b.qty} → {a.qty} shares · avg cost {price(b.avg_cost)} → {price(a.avg_cost)}
                {a.realized_pnl !== b.realized_pnl && <> · realized {money(a.realized_pnl - b.realized_pnl, { signed: true })}</>}
              </div>
            ))}
            <div className="row" style={{ marginTop: 8 }}>
              <button className="btn primary" onClick={() => submit(false)}>Save</button>
              <button className="btn ghost" onClick={() => setPreview(null)}>Cancel</button>
            </div>
          </div>
        )}
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      </section>

      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Trade log {txns ? <span className="muted">· {rows.length}</span> : null}</h2>
          <div className="row">
            <input className="input" placeholder="Filter symbol" value={filter} onChange={(e) => setFilter(e.target.value)}
                   aria-label="Filter by symbol" style={{ maxWidth: 140 }} />
            <label className="small text-2 row" style={{ gap: 4 }}>
              <input type="checkbox" checked={showDeleted} onChange={(e) => setShowDeleted(e.target.checked)} /> deleted
            </label>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Type</th><th>Symbol</th><th>Shares</th><th>Price</th><th>Fee / amount</th><th>By</th><th>Note</th><th aria-label="Delete" /></tr></thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} style={{ cursor: "default", opacity: t.deleted ? 0.45 : 1, textDecoration: t.deleted ? "line-through" : undefined }}>
                  <td>{t.ts.slice(0, 10)}</td>
                  <td>{t.type === "OPENING" ? "Opening" : t.type}</td>
                  <td><span className="sym">{t.symbol}</span></td>
                  <td>{t.qty || ""}</td>
                  <td>{t.price ? price(t.price) : ""}</td>
                  <td>{t.amount ? money(t.amount) : t.fee ? money(t.fee) : ""}</td>
                  <td><span className={`tag ${t.source === "mcp" ? "agent" : ""}`}>{SOURCE_LABEL[t.source] ?? t.source}</span></td>
                  <td style={{ textAlign: "left", whiteSpace: "normal" }} className="text-2 small">{t.note ?? ""}</td>
                  <td>{!t.deleted && <button className="btn ghost" title="Delete" onClick={() => remove(t)}>×</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
