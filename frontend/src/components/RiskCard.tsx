import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RiskReport } from "../api";
import { money, pct, tone } from "../format";

const TOP_RISK = 15;

/** Diverging fill for a correlation: orange for positive, blue for negative, fading to the surface at 0. */
function corrFill(r: number | null): string | undefined {
  if (r == null) return undefined;
  const hue = r >= 0 ? "var(--series-2)" : "var(--series-1)";
  return `color-mix(in srgb, ${hue} ${Math.round(Math.min(Math.abs(r), 1) * 70)}%, transparent)`;
}

const reading = (f: string, b: number, t: number) => {
  if (Math.abs(t) < 2) return "no clear tilt";
  const pos: Record<string, string> = { "Mkt-RF": "more market-sensitive than the market", SMB: "small caps", HML: "value",
    RMW: "highly profitable firms", CMA: "conservative investors", Mom: "recent winners" };
  const neg: Record<string, string> = { "Mkt-RF": "less market-sensitive than the market", SMB: "large caps", HML: "growth",
    RMW: "less profitable firms", CMA: "aggressive investors (fast asset growth)", Mom: "recent losers" };
  if (f === "Mkt-RF") return b > 1 ? pos[f] : neg[f];
  return `tilts to ${(b > 0 ? pos : neg)[f]}`;
};

/** Risk of the portfolio as it stands today, from a year of daily returns. */
export function RiskCard({ portfolio }: { portfolio: string }) {
  const [r, setR] = useState<RiskReport | null>(null);
  const [failed, setFailed] = useState<string | null>(null);

  useEffect(() => {
    let stale = false;
    setR(null);
    setFailed(null);
    api.risk(portfolio).then((x) => !stale && setR(x), (e) => !stale && setFailed(e.message));
    return () => { stale = true; };
  }, [portfolio]);

  if (failed) return <section className="card"><h2>Risk</h2><div className="error">{failed}</div></section>;
  if (!r) return <section className="card"><h2>Risk</h2><p className="muted">Loading risk… (the first time downloads long price history for the stress tests)</p></section>;
  if (!r.available) return <section className="card"><h2>Risk</h2><p className="muted">{r.reason}</p></section>;

  const v95 = r.var["95"], v99 = r.var["99"];
  const top = r.positions.slice(0, TOP_RISK);
  const maxShare = Math.max(...top.map((p) => Math.max(p.weight_pct, p.risk_pct)), 1);
  const c = r.correlation;

  return (
    <section className="card stack" style={{ gap: 18 }}>
      <h2 style={{ margin: 0 }}>Risk <span className="muted small">· today's holdings over the last {r.lookback_days} trading days, to {r.as_of}</span></h2>

      <div className="tiles">
        <div className="tile">
          <div className="label">Beta vs {r.benchmark}</div>
          <div className="value">{r.beta.toFixed(2)}</div>
          <div className="delta muted">{r.benchmark} ±1% → you ±{r.beta.toFixed(1)}%</div>
        </div>
        <div className="tile">
          <div className="label">Volatility (annualized)</div>
          <div className="value">{r.volatility_pct.toFixed(1)}%</div>
          <div className="delta muted">{r.benchmark}: {r.benchmark_volatility_pct.toFixed(1)}%</div>
        </div>
        <div className="tile" title="Historical: the 5th-percentile daily loss over the year; CVaR is the average loss on days worse than that">
          <div className="label">1-day VaR 95%</div>
          <div className="value">{money(-v95.var_value, { whole: true })}</div>
          <div className="delta muted">{v95.var_pct.toFixed(2)}% · CVaR {v95.cvar_pct.toFixed(2)}% ({money(-v95.cvar_value, { whole: true })})</div>
        </div>
        <div className="tile">
          <div className="label">1-day VaR 99%</div>
          <div className="value">{money(-v99.var_value, { whole: true })}</div>
          <div className="delta muted">{v99.var_pct.toFixed(2)}% · CVaR {v99.cvar_pct.toFixed(2)}%</div>
        </div>
        <div className="tile">
          <div className="label">Max drawdown (1 year)</div>
          <div className="value down">{r.max_drawdown_pct.toFixed(1)}%</div>
          <div className="delta muted">of today's holdings</div>
        </div>
      </div>

      <div>
        <h3 className="sub">Stress scenarios</h3>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Scenario</th><th>Window</th><th>{r.benchmark}</th><th>Your portfolio (est.)</th><th>Change in value</th><th>Estimated from beta</th></tr></thead>
            <tbody>
              {r.scenarios.map((s) => (
                <tr key={s.key} style={{ cursor: "default" }}>
                  <td style={{ textAlign: "left" }}>{s.label}</td>
                  <td className="muted">{s.start ? `${s.start} → ${s.end}` : "–"}</td>
                  <td className={tone(s.spy_pct)}>{pct(s.spy_pct, 1)}</td>
                  <td className={tone(s.portfolio_pct)}><strong>{pct(s.portfolio_pct, 1)}</strong></td>
                  <td className={tone(s.value)}>{money(s.value, { signed: true, whole: true })}</td>
                  <td className="muted" title={s.proxied.join(", ")}>
                    {s.key === "spy_down_10" ? "all holdings" : s.proxied.length ? `${s.proxied.length} of ${r.positions.length} holdings` : "none"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small muted" style={{ margin: "6px 0 0" }}>
          Each holding's actual price change over the window; holdings listed later use their beta to {r.benchmark}{" "}
          (hover the count for which). Price only, no dividends.
        </p>
      </div>

      <div className="grid-2" style={{ alignItems: "start" }}>
        <div>
          <h3 className="sub">Where the risk comes from</h3>
          <div className="row small text-2" style={{ gap: 14, marginBottom: 6 }}>
            <span><span className="swatch" style={{ background: "var(--axis)" }} /> Weight</span>
            <span><span className="swatch" style={{ background: "var(--series-1)" }} /> Share of risk</span>
          </div>
          <table className="risk-bars">
            <colgroup><col style={{ width: 64 }} /><col /><col style={{ width: 58 }} /><col style={{ width: 58 }} /><col style={{ width: 62 }} /></colgroup>
            <tbody>
              {top.map((p) => (
                <tr key={p.symbol} style={{ cursor: "default" }}>
                  <td style={{ textAlign: "left" }}><Link to={`/t/${p.symbol}`}>{p.symbol}</Link>{p.proxied && <span className="muted" title={`Only ${p.history_days} days of history`}> *</span>}</td>
                  <td className="bars">
                    <div className="bar w" style={{ width: `${(p.weight_pct / maxShare) * 100}%` }} />
                    <div className="bar r" style={{ width: `${(Math.max(p.risk_pct, 0) / maxShare) * 100}%` }} />
                  </td>
                  <td className="num">{p.weight_pct.toFixed(1)}%</td>
                  <td className="num"><strong>{p.risk_pct.toFixed(1)}%</strong></td>
                  <td className="num muted" title="Beta to the benchmark">β {p.beta.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="small muted" style={{ margin: "6px 0 0" }}>
            Share of risk = the position's contribution to portfolio variance; it can exceed its weight (volatile, correlated)
            or fall below it (diversifying). * Short history, filled with beta × {r.benchmark}.
          </p>
        </div>

        <div>
          <h3 className="sub">Correlations · largest {c.symbols.length} positions</h3>
          <div className="table-wrap">
            <table className="corr">
              <thead><tr><th />{c.symbols.map((s) => <th key={s}>{s}</th>)}</tr></thead>
              <tbody>
                {c.symbols.map((s, i) => (
                  <tr key={s} style={{ cursor: "default" }}>
                    <th>{s}</th>
                    {c.matrix[i].map((x, j) => (
                      <td key={j} style={{ background: i === j ? undefined : corrFill(x) }} className={i === j ? "muted" : undefined}
                          title={x == null ? "no price movement" : `${s} vs ${c.symbols[j]}: ${x.toFixed(2)}`}>
                        {x == null ? "–" : i === j ? "1" : x.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row small text-2" style={{ gap: 14, marginTop: 6 }}>
            <span><span className="swatch" style={{ background: corrFill(-0.9) }} /> move opposite</span>
            <span><span className="swatch" style={{ background: "var(--grid)" }} /> unrelated</span>
            <span><span className="swatch" style={{ background: corrFill(0.9) }} /> move together</span>
          </div>
        </div>
      </div>

      {r.factors && (
        <div>
          <h3 className="sub">Factor exposures <span className="muted small">· Fama-French 5 + momentum, {r.factors.from} → {r.factors.to} ({r.factors.days} days), R² {r.factors.r2.toFixed(2)}</span></h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Factor</th><th>Loading</th><th>t-stat</th><th>Reading</th></tr></thead>
              <tbody>
                {r.factors.loadings.map((l) => (
                  <tr key={l.factor} style={{ cursor: "default" }}>
                    <td style={{ textAlign: "left" }}>{l.label}</td>
                    <td><strong>{l.beta.toFixed(2)}</strong></td>
                    <td className={Math.abs(l.t) >= 2 ? undefined : "muted"}>{l.t.toFixed(1)}</td>
                    <td style={{ textAlign: "left" }} className={Math.abs(l.t) >= 2 ? undefined : "muted"}>{reading(l.factor, l.beta, l.t)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted" style={{ margin: "6px 0 0" }}>
            Regression of daily excess returns on factor returns (Kenneth French data library, published with a lag of a month or two).
            |t| ≥ 2 is a reliable tilt. Annualized alpha {pct(r.factors.alpha_annual_pct, 1)} — treat with caution over one year.
          </p>
        </div>
      )}
    </section>
  );
}
