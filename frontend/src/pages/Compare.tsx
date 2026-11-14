import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, api, type CompareFull, type CompareRow } from "../api";
import { CompareChart, type SeriesStyle } from "../components/CompareChart";
import { TickerInput } from "../components/TickerInput";
import { COMPARE_MAX, ago, clearSessions, forgetSession, loadSessions, parseSymbols, rememberSession,
  type CompareSession } from "../compareSessions";
import { extLabel, pct, price, tone } from "../format";
import { GROUPS, METRICS, formatMetric, metricTone, metricValue, type Metrics } from "../metrics";

// Which way is better, where that's meaningful: valuation multiples low, growth/margins/returns high.
// Size, payout, beta and distance-from-average rows aren't ranked.
const LOWER_BETTER = new Set(["pe_ttm", "pe_forward", "peg", "peg_ttm", "ps_ttm", "pb", "ev_ebitda", "debt_to_equity",
  "expense_ratio_pct"]);
const HIGHER_BETTER = new Set([...GROUPS.Growth, ...GROUPS.Profitability,
  "return_1w_pct", "return_1m_pct", "return_3m_pct", "return_6m_pct", "return_ytd_price_pct", "return_1y_pct",
  "cagr_3y_pct", "cagr_5y_pct", "rel_sp500_1y_pct", "dividend_yield_pct", "dividend_growth_5y_pct",
  "ytd_return_pct", "return_3y_pct", "return_5y_pct"]);
const isFund = (r: CompareRow) => r.type === "ETP";

const SLOTS = 8;
const styleFor = (slot: number): SeriesStyle =>
  ({ color: `var(--series-${(slot % SLOTS) + 1})`, dash: slot >= SLOTS ? "6 4" : undefined });

/** Each symbol keeps its color while it stays in the comparison (removing one never repaints the rest). */
function useStableSlots(symbols: string[]) {
  const slots = useRef(new Map<string, number>());
  const m = slots.current;
  for (const s of [...m.keys()]) if (!symbols.includes(s)) m.delete(s);
  for (const s of symbols) {
    if (m.has(s)) continue;
    const used = new Set(m.values());
    let i = 0;
    while (used.has(i)) i++;
    m.set(s, i);
  }
  return (s: string) => styleFor(m.get(s) ?? 0);
}

export function Compare({ portfolio }: { portfolio: string }) {
  const [params, setParams] = useSearchParams();
  const raw = params.get("s");
  const symbols = useMemo(() => parseSymbols(raw).slice(0, COMPARE_MAX), [raw]);
  const key = symbols.join(",");
  const styleOf = useStableSlots(symbols);

  const [input, setInput] = useState("");
  const [result, setResult] = useState<CompareFull | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<CompareSession[]>(loadSessions);
  const [showAll, setShowAll] = useState(false);
  const [suggest, setSuggest] = useState<{ peers: string[]; holdings: string[]; watch: string[] }>({ peers: [], holdings: [], watch: [] });

  const setSymbols = (list: string[]) => setParams({ s: list.slice(0, COMPARE_MAX).join(",") });

  // Coming back to Compare without symbols: reopen the last comparison, else the five largest holdings.
  useEffect(() => {
    if (raw !== null) return;
    const last = loadSessions()[0];
    if (last) {
      setParams({ s: last.symbols.join(",") }, { replace: true });
      return;
    }
    api.portfolio(portfolio).then((s) => setParams({ s: s.positions.slice(0, 5).map((p) => p.symbol).join(",") }, { replace: true }),
      () => undefined);
  }, [raw, portfolio, setParams]);

  useEffect(() => {
    if (!symbols.length) { setResult(null); return; }
    let stale = false;
    setLoading(true);
    setError(null);
    api.compareFull(symbols).then((r) => {
      if (stale) return;
      setResult(r);
      setSessions(rememberSession(symbols));
    }, (e: ApiError) => !stale && setError(e.message)).finally(() => !stale && setLoading(false));
    return () => { stale = true; };
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps

  // Suggestions: the first symbol's peers, your largest holdings, your watchlist.
  const first = symbols[0];
  useEffect(() => {
    if (!first) return;
    api.peerList(first).then((p) => setSuggest((s) => ({ ...s, peers: p.peers })), () => setSuggest((s) => ({ ...s, peers: [] })));
  }, [first]);
  useEffect(() => {
    api.portfolio(portfolio).then((p) => setSuggest((s) => ({ ...s, holdings: p.positions.slice(0, 10).map((x) => x.symbol) })),
      () => undefined);
    api.watchlist().then((w) => setSuggest((s) => ({ ...s, watch: w.items.map((i) => i.symbol) })), () => undefined);
  }, [portfolio]);

  const add = (more: string[]) => setSymbols([...symbols, ...more.map((s) => s.toUpperCase()).filter((s) => !symbols.includes(s))]);
  const remove = (s: string) => setSymbols(symbols.filter((x) => x !== s));
  const full = symbols.length >= COMPARE_MAX;
  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const more = parseSymbols(input);
    if (more.length) add(more);
    setInput("");
  };
  const offer = (list: string[]) => list.filter((s) => !symbols.includes(s)).slice(0, 8);

  const rows = result?.rows.filter((r) => symbols.includes(r.symbol)) ?? [];
  const byCol = (r: CompareRow) => r as unknown as Metrics;

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <h2 style={{ margin: 0 }}>Compare <span className="muted small">· up to {COMPARE_MAX} symbols</span></h2>
          {symbols.length > 0 && <button className="btn ghost small" onClick={() => setSymbols([])}>Clear all</button>}
        </div>
        <div className="sym-chips" style={{ marginBottom: 10 }}>
          {symbols.map((s) => {
            const st = styleOf(s);
            return (
              <span key={s} className="sym-chip">
                <svg className="swatch" width="14" height="4" aria-hidden><line x1="0" y1="2" x2="14" y2="2" stroke={st.color} strokeWidth="3" strokeDasharray={st.dash ? "4 3" : undefined} /></svg>
                <Link to={`/t/${s}`}>{s}</Link>
                <button aria-label={`Remove ${s}`} title={`Remove ${s}`} onClick={() => remove(s)}>×</button>
              </span>
            );
          })}
          {!symbols.length && <span className="muted small">Add symbols to compare.</span>}
        </div>
        <form className="row" onSubmit={onSubmit}>
          <TickerInput value={input} onChange={setInput} aria-label="Add symbols"
                       placeholder={full ? `${COMPARE_MAX} symbols is the limit` : "Add a ticker or company, e.g. AAPL"}
                       style={{ maxWidth: 420 }} />
          <button className="btn primary" disabled={full || !input.trim()}>Add</button>
        </form>
        <div className="stack" style={{ gap: 6, marginTop: 10 }}>
          {([["Peers of " + (first ?? ""), offer(suggest.peers)], ["Your holdings", offer(suggest.holdings)],
             ["Watchlist", offer(suggest.watch)]] as [string, string[]][]).filter(([, l]) => l.length && !full).map(([label, list]) => (
            <div key={label} className="suggest">
              <span className="lbl">{label}:</span>
              {list.map((s) => <button key={s} onClick={() => add([s])} title={`Add ${s}`}>+ {s}</button>)}
            </div>
          ))}
        </div>
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      </section>

      {sessions.length > 0 && (
        <section className="card">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
            <h2 style={{ margin: 0 }}>Recent comparisons</h2>
            <button className="btn ghost small" onClick={() => { clearSessions(); setSessions([]); }}>Clear history</button>
          </div>
          <div className="history-list">
            {(showAll ? sessions : sessions.slice(0, 5)).map((s) => {
              const current = s.symbols.join(",") === key;
              return (
                <div key={s.symbols.join(",")} className={`history-item ${current ? "current" : ""}`} role="button" tabIndex={0}
                     onClick={() => setSymbols(s.symbols)} onKeyDown={(e) => e.key === "Enter" && setSymbols(s.symbols)}>
                  <span className="syms">{s.symbols.join(" · ")}</span>
                  <span className="small muted">{current ? "open now" : ago(s.at)}</span>
                  <button className="btn ghost" aria-label="Remove from history" title="Remove from history"
                          onClick={(e) => { e.stopPropagation(); setSessions(forgetSession(s.symbols)); }}>×</button>
                </div>
              );
            })}
          </div>
          {sessions.length > 5 && (
            <button className="btn ghost small" style={{ marginTop: 4 }} onClick={() => setShowAll((x) => !x)}>
              {showAll ? "Show fewer" : `Show all ${sessions.length}`}
            </button>
          )}
        </section>
      )}

      {symbols.length > 0 && <CompareChart symbols={symbols} styleOf={styleOf} />}

      {symbols.length > 0 && (
        <section className="card" style={{ opacity: loading ? 0.6 : 1 }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>Indicators</h2>
            <span className="small muted">{loading ? "Loading…" : "Highlighted: most favorable in the row (lower multiples; higher growth, margins, returns)"}</span>
          </div>
          {rows.length > 0 && (
            <div className="table-wrap">
              <table className="compare-table">
                <thead>
                  <tr>
                    <th>Indicator</th>
                    {rows.map((r) => (
                      <th key={r.symbol}>
                        <span className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                          <svg width="14" height="4" aria-hidden><line x1="0" y1="2" x2="14" y2="2" stroke={styleOf(r.symbol).color} strokeWidth="3" strokeDasharray={styleOf(r.symbol).dash ? "4 3" : undefined} /></svg>
                          <Link to={`/t/${r.symbol}`}>{r.symbol}</Link>
                        </span>
                        <span className="name" title={r.name ?? undefined}>{r.name ?? ""}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="group"><td colSpan={rows.length + 1}>Quote</td></tr>
                  <tr style={{ cursor: "default" }}>
                    <td className="text-2">Price</td>
                    {rows.map((r) => <td key={r.symbol}>{price(r.price)}</td>)}
                  </tr>
                  <tr style={{ cursor: "default" }}>
                    <td className="text-2">Day %</td>
                    {rows.map((r) => (
                      <td key={r.symbol} className={tone(r.change_pct)}>
                        {pct(r.change_pct)}
                        {r.ext_price != null && <span className="ext-line">{extLabel(r.ext_session, true)} <span className={tone(r.ext_change_pct)}>{pct(r.ext_change_pct)}</span></span>}
                      </td>
                    ))}
                  </tr>
                  {Object.entries(GROUPS).filter(([g]) => g !== "Fund" || rows.some(isFund)).map(([group, keys]) => {
                    const shown = (keys as readonly string[]).filter((k) => rows.some((r) => metricValue(k, byCol(r), r.price) != null));
                    if (!shown.length) return null;
                    return [
                      <tr key={group} className="group"><td colSpan={rows.length + 1}>{group}</td></tr>,
                      ...shown.map((k) => {
                        const vals = rows.map((r) => metricValue(k, byCol(r), r.price));
                        const ranked = vals.filter((v): v is number => v != null && (!LOWER_BETTER.has(k) || v > 0));
                        const best = ranked.length >= 2 && (LOWER_BETTER.has(k) ? Math.min(...ranked) : HIGHER_BETTER.has(k) ? Math.max(...ranked) : null);
                        const d = METRICS[k];
                        return (
                          <tr key={k} style={{ cursor: "default" }}>
                            <td className="text-2" title={d.title}>{d.label}</td>
                            {vals.map((v, i) => (
                              <td key={rows[i].symbol} className={[metricTone(k, v), best !== false && best !== null && v === best ? "best" : ""].filter(Boolean).join(" ")}>
                                {formatMetric(k, v)}
                              </td>
                            ))}
                          </tr>
                        );
                      }),
                    ];
                  })}
                </tbody>
              </table>
            </div>
          )}
          {result && Object.keys(result.errors).length > 0 && (
            <p className="small muted">Missing data: {Object.entries(result.errors).map(([s, e]) => `${s} (${e})`).join("; ")}</p>
          )}
        </section>
      )}
    </div>
  );
}
