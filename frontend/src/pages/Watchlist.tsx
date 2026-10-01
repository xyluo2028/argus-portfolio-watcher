import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api, type StreamUpdate, type WatchItem } from "../api";
import { TickerInput } from "../components/TickerInput";
import { big, pct, price, ratio, tone } from "../format";

const pctCell = (v: number | null | undefined) => (v == null ? "–" : `${v.toFixed(1)}%`);

export function Watchlist({ live }: { live: StreamUpdate | null }) {
  const [items, setItems] = useState<WatchItem[] | null>(null);
  const [input, setInput] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const load = useCallback(() => api.watchlist().then((w) => setItems(w.items), (e: ApiError) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const symbols = input.split(/[\s,]+/).filter(Boolean);
    if (!symbols.length) return;
    setBusy(true);
    setError(null);
    try {
      await api.watchAdd(symbols, note || undefined);
      setInput("");
      setNote("");
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (symbol: string) => {
    await api.watchRemove(symbol).catch((e: ApiError) => setError(e.message));
    load();
  };

  return (
    <div className="stack">
      <section className="card">
        <h2>Add to watchlist</h2>
        <form className="row" onSubmit={add}>
          <TickerInput placeholder="Tickers or company, e.g. TSLA, COST" value={input} onChange={setInput}
                       aria-label="Tickers" />
          <input className="input" placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)}
                 aria-label="Note" style={{ flex: 2 }} />
          <button className="btn primary" disabled={busy}>{busy ? "Adding…" : "Add"}</button>
        </form>
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      </section>

      <section className="card">
        <h2>Watchlist {items ? <span className="muted">· {items.length}</span> : null}</h2>
        {!items ? <p className="muted">Loading…</p> : items.length === 0 ? (
          <p className="muted">Nothing yet. Add tickers above, or ask Claude: “add TSLA to my Argus watchlist”.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th><th>Price</th><th>Day %</th><th>Mkt cap</th><th>P/E</th><th>Fwd P/E</th><th>P/S</th>
                  <th>Rev growth</th><th>Net margin</th><th>Note</th><th aria-label="Remove" />
                </tr>
              </thead>
              <tbody>
                {items.map((i) => {
                  const q = live?.quotes[i.symbol] ?? i.quote;
                  const m = i.metrics ?? {};
                  return (
                    <tr key={i.symbol} onClick={() => navigate(`/t/${i.symbol}`)}>
                      <td><span className="sym">{i.symbol}</span></td>
                      <td>{price(q?.price)}</td>
                      <td className={tone(q?.change_pct)}>{pct(q?.change_pct)}</td>
                      <td>{big(m.market_cap)}</td>
                      <td>{ratio(m.pe_ttm, 1)}</td>
                      <td>{ratio(m.pe_forward, 1)}</td>
                      <td>{ratio(m.ps_ttm, 1)}</td>
                      <td className={tone(m.revenue_growth_yoy_pct)}>{pct(m.revenue_growth_yoy_pct, 1)}</td>
                      <td>{pctCell(m.net_margin_pct)}</td>
                      <td style={{ textAlign: "left", whiteSpace: "normal" }} className="text-2">{i.note ?? ""}</td>
                      <td>
                        <button className="btn ghost" title={`Remove ${i.symbol}`}
                                onClick={(e) => { e.stopPropagation(); remove(i.symbol); }}>×</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
