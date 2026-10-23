import { useEffect, useState } from "react";
import { api, type Research } from "../api";
import { big, money, nyTime, pct, price, tone } from "../format";

const TABS = ["Analysts", "Growth", "Estimates", "Insiders", "Ownership & short", "Valuation", "Quality", "News"] as const;
type Tab = (typeof TABS)[number];
const FUND_TABS: Tab[] = ["Ownership & short", "News"];
const TAB_KEY = "argus.researchTab";

const HORIZONS: Record<string, string> = { "0q": "This quarter", "+1q": "Next quarter", "0y": "This year", "+1y": "Next year" };
const RATING_SEGMENTS = [
  { key: "strongBuy", label: "Strong buy", color: "var(--up)", alpha: 100 },
  { key: "buy", label: "Buy", color: "var(--up)", alpha: 55 },
  { key: "hold", label: "Hold", color: "var(--axis)", alpha: 100 },
  { key: "sell", label: "Sell", color: "var(--down)", alpha: 55 },
  { key: "strongSell", label: "Strong sell", color: "var(--down)", alpha: 100 },
] as const;

const pctPlain = (v: number | null | undefined, d = 1) => (v == null ? "–" : `${v.toFixed(d)}%`);
const fill = (c: string, a: number) => (a === 100 ? c : `color-mix(in srgb, ${c} ${a}%, transparent)`);

/** Analyst views, estimates, insiders, ownership, short interest, valuation history, quality and news. */
export function ResearchCard({ symbol }: { symbol: string }) {
  const [r, setR] = useState<Research | null>(null);
  const [failed, setFailed] = useState(false);
  const [tab, setTab] = useState<Tab>(() => {
    try { return (localStorage.getItem(TAB_KEY) as Tab) || "Analysts"; } catch { return "Analysts"; }
  });

  useEffect(() => {
    let stale = false;
    setR(null);
    setFailed(false);
    api.research(symbol).then((x) => !stale && setR(x), () => !stale && setFailed(true));
    return () => { stale = true; };
  }, [symbol]);

  if (failed) return null;
  const tabs = r?.fund ? FUND_TABS : [...TABS];
  const current = tabs.includes(tab) ? tab : tabs[0];
  const pick = (t: Tab) => { setTab(t); try { localStorage.setItem(TAB_KEY, t); } catch { /* ignore */ } };

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Research</h2>
        <div className="seg tabs" role="tablist" aria-label="Research">
          {tabs.map((t) => <button key={t} role="tab" aria-selected={t === current} aria-pressed={t === current} onClick={() => pick(t)}>{t}</button>)}
        </div>
      </div>
      {!r ? <p className="muted">Loading research…</p> : (
        <>
          {current === "Analysts" && <Analysts r={r} />}
          {current === "Growth" && <Growth r={r} />}
          {current === "Estimates" && <Estimates r={r} />}
          {current === "Insiders" && <Insiders r={r} />}
          {current === "Ownership & short" && <Ownership r={r} />}
          {current === "Valuation" && <Valuation r={r} />}
          {current === "Quality" && <Quality r={r} />}
          {current === "News" && <News r={r} />}
        </>
      )}
    </section>
  );
}

function Analysts({ r }: { r: Research }) {
  const a = r.analysts;
  if (!a || !a.count) return <p className="muted">No analyst coverage.</p>;
  const latest = a.trend[0];
  const total = latest ? RATING_SEGMENTS.reduce((s, x) => s + (latest[x.key] ?? 0), 0) : 0;
  const lo = a.target_low ?? 0, hi = a.target_high ?? 0;
  const span = Math.max(hi, r.price ?? hi) - Math.min(lo, r.price ?? lo) || 1;
  const left = Math.min(lo, r.price ?? lo);
  const at = (v: number) => `${((v - left) / span) * 100}%`;
  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="tiles">
        <div className="tile"><div className="label">Consensus</div><div className="value" style={{ textTransform: "capitalize" }}>{(a.rating ?? "–").replace("_", " ")}</div>
          <div className="delta muted">{a.count} analysts · mean {a.rating_mean?.toFixed(2) ?? "–"} (1 = strong buy, 5 = sell){a.rating_source === "yahoo" && " · Yahoo"}</div></div>
        <div className="tile"><div className="label">Mean price target</div><div className="value">{price(a.target_mean)}</div>
          <div className={`delta ${tone(a.upside_pct)}`}>{pct(a.upside_pct, 1)} from {price(r.price)}
            {a.target_count != null && a.target_count !== a.count && <span className="muted"> · {a.target_count} targets</span>}</div></div>
        <div className="tile"><div className="label">Target range</div><div className="value">{price(a.target_low)} – {price(a.target_high)}</div>
          <div className="delta muted">median {price(a.target_median)}</div></div>
      </div>
      {a.target_low != null && a.target_high != null && (
        <div>
          <h3 className="sub">Price targets vs today</h3>
          <div className="range-track" role="img" aria-label={`Targets ${price(lo)} to ${price(hi)}, mean ${price(a.target_mean)}, price ${price(r.price)}`}>
            <div className="range-band" style={{ left: at(lo), width: `calc(${at(hi)} - ${at(lo)})` }} />
            {a.target_mean != null && <div className="range-tick" style={{ left: at(a.target_mean) }} title={`Mean ${price(a.target_mean)}`} />}
            {r.price != null && <div className="range-dot" style={{ left: at(r.price) }} title={`Price ${price(r.price)}`} />}
          </div>
          <div className="row small muted" style={{ justifyContent: "space-between" }}>
            <span>low {price(lo)}</span><span>● price · | mean</span><span>high {price(hi)}</span>
          </div>
        </div>
      )}
      {latest && total > 0 && (
        <div>
          <h3 className="sub">Ratings by month</h3>
          {a.trend.map((m) => {
            const n = RATING_SEGMENTS.reduce((s, x) => s + (m[x.key] ?? 0), 0) || 1;
            return (
              <div key={m.period} className="row" style={{ gap: 8, marginBottom: 4 }}>
                <span className="small muted" style={{ width: 56 }}>{m.period === "0m" ? "Now" : `${m.period.replace("m", "")} mo`}</span>
                <div className="stacked">
                  {RATING_SEGMENTS.map((x) => (m[x.key] ?? 0) > 0 && (
                    <div key={x.key} style={{ width: `${(m[x.key] / n) * 100}%`, background: fill(x.color, x.alpha) }} title={`${x.label}: ${m[x.key]}`} />
                  ))}
                </div>
                <span className="small num" style={{ width: 150, whiteSpace: "nowrap" }}>{m.strongBuy + m.buy} buy · {m.hold} hold · {m.sell + m.strongSell} sell</span>
              </div>
            );
          })}
          <div className="row small text-2" style={{ gap: 12, marginTop: 6 }}>
            {RATING_SEGMENTS.map((x) => <span key={x.key}><span className="swatch" style={{ background: fill(x.color, x.alpha) }} />{x.label}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}

const quarterLabel = (iso: string) => {
  const d = new Date(`${iso}T12:00:00Z`);
  return d.toLocaleDateString("en-US", { timeZone: "UTC", month: "short", year: "2-digit" });
};

function RevenueBars({ quarters }: { quarters: NonNullable<Research["growth"]>["quarters"] }) {
  const q = [...quarters].reverse().filter((x) => x.revenue != null);  // oldest -> newest
  if (q.length < 2) return null;
  const W = 640, H = 170, T = 22, B = 22, gap = 2;
  const max = Math.max(...q.map((x) => x.revenue as number));
  const bw = W / q.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="rev-bars" role="img"
         aria-label={`Quarterly revenue: ${q.map((x) => `${quarterLabel(x.period_end)} ${big(x.revenue)}`).join(", ")}`}>
      {q.map((x, i) => {
        const h = ((x.revenue as number) / max) * (H - T - B);
        const xPos = i * bw + gap;
        return (
          <g key={x.period_end}>
            <title>{`${quarterLabel(x.period_end)}: revenue ${big(x.revenue)}${x.revenue_yoy_pct != null ? `, ${pct(x.revenue_yoy_pct, 1)} YoY` : ""}`}</title>
            <path d={`M${xPos},${H - B} v${-(h - 4)} q0,-4 4,-4 h${bw - 2 * gap - 8} q4,0 4,4 v${h - 4} z`} fill="var(--series-1)" />
            {x.revenue_yoy_pct != null && (
              <text x={xPos + (bw - 2 * gap) / 2} y={H - B - h - 6} textAnchor="middle" className="bar-label">{pct(x.revenue_yoy_pct, 0)}</text>
            )}
            <text x={xPos + (bw - 2 * gap) / 2} y={H - 6} textAnchor="middle" className="axis">{quarterLabel(x.period_end)}</text>
          </g>
        );
      })}
    </svg>
  );
}

function Growth({ r }: { r: Research }) {
  const g = r.growth;
  if (!g) return <p className="muted">No growth data.</p>;
  const fy = g.forward.find((f) => f.horizon === "0y");
  const tile = (label: string, v: number | null | undefined, note?: string) => (
    <div className="tile"><div className="label">{label}</div><div className={`value ${tone(v)}`}>{pct(v, 1)}</div>{note && <div className="delta muted">{note}</div>}</div>
  );
  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="tiles">
        {tile("Revenue CAGR 3Y", g.reported.revenue_3y ?? g.filed_cagr.revenue_3y, `5Y ${pct(g.reported.revenue_5y ?? g.filed_cagr.revenue_5y, 1)}`)}
        {tile("EPS CAGR 3Y", g.reported.eps_3y, `5Y ${pct(g.reported.eps_5y, 1)}`)}
        {tile("Price CAGR 3Y", g.price_cagr_3y, `5Y ${pct(g.price_cagr_5y, 1)}`)}
        {fy && tile("This year, expected", fy.revenue_growth_pct, `revenue · EPS ${pct(fy.eps_growth_pct, 1)} vs S&P ${pct(fy.index_eps_growth_pct, 1)}`)}
        <div className="tile"><div className="label">PEG</div><div className="value">{g.peg?.toFixed(2) ?? "–"}</div>
          <div className="delta muted">P/E ÷ expected growth; under 1 = growth priced cheaply</div></div>
      </div>

      {g.quarters.length > 0 && (
        <div>
          <h3 className="sub">Quarterly revenue <span className="muted small">· labels are growth vs the same quarter a year earlier</span></h3>
          <RevenueBars quarters={g.quarters} />
          <div className="table-wrap">
            <table>
              <thead><tr><th>Quarter ended</th><th>Revenue</th><th>YoY</th><th>Net income</th><th>YoY</th><th>Gross margin</th><th>Operating margin</th></tr></thead>
              <tbody>
                {g.quarters.slice(0, 8).map((q) => (
                  <tr key={q.period_end} style={{ cursor: "default" }}>
                    <td>{q.period_end}</td><td>{big(q.revenue)}</td><td className={tone(q.revenue_yoy_pct)}>{pct(q.revenue_yoy_pct, 1)}</td>
                    <td className={tone(q.net_income)}>{big(q.net_income)}</td><td className={tone(q.net_income_yoy_pct)}>{pct(q.net_income_yoy_pct, 1)}</td>
                    <td>{q.gross_margin_pct == null ? "–" : `${q.gross_margin_pct.toFixed(1)}%`}</td>
                    <td>{q.operating_margin_pct == null ? "–" : `${q.operating_margin_pct.toFixed(1)}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {g.forward.length > 0 && (
        <div>
          <h3 className="sub">What analysts expect</h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Period</th><th>Revenue est.</th><th>Range</th><th>Growth</th><th>EPS est.</th><th>Range</th><th>Growth</th><th>S&amp;P 500 EPS growth</th><th>Analysts</th></tr></thead>
              <tbody>
                {g.forward.map((f) => (
                  <tr key={f.horizon} style={{ cursor: "default" }}>
                    <td style={{ textAlign: "left" }}>{f.label}</td>
                    <td>{big(f.revenue)}</td><td className="muted">{f.revenue_low != null ? `${big(f.revenue_low)}–${big(f.revenue_high)}` : "–"}</td>
                    <td className={tone(f.revenue_growth_pct)}>{pct(f.revenue_growth_pct, 1)}</td>
                    <td>{f.eps?.toFixed(2) ?? "–"}</td><td className="muted">{f.eps_low != null ? `${f.eps_low.toFixed(2)}–${f.eps_high?.toFixed(2)}` : "–"}</td>
                    <td className={tone(f.eps_growth_pct)}>{pct(f.eps_growth_pct, 1)}</td>
                    <td className="muted">{pct(f.index_eps_growth_pct, 1)}</td>
                    <td className="muted">{f.revenue_analysts ?? f.eps_analysts ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {g.years.length > 1 && (
        <div>
          <h3 className="sub">Annual <span className="muted small">· from 10-K filings; revenue CAGR {pct(g.filed_cagr.revenue_3y, 1)} (3Y) / {pct(g.filed_cagr.revenue_5y, 1)} (5Y), net income {pct(g.filed_cagr.net_income_3y, 1)} / {pct(g.filed_cagr.net_income_5y, 1)}</span></h3>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Fiscal year ended</th>{g.years.map((y) => <th key={y.period_end}>{y.period_end.slice(0, 7)}</th>)}</tr></thead>
              <tbody>
                <tr style={{ cursor: "default" }}><td style={{ textAlign: "left" }}>Revenue</td>{g.years.map((y) => <td key={y.period_end}>{big(y.revenue)}</td>)}</tr>
                <tr style={{ cursor: "default" }}><td style={{ textAlign: "left" }}>Net income</td>{g.years.map((y) => <td key={y.period_end} className={tone(y.net_income)}>{big(y.net_income)}</td>)}</tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
      <p className="small muted" style={{ margin: 0 }}>
        History from SEC filings; CAGR = compound annual growth. EPS growth uses Finnhub's split-adjusted figures (SEC per-share history
        isn't adjusted for splits, so the quarterly table shows net income). Estimates are analyst consensus via Yahoo.
      </p>
    </div>
  );
}

function Estimates({ r }: { r: Research }) {
  const t = r.estimates?.trend, rev = r.estimates?.revisions;
  if (!t) return <p className="muted">No estimates.</p>;
  const hs = Object.keys(HORIZONS).filter((h) => t[h]);
  const chg = (h: string) => { const now = t[h]?.current, then = t[h]?.["30daysAgo"]; return now != null && then ? (now / then - 1) * 100 : null; };
  return (
    <>
      <div className="table-wrap">
        <table>
          <thead><tr><th>EPS estimate</th><th>Now</th><th>7 days ago</th><th>30 days ago</th><th>60 days ago</th><th>90 days ago</th><th>30-day change</th><th>Revisions up / down (30d)</th></tr></thead>
          <tbody>
            {hs.map((h) => (
              <tr key={h} style={{ cursor: "default" }}>
                <td style={{ textAlign: "left" }}>{HORIZONS[h]}</td>
                <td><strong>{t[h].current?.toFixed(2) ?? "–"}</strong></td>
                <td>{t[h]["7daysAgo"]?.toFixed(2) ?? "–"}</td><td>{t[h]["30daysAgo"]?.toFixed(2) ?? "–"}</td>
                <td>{t[h]["60daysAgo"]?.toFixed(2) ?? "–"}</td><td>{t[h]["90daysAgo"]?.toFixed(2) ?? "–"}</td>
                <td className={tone(chg(h))}>{pct(chg(h), 1)}</td>
                <td><span className="up">{rev?.[h]?.upLast30days ?? "–"}↑</span> / <span className="down">{rev?.[h]?.downLast30days ?? "–"}↓</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ margin: "8px 0 0" }}>Consensus EPS (Yahoo). Rising estimates and more upward than downward revisions are what moves estimates-driven stocks.</p>
    </>
  );
}

function Insiders({ r }: { r: Research }) {
  const i = r.insiders;
  if (!i) return <p className="muted">No insider data.</p>;
  return (
    <div className="stack" style={{ gap: 14 }}>
      <div className="tiles">
        <div className="tile"><div className="label">Open-market buys</div><div className="value up">{money(i.buy_value, { whole: true })}</div>
          <div className="delta muted">{i.buy_count} trades by {i.buyers} insiders</div></div>
        <div className="tile"><div className="label">Open-market sales</div><div className="value down">{money(i.sell_value, { whole: true })}</div>
          <div className="delta muted">{i.sell_count} trades by {i.sellers} insiders</div></div>
        <div className="tile"><div className="label">Net</div><div className={`value ${tone(i.buy_value - i.sell_value)}`}>{money(i.buy_value - i.sell_value, { signed: true, whole: true })}</div>
          <div className="delta muted">since {i.since}</div></div>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Date</th><th>Insider</th><th>Type</th><th>Shares</th><th>Price</th><th>Value</th></tr></thead>
          <tbody>
            {i.recent.map((t, k) => (
              <tr key={k} style={{ cursor: "default" }} className={t.code === "P" || t.code === "S" ? undefined : "muted"}>
                <td>{t.date}</td><td style={{ textAlign: "left" }}>{t.name}</td>
                <td className={t.code === "P" ? "up" : t.code === "S" ? "down" : undefined}>{t.kind}{t.derivative ? " (derivative)" : ""}</td>
                <td>{t.shares?.toLocaleString("en-US")}</td><td>{t.price ? price(t.price) : "–"}</td><td>{t.value ? money(t.value, { whole: true }) : "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ margin: 0 }}>SEC Form 4 filings via Finnhub. Only open-market buys and sales count above; awards, option exercises, tax withholding and gifts are routine (greyed).</p>
    </div>
  );
}

function Ownership({ r }: { r: Research }) {
  const o = r.ownership, s = r.short_interest;
  return (
    <div className="stack" style={{ gap: 14 }}>
      <div className="tiles">
        <div className="tile"><div className="label">Held by institutions</div><div className="value">{pctPlain(o.institutions_pct)}</div>
          <div className="delta muted">insiders {pctPlain(o.insiders_pct, 2)}</div></div>
        <div className="tile"><div className="label">Short interest</div><div className="value">{pctPlain(s.pct_float, 2)}</div>
          <div className="delta muted">of float · {big(s.shares_short)} shares</div></div>
        <div className="tile"><div className="label">Days to cover</div><div className="value">{s.days_to_cover?.toFixed(1) ?? "–"}</div>
          <div className="delta muted">short shares ÷ average daily volume</div></div>
        <div className="tile"><div className="label">Short change</div><div className={`value ${tone(s.change_pct != null ? -s.change_pct : null)}`}>{pct(s.change_pct, 1)}</div>
          <div className="delta muted">vs prior month{s.as_of ? ` · as of ${s.as_of}` : ""}</div></div>
      </div>
      {o.top.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Top institutions (13F)</th><th>% held</th><th>Shares</th><th>Value</th><th>Change</th><th>Reported</th></tr></thead>
            <tbody>
              {o.top.map((h) => (
                <tr key={h.Holder} style={{ cursor: "default" }}>
                  <td style={{ textAlign: "left" }}>{h.Holder}</td><td>{pctPlain(h.pctHeld != null ? h.pctHeld * 100 : null, 2)}</td>
                  <td>{big(h.Shares)}</td><td>{big(h.Value)}</td>
                  <td className={tone(h.pctChange)}>{pct(h.pctChange != null ? h.pctChange * 100 : null, 1)}</td><td className="muted">{h["Date Reported"]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="small muted" style={{ margin: 0 }}>Yahoo: institutional holdings from 13F filings (quarterly, ~45 days late); short interest from exchange reports (twice a month).</p>
    </div>
  );
}

function Valuation({ r }: { r: Research }) {
  const v = r.valuation;
  if (!v || v.length === 0) return <p className="muted">No valuation history.</p>;
  return (
    <div className="stack" style={{ gap: 14 }}>
      {v.map((b) => {
        const lo = b.min, hi = b.max, span = hi - lo || 1;
        const at = (x: number) => `${Math.min(100, Math.max(0, ((x - lo) / span) * 100))}%`;
        const where = b.percentile == null ? "n/a (negative)" : b.percentile < 25 ? "cheap vs its history" : b.percentile > 75 ? "expensive vs its history" : "middle of its range";
        return (
          <div key={b.key}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>{b.label}</strong>
              <span className="small">
                now <strong>{b.current?.toFixed(1) ?? "–"}</strong>
                {b.percentile != null && <> · {Math.round(b.percentile)}th percentile, {where}</>}
              </span>
            </div>
            <div className="range-track" role="img" aria-label={`${b.label} 5-year range ${lo.toFixed(1)} to ${hi.toFixed(1)}, median ${b.median.toFixed(1)}, now ${b.current?.toFixed(1)}`}>
              <div className="range-band" style={{ left: at(b.p25), width: `calc(${at(b.p75)} - ${at(b.p25)})` }} />
              <div className="range-tick" style={{ left: at(b.median) }} />
              {b.current != null && b.current > 0 && <div className="range-dot" style={{ left: at(b.current) }} />}
            </div>
            <div className="row small muted" style={{ justifyContent: "space-between" }}>
              <span>min {lo.toFixed(1)}</span><span>middle half {b.p25.toFixed(1)}–{b.p75.toFixed(1)} · median {b.median.toFixed(1)}</span><span>max {hi.toFixed(1)}</span>
            </div>
          </div>
        );
      })}
      <p className="small muted" style={{ margin: 0 }}>Quarter-end values over 5 years (Finnhub, {v[0].points} quarters). ● today · | median · bar = middle half. Loss-making quarters are left out of P/E.</p>
    </div>
  );
}

function Quality({ r }: { r: Research }) {
  const q = r.quality;
  if (!q) return <p className="muted">No statements available.</p>;
  const p = q.piotroski, z = q.altman;
  return (
    <div className="grid-2" style={{ alignItems: "start" }}>
      <div>
        <h3 className="sub">Piotroski F-score</h3>
        {!p.available ? <p className="muted">{p.reason}</p> : (
          <>
            <div className="row" style={{ gap: 10, marginBottom: 8 }}>
              <span className="hero-value" style={{ fontSize: 30 }}>{p.score}<span className="muted" style={{ fontSize: 16 }}>/{p.out_of}</span></span>
              <span className={`tag ${p.label === "strong" ? "up" : p.label === "weak" ? "down" : ""}`}>{p.label}</span>
              <span className="small muted">FY {p.fiscal_years[0]?.slice(0, 4)} vs {p.fiscal_years[1]?.slice(0, 4)}</span>
            </div>
            <ul className="checks">
              {p.tests.map((t) => (
                <li key={t.test} className={t.pass === null ? "muted" : undefined}>
                  <span className={t.pass ? "up" : t.pass === false ? "down" : "muted"} aria-label={t.pass ? "pass" : t.pass === false ? "fail" : "unknown"}>
                    {t.pass ? "✓" : t.pass === false ? "✗" : "–"}
                  </span> {t.test}
                </li>
              ))}
            </ul>
            <p className="small muted" style={{ margin: "6px 0 0" }}>7–9 strong, 4–6 average, 0–3 weak: profitability, balance-sheet and efficiency trends.</p>
          </>
        )}
      </div>
      <div>
        <h3 className="sub">Altman Z-score</h3>
        {!z.available ? <p className="muted">{z.reason}</p> : (
          <>
            <div className="row" style={{ gap: 10, marginBottom: 8 }}>
              <span className="hero-value" style={{ fontSize: 30 }}>{z.z?.toFixed(1)}</span>
              <span className={`tag ${z.zone === "safe" ? "up" : z.zone === "distress" ? "down" : ""}`}>{z.zone} zone</span>
            </div>
            <table>
              <tbody>
                {[["Working capital / assets", "wc_ta", 1.2], ["Retained earnings / assets", "re_ta", 1.4], ["EBIT / assets", "ebit_ta", 3.3],
                  ["Market value / liabilities", "mve_tl", 0.6], ["Sales / assets", "sales_ta", 1.0]].map(([label, k, wgt]) => (
                  <tr key={k as string} style={{ cursor: "default" }}>
                    <td style={{ textAlign: "left" }}>{label}</td><td className="num">{z.parts[k as string]?.toFixed(2)}</td>
                    <td className="num muted">× {wgt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="small muted" style={{ margin: "6px 0 0" }}>
              Above 2.99 safe, 1.81–2.99 grey, below 1.81 distress (bankruptcy-risk model). {z.caveat ?? ""}
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function News({ r }: { r: Research }) {
  if (r.news.length === 0) return <p className="muted">No headlines in the last week.</p>;
  const t = r.news_tone;
  return (
    <>
      <p className="small" style={{ marginTop: 0 }}>
        Last 7 days: <span className="up">{t.positive} positive</span> · {t.neutral} neutral · <span className="down">{t.negative} negative</span>
        <span className="muted"> (keyword-based tone; a hint for scanning, not a judgment)</span>
      </p>
      <ul className="news">
        {r.news.map((n) => (
          <li key={n.url}>
            <span className={`tag ${n.tone.label === "positive" ? "up" : n.tone.label === "negative" ? "down" : ""}`}>{n.tone.label}</span>
            <a href={n.url} target="_blank" rel="noreferrer">{n.headline}</a>
            <span className="small muted"> · {n.source} · {nyTime(n.ts)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}
