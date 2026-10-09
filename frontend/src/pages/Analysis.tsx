import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { DividendsCard } from "../components/DividendsCard";
import { RiskCard } from "../components/RiskCard";
import { ALL, ApiError, api, type Drift, type Exposure, type SimResult, type SimTrade } from "../api";
import { BarList, topN } from "../components/BarList";
import { money, tone } from "../format";

function ExposureSection({ portfolio }: { portfolio: string }) {
  const [e, setE] = useState<Exposure | null>(null);
  const [look, setLook] = useState(true);
  useEffect(() => { setE(null); api.exposure(portfolio).then(setE, () => undefined); }, [portfolio]);
  if (!e) return <section className="card"><p className="muted">Loading exposure…</p></section>;
  const c = e.concentration;
  const sectors = look ? e.by_sector_lookthrough : e.by_sector_direct;
  return (
    <>
      <section className="tiles" aria-label="Concentration">
        <div className="tile"><div className="label">Largest position</div><div className="value">{c.top1_pct.toFixed(1)}%</div></div>
        <div className="tile"><div className="label">Top 5 positions</div><div className="value">{c.top5_pct.toFixed(1)}%</div></div>
        <div className="tile"><div className="label">Effective positions</div><div className="value">{c.effective_positions.toFixed(1)}</div>
          <div className="delta muted">of {c.positions} held (1 / HHI)</div></div>
        <div className="tile"><div className="label">Stocks / ETFs</div>
          <div className="value">{e.by_type.map((t) => `${t.weight_pct.toFixed(0)}%`).join(" / ")}</div>
          <div className="delta muted">{e.by_type.map((t) => t.key).join(" / ")}</div></div>
      </section>
      <section className="grid-2">
        <div className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>Sectors</h2>
            <div className="seg">
              <button aria-pressed={look} onClick={() => setLook(true)}>Look-through</button>
              <button aria-pressed={!look} onClick={() => setLook(false)}>Direct</button>
            </div>
          </div>
          <BarList items={topN(sectors.map((r) => [r.key, r.value] as [string, number]), 10)} total={e.total_value} />
          <p className="small muted">{look ? "ETFs split by their own sector weights." : "ETFs counted as one bucket."}</p>
        </div>
        <div className="card">
          <h2>Single-stock exposure <span className="muted small">· incl. via ETF top holdings</span></h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Stock</th><th>Direct</th><th>Via ETFs</th><th>Total</th></tr></thead>
              <tbody>
                {e.top_stock_exposure.slice(0, 10).map((s) => (
                  <tr key={s.symbol} style={{ cursor: "default" }}>
                    <td><Link to={`/t/${s.symbol}`} className="sym">{s.symbol}</Link>{s.via.length ? <span className="name">via {s.via.join(", ")}</span> : null}</td>
                    <td>{money(s.direct, { whole: true })}</td><td>{money(s.via_etfs, { whole: true })}</td>
                    <td>{s.total_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted">Indirect amounts only count each ETF's published top holdings, so they're a lower bound.</p>
        </div>
      </section>
    </>
  );
}

function DriftSection({ portfolio }: { portfolio: string }) {
  const [level, setLevel] = useState<"symbol" | "sector">("sector");
  const [drift, setDrift] = useState<Drift | null>(null);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => api.drift(portfolio, level).then((d) => {
    setDrift(d);
    setEdit(Object.fromEntries(d.rows.map((r) => [r.key, r.target_pct == null ? "" : String(r.target_pct)])));
  }, () => undefined), [portfolio, level]);
  useEffect(() => { setMsg(null); load(); }, [load]);

  const weights = () => Object.fromEntries(Object.entries(edit).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)]));
  const apply = async (dryRun: boolean) => {
    try {
      const d = await api.setTargets(portfolio, level, weights(), dryRun);
      setDrift(d);
      setMsg(dryRun ? "Preview — not saved." : "Targets saved.");
    } catch (e) {
      setMsg((e as ApiError).message);
    }
  };
  const sum = Object.values(weights()).reduce((a, b) => a + b, 0);

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Targets &amp; drift <span className="muted small">· band ±{drift?.tolerance_pp ?? 2} pp</span></h2>
        <div className="seg">
          <button aria-pressed={level === "sector"} onClick={() => setLevel("sector")}>By sector</button>
          <button aria-pressed={level === "symbol"} onClick={() => setLevel("symbol")}>By position</button>
        </div>
      </div>
      {!drift ? <p className="muted">Loading…</p> : (
        <>
          <div className="table-wrap" style={{ maxHeight: 420, overflowY: "auto" }}>
            <table>
              <thead><tr><th>{level === "sector" ? "Sector" : "Position"}</th><th>Now</th><th>Target %</th><th>Drift</th><th>Trade to target</th></tr></thead>
              <tbody>
                {drift.rows.map((r) => (
                  <tr key={r.key} style={{ cursor: "default" }}>
                    <td>{r.key}</td>
                    <td>{r.weight_pct.toFixed(1)}%</td>
                    <td><input className="input" type="number" step="any" min="0" max="100" style={{ width: 80, minWidth: 0, textAlign: "right" }}
                               value={edit[r.key] ?? ""} aria-label={`Target for ${r.key}`}
                               onChange={(e) => setEdit({ ...edit, [r.key]: e.target.value })} /></td>
                    <td className={r.outside_band ? tone(-(r.drift_pp ?? 0)) : "muted"}>
                      {r.drift_pp == null ? "–" : `${r.drift_pp > 0 ? "+" : r.drift_pp < 0 ? "−" : ""}${Math.abs(r.drift_pp).toFixed(1)} pp`}{r.outside_band ? " ⚑" : ""}
                    </td>
                    <td>{r.trade_to_target == null ? "–" : `${r.trade_to_target >= 0 ? "Buy" : "Sell"} ${money(Math.abs(r.trade_to_target), { whole: true })}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row" style={{ marginTop: 10 }}>
            <span className={`small ${Math.abs(sum - 100) > 0.5 && sum > 0 ? "down" : "text-2"}`}>Targets sum to {sum.toFixed(1)}%</span>
            <div className="spacer" />
            <button className="btn" onClick={() => apply(true)}>Preview</button>
            <button className="btn primary" onClick={() => apply(false)}>Save targets</button>
          </div>
          {msg && <p className="small text-2">{msg} {drift.warnings.join(" ")}</p>}
        </>
      )}
    </section>
  );
}

function WhatIf({ portfolio }: { portfolio: string }) {
  const [rows, setRows] = useState<{ symbol: string; side: "BUY" | "SELL"; mode: "qty" | "amount"; n: string }[]>(
    [{ symbol: "", side: "SELL", mode: "qty", n: "" }]);
  const [res, setRes] = useState<SimResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const trades: SimTrade[] = rows.filter((r) => r.symbol && r.n).map((r) => ({
      symbol: r.symbol, side: r.side, ...(r.mode === "qty" ? { qty: Number(r.n) } : { amount: Number(r.n) }) }));
    try {
      setRes(await api.simulate(portfolio, trades));
    } catch (err) {
      setRes(null);
      setError((err as ApiError).message);
    }
  };
  const set = (i: number, patch: Partial<(typeof rows)[number]>) => setRows(rows.map((r, j) => (j === i ? { ...r, ...patch } : r)));

  return (
    <section className="card">
      <h2>What-if <span className="muted small">· simulate trades at current prices; nothing is saved</span></h2>
      <form className="stack" style={{ gap: 8 }} onSubmit={run}>
        {rows.map((r, i) => (
          <div className="row" key={i}>
            <select value={r.side} onChange={(e) => set(i, { side: e.target.value as "BUY" | "SELL" })} aria-label="Side">
              <option>SELL</option><option>BUY</option>
            </select>
            <input className="input" placeholder="Symbol" value={r.symbol} onChange={(e) => set(i, { symbol: e.target.value })} style={{ maxWidth: 110 }} aria-label="Symbol" />
            <input className="input" type="number" step="any" min="0" placeholder={r.mode === "qty" ? "Shares" : "Amount $"} value={r.n}
                   onChange={(e) => set(i, { n: e.target.value })} style={{ maxWidth: 130 }} aria-label="Size" />
            <div className="seg">
              <button type="button" aria-pressed={r.mode === "qty"} onClick={() => set(i, { mode: "qty" })}>shares</button>
              <button type="button" aria-pressed={r.mode === "amount"} onClick={() => set(i, { mode: "amount" })}>$</button>
            </div>
            {rows.length > 1 && <button type="button" className="btn ghost" onClick={() => setRows(rows.filter((_, j) => j !== i))}>×</button>}
          </div>
        ))}
        <div className="row">
          <button type="button" className="btn" onClick={() => setRows([...rows, { symbol: "", side: "BUY", mode: "amount", n: "" }])}>+ Trade</button>
          <button className="btn primary">Simulate</button>
        </div>
      </form>
      {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      {res && (
        <div style={{ marginTop: 12 }}>
          <div className="stats" style={{ marginBottom: 10 }}>
            <div className="stat"><div className="k">Net cash</div><div className={`v ${tone(res.net_cash)}`}>{money(res.net_cash, { signed: true })}</div></div>
            <div className="stat"><div className="k">Realized P&amp;L (FIFO)</div><div className={`v ${tone(res.realized_pnl_from_trades)}`}>{money(res.realized_pnl_from_trades, { signed: true })}</div></div>
            <div className="stat"><div className="k">Largest position</div><div className="v">{res.concentration_before.top1_pct.toFixed(1)}% → {res.concentration_after.top1_pct.toFixed(1)}%</div></div>
            <div className="stat"><div className="k">Effective positions</div><div className="v">{res.concentration_before.effective_positions.toFixed(1)} → {res.concentration_after.effective_positions.toFixed(1)}</div></div>
          </div>
          <table>
            <thead><tr><th>Symbol</th><th>Weight before</th><th>Weight after</th><th>Shares after</th></tr></thead>
            <tbody>{res.positions_changed.map((c) => (
              <tr key={c.symbol} style={{ cursor: "default" }}><td className="sym">{c.symbol}</td>
                <td>{c.weight_before == null ? "0.0%" : `${c.weight_before.toFixed(1)}%`}</td>
                <td>{c.weight_after.toFixed(1)}%</td><td>{c.qty_after}</td></tr>))}
            </tbody>
          </table>
          <p className="small muted">
            Largest sectors after (look-through): {res.sector_lookthrough_after.slice(0, 3).map((s) => `${s.key} ${s.weight_pct.toFixed(1)}%`).join(" · ")}
          </p>
        </div>
      )}
    </section>
  );
}

export function Analysis({ portfolio }: { portfolio: string }) {
  return (
    <div className="stack">
      <ExposureSection portfolio={portfolio} />
      <RiskCard portfolio={portfolio} />
      <DividendsCard portfolio={portfolio} />
      {portfolio === ALL ? (
        <p className="muted small">Targets and what-if trades work per portfolio; pick one in the header.</p>
      ) : (
        <>
          <DriftSection portfolio={portfolio} />
          <WhatIf portfolio={portfolio} />
        </>
      )}
    </div>
  );
}
