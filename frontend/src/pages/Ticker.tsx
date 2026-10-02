import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ApiError,
  api,
  type Financials,
  type Fundamentals,
  type HistoryResponse,
  type Position,
  type Quote,
  type StreamUpdate,
} from "../api";
import { CandleChart, OVERLAY_COLOR, type Overlay, type Pane } from "../components/CandleChart";
import { CompanyCard } from "../components/CompanyCard";
import { EventsCard } from "../components/EventsCard";
import { PeersCard } from "../components/PeersCard";
import { PositionCard } from "../components/PositionCard";
import { RevenueColumns } from "../components/RevenueColumns";
import { SymbolNotes } from "../components/SymbolNotes";
import { big, money, nyTime, pct, price, quoteTime, ratio, tone } from "../format";

const RANGES = [
  { label: "1D", period: "1d", interval: "5m" },
  { label: "5D", period: "5d", interval: "15m" },
  { label: "1M", period: "1mo", interval: "1d" },
  { label: "3M", period: "3mo", interval: "1d" },
  { label: "6M", period: "6mo", interval: "1d" },
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

const STATS: { key: string; label: string; fmt: (v: number | null | undefined) => string }[] = [
  { key: "market_cap", label: "Market cap", fmt: big },
  { key: "pe_ttm", label: "P/E (TTM)", fmt: ratio },
  { key: "pe_forward", label: "P/E (forward)", fmt: ratio },
  { key: "peg", label: "PEG", fmt: ratio },
  { key: "pb", label: "P/B", fmt: ratio },
  { key: "ps_ttm", label: "P/S (TTM)", fmt: ratio },
  { key: "ev_ebitda", label: "EV/EBITDA", fmt: ratio },
  { key: "eps_ttm", label: "EPS (TTM)", fmt: (v) => money(v) },
  { key: "revenue_ttm", label: "Revenue (TTM)", fmt: big },
  { key: "revenue_growth_yoy_pct", label: "Revenue growth YoY", fmt: (v) => pct(v, 1) },
  { key: "gross_margin_pct", label: "Gross margin", fmt: (v) => (v == null ? "–" : `${v.toFixed(1)}%`) },
  { key: "operating_margin_pct", label: "Operating margin", fmt: (v) => (v == null ? "–" : `${v.toFixed(1)}%`) },
  { key: "net_margin_pct", label: "Net margin", fmt: (v) => (v == null ? "–" : `${v.toFixed(1)}%`) },
  { key: "roe_pct", label: "ROE", fmt: (v) => (v == null ? "–" : `${v.toFixed(1)}%`) },
  { key: "fcf_ttm", label: "Free cash flow", fmt: big },
  { key: "debt_to_equity", label: "Debt/Equity", fmt: ratio },
  { key: "dividend_yield_pct", label: "Dividend yield", fmt: (v) => (v == null ? "–" : `${v.toFixed(2)}%`) },
  { key: "beta", label: "Beta", fmt: ratio },
  { key: "expense_ratio_pct", label: "Expense ratio", fmt: (v) => (v == null ? "–" : `${v.toFixed(2)}%`) },
];

export function Ticker({ portfolio, live }: { portfolio: string; live: StreamUpdate | null }) {
  const symbol = (useParams().symbol ?? "").toUpperCase();
  const [range, setRange] = useState<(typeof RANGES)[number]>(RANGES[5]);
  const [overlays, setOverlays] = useState<Overlay[]>(["sma50", "sma200"]);
  const [panes, setPanes] = useState<Pane[]>(["volume"]);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [historyErr, setHistoryErr] = useState<ApiError | null>(null);
  const [fund, setFund] = useState<Fundamentals | null>(null);
  const [fin, setFin] = useState<Financials | null>(null);
  const [finErr, setFinErr] = useState<ApiError | null>(null);
  const [finPeriod, setFinPeriod] = useState<"quarterly" | "annual">("quarterly");
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

  useEffect(() => {
    setFinErr(null);
    api.financials(symbol, finPeriod).then(setFin, (e) => { setFin(null); setFinErr(e); });
  }, [symbol, finPeriod]);

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
          <div className="seg" role="group" aria-label="Range">
            {RANGES.map((r) => (
              <button key={r.label} aria-pressed={r.label === range.label} onClick={() => setRange(r)}>{r.label}</button>
            ))}
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

      <section className="grid-2">
        <div className="card">
          <h2>Valuation &amp; fundamentals {fund && <span className="muted small">· as of {nyTime(fund.as_of)}</span>}</h2>
          {fund ? (
            <div className="stats">
              {STATS.filter((s) => m[s.key] != null).map((s) => (
                <div className="stat" key={s.key} title={fund.sources[s.key] ? `source: ${fund.sources[s.key]}` : undefined}>
                  <div className="k">{s.label}</div>
                  <div className="v">{s.fmt(m[s.key])}</div>
                </div>
              ))}
            </div>
          ) : <p className="muted">Loading…</p>}
        </div>

        <PositionCard symbol={symbol} portfolio={portfolio} position={position} lastPrice={quote?.price}
                      onChanged={loadPosition} />
      </section>

      <PeersCard symbol={symbol} />

      <SymbolNotes symbol={symbol} />
      <EventsCard symbol={symbol} />

      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Reported financials {fin?.company ? <span className="muted small">· {fin.company} · SEC EDGAR</span> : null}</h2>
          <div className="seg">
            {(["quarterly", "annual"] as const).map((p) => (
              <button key={p} aria-pressed={finPeriod === p} onClick={() => setFinPeriod(p)}>{p === "quarterly" ? "Quarterly" : "Annual"}</button>
            ))}
          </div>
        </div>
        {finErr ? <p className="muted">{finErr.message}</p> : fin ? (
          <>
            <RevenueColumns periods={fin.periods} />
            <div className="table-wrap">
              <table>
                <thead><tr><th>Period end</th><th>Revenue</th><th>Gross %</th><th>Operating %</th><th>Net income</th><th>EPS (dil.)</th><th>FCF</th></tr></thead>
                <tbody>
                  {fin.periods.map((p) => (
                    <tr key={p.period_end} style={{ cursor: "default" }}>
                      <td>{p.period_end}</td><td>{big(p.revenue)}</td>
                      <td>{p.gross_margin_pct == null ? "–" : p.gross_margin_pct.toFixed(1)}</td>
                      <td>{p.operating_margin_pct == null ? "–" : p.operating_margin_pct.toFixed(1)}</td>
                      <td className={tone(p.net_income)}>{big(p.net_income)}</td>
                      <td>{p.eps_diluted == null ? "–" : p.eps_diluted.toFixed(2)}</td>
                      <td>{big(p.free_cash_flow)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : <p className="muted">Loading…</p>}
      </section>
    </div>
  );
}
