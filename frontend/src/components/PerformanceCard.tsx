import { ColorType, createChart, LineSeries, type MouseEventParams, type Time } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { ApiError, api, type Performance } from "../api";
import { money, pct, tone } from "../format";

const RANGES = [
  { key: "1mo", label: "1M" }, { key: "3mo", label: "3M" }, { key: "ytd", label: "YTD" },
  { key: "1y", label: "1Y" }, { key: "all", label: "All" },
] as const;

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

/** Portfolio TWR vs benchmark, both rebased to 0% on one percent axis (never two y-scales). */
export function PerformanceCard({ portfolio, refreshKey }: { portfolio: string; refreshKey: string }) {
  const [range, setRange] = useState<string>("all");
  const [perf, setPerf] = useState<Performance | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [hover, setHover] = useState<{ d: string; p: number; b: number | null } | null>(null);
  const [themeTick, setThemeTick] = useState(0);
  const el = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bump = () => setThemeTick((t) => t + 1);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", bump);
    window.addEventListener("argus-theme", bump);
    return () => { mq.removeEventListener("change", bump); window.removeEventListener("argus-theme", bump); };
  }, []);

  useEffect(() => {
    let stale = false;
    setError(null);
    api.performance(portfolio, range).then((p) => !stale && setPerf(p), (e) => !stale && setError(e));
    return () => { stale = true; };
  }, [portfolio, range, refreshKey]);

  useEffect(() => {
    if (!el.current || !perf || perf.series.length === 0) return;
    const chart = createChart(el.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: css("--surface") }, textColor: css("--muted"),
        fontFamily: css("--font"), attributionLogo: false },
      grid: { vertLines: { visible: false }, horzLines: { color: css("--grid") } },
      rightPriceScale: { borderColor: css("--axis") },
      timeScale: { borderColor: css("--axis") },
      localization: { priceFormatter: (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(1)}%` },
      handleScroll: false,
      handleScale: false,
    });
    const common = { lineWidth: 2 as const, priceLineVisible: false, crosshairMarkerRadius: 4 };
    // Emphasis: the portfolio carries the accent; the benchmark is the muted reference.
    const port = chart.addSeries(LineSeries, { ...common, color: css("--series-1"), title: perf.portfolio });
    const bench = chart.addSeries(LineSeries, { ...common, color: css("--muted"), title: perf.benchmark });
    port.setData(perf.series.map((s) => ({ time: s.d as Time, value: s.twr_pct })));
    bench.setData(perf.series.flatMap((s) => (s.bench_pct == null ? [] : [{ time: s.d as Time, value: s.bench_pct }])));
    chart.timeScale().fitContent();
    const onMove = (p: MouseEventParams) => {
      const s = p.time ? perf.series.find((x) => x.d === p.time) : undefined;
      setHover(s ? { d: s.d, p: s.twr_pct, b: s.bench_pct } : null);
    };
    chart.subscribeCrosshairMove(onMove);
    return () => { chart.unsubscribeCrosshairMove(onMove); chart.remove(); };
  }, [perf, themeTick]);

  const s = perf?.summary ?? {};
  const last = perf?.series[perf.series.length - 1];
  const shown = hover ?? (last ? { d: last.d, p: last.twr_pct, b: last.bench_pct } : null);

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Performance vs {perf?.benchmark ?? "benchmark"}
          <span className="muted small"> · time-weighted{perf?.provisional_today ? " · today is provisional" : ""}</span></h2>
        <div className="seg" role="group" aria-label="Range">
          {RANGES.map((r) => (
            <button key={r.key} aria-pressed={range === r.key} onClick={() => setRange(r.key)}>{r.label}</button>
          ))}
        </div>
      </div>
      {error ? <div className="error">{error.message}</div> : !perf ? <p className="muted">Loading performance…</p> : (
        <>
          <div className="stats" style={{ marginBottom: 12 }}>
            <div className="stat"><div className="k">Return</div><div className={`v ${tone(s.twr_pct)}`}>{pct(s.twr_pct)}</div></div>
            <div className="stat"><div className="k">{perf.benchmark}</div><div className={`v ${tone(s.benchmark_pct)}`}>{pct(s.benchmark_pct)}</div></div>
            <div className="stat"><div className="k">Excess return</div><div className={`v ${tone(s.excess_pct)}`}>{pct(s.excess_pct)}</div></div>
            <div className="stat"><div className="k">Gain</div><div className={`v ${tone(s.gain)}`}>{money(s.gain, { signed: true, whole: true })}</div></div>
            <div className="stat"><div className="k">Max drawdown</div><div className="v">{pct(s.max_drawdown_pct)}</div></div>
            <div className="stat"><div className="k">Volatility (ann.)</div><div className="v">{s.volatility_pct == null ? "–" : `${s.volatility_pct.toFixed(1)}%`}</div></div>
          </div>
          {/* Legend (two series), with values for the hovered or latest day. */}
          <div className="row small" style={{ gap: 16, marginBottom: 4 }} aria-live="polite">
            <span className="muted">{shown?.d}</span>
            <span className="row" style={{ gap: 6 }}><span className="key" style={{ width: 12, height: 2, background: "var(--series-1)", display: "inline-block" }} />
              {perf.portfolio} <strong className="num">{pct(shown?.p)}</strong></span>
            <span className="row" style={{ gap: 6 }}><span className="key" style={{ width: 12, height: 2, background: "var(--muted)", display: "inline-block" }} />
              {perf.benchmark} <strong className="num">{pct(shown?.b)}</strong></span>
          </div>
          <div ref={el} style={{ height: 260 }} />
          <p className="small muted" style={{ marginBottom: 0 }}>
            Since {s.start}. Buys and holdings you already owned count as money in, so adding money isn't performance.
          </p>
        </>
      )}
    </section>
  );
}
