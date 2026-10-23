import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api, type CompareHistory } from "../api";
import { pct } from "../format";

/** A series' look: one of the 8 categorical hues, dashed from the 9th on (never a made-up hue). */
export interface SeriesStyle { color: string; dash?: string }

const PERIODS: [string, string][] = [["1mo", "1M"], ["3mo", "3M"], ["6mo", "6M"], ["ytd", "YTD"], ["1y", "1Y"], ["3y", "3Y"], ["5y", "5Y"]];
const H = 300;
const PAD = { l: 8, r: 52, t: 10, b: 24 };
const KEY = "argus.compare.period";

type Pt = { d: string; v: number };

/** Price return of each symbol since the start of the range, on one % axis. */
export function CompareChart({ symbols, styleOf }: { symbols: string[]; styleOf: (s: string) => SeriesStyle }) {
  const [period, setPeriod] = useState(() => {
    try { return localStorage.getItem(KEY) ?? "1y"; } catch { return "1y"; }
  });
  const [data, setData] = useState<CompareHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<number | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const key = symbols.join(",");

  useEffect(() => {
    if (!symbols.length) return;
    let stale = false;
    setError(null);
    api.compareHistory(symbols, period).then((d) => !stale && setData(d), (e) => !stale && setError(e.message));
    return () => { stale = true; };
  }, [key, period]); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  const pick = (p: string) => {
    setPeriod(p);
    try { localStorage.setItem(KEY, p); } catch { /* ignore */ }
  };

  // Rebase each series to its first close in the range.
  const series: Record<string, Pt[]> = {};
  for (const s of symbols) {
    const raw = data?.series[s] ?? [];
    if (raw.length) series[s] = raw.map(([d, c]) => ({ d, v: (c / raw[0][1] - 1) * 100 }));
  }
  const dates = [...new Set(Object.values(series).flatMap((pts) => pts.map((p) => p.d)))].sort();
  const all = Object.values(series).flat().map((p) => p.v);
  const lo = Math.min(0, ...all), hi = Math.max(0, ...all);
  const pad = (hi - lo) * 0.06 || 1;
  const yMin = lo - pad, yMax = hi + pad;
  const plotW = Math.max(width - PAD.l - PAD.r, 10), plotH = H - PAD.t - PAD.b;
  const xi = new Map(dates.map((d, i) => [d, i]));
  const x = (d: string) => PAD.l + ((xi.get(d) ?? 0) / Math.max(dates.length - 1, 1)) * plotW;
  const y = (v: number) => PAD.t + (1 - (v - yMin) / (yMax - yMin)) * plotH;
  const ticks = niceTicks(yMin, yMax, 5);
  const xLabels = dates.length ? [0, Math.floor(dates.length / 3), Math.floor((2 * dates.length) / 3), dates.length - 1] : [];
  const fmtDate = (d: string) => new Date(`${d}T12:00:00Z`).toLocaleDateString("en-US", {
    timeZone: "UTC", month: "short", ...(period === "3y" || period === "5y" ? { year: "2-digit" } : { day: "numeric" }) });

  const last = (s: string) => series[s]?.[series[s].length - 1]?.v ?? null;
  const at = (s: string, d: string) => {
    const pts = series[s];
    if (!pts) return null;
    let found: number | null = null;
    for (const p of pts) { if (p.d <= d) found = p.v; else break; }
    return found;
  };
  const hoverDate = hover != null ? dates[hover] : null;
  const ranked = [...symbols].filter((s) => series[s]).sort((a, b) => (last(b) ?? -Infinity) - (last(a) ?? -Infinity));
  const direct = ranked.length <= 4; // few lines: label them at their ends too

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!dates.length) return;
    const r = e.currentTarget.getBoundingClientRect();
    const f = (e.clientX - r.left - PAD.l) / plotW;
    setHover(Math.max(0, Math.min(dates.length - 1, Math.round(f * (dates.length - 1)))));
  };

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Price performance <span className="muted small">· price return since the start of the range, no dividends</span></h2>
        <div className="seg" role="group" aria-label="Range">
          {PERIODS.map(([p, label]) => <button key={p} aria-pressed={period === p} onClick={() => pick(p)}>{label}</button>)}
        </div>
      </div>
      {error ? <div className="error">{error}</div> : (
        <>
          <div className="row small" style={{ gap: 14, flexWrap: "wrap", marginBottom: 6 }} aria-label="Legend">
            {ranked.map((s) => {
              const st = styleOf(s);
              const v = hoverDate ? at(s, hoverDate) : last(s);
              return (
                <span key={s} className="row" style={{ gap: 6 }}>
                  <svg width="18" height="6" aria-hidden><line x1="0" y1="3" x2="18" y2="3" stroke={st.color} strokeWidth="2.5" strokeDasharray={st.dash} /></svg>
                  <strong>{s}</strong><span className="num">{pct(v, 1)}</span>
                </span>
              );
            })}
            {hoverDate && <span className="muted">· {fmtDate(hoverDate)}</span>}
          </div>
          <div ref={box} className="compare-chart" style={{ height: H, opacity: data ? 1 : 0.4 }}>
            {width > 0 && dates.length > 1 && (
              <svg width={width} height={H} onMouseMove={onMove} onMouseLeave={() => setHover(null)} role="img"
                   aria-label={`Price return over ${period}: ${ranked.map((s) => `${s} ${pct(last(s), 1)}`).join(", ")}`}>
                {ticks.map((t) => (
                  <g key={t}>
                    <line x1={PAD.l} x2={PAD.l + plotW} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} strokeWidth={1} />
                    <text x={PAD.l + plotW + 6} y={y(t) + 4} fontSize="11" fill="var(--muted)">{pct(t, 0)}</text>
                  </g>
                ))}
                {xLabels.map((i) => (
                  <text key={i} x={x(dates[i])} y={H - 6} fontSize="11" fill="var(--muted)"
                        textAnchor={i === 0 ? "start" : i === dates.length - 1 ? "end" : "middle"}>{fmtDate(dates[i])}</text>
                ))}
                {ranked.map((s) => {
                  const st = styleOf(s);
                  const d = series[s].map((p, i) => `${i ? "L" : "M"}${x(p.d).toFixed(1)},${y(p.v).toFixed(1)}`).join("");
                  return <path key={s} d={d} fill="none" stroke={st.color} strokeWidth={2} strokeDasharray={st.dash}
                               strokeLinejoin="round" strokeLinecap="round" />;
                })}
                {direct && endLabels(ranked.map((s) => ({ s, y: y(series[s][series[s].length - 1].v) - 6 })), 13).map(({ s, y: ly }) => (
                  <text key={s} x={PAD.l + plotW - 2} y={ly} fontSize="11" fontWeight="600" fill="var(--text-2)" textAnchor="end">{s}</text>
                ))}
                {hoverDate && (
                  <g>
                    <line x1={x(hoverDate)} x2={x(hoverDate)} y1={PAD.t} y2={PAD.t + plotH} stroke="var(--axis)" />
                    {ranked.map((s) => {
                      const v = at(s, hoverDate);
                      return v == null ? null : <circle key={s} cx={x(hoverDate)} cy={y(v)} r={4} fill={styleOf(s).color} stroke="var(--surface)" strokeWidth={2} />;
                    })}
                  </g>
                )}
              </svg>
            )}
            {data && dates.length <= 1 && <p className="muted">No price history for this range.</p>}
          </div>
        </>
      )}
    </section>
  );
}

/** End-of-line labels pushed apart so lines ending close together stay readable. */
function endLabels(items: { s: string; y: number }[], gap: number) {
  const out = [...items].sort((a, b) => a.y - b.y);
  for (let i = 1; i < out.length; i++) if (out[i].y - out[i - 1].y < gap) out[i] = { ...out[i], y: out[i - 1].y + gap };
  return out;
}

function niceTicks(lo: number, hi: number, n: number): number[] {
  const raw = (hi - lo) / n;
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) out.push(Math.round(t * 1e6) / 1e6);
  return out;
}
