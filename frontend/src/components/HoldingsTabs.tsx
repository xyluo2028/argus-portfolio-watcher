import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type DividendHolding, type EarningsRow } from "../api";
import { big, money, pct, price, ratio, tone } from "../format";
import { COMPARE_MAX, compareUrl } from "../compareSessions";
import { GROUPS, METRICS, formatMetric, metricTone, metricValue } from "../metrics";

/** Rows picked (with checkboxes) to send to Compare. */
export interface Selection { has: (symbol: string) => boolean; toggle: (symbol: string) => void; full: boolean }

/** The checkbox cell of a pickable row (clicks don't open the row). */
export function PickCell({ symbol, sel }: { symbol: string; sel: Selection }) {
  const on = sel.has(symbol);
  return (
    <td className="pick" onClick={(e) => e.stopPropagation()}>
      <input type="checkbox" checked={on} disabled={!on && sel.full} aria-label={`Select ${symbol} to compare`}
             title={!on && sel.full ? `Compare takes up to ${COMPARE_MAX}` : `Select ${symbol} to compare`}
             onChange={() => sel.toggle(symbol)} onKeyDown={(e) => e.stopPropagation()} />
    </td>
  );
}

// The first tab is the caller's own view ("Holdings" on a portfolio, "Overview" on the watchlist);
// callers may add more of their own (e.g. "Heatmap") before the metric tabs.
const METRIC_TABS = ["Financials", "Growth", "Dividends", "Earnings", "Profitability", "Momentum"] as const;
type MetricTab = (typeof METRIC_TABS)[number];
type Tab = "First" | MetricTab | `view:${string}`;
const isMetricTab = (t: Tab): t is MetricTab => (METRIC_TABS as readonly string[]).includes(t);

/** What a metric row needs to know about a symbol. */
export interface TabRow { symbol: string; name?: string | null; price?: number | null;
  sector?: string | null; type?: string | null; market_value?: number | null }

const isFund = (r: TabRow) => r.type === "ETP" || r.sector === "ETF";
type Kind = "all" | "stocks" | "etfs";
const KINDS: [Kind, string][] = [["all", "All"], ["stocks", "Stocks"], ["etfs", "ETFs"]];
const ofKind = (r: TabRow, kind: Kind) => kind === "all" || (kind === "etfs") === isFund(r);
type Filter = { sector: string; kind: Kind };  // sector "" = all
/** Where the rows come from; picks the endpoints. */
export type TabSource = { kind: "portfolio"; name: string } | { kind: "watchlist"; name: string };
const POLL_MS = 3000;
const MAX_POLLS = 60; // ~3 minutes: enough for a cold cache under Finnhub's 60 calls/minute

type Metrics = Record<string, number | null>;
type Row = { p: TabRow; m?: Metrics; div?: DividendHolding; earn?: EarningsRow };
type Col = { label: string; title?: string; value: (r: Row) => number | string | null | undefined; cell?: (r: Row) => React.ReactNode };


const day = (iso: string | null | undefined) =>
  iso ? new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" }) : "–";
const HOUR: Record<string, string> = { bmo: "pre", amc: "post", dmh: "mid" };

/** A metric column straight from the shared definitions (same label, format and color as the stock page). */
function fromDef(key: string): Col {
  const d = METRICS[key];
  return {
    label: d.short, title: d.title ?? (d.label !== d.short ? d.label : undefined),
    value: (r) => metricValue(key, r.m, r.p.price),
    cell: (r) => { const v = metricValue(key, r.m, r.p.price); return <span className={metricTone(key, v)}>{formatMetric(key, v)}</span>; },
  };
}

// Watchlists hold no shares: no income or yield on cost.
const NEEDS_SHARES = new Set(["Yield on cost", "Annual income"]);

const COLUMNS: Record<MetricTab, Col[]> = {
  Financials: GROUPS.Financials.map(fromDef),
  Growth: GROUPS.Growth.map(fromDef),
  Dividends: [
    { label: "Fwd yield", title: "Latest payment × payments per year ÷ live price", value: (r) => (r.div?.pays ? r.div.yield_pct : null),
      cell: (r) => (r.div?.pays && r.div.yield_pct != null ? `${r.div.yield_pct.toFixed(2)}%` : "–") },
    { label: "Annual / sh", title: "Latest payment × payments per year", value: (r) => (r.div?.pays ? r.div.rate : null),
      cell: (r) => (r.div?.pays ? `$${r.div.rate.toFixed(r.div.rate < 1 ? 3 : 2)}` : "–") },
    { label: "Frequency", value: (r) => r.div?.frequency ?? null, cell: (r) => r.div?.frequency ?? "–" },
    { label: "Yield on cost", value: (r) => (r.div?.pays ? r.div.yield_on_cost_pct : null),
      cell: (r) => (r.div?.pays && r.div.yield_on_cost_pct != null ? `${r.div.yield_on_cost_pct.toFixed(2)}%` : "–") },
    fromDef("payout_ratio_pct"),
    fromDef("dividend_growth_5y_pct"),
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
  Profitability: GROUPS.Profitability.map(fromDef),
  Momentum: GROUPS.Momentum.map(fromDef),
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
export function HoldingsTabs({ source, rows: allRows, first, views = [] }: {
  source: TabSource; rows: TabRow[];
  /** The caller's own tab; `content` may take the filtered rows. */
  first: { label: string; content: React.ReactNode | ((rows: TabRow[], sel: Selection) => React.ReactNode) };
  /** More caller tabs after the first, also given the filtered rows. */
  views?: { label: string; content: (rows: TabRow[]) => React.ReactNode }[];
}) {
  // -- picking rows for Compare (kept across tabs and filters) ------------------------------------
  const navigateTo = useNavigate();
  const [picked, setPicked] = useState<string[]>([]);
  useEffect(() => { setPicked([]); }, [source.kind, source.name]);
  const sel: Selection = {
    has: (s) => picked.includes(s),
    toggle: (s) => setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : p.length < COMPARE_MAX ? [...p, s] : p)),
    full: picked.length >= COMPARE_MAX,
  };
  // -- filters (sector; all / stocks / ETFs): only when the rows carry sectors -------------------
  const filterKey = `argus.filter.${source.kind}`;
  const [filter, setFilter] = useState<Filter>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(filterKey) ?? "{}");
      // Before the 3-way choice there was an "Exclude ETFs" checkbox (noEtf).
      const kind: Kind = KINDS.some(([k]) => k === saved.kind) ? saved.kind : saved.noEtf ? "stocks" : "all";
      return { sector: typeof saved.sector === "string" ? saved.sector : "", kind };
    } catch {
      return { sector: "", kind: "all" };
    }
  });
  const updateFilter = (f: Filter) => {
    setFilter(f);
    try { localStorage.setItem(filterKey, JSON.stringify(f)); } catch { /* ignore */ }
  };
  const sectors = useMemo(() => {
    const n = new Map<string, number>();
    for (const r of allRows) if (r.sector && ofKind(r, filter.kind)) n.set(r.sector, (n.get(r.sector) ?? 0) + 1);
    return [...n.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [allRows, filter.kind]);
  const hasSectors = allRows.some((r) => r.sector);
  const hasBoth = allRows.some(isFund) && allRows.some((r) => !isFund(r));
  // A remembered sector that's no longer held (or outside the chosen kind) counts as "all".
  const sector = sectors.some(([k]) => k === filter.sector) ? filter.sector : "";
  const kindCount = allRows.filter((r) => ofKind(r, filter.kind)).length;
  const rows = useMemo(() => allRows.filter((r) => ofKind(r, filter.kind) && (!sector || r.sector === sector)),
                       [allRows, filter.kind, sector]);
  const filtered = rows.length !== allRows.length;
  const totalValue = allRows.reduce((s, r) => s + (r.market_value ?? 0), 0);
  const shownValue = rows.reduce((s, r) => s + (r.market_value ?? 0), 0);

  const tabKey = `argus.tabs.${source.kind}`;
  const [tab, setTab] = useState<Tab>(() => {
    try {
      const t = localStorage.getItem(tabKey) as Tab | null;
      return t && (t === "First" || isMetricTab(t) || views.some((v) => `view:${v.label}` === t)) ? t : "First";
    } catch {
      return "First";
    }
  });
  const pick = (t: Tab) => {
    setTab(t);
    try { localStorage.setItem(tabKey, t); } catch { /* ignore */ }
  };

  // Data for every position (not just the filtered ones), so changing a filter never refetches.
  const symbols = useMemo(() => allRows.map((p) => p.symbol).sort(), [allRows]);
  const needsMetrics = isMetricTab(tab) && tab !== "Earnings";
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
  const cols = useMemo(() => (!isMetricTab(tab) ? [] : COLUMNS[tab].filter((c) => source.kind === "portfolio" || !NEEDS_SHARES.has(c.label))),
                       [tab, source.kind]);
  const view = views.find((v) => `view:${v.label}` === tab);

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
        <div className="seg tabs" role="tablist" aria-label="Views">
          {(["First", ...views.map((v) => `view:${v.label}` as Tab), ...METRIC_TABS] as Tab[]).map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} aria-pressed={tab === t} onClick={() => pick(t)}>
              {t === "First" ? first.label : t.startsWith("view:") ? t.slice(5) : t}
            </button>
          ))}
        </div>
        {waiting && <span className="small muted">{waiting}</span>}
      </div>
      {hasSectors && (
        <div className="row filter-bar">
          {hasBoth && (
            <div className="seg" role="group" aria-label="Stocks or ETFs">
              {KINDS.map(([k, label]) => (
                <button key={k} aria-pressed={filter.kind === k} onClick={() => updateFilter({ ...filter, kind: k })}>
                  {label}{k !== "all" ? ` (${allRows.filter((r) => ofKind(r, k)).length})` : ""}
                </button>
              ))}
            </div>
          )}
          {sectors.length > 1 && (
            <select value={sector} onChange={(e) => updateFilter({ ...filter, sector: e.target.value })} aria-label="Sector">
              <option value="">All sectors ({kindCount})</option>
              {sectors.map(([k, n]) => <option key={k} value={k}>{k === "ETF" ? "ETFs" : k} ({n})</option>)}
            </select>
          )}
          {filtered && (
            <>
              <span className="small muted">
                Showing {rows.length} of {allRows.length}
                {totalValue > 0 && <> · {money(shownValue, { whole: true })} ({((shownValue / totalValue) * 100).toFixed(1)}% of the portfolio)</>}
              </span>
              <button className="btn ghost small" onClick={() => updateFilter({ sector: "", kind: "all" })}>Clear</button>
            </>
          )}
        </div>
      )}
      {picked.length > 0 && (
        <div className="select-bar" role="status">
          <strong>{picked.length} selected</strong>
          <span className="muted">{picked.join(", ")}{sel.full ? ` (the most Compare takes)` : ""}</span>
          <span style={{ flex: 1 }} />
          <button className="btn primary small" onClick={() => navigateTo(compareUrl(picked))}>Compare {picked.length}</button>
          <button className="btn ghost small" onClick={() => setPicked([])}>Clear</button>
        </div>
      )}
      {tab === "First" ? (typeof first.content === "function" ? first.content(rows, sel) : first.content)
        : view ? view.content(rows) : !isMetricTab(tab) ? null : (
        <MetricTable key={tab} cols={cols} note={NOTES[tab]} sel={sel}
                     rows={rows.map((p) => ({ p, m: metrics[p.symbol], div: divs?.[p.symbol], earn: earn?.[p.symbol] }))} />
      )}
    </section>
  );
}

function MetricTable({ cols, rows, note, sel }: { cols: Col[]; rows: Row[]; note?: string; sel: Selection }) {
  const [sort, setSort] = useState<{ i: number; dir: 1 | -1 } | null>(null);
  const navigate = useNavigate();
  // No reset effect: the parent keys this table by tab, so a new tab starts unsorted, while live
  // price updates (a re-render every second or so) leave the chosen sort alone.

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
              <th className="pick" aria-label="Select to compare" /><th className="rank" title="Rank in the current sort order">#</th>
              <th className="left">Symbol</th><th>Price</th>
              {cols.map((c, i) => (
                <th key={c.label} title={c.title} onClick={() => setSort((s) => (s?.i === i ? { i, dir: (s.dir * -1) as 1 | -1 } : { i, dir: -1 }))}
                    aria-sort={sort?.i === i ? (sort.dir === 1 ? "ascending" : "descending") : undefined}>
                  {c.label}{sort?.i === i ? (sort.dir === 1 ? " ↑" : " ↓") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, n) => (
              <tr key={r.p.symbol} tabIndex={0} onClick={() => navigate(`/t/${r.p.symbol}`)}
                  onKeyDown={(e) => e.key === "Enter" && navigate(`/t/${r.p.symbol}`)}>
                <PickCell symbol={r.p.symbol} sel={sel} />
                <td className="rank">{n + 1}</td>
                <td className="left"><span className="sym">{r.p.symbol}</span><span className="name" title={r.p.name ?? undefined}>{r.p.name ?? ""}</span></td>
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
