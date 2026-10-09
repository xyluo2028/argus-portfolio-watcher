import { Fragment, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type EconEvent, type MarketContext } from "../api";
import { pct, tone } from "../format";

const CURVE_STYLE = [
  { stroke: "var(--series-1)", dash: undefined, width: 2.5 },  // today
  { stroke: "var(--series-2)", dash: "6 4", width: 2 },        // 1 month ago
  { stroke: "var(--series-3)", dash: "2 4", width: 2 },        // 1 year ago
];

const day = (iso: string) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric" });

/** For a yield, a return is a change in rate: show it in basis points, not as a % of the yield. */
function bp(last: number, retPct: number | null | undefined) {
  if (retPct == null) return "–";
  const change = last - last / (1 + retPct / 100);
  return `${change >= 0 ? "+" : "−"}${Math.abs(change * 100).toFixed(0)} bp`;
}

function fmtLevel(kind: string, v: number) {
  if (kind === "yield") return `${v.toFixed(2)}%`;
  if (kind === "$") return v >= 1000 ? `$${Math.round(v).toLocaleString("en-US")}` : `$${v.toFixed(2)}`;
  return v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Heat fill for a return: green up, red down, stronger with size (relative to the column's largest move). */
function heat(v: number | null | undefined, scale: number) {
  if (v == null || !scale) return undefined;
  const a = Math.round(Math.min(Math.abs(v) / scale, 1) * 55) + 6;
  return `color-mix(in srgb, ${v >= 0 ? "var(--up)" : "var(--down)"} ${a}%, transparent)`;
}

function Spark({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${28 - ((v - lo) / span) * 26 - 1}`).join(" ");
  return (
    <svg viewBox="0 0 100 28" preserveAspectRatio="none" className="spark" aria-hidden>
      <polyline points={pts} fill="none" stroke="var(--series-1)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function Markets() {
  const [m, setM] = useState<MarketContext | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [allEvents, setAllEvents] = useState(false);

  useEffect(() => {
    api.marketContext().then(setM, (e) => setFailed(e.message));
    const id = setInterval(() => api.marketContext().then(setM, () => undefined), 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  const scales = useMemo(() => {
    const out: Record<string, number> = {};
    for (const p of m?.periods ?? []) out[p] = Math.max(...(m?.sectors ?? []).map((s) => Math.abs(s.returns[p] ?? 0)), 0.01);
    return out;
  }, [m]);

  if (failed) return <div className="error">{failed}</div>;
  if (!m) return <p className="muted">Loading markets…</p>;

  const b = m.breadth;
  const byDate = new Map<string, EconEvent[]>();
  for (const e of (allEvents ? m.calendar?.all_events : m.calendar?.events) ?? []) byDate.set(e.date, [...(byDate.get(e.date) ?? []), e]);

  return (
    <div className="stack">
      {Object.keys(m.errors).length > 0 && (
        <div className="error">Some sources didn't answer: {Object.entries(m.errors).map(([k, v]) => `${k} (${v})`).join("; ")}</div>
      )}

      <section className="gauges" aria-label="Market gauges">
        {m.gauges.map((g) => {
          const d = g.returns["1D"];
          return (
            <div className="tile gauge" key={g.symbol}>
              <div className="label">{g.label}</div>
              <div className="value">{fmtLevel(g.kind, g.last)}</div>
              <div className="delta">
                {g.kind === "yield" && g.change != null
                  ? <span className={tone(g.change)}>{g.change >= 0 ? "+" : "−"}{Math.abs(g.change * 100).toFixed(0)} bp</span>
                  : <span className={tone(d)}>{pct(d, 2)}</span>}
                {(["1M", "YTD"] as const).map((p) => (
                  <Fragment key={p}>
                    <span className="muted"> · {p} </span>
                    <span className={tone(g.returns[p])}>{g.kind === "yield" ? bp(g.last, g.returns[p]) : pct(g.returns[p], 1)}</span>
                  </Fragment>
                ))}
              </div>
              <Spark values={g.spark} />
            </div>
          );
        })}
      </section>

      <section className="stack">
        <div className="card">
          <h2>Sectors <span className="muted small">· SPDR sector ETFs, price return</span></h2>
          <div className="table-wrap">
            <table className="heat">
              <thead><tr><th>Sector</th>{m.periods.map((p) => <th key={p}>{p}</th>)}<th title="Above its 50-day / 200-day average">50D · 200D</th></tr></thead>
              <tbody>
                {m.sectors.map((s) => (
                  <tr key={s.symbol} style={{ cursor: "default" }}>
                    <td style={{ textAlign: "left" }}><Link to={`/t/${s.symbol}`}>{s.name}</Link></td>
                    {m.periods.map((p) => (
                      <td key={p} style={{ background: heat(s.returns[p], scales[p]) }} title={`${s.name} ${p}: ${pct(s.returns[p], 2)}`}>
                        {pct(s.returns[p], 1)}
                      </td>
                    ))}
                    <td>
                      <span className={s.above_50d ? "up" : "down"} aria-label={s.above_50d ? "above 50-day" : "below 50-day"}>{s.above_50d ? "▲" : "▼"}</span>{" "}
                      <span className={s.above_200d ? "up" : "down"} aria-label={s.above_200d ? "above 200-day" : "below 200-day"}>{s.above_200d ? "▲" : "▼"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted" style={{ margin: "6px 0 0" }}>Shading is relative to each column's biggest move. ▲ above / ▼ below the 50- and 200-day averages.</p>
        </div>

        <div className="card">
          <h2>Breadth <span className="muted small">· is the rally broad or narrow?</span></h2>
          <table>
            <thead><tr><th>Gauge</th><th>1M</th><th>3M</th><th>YTD</th><th>1Y</th></tr></thead>
            <tbody>
              {[["Equal- vs cap-weighted S&P 500 (RSP − SPY)", b.equal_vs_cap], ["Small vs large caps (IWM − SPY)", b.small_vs_large]].map(([label, r]) => (
                <tr key={label as string} style={{ cursor: "default" }}>
                  <td style={{ textAlign: "left" }}>{label as string}</td>
                  {(["1M", "3M", "YTD", "1Y"] as const).map((p) => {
                    const v = (r as Record<string, number | null>)[p];
                    return <td key={p} className={tone(v)}>{v == null ? "–" : `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(1)} pp`}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="tiles" style={{ marginTop: 12 }}>
            <div className="tile"><div className="label">Sectors above 50-day</div><div className="value">{b.sectors_above_50d}/{b.sectors}</div></div>
            <div className="tile"><div className="label">Sectors above 200-day</div><div className="value">{b.sectors_above_200d}/{b.sectors}</div></div>
          </div>
          <p className="small muted" style={{ margin: "8px 0 0" }}>
            Negative spreads mean the average stock trails the index: gains rest on a few large companies. These are proxies, not a count of all 500 members.
          </p>
        </div>
      </section>

      {m.yield_curve && <YieldCurve yc={m.yield_curve} />}

      {m.calendar && (
        <section className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>Economic calendar <span className="muted small">· US, next 3 weeks, times ET</span></h2>
            <label className="small"><input type="checkbox" checked={allEvents} onChange={(e) => setAllEvents(e.target.checked)} /> all {m.calendar.all_count} US releases</label>
          </div>
          {m.calendar.fomc.length > 0 && (
            <p style={{ marginTop: 0 }}>
              <strong>FOMC meetings:</strong>{" "}
              {m.calendar.fomc.map((f, i) => (
                <span key={f.date}>{i > 0 && " · "}{f.month} {f.days}{f.projections && <span className="tag" title="Summary of Economic Projections (dot plot)" style={{ marginLeft: 4 }}>projections</span>}</span>
              ))}
              <span className="muted small"> (decision on the last day, 2:00 pm ET)</span>
            </p>
          )}
          {(
            <div className="table-wrap">
              <table>
                <thead><tr><th>Date</th><th>Time</th><th>Release</th><th>Consensus</th><th>Previous</th><th>Actual</th></tr></thead>
                <tbody>
                  {[...byDate.entries()].map(([d, evs]) => (
                    <Fragment key={d}>
                      {evs.map((e, i) => (
                        <tr key={`${d}-${i}`} style={{ cursor: "default" }} className={e.actual ? "muted" : undefined}>
                          <td>{i === 0 ? day(d) : ""}</td><td>{e.time_et ?? ""}</td>
                          <td style={{ textAlign: "left" }}>{e.event}</td><td>{e.consensus ?? "–"}</td><td>{e.previous ?? "–"}</td>
                          <td>{e.actual ? <strong>{e.actual}</strong> : "–"}</td>
                        </tr>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="small muted" style={{ margin: "6px 0 0" }}>Releases from Nasdaq's economic calendar; FOMC dates from the Federal Reserve. Some appear twice (month-on-month and year-on-year): "Previous" tells them apart.</p>
        </section>
      )}
    </div>
  );
}

function YieldCurve({ yc }: { yc: NonNullable<MarketContext["yield_curve"]> }) {
  const [hover, setHover] = useState<number | null>(null);
  const tenors = yc.lines[0].points.map((p) => p.tenor);
  const all = yc.lines.flatMap((l) => l.points.map((p) => p.yield).filter((v): v is number => v != null));
  // Round tick steps (0.25 / 0.5 / 1 percentage points) and an axis that starts and ends on one.
  const rawLo = Math.min(...all), rawHi = Math.max(...all);
  const step = rawHi - rawLo > 4 ? 1 : rawHi - rawLo > 1.5 ? 0.5 : 0.25;
  const lo = Math.floor(rawLo / step) * step - step, hi = Math.ceil(rawHi / step) * step;
  const W = 720, H = 260, L = 44, R = 140, T = 14, B = 30;
  const x = (i: number) => L + (i / (tenors.length - 1)) * (W - L - R);
  const y = (v: number) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  const ticks = Array.from({ length: Math.round((hi - lo) / step) + 1 }, (_, i) => lo + i * step);
  const inverted = (v: number | null) => v != null && v < 0;
  return (
    <section className="card">
      <h2>Treasury yield curve <span className="muted small">· par yields, {yc.as_of}</span></h2>
      <div className="tiles" style={{ marginBottom: 12 }}>
        <div className="tile"><div className="label">10Y − 2Y</div>
          <div className={`value ${inverted(yc.spread_10y_2y) ? "down" : ""}`}>{yc.spread_10y_2y == null ? "–" : `${(yc.spread_10y_2y * 100).toFixed(0)} bp`}</div>
          <div className="delta muted">{inverted(yc.spread_10y_2y) ? "inverted" : "normal (upward)"}</div></div>
        <div className="tile"><div className="label">10Y − 3M</div>
          <div className={`value ${inverted(yc.spread_10y_3m) ? "down" : ""}`}>{yc.spread_10y_3m == null ? "–" : `${(yc.spread_10y_3m * 100).toFixed(0)} bp`}</div>
          <div className="delta muted">{inverted(yc.spread_10y_3m) ? "inverted — historically a recession signal" : "normal (upward)"}</div></div>
      </div>
      <div style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="curve" role="img"
             aria-label={`Yield curve: ${yc.lines.map((l) => `${l.label} ${l.points.map((p) => `${p.tenor} ${p.yield}%`).join(", ")}`).join("; ")}`}
             onMouseLeave={() => setHover(null)}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
              <text x={L - 6} y={y(t) + 4} textAnchor="end" className="axis">{t.toFixed(2)}%</text>
            </g>
          ))}
          {tenors.map((t, i) => <text key={t} x={x(i)} y={H - 10} textAnchor="middle" className="axis">{t.replace(" Mo", "M").replace(" Yr", "Y")}</text>)}
          {hover != null && <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="var(--axis)" />}
          {[...yc.lines].reverse().map((l) => {
            const k = yc.lines.indexOf(l), st = CURVE_STYLE[k];
            const pts = l.points.map((p, i) => (p.yield == null ? null : `${x(i)},${y(p.yield)}`)).filter(Boolean).join(" ");
            const last = [...l.points].reverse().find((p) => p.yield != null);
            return (
              <g key={l.label}>
                <polyline points={pts} fill="none" stroke={st.stroke} strokeWidth={st.width} strokeDasharray={st.dash} strokeLinejoin="round" />
                {k === 0 && l.points.map((p, i) => p.yield != null && (
                  <circle key={i} cx={x(i)} cy={y(p.yield)} r={4} fill={st.stroke} stroke="var(--surface)" strokeWidth={2} />
                ))}
                {last && <text x={W - R + 8} y={y(last.yield!) + 4} className="end-label">{l.label} {last.yield!.toFixed(2)}%</text>}
              </g>
            );
          })}
          {tenors.map((t, i) => (
            <rect key={t} x={x(i) - (W - L - R) / (tenors.length - 1) / 2} y={T} width={(W - L - R) / (tenors.length - 1)} height={H - T - B}
                  fill="transparent" onMouseEnter={() => setHover(i)} />
          ))}
        </svg>
        {hover != null && (
          <div className="curve-tip" style={{ left: `${(x(hover) / W) * 100}%` }}>
            <strong>{tenors[hover]}</strong>
            {yc.lines.map((l, k) => (
              <div key={l.label}><span className="swatch" style={{ background: CURVE_STYLE[k].stroke }} />{l.label}: {l.points[hover].yield?.toFixed(2) ?? "–"}%</div>
            ))}
          </div>
        )}
      </div>
      <div className="row small text-2" style={{ gap: 14, margin: "6px 0 10px" }}>
        {yc.lines.map((l, k) => (
          <span key={l.label}>
            <svg width="22" height="8" aria-hidden><line x1="0" x2="22" y1="4" y2="4" stroke={CURVE_STYLE[k].stroke} strokeWidth="2" strokeDasharray={CURVE_STYLE[k].dash} /></svg>{" "}
            {l.label} ({l.date})
          </span>
        ))}
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th />{tenors.map((t) => <th key={t}>{t.replace(" Mo", "M").replace(" Yr", "Y")}</th>)}</tr></thead>
          <tbody>
            {yc.lines.map((l) => (
              <tr key={l.label} style={{ cursor: "default" }}>
                <td style={{ textAlign: "left" }}>{l.label}</td>
                {l.points.map((p) => <td key={p.tenor}>{p.yield?.toFixed(2) ?? "–"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ margin: "6px 0 0" }}>US Treasury daily par yield curve. Inversion (short above long) has preceded most US recessions, with long and variable lags.</p>
    </section>
  );
}
