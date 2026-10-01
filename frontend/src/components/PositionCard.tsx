import { useCallback, useEffect, useState } from "react";
import { ALL, ApiError, api, type Position, type PositionPreview, type Txn } from "../api";
import { money, pct, price, tone } from "../format";

const TYPE_LABEL: Record<string, string> = { OPENING: "Opening", BUY: "Buy", SELL: "Sell", DIVIDEND: "Dividend", SPLIT: "Split", FEE: "Fee" };
const SHARE_TYPES = new Set(["OPENING", "BUY", "SELL"]);

const nyToday = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York" }).format(new Date());
const errText = (e: unknown) => {
  const err = e as ApiError;
  return `${err.message}${err.hint ? ` — ${err.hint}` : ""}`;
};

interface Props {
  symbol: string;
  portfolio: string;
  position: Position | null;
  lastPrice: number | null | undefined;
  onChanged: () => void;
}

/** "Your position": stats, a buy/sell form, and this symbol's transactions with edit and delete. */
export function PositionCard({ symbol, portfolio, position, lastPrice, onChanged }: Props) {
  const [txns, setTxns] = useState<Txn[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trading, setTrading] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);

  const load = useCallback(() => {
    api.transactions(portfolio, false, symbol).then(setTxns, (e) => setError(errText(e)));
  }, [portfolio, symbol]);
  useEffect(() => { setError(null); setTrading(false); setEditing(null); load(); }, [load]);

  const changed = () => { setTrading(false); setEditing(null); load(); onChanged(); };

  const remove = async (t: Txn) => {
    setError(null);
    try {
      await api.deleteTransaction(t.id, true); // refused if later trades depend on it
      if (!window.confirm(`Delete ${TYPE_LABEL[t.type] ?? t.type} ${t.qty} ${t.symbol} on ${t.ts.slice(0, 10)}? It stays in the audit log.`)) return;
      await api.deleteTransaction(t.id, false);
      changed();
    } catch (e) {
      setError(errText(e));
    }
  };

  const allView = portfolio === ALL;
  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Your position</h2>
        {!trading && <button className="btn primary" onClick={() => { setTrading(true); setEditing(null); }}>Buy / Sell</button>}
      </div>

      {position ? (
        <div className="stats" style={{ marginBottom: 12 }}>
          <div className="stat"><div className="k">Shares</div><div className="v">{position.qty}</div></div>
          <div className="stat"><div className="k">Avg cost</div><div className="v">{price(position.avg_cost)}</div></div>
          <div className="stat"><div className="k">Value</div><div className="v">{money(position.market_value)}</div></div>
          <div className="stat"><div className="k">Unrealized</div>
            <div className={`v ${tone(position.unrealized_pnl)}`}>{money(position.unrealized_pnl, { signed: true })} ({pct(position.unrealized_pct, 1)})</div></div>
        </div>
      ) : <p className="muted">Not held in {allView ? "any portfolio" : portfolio}.</p>}

      {trading && (
        <TradeForm symbol={symbol} portfolio={portfolio} held={position?.qty ?? 0} lastPrice={lastPrice}
                   onDone={changed} onCancel={() => setTrading(false)} />
      )}
      {error && <div className="error" style={{ margin: "10px 0" }}>{error}</div>}

      {txns && txns.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Date</th>{allView && <th>Portfolio</th>}<th>Type</th><th>Shares</th><th>Price</th><th aria-label="Actions" /></tr></thead>
            <tbody>
              {txns.map((t) => editing === t.id ? (
                <tr key={t.id} style={{ cursor: "default" }}>
                  <td colSpan={allView ? 6 : 5}>
                    <EditForm txn={t} onDone={changed} onCancel={() => setEditing(null)} />
                  </td>
                </tr>
              ) : (
                <tr key={t.id} style={{ cursor: "default" }}>
                  <td>{t.ts.slice(0, 10)}</td>
                  {allView && <td>{t.portfolio}</td>}
                  <td>{TYPE_LABEL[t.type] ?? t.type}</td>
                  <td>{SHARE_TYPES.has(t.type) ? t.qty : "–"}</td>
                  <td>{SHARE_TYPES.has(t.type) ? price(t.price) : money(t.amount)}</td>
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {SHARE_TYPES.has(t.type) && (
                      <button className="btn ghost" onClick={() => { setEditing(t.id); setTrading(false); }}>Edit</button>
                    )}
                    <button className="btn ghost" onClick={() => remove(t)} aria-label={`Delete transaction ${t.id}`}>×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Change({ before, after }: { before: PositionPreview; after: PositionPreview }) {
  return (
    <div className="preview small">
      Shares {before.qty} → <strong>{after.qty}</strong> · avg cost {price(before.avg_cost)} → <strong>{price(after.avg_cost)}</strong>
      {after.realized_pnl !== before.realized_pnl && <> · realized {money(after.realized_pnl, { signed: true })}</>}
    </div>
  );
}

function TradeForm({ symbol, portfolio, held, lastPrice, onDone, onCancel }: {
  symbol: string; portfolio: string; held: number; lastPrice: number | null | undefined;
  onDone: () => void; onCancel: () => void;
}) {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState("");
  const [px, setPx] = useState(lastPrice ? lastPrice.toFixed(2) : "");
  const [fee, setFee] = useState("");
  const [date, setDate] = useState(nyToday);
  const [target, setTarget] = useState(portfolio === ALL ? "" : portfolio);
  const [names, setNames] = useState<string[]>([]);
  const [preview, setPreview] = useState<{ before: PositionPreview; after: PositionPreview } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [key] = useState(() => crypto.randomUUID()); // retrying a save never doubles it

  useEffect(() => {
    if (portfolio === ALL) api.portfolios().then((ps) => setNames(ps.map((p) => p.name)), () => undefined);
  }, [portfolio]);
  useEffect(() => setPreview(null), [side, qty, px, fee, date, target]);

  const submit = async (dryRun: boolean) => {
    setError(null);
    if (!target) return setError("Pick a portfolio.");
    try {
      const r = await api.addTransaction(target, {
        type: side, symbol, qty: Number(qty), price: Number(px), fee: Number(fee || 0), date,
        idempotency_key: key, dry_run: dryRun,
      });
      if (dryRun) setPreview(r.positions[0] ?? null);
      else onDone();
    } catch (e) {
      setPreview(null);
      setError(errText(e));
    }
  };

  const valid = Number(qty) > 0 && Number(px) > 0 && !!date && !!target;
  return (
    <form className="trade" onSubmit={(e) => { e.preventDefault(); if (valid) submit(!preview); }}>
      <div className="row">
        <div className="seg" role="group" aria-label="Side">
          {(["BUY", "SELL"] as const).map((s) => (
            <button type="button" key={s} aria-pressed={side === s} onClick={() => setSide(s)}
                    disabled={s === "SELL" && held <= 0 && portfolio !== ALL}>{s === "BUY" ? "Buy" : "Sell"}</button>
          ))}
        </div>
        {portfolio === ALL && (
          <select value={target} onChange={(e) => setTarget(e.target.value)} aria-label="Portfolio">
            <option value="">Portfolio…</option>
            {names.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        )}
      </div>
      <div className="row">
        <label className="field">Shares<input className="input" type="number" min="0" step="any" value={qty} onChange={(e) => setQty(e.target.value)} /></label>
        <label className="field">Price<input className="input" type="number" min="0" step="any" value={px} onChange={(e) => setPx(e.target.value)} /></label>
        <label className="field">Fee<input className="input" type="number" min="0" step="any" value={fee} placeholder="0" onChange={(e) => setFee(e.target.value)} /></label>
        <label className="field">Date<input className="input" type="date" value={date} max={nyToday()} onChange={(e) => setDate(e.target.value)} /></label>
      </div>
      {side === "SELL" && held > 0 && portfolio !== ALL && (
        <p className="small muted" style={{ margin: 0 }}>
          You hold {held}. <button type="button" className="btn ghost" onClick={() => setQty(String(held))}>Sell all</button>
        </p>
      )}
      {preview && <Change {...preview} />}
      {error && <div className="error">{error}</div>}
      <div className="row">
        <span className="small muted">
          {valid ? `${side === "BUY" ? "Buy" : "Sell"} ${qty} × ${price(Number(px))} = ${money(Number(qty) * Number(px))}` : "Records a trade you made at your broker."}
        </span>
        <div className="spacer" />
        <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
        {preview
          ? <button className="btn primary" disabled={!valid}>Confirm {side === "BUY" ? "buy" : "sell"}</button>
          : <button className="btn" disabled={!valid}>Preview</button>}
      </div>
    </form>
  );
}

function EditForm({ txn, onDone, onCancel }: { txn: Txn; onDone: () => void; onCancel: () => void }) {
  const [qty, setQty] = useState(String(txn.qty));
  const [px, setPx] = useState(String(txn.price));
  const [fee, setFee] = useState(String(txn.fee || ""));
  const [date, setDate] = useState(txn.ts.slice(0, 10));
  const [preview, setPreview] = useState<{ before: PositionPreview; after: PositionPreview } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setPreview(null), [qty, px, fee, date]);

  const submit = async (dryRun: boolean) => {
    setError(null);
    try {
      const r = await api.editTransaction(txn.id, {
        qty: Number(qty), price: Number(px), fee: Number(fee || 0),
        date: date !== txn.ts.slice(0, 10) ? date : undefined, // unchanged keeps the original time
        dry_run: dryRun,
      });
      if (dryRun) setPreview(r.position);
      else onDone();
    } catch (e) {
      setPreview(null);
      setError(errText(e));
    }
  };

  const valid = Number(qty) > 0 && Number(px) >= 0 && !!date;
  return (
    <form className="trade" onSubmit={(e) => { e.preventDefault(); if (valid) submit(!preview); }}>
      <div className="small muted">Edit {TYPE_LABEL[txn.type] ?? txn.type} #{txn.id}</div>
      <div className="row">
        <label className="field">Shares<input className="input" type="number" min="0" step="any" value={qty} onChange={(e) => setQty(e.target.value)} /></label>
        <label className="field">Price<input className="input" type="number" min="0" step="any" value={px} onChange={(e) => setPx(e.target.value)} /></label>
        <label className="field">Fee<input className="input" type="number" min="0" step="any" value={fee} placeholder="0" onChange={(e) => setFee(e.target.value)} /></label>
        <label className="field">Date<input className="input" type="date" value={date} max={nyToday()} onChange={(e) => setDate(e.target.value)} /></label>
      </div>
      {preview && <Change {...preview} />}
      {error && <div className="error">{error}</div>}
      <div className="row">
        <div className="spacer" />
        <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
        {preview ? <button className="btn primary" disabled={!valid}>Save</button>
          : <button className="btn" disabled={!valid}>Preview</button>}
      </div>
    </form>
  );
}
