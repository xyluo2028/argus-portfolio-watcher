import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type Peers } from "../api";
import { big, pct, price, ratio, tone } from "../format";
import { TickerInput } from "./TickerInput";

type Cell = number | string | null | undefined;
const num = (v: Cell) => (typeof v === "number" ? v : null);
const pctPlain = (v: Cell) => (typeof v === "number" ? `${v.toFixed(1)}%` : "–");

/** The symbol next to its peers: yours if you've edited the list, otherwise Finnhub's suggestions. */
export function PeersCard({ symbol }: { symbol: string }) {
  const [data, setData] = useState<Peers | null>(null);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setData(null);
    setError(null);
    api.peers(symbol).then(setData, (e: ApiError) => setError(e.message));
  }, [symbol]);

  const save = useCallback(async (peers: string[] | null) => {
    setBusy(true);
    setError(null);
    try {
      setData(await api.setPeers(symbol, peers));
      setInput("");
    } catch (e) {
      const err = e as ApiError;
      setError(`${err.message}${err.hint ? ` — ${err.hint}` : ""}`);
    } finally {
      setBusy(false);
    }
  }, [symbol]);

  const add = (e: React.FormEvent) => {
    e.preventDefault();
    const more = input.split(/[\s,]+/).filter(Boolean).map((s) => s.toUpperCase());
    if (data && more.length) save([...data.peers, ...more]);
  };

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Peers</h2>
        {data && (data.custom
          ? <button className="btn ghost small" disabled={busy} onClick={() => save(null)}>Reset to suggestions</button>
          : <span className="small muted">Suggested by Finnhub (same sub-industry) · edit to make it yours</span>)}
      </div>

      {!data ? (error ? null : <p className="muted">Loading…</p>) : (
        <>
          {data.rows.length <= 1 ? (
            <p className="muted">
              {data.custom ? "No peers in your list." : "No US-listed peers suggested (Finnhub lists home-market peers for non-US companies)."} Add some below.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr>
                  <th>Symbol</th><th>Price</th><th>Day %</th><th>Mkt cap</th><th>Fwd P/E</th><th>P/S</th>
                  <th>Rev growth</th><th>Net margin</th><th aria-label="Remove" />
                </tr></thead>
                <tbody>
                  {data.rows.map((r) => {
                    const sym = String(r.symbol);
                    const self = sym === data.symbol;
                    return (
                      <tr key={sym} style={{ cursor: "default", fontWeight: self ? 600 : undefined }} className={self ? "self" : undefined}>
                        <td>{self ? sym : <Link to={`/t/${sym}`}>{sym}</Link>}</td>
                        <td>{price(num(r.price))}</td>
                        <td className={tone(num(r.change_pct))}>{pct(num(r.change_pct))}</td>
                        <td>{big(num(r.market_cap))}</td>
                        <td>{ratio(num(r.pe_forward), 1)}</td>
                        <td>{ratio(num(r.ps_ttm), 1)}</td>
                        <td className={tone(num(r.revenue_growth_yoy_pct))}>{pct(num(r.revenue_growth_yoy_pct), 1)}</td>
                        <td>{pctPlain(r.net_margin_pct)}</td>
                        <td style={{ textAlign: "right" }}>
                          {!self && <button className="btn ghost" disabled={busy} aria-label={`Remove ${sym}`}
                                            onClick={() => save(data.peers.filter((p) => p !== sym))}>×</button>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <form className="row" style={{ marginTop: 10 }} onSubmit={add}>
            <TickerInput value={input} onChange={setInput} placeholder="Add a peer, e.g. LITE" aria-label="Add peer" />
            <button className="btn" disabled={busy || !input.trim()}>Add</button>
          </form>
        </>
      )}
      {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
    </section>
  );
}
