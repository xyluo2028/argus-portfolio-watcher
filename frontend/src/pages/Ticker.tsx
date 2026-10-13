import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ApiError,
  api,
  type Fundamentals,
  type HistoryResponse,
  type Position,
  type Quote,
  type ReturnBases,
  type StreamUpdate,
} from "../api";
import { CandleChart, OVERLAY_COLOR, type Overlay, type Pane } from "../components/CandleChart";
import { CompanyCard } from "../components/CompanyCard";
import { EventsCard } from "../components/EventsCard";
import { FinancialsCard } from "../components/FinancialsCard";
import { HoldingsCard } from "../components/HoldingsCard";
import { PeersCard } from "../components/PeersCard";
import { ResearchCard } from "../components/ResearchCard";
import { PositionCard } from "../components/PositionCard";
import { SymbolNotes } from "../components/SymbolNotes";
import { extLabel, nyTime, pct, price, quoteTime, tone } from "../format";
import { GROUPS, METRICS, formatMetric, metricTone, metricValue, type GroupName } from "../metrics";

const RANGES = [
  { label: "1D", period: "1d", interval: "5m" },
  { label: "5D", period: "5d", interval: "15m" },
  { label: "1M", period: "1mo", interval: "1d" },
  { label: "3M", period: "3mo", interval: "1d" },
  { label: "6M", period: "6mo", interval: "1d" },
  { label: "YTD", period: "ytd", interval: "1d" },
  { label: "1Y", period: "1y", interval: "1d" },
  { label: "5Y", period: "5y", interval: "1d" },
  { label: "Max", period: "max", interval: "1d" },
] as const;

const OVERLAYS: { key: Overlay; label: string }[] = [
  { key: "sma20", label: "SMA 20" }, { key: "sma50", label: "SMA 50" },
  { key: "sma200", label: "SMA 200" }, { key: "bb20", label: "Bollinger 20" },
];
const PANES: { key: Pane; label: string }[] = [
  { key: "volume", label: "Volume" }, { key: "rsi14", label: "RSI 14" }, { key: "macd", label: "MACD" },
];

// Same indicators, names and groups as the dashboard's tabs (src/metrics.ts).
const SECTIONS: { group: GroupName; title: string }[] = [
  { group: "Financials", title: "Valuation & size" }, { group: "Growth", title: "Growth" },
  { group: "Profitability", title: "Profitability" }, { group: "Momentum", title: "Momentum" },
  { group: "Dividends & risk", title: "Dividends & risk" }, { group: "Fund", title: "Fund" },
];

export function Ticker({ portfolio, live }: { portfolio: string; live: StreamUpdate | null }) {
  const symbol = (useParams().symbol ?? "").toUpperCase();
  const [range, setRange] = useState<(typeof RANGES)[number]>(RANGES.find((r) => r.label === "1Y")!);
  const [bases, setBases] = useState<ReturnBases | null>(null);
  const [overlays, setOverlays] = useState<Overlay[]>(["sma50", "sma200"]);
  const [panes, setPanes] = useState<Pane[]>(["volume"]);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [historyErr, setHistoryErr] = useState<ApiError | null>(null);
  const [fund, setFund] = useState<Fundamentals | null>(null);
  const [position, setPosition] = useState<Position | null>(null);
  const [polled, setPolled] = useState<Quote | null>(null);

  const indicators = useMemo(() => [...overlays, ...panes.filter((p) => p !== "volume")], [overlays, panes]);

  useEffect(() => {
    let stale = false;
    setHistoryErr(null);
    api.history(symbol, range.period, range.interval, indicators).then(
      (h) => !stale && setHistory(h), (e) => !stale && setHistoryErr(e));
    return () => { stale = true; };
  }, [symbol, range, indicators]);

  const loadPosition = useCallback(() => {
    api.portfolio(portfolio).then(
      (s) => setPosition(s.positions.find((p) => p.symbol === symbol) ?? null), () => setPosition(null));
  }, [symbol, portfolio]);

  useEffect(() => {
    setFund(null);
    api.fundamentals(symbol).then(setFund, () => setFund(null));
  }, [symbol]);
  useEffect(loadPosition, [loadPosition]);

  // Held/watched symbols arrive over the stream; anything else is polled.
  const streamed = live?.quotes[symbol];
  useEffect(() => {
    if (streamed) return;
    const load = () => api.quotes([symbol]).then((r) => setPolled(r.quotes[0] ?? null), () => undefined);
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [symbol, streamed]);
  const quote = streamed ?? polled;

  // Each range's base price comes from the server; the return itself follows the live price.
  const session = live?.market.session;
  useEffect(() => {
    let stale = false;
    setBases(null);
    api.returnBases(symbol).then((b) => !stale && setBases(b), () => undefined);
    return () => { stale = true; };
  }, [symbol, session]);
  const rangeReturn = (label: string): number | null => {
    const now = quote?.price ?? bases?.last_close?.close;
    const base = label === "1D" ? (quote?.prev_close ?? bases?.bases["1D"]?.close) : bases?.bases[label]?.close;
    return now != null && base ? (now / base - 1) * 100 : null;
  };

  const toggle = <T,>(list: T[], item: T) => (list.includes(item) ? list.filter((x) => x !== item) : [...list, item]);
  const m = fund?.metrics ?? {};
  const high52 = m.high_52w, low52 = m.low_52w;

  return (
    <div className="stack">
      <div className="row small"><Link to="/" className="muted">← Dashboard</Link></div>
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <div className="hero-label">{symbol}{position?.name ? ` · ${position.name}` : ""}{position?.sector ? ` · ${position.sector}` : ""}</div>
            <div className="hero-value">{price(quote?.price)}</div>
            <div className={`hero-delta ${tone(quote?.change)}`}>
              {quote?.change == null ? "–" : `${quote.change > 0 ? "+" : quote.change < 0 ? "−" : ""}${Math.abs(quote.change).toFixed(2)}`} ({pct(quote?.change_pct)})
              <span className="muted small"> {quote ? `· ${quoteTime(quote, live?.market.session ?? "closed")} · ${quote.source}` : ""}</span>
            </div>
            {quote?.ext_price != null && (
              <div className="ext-hero">
                <span className="muted">{extLabel(quote.ext_session)}</span>{" "}
                <span className="num">{price(quote.ext_price)}</span>{" "}
                <span className={tone(quote.ext_change)}>
                  {`${quote.ext_change! > 0 ? "+" : quote.ext_change! < 0 ? "−" : ""}${Math.abs(quote.ext_change!).toFixed(2)}`} ({pct(quote.ext_change_pct)})
                </span>
                <span className="muted small"> · {nyTime(quote.ext_as_of!)}</span>
              </div>
            )}
          </div>
          {high52 != null && low52 != null && quote && (
            <div className="small text-2" style={{ minWidth: 220 }}>
              52-week range
              <div style={{ position: "relative", height: 6, background: "var(--grid)", borderRadius: 3, margin: "6px 0" }}>
                <div style={{ position: "absolute", top: -3, width: 12, height: 12, borderRadius: "50%", background: "var(--series-1)",
                  boxShadow: "0 0 0 2px var(--surface)",
                  left: `calc(${Math.min(100, Math.max(0, ((quote.price - low52) / (high52 - low52)) * 100))}% - 6px)` }} />
              </div>
              <div className="row num" style={{ justifyContent: "space-between" }}><span>{price(low52)}</span><span>{price(high52)}</span></div>
            </div>
          )}
        </div>
      </section>

      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <div className="seg ranges" role="group" aria-label="Range">
            {RANGES.map((r) => {
              const ret = rangeReturn(r.label);
              const base = r.label === "1D" ? null : bases?.bases[r.label];
              return (
                <button key={r.label} aria-pressed={r.label === range.label} onClick={() => setRange(r)}
                        title={base ? `Price return since the ${base.date} close (${price(base.close)}); dividends not included` : undefined}>
                  <span>{r.label}</span>
                  <span className={`ret ${tone(ret)}`}>
                    {ret == null ? "–" : Math.abs(ret) >= 1000 ? `${ret > 0 ? "+" : "−"}${Math.round(Math.abs(ret)).toLocaleString("en-US")}%` : pct(ret, 1)}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="row">
            {OVERLAYS.map((o) => (
              <button key={o.key} className="chip" aria-pressed={overlays.includes(o.key)}
                      onClick={() => setOverlays((l) => toggle(l, o.key))}>
                <span className="key" style={{ background: OVERLAY_COLOR[o.key] }} />{o.label}
              </button>
            ))}
            {PANES.map((p) => (
              <button key={p.key} className="chip" aria-pressed={panes.includes(p.key)}
                      onClick={() => setPanes((l) => toggle(l, p.key))}>{p.label}</button>
            ))}
          </div>
        </div>
        {historyErr ? <div className="error">{historyErr.message}</div>
          : history ? <CandleChart data={history} overlays={overlays} panes={panes} live={quote} />
          : <div className="chart-box muted">Loading chart…</div>}
      </section>

      <CompanyCard symbol={symbol} />
      <HoldingsCard symbol={symbol} />

      <section className="card">
        <h2>Valuation &amp; fundamentals {fund && <span className="muted small">· as of {nyTime(fund.as_of)} · same figures as the dashboard tabs</span>}</h2>
        {fund ? (
          <div className="fund-groups">
            {SECTIONS.map(({ group, title }) => {
              const keys = GROUPS[group].filter((k) => metricValue(k, m, quote?.price) != null);
              if (keys.length === 0) return null;
              return (
                <div key={group}>
                  <h3 className="sub">{title}</h3>
                  <dl className="kv">
                    {keys.map((k) => {
                      const v = metricValue(k, m, quote?.price), d = METRICS[k];
                      const src = fund.sources[k] ? `source: ${fund.sources[k]}` : undefined;
                      return (
                        <div key={k} title={[d.title, src].filter(Boolean).join(" · ") || undefined}>
                          <dt>{d.label}</dt><dd className={metricTone(k, v)}>{formatMetric(k, v)}</dd>
                        </div>
                      );
                    })}
                  </dl>
                </div>
              );
            })}
          </div>
        ) : <p className="muted">Loading…</p>}
      </section>

      <section>

        <PositionCard symbol={symbol} portfolio={portfolio} position={position} lastPrice={quote?.price}
                      onChanged={loadPosition} />
      </section>

      <PeersCard symbol={symbol} />
      <ResearchCard symbol={symbol} />

      <SymbolNotes symbol={symbol} />
      <EventsCard symbol={symbol} />

      <FinancialsCard symbol={symbol} />
    </div>
  );
}
