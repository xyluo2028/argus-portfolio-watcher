import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type DividendHolding, type EarningsRow } from "../api";
import { big, money, pct, price, ratio, tone } from "../format";

// The first tab is the caller's own view ("Holdings" on a portfolio, "Overview" on the watchlist).
const TABS = ["First", "Financials", "Growth", "Dividends", "Earnings", "Profitability", "Momentum"] as const;
type Tab = (typeof TABS)[number];
type MetricTab = Exclude<Tab, "First">;

/** What a metric row needs to know about a symbol. */
export interface TabRow { symbol: string; name?: string | null; price?: number | null }
/** Where the rows come from; picks the endpoints. */
export type TabSource = { kind: "portfolio"; name: string } | { kind: "watchlist"; name: string };
const POLL_MS = 3000;
const MAX_POLLS = 60; // ~3 minutes: enough for a cold cache under Finnhub's 60 calls/minute

type Metrics = Record<string, number | null>;
type Row = { p: TabRow; m?: Metrics; div?: DividendHolding; earn?: EarningsRow };
type Col = { label: string; title?: string; value: (r: Row) => number | string | null | undefined; cell?: (r: Row) => React.ReactNode };

const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const rel = (a: number | null | undefined, b: number | null | undefined) => (a != null && b ? (a / b - 1) * 100 : null);
/** Signed percent, colored by direction. */
const signed = (key: string): Col["cell"] => (r) => { const v = num(r.m?.[key]); return <span className={tone(v)}>{pct(v, 1)}</span>; };
/** Unsigned percent; negatives still read red. */
const plain = (v: number | null) => (v == null ? "–" : <span className={v < 0 ? "down" : undefined}>{v.toFixed(1)}%</span>);
const metric = (key: string) => (r: Row) => num(r.m?.[key]);

const day = (iso: string | null | undefined) =>
  iso ? new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" }) : "–";
const HOUR: Record<string, string> = { bmo: "pre", amc: "post", dmh: "mid" };

// Watchlists hold no shares: no income or yield on cost.
const NEEDS_SHARES = new Set(["Yield on cost", "Annual income"]);

const COLUMNS: Record<MetricTab, Col[]> = {
  Financials: [
    { label: "Mkt cap", value: metric("market_cap"), cell: (r) => big(num(r.m?.market_cap)) },
    { label: "P/E", title: "Trailing 12 months", value: metric("pe_ttm"), cell: (r) => ratio(num(r.m?.pe_ttm), 1) },
    { label: "Fwd P/E", value: metric("pe_forward"), cell: (r) => ratio(num(r.m?.pe_forward), 1) },
    { label: "PEG", value: metric("peg"), cell: (r) => ratio(num(r.m?.peg)) },
    { label: "P/S", value: metric("ps_ttm"), cell: (r) => ratio(num(r.m?.ps_ttm), 1) },
    { label: "P/B", value: metric("pb"), cell: (r) => ratio(num(r.m?.pb), 1) },
    { label: "EV/EBITDA", value: metric("ev_ebitda"), cell: (r) => ratio(num(r.m?.ev_ebitda), 1) },
    { label: "Debt/Eq", value: metric("debt_to_equity"), cell: (r) => ratio(num(r.m?.debt_to_equity)) },
    { label: "FCF (TTM)", value: metric("fcf_ttm"), cell: (r) => big(num(r.m?.fcf_ttm)) },
  ],
  Growth: [
    { label: "Rev YoY", title: "Revenue, trailing 12 months vs a year earlier", value: metric("revenue_growth_yoy_pct"), cell: signed("revenue_growth_yoy_pct") },
    { label: "Rev Q YoY", title: "Latest quarter vs the same quarter a year earlier", value: metric("revenue_growth_q_yoy_pct"), cell: signed("revenue_growth_q_yoy_pct") },
    { label: "Rev 3Y", title: "3-year annual growth rate", value: metric("revenue_growth_3y_pct"), cell: signed("revenue_growth_3y_pct") },
    { label: "Rev 5Y", title: "5-year annual growth rate", value: metric("revenue_growth_5y_pct"), cell: signed("revenue_growth_5y_pct") },
    { label: "EPS YoY", value: metric("eps_growth_yoy_pct"), cell: signed("eps_growth_yoy_pct") },
    { label: "EPS Q YoY", value: metric("eps_growth_q_yoy_pct"), cell: signed("eps_growth_q_yoy_pct") },
    { label: "EPS 3Y", value: metric("eps_growth_3y_pct"), cell: signed("eps_growth_3y_pct") },
    { label: "EPS 5Y", value: metric("eps_growth_5y_pct"), cell: signed("eps_growth_5y_pct") },
  ],
  Dividends: [
    { label: "Yield", value: (r) => (r.div?.pays ? r.div.yield_pct : null), cell: (r) => (r.div?.pays && r.div.yield_pct != null ? `${r.div.yield_pct.toFixed(2)}%` : "–") },
    { label: "Annual / sh", title: "Latest payment × payments per year", value: (r) => (r.div?.pays ? r.div.rate : null),
      cell: (r) => (r.div?.pays ? `$${r.div.rate.toFixed(r.div.rate < 1 ? 3 : 2)}` : "–") },
    { label: "Frequency", value: (r) => r.div?.frequency ?? null, cell: (r) => r.div?.frequency ?? "–" },
    { label: "Yield on cost", value: (r) => (r.div?.pays ? r.div.yield_on_cost_pct : null),
      cell: (r) => (r.div?.pays && r.div.yield_on_cost_pct != null ? `${r.div.yield_on_cost_pct.toFixed(2)}%` : "–") },
    { label: "Payout", title: "Dividends as a share of earnings (TTM)", value: metric("payout_ratio_pct"), cell: (r) => plain(num(r.m?.payout_ratio_pct)) },
    { label: "Div growth 5Y", title: "5-year annual dividend growth", value: metric("dividend_growth_5y_pct"), cell: signed("dividend_growth_5y_pct") },
    { label: "Next ex-date", title: "Estimated from the payment rhythm", value: (r) => r.div?.next_ex_date_est ?? null,
      cell: (r) => (r.div?.next_ex_date_est ? `~${day(r.div.next_ex_date_est)}` : "–") },
    { label: "Annual income", value: (r) => (r.div?.pays ? r.div.annual_income : null), cell: (r) => (r.div?.pays ? money(r.div.annual_income) : "–") },
  ],
  Earnings: [
    { label: "Last report", title: "Report date, or the fiscal quarter when only EPS history is available",
      value: (r) => r.earn?.last?.date ?? r.earn?.last?.period ?? null,
      cell: (r) => { const l = r.earn?.last; return !l ? "–" : l.date ? day(l.date) : l.quarter && l.year ? `Q${l.quarter} FY${String(l.year).slice(2)}` : day(l.period); } },
    { label: "EPS", value: (r) => r.earn?.last?.epsActual ?? null, cell: (r) => ratio(r.earn?.last?.epsActual) },
    { label: "Est.", value: (r) => r.earn?.last?.epsEstimate ?? null, cell: (r) => ratio(r.earn?.last?.epsEstimate) },
    { label: "Surprise", value: (r) => r.earn?.last?.epsSurprisePct ?? null,
      cell: (r) => { const v = r.earn?.last?.epsSurprisePct ?? null; return <span className={tone(v)}>{pct(v, 1)}</span>; } },
    { label: "Next report", value: (r) => r.earn?.next?.date ?? null,
      cell: (r) => { const n = r.earn?.next; return !n ? "–" : <>{day(n.date)}{n.hour && HOUR[n.hour] ? <span className="muted"> · {HOUR[n.hour]}</span> : null}</>; } },
    { label: "EPS est.", value: (r) => r.earn?.next?.epsEstimate ?? null, cell: (r) => ratio(r.earn?.next?.epsEstimate) },
    { label: "Rev est.", value: (r) => r.earn?.next?.revenueEstimate ?? null, cell: (r) => big(r.earn?.next?.revenueEstimate) },
  ],
  Profitability: [
    { label: "Gross", value: metric("gross_margin_pct"), cell: (r) => plain(num(r.m?.gross_margin_pct)) },
    { label: "Operating", value: metric("operating_margin_pct"), cell: (r) => plain(num(r.m?.operating_margin_pct)) },
    { label: "Net", value: metric("net_margin_pct"), cell: (r) => plain(num(r.m?.net_margin_pct)) },
    { label: "FCF margin", title: "Free cash flow ÷ revenue (TTM)",
      value: (r) => { const f = num(r.m?.fcf_ttm), rev = num(r.m?.revenue_ttm); return f != null && rev ? (f / rev) * 100 : null; },
      cell: (r) => { const f = num(r.m?.fcf_ttm), rev = num(r.m?.revenue_ttm); return plain(f != null && rev ? (f / rev) * 100 : null); } },
    { label: "ROE", value: metric("roe_pct"), cell: (r) => plain(num(r.m?.roe_pct)) },
    { label: "ROA", value: metric("roa_pct"), cell: (r) => plain(num(r.m?.roa_pct)) },
    { label: "ROI", title: "Return on invested capital", value: metric("roi_pct"), cell: (r) => plain(num(r.m?.roi_pct)) },
  ],
  Momentum: [
    { label: "1W", value: metric("return_1w_pct"), cell: signed("return_1w_pct") },
    { label: "1M", title: "Last month, to the latest daily close", value: metric("return_1m_pct"), cell: signed("return_1m_pct") },
    { label: "3M", value: metric("return_3m_pct"), cell: signed("return_3m_pct") },
    { label: "6M", value: metric("return_6m_pct"), cell: signed("return_6m_pct") },
    { label: "YTD", value: metric("return_ytd_price_pct"), cell: signed("return_ytd_price_pct") },
    { label: "1Y", value: metric("return_1y_pct"), cell: signed("return_1y_pct") },
    { label: "vs S&P 1Y", title: "1-year return relative to the S&P 500", value: metric("rel_sp500_1y_pct"), cell: signed("rel_sp500_1y_pct") },
    { label: "From 52W high", value: (r) => rel(r.p.price, num(r.m?.high_52w)),
      cell: (r) => { const v = rel(r.p.price, num(r.m?.high_52w)); return <span className={tone(v)}>{pct(v, 1)}</span>; } },
    { label: "vs 50D avg", value: (r) => rel(r.p.price, num(r.m?.sma50)),
      cell: (r) => { const v = rel(r.p.price, num(r.m?.sma50)); return <span className={tone(v)}>{pct(v, 1)}</span>; } },
    { label: "vs 200D avg", value: (r) => rel(r.p.price, num(r.m?.sma200)),
      cell: (r) => { const v = rel(r.p.price, num(r.m?.sma200)); return <span className={tone(v)}>{pct(v, 1)}</span>; } },
  ],
};

const NOTES: Partial<Record<Tab, string>> = {
  Financials: "Valuation and balance sheet from Finnhub and Yahoo, refreshed daily.",
  Growth: "YoY = trailing 12 months (or the latest quarter) vs a year earlier; 3Y/5Y are annual growth rates.",
  Dividends: "Annual rate = latest payment × payments per year; yields use the live price.",
  Earnings: "Pre = before the open, post = after the close. Older reports show the fiscal quarter instead of a date.",
  Profitability: "Trailing 12 months.",
  Momentum: "Returns to the last daily close; distance from the high and the 50/200-day averages use the live price.",
};

/** One request for the whole portfolio. The server answers from its cache (stale values included)
 * and refreshes missing or stale symbols in the background; poll while it reports them pending. */
function useFundamentals(source: TabSource, enabled: boolean) {
  const key = `${source.kind}:${source.name}`;
  const [data, setData] = useState<{ metrics: Record<string, Metrics>; pending: string[] } | null>(null);
  useEffect(() => { setData(null); }, [key]);
  useEffect(() => {
    if (!enabled) return;
    let stop = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = (polls: number) => {
      (source.kind === "portfolio" ? api.portfolioFundamentals(source.name) : api.watchlistFundamentals(source.name)).then((r) => {
        if (stop) return;
        setData({ metrics: r.metrics, pending: r.pending });
        if (r.pending.length && polls < MAX_POLLS) timer = setTimeout(() => load(polls + 1), POLL_MS);
      }, () => { if (!stop) setData((d) => d ?? { metrics: {}, pending: [] }); });
    };
    load(0);
    return () => { stop = true; clearTimeout(timer); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, enabled]);
  return data;
}

/** Tabbed per-symbol views. `first` is the caller's own tab (its label and content); the rest are
 * shared metric tables fed by the portfolio's or the watchlist's endpoints. */
export function HoldingsTabs({ source, rows, first }: {
  source: TabSource; rows: TabRow[]; first: { label: string; content: React.ReactNode };
}) {
  const tabKey = `argus.tabs.${source.kind}`;
  const [tab, setTab] = useState<Tab>(() => {
    try {
      const t = localStorage.getItem(tabKey) as Tab | null;
      return t && TABS.includes(t) ? t : "First";
    } catch {
      return "First";
    }
  });
  const pick = (t: Tab) => {
    setTab(t);
    try { localStorage.setItem(tabKey, t); } catch { /* ignore */ }
  };

  const symbols = useMemo(() => rows.map((p) => p.symbol).sort(), [rows]);
  const needsMetrics = ["Financials", "Growth", "Dividends", "Profitability", "Momentum"].includes(tab);
  const fund = useFundamentals(source, needsMetrics);
  const metrics = fund?.metrics ?? {};

  const sourceKey = `${source.kind}:${source.name}`;
  const [divs, setDivs] = useState<Record<string, DividendHolding> | null>(null);
  const [earn, setEarn] = useState<Record<string, EarningsRow> | null>(null);
  useEffect(() => { setDivs(null); setEarn(null); }, [sourceKey, symbols.join(",")]);
  useEffect(() => {
    const isPf = source.kind === "portfolio";
    if (tab === "Dividends" && divs === null) {
      (isPf ? api.dividends(source.name) : api.watchlistDividends(source.name))
        .then((d) => setDivs(Object.fromEntries(d.holdings.map((h) => [h.symbol, h]))), () => setDivs({}));
    }
    if (tab === "Earnings" && earn === null) {
      (isPf ? api.earnings(source.name) : api.watchlistEarnings(source.name))
        .then((d) => setEarn(Object.fromEntries(d.rows.map((r) => [r.symbol, r]))), () => setEarn({}));
    }
  }, [tab, sourceKey, divs, earn]); // eslint-disable-line react-hooks/exhaustive-deps

  const pendingCount = fund ? fund.pending.length : symbols.length;
  const waiting =
    tab === "Dividends" && divs === null ? "Loading dividend history…"
    : tab === "Earnings" && earn === null ? "Loading earnings dates…"
    : needsMetrics && !fund ? "Loading metrics…"
    : needsMetrics && pendingCount ? `Updating metrics ${symbols.length - pendingCount}/${symbols.length}…` : null;
  const cols = tab === "First" ? [] : COLUMNS[tab].filter((c) => source.kind === "portfolio" || !NEEDS_SHARES.has(c.label));

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
        <div className="seg tabs" role="tablist" aria-label="Views">
          {TABS.map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} aria-pressed={tab === t} onClick={() => pick(t)}>
              {t === "First" ? first.label : t}
            </button>
          ))}
        </div>
        {waiting && <span className="small muted">{waiting}</span>}
      </div>
      {tab === "First" ? first.content : (
        <MetricTable cols={cols} note={NOTES[tab]}
                     rows={rows.map((p) => ({ p, m: metrics[p.symbol], div: divs?.[p.symbol], earn: earn?.[p.symbol] }))} />
      )}
    </section>
  );
}

function MetricTable({ cols, rows, note }: { cols: Col[]; rows: Row[]; note?: string }) {
  const [sort, setSort] = useState<{ i: number; dir: 1 | -1 } | null>(null);
  const navigate = useNavigate();
  useEffect(() => setSort(null), [cols]);

  const sorted = useMemo(() => {
    if (!sort) return rows; // portfolio order (by value)
    const v = (r: Row) => cols[sort.i].value(r);
    return [...rows].sort((a, b) => {
      const x = v(a), y = v(b);
      if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1; // blanks last either way
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
    });
  }, [rows, cols, sort]);

  return (
    <>
      <div className="table-wrap">
        <table className="metric-table">
          <thead>
            <tr>
              <th>Symbol</th><th>Price</th>
              {cols.map((c, i) => (
                <th key={c.label} title={c.title} onClick={() => setSort((s) => (s?.i === i ? { i, dir: (s.dir * -1) as 1 | -1 } : { i, dir: -1 }))}
                    aria-sort={sort?.i === i ? (sort.dir === 1 ? "ascending" : "descending") : undefined}>
                  {c.label}{sort?.i === i ? (sort.dir === 1 ? " ↑" : " ↓") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr key={r.p.symbol} tabIndex={0} onClick={() => navigate(`/t/${r.p.symbol}`)}
                  onKeyDown={(e) => e.key === "Enter" && navigate(`/t/${r.p.symbol}`)}>
                <td><span className="sym">{r.p.symbol}</span><span className="name" title={r.p.name ?? undefined}>{r.p.name ?? ""}</span></td>
                <td>{price(r.p.price)}</td>
                {cols.map((c) => <td key={c.label}>{c.cell ? c.cell(r) : String(c.value(r) ?? "–")}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {note && <p className="small muted" style={{ margin: "8px 0 0" }}>{note}</p>}
    </>
  );
}
