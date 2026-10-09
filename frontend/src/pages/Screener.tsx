import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type ScreenResult, type ScreenerStatus } from "../api";
import { big, nyTime, price, tone } from "../format";

type Filter = { field: string; min: string; max: string };
const BILLIONS = new Set(["market_cap", "revenue", "net_income"]);  // entered in $B

const PRESETS: { name: string; hint: string; sort: string; filters: Filter[] }[] = [
  { name: "Quality compounders", hint: "Growing, very profitable, modest leverage", sort: "roe_pct", filters: [
    { field: "market_cap", min: "2", max: "" }, { field: "revenue_growth_pct", min: "10", max: "" },
    { field: "net_margin_pct", min: "15", max: "" }, { field: "roe_pct", min: "15", max: "" }, { field: "debt_to_equity", min: "", max: "2" }] },
  { name: "Cash machines", hint: "High free-cash-flow yield", sort: "fcf_yield_pct", filters: [
    { field: "market_cap", min: "1", max: "" }, { field: "fcf_yield_pct", min: "6", max: "" }, { field: "fcf_margin_pct", min: "15", max: "" }] },
  { name: "Fast growers", hint: "Revenue up 30%+ with good gross margins", sort: "revenue_growth_pct", filters: [
    { field: "market_cap", min: "1", max: "" }, { field: "revenue_growth_pct", min: "30", max: "" }, { field: "gross_margin_pct", min: "40", max: "" }] },
  { name: "Value", hint: "Low P/E and P/B, still profitable", sort: "pe", filters: [
    { field: "market_cap", min: "1", max: "" }, { field: "pe", min: "", max: "12" }, { field: "pb", min: "", max: "1.5" }, { field: "net_margin_pct", min: "5", max: "" }] },
  { name: "Profitable small caps", hint: "$0.3–2B, profitable and growing, liquid balance sheet", sort: "revenue_growth_pct", filters: [
    { field: "market_cap", min: "0.3", max: "2" }, { field: "net_margin_pct", min: "10", max: "" },
    { field: "revenue_growth_pct", min: "10", max: "" }, { field: "current_ratio", min: "1.5", max: "" }] },
];

const COLUMNS = ["market_cap", "revenue_growth_pct", "gross_margin_pct", "net_margin_pct", "fcf_yield_pct", "pe", "ps", "roe_pct", "debt_to_equity"];

function show(field: string, v: unknown, unit: string | undefined) {
  if (typeof v !== "number") return "–";
  if (unit === "$") return field === "price" ? price(v) : big(v);
  if (unit === "%") return `${v.toFixed(1)}%`;
  return v.toFixed(field === "debt_to_equity" || field === "current_ratio" ? 2 : 1);
}

export function Screener() {
  const [status, setStatus] = useState<ScreenerStatus | null>(null);
  const [filters, setFilters] = useState<Filter[]>(PRESETS[0].filters);
  const [sort, setSort] = useState(PRESETS[0].sort);
  const [desc, setDesc] = useState(true);
  const [otc, setOtc] = useState(false);
  const [res, setRes] = useState<ScreenResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState<Set<string>>(new Set());
  const seq = useRef(0);

  useEffect(() => { api.screenerStatus().then(setStatus, () => undefined); }, []);
  const fields = status?.fields ?? {};

  const body = useMemo(() => ({
    filters: Object.fromEntries(filters.filter((f) => f.min !== "" || f.max !== "").map((f) => {
      const k = BILLIONS.has(f.field) ? 1e9 : 1;
      return [f.field, [f.min === "" ? null : Number(f.min) * k, f.max === "" ? null : Number(f.max) * k]];
    })),
    sort, descending: desc, include_otc: otc, limit: 200,
  }), [filters, sort, desc, otc]);

  // Run the screen as you edit (debounced); while the universe builds, poll until it's ready.
  useEffect(() => {
    const n = ++seq.current;
    let timer: ReturnType<typeof setTimeout>;
    const run = () => api.screen(body).then((r) => {
      if (n !== seq.current) return;
      setRes(r); setStatus(r.status); setError(null);
      if (r.status.building && !r.status.built) timer = setTimeout(run, 3000);
    }, (e: ApiError) => n === seq.current && setError(`${e.message}${e.hint ? ` — ${e.hint}` : ""}`));
    timer = setTimeout(run, 350);
    return () => clearTimeout(timer);
  }, [body]);

  const set = (i: number, patch: Partial<Filter>) => setFilters((fs) => fs.map((f, j) => (j === i ? { ...f, ...patch } : f)));
  const used = new Set(filters.map((f) => f.field));
  const watch = async (sym: string) => {
    try { await api.watchAdd([sym]); setAdded((s) => new Set(s).add(sym)); } catch (e) { setError((e as ApiError).message); }
  };

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>Screener <span className="muted small">· US-listed companies, SEC filings + live market caps</span></h2>
          {status?.built && (
            <span className="small muted">
              FY {status.fiscal_year} fundamentals ({status.companies?.toLocaleString("en-US")} companies) · prices {status.prices_at ? nyTime(status.prices_at) : "–"}
            </span>
          )}
        </div>
        <div className="row" style={{ gap: 6, margin: "12px 0" }}>
          {PRESETS.map((p) => (
            <button key={p.name} className="btn" title={p.hint} onClick={() => { setFilters(p.filters); setSort(p.sort); setDesc(p.sort !== "pe"); }}>{p.name}</button>
          ))}
        </div>
        <div className="stack" style={{ gap: 6 }}>
          {filters.map((f, i) => {
            const unit = fields[f.field]?.unit;
            const hint = BILLIONS.has(f.field) ? "$B" : unit === "%" ? "%" : unit === "x" ? "×" : "";
            return (
              <div className="row filter-row" key={i}>
                <select value={f.field} onChange={(e) => set(i, { field: e.target.value })} aria-label="Field">
                  {Object.entries(fields).map(([k, v]) => <option key={k} value={k} disabled={k !== f.field && used.has(k)}>{v.label}</option>)}
                </select>
                <input className="input" inputMode="decimal" placeholder={`min ${hint}`} value={f.min} onChange={(e) => set(i, { min: e.target.value })} aria-label="Minimum" />
                <span className="muted">to</span>
                <input className="input" inputMode="decimal" placeholder={`max ${hint}`} value={f.max} onChange={(e) => set(i, { max: e.target.value })} aria-label="Maximum" />
                <button className="btn ghost" onClick={() => setFilters((fs) => fs.filter((_, j) => j !== i))} aria-label="Remove filter">×</button>
              </div>
            );
          })}
        </div>
        <div className="row" style={{ marginTop: 10, gap: 12 }}>
          <button className="btn" onClick={() => {
            const next = Object.keys(fields).find((k) => !used.has(k));
            if (next) setFilters((fs) => [...fs, { field: next, min: "", max: "" }]);
          }}>+ Filter</button>
          <label className="small">Sort by{" "}
            <select value={sort} onChange={(e) => setSort(e.target.value)}>{Object.entries(fields).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select>
          </label>
          <button className="btn ghost" onClick={() => setDesc((d) => !d)}>{desc ? "high → low" : "low → high"}</button>
          <label className="small"><input type="checkbox" checked={otc} onChange={(e) => setOtc(e.target.checked)} /> include OTC</label>
        </div>
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      </section>

      <section className="card">
        {!res || (!res.status.built && res.status.building) ? (
          <p className="muted">
            {res?.status.building ? `Building the universe from SEC filings — ${res.status.progress ?? "starting"}… (about a minute, once a week)` : "Screening…"}
          </p>
        ) : (
          <>
            <h2>{res.matches.toLocaleString("en-US")} matches {res.matches > res.rows.length && <span className="muted small">· showing {res.rows.length}</span>}</h2>
            <div className="table-wrap">
              <table className="metric-table">
                <thead><tr><th>Symbol</th><th>Price</th>{COLUMNS.map((c) => <th key={c} className={c === sort ? "sorted" : undefined}>{fields[c]?.label ?? c}</th>)}<th /></tr></thead>
                <tbody>
                  {res.rows.map((r) => (
                    <tr key={r.symbol} style={{ cursor: "default" }}>
                      <td><Link to={`/t/${r.symbol.replace("-", ".")}`} className="sym">{r.symbol}</Link><span className="name" title={`${r.name ?? ""} · ${r.exchange ?? ""}`}>{r.name}</span></td>
                      <td>{show("price", r.price, "$")}</td>
                      {COLUMNS.map((c) => (
                        <td key={c} className={c.endsWith("growth_pct") ? tone(r[c] as number) : undefined}>{show(c, r[c], fields[c]?.unit)}</td>
                      ))}
                      <td><button className="btn ghost small" disabled={added.has(r.symbol)} onClick={() => watch(r.symbol.replace("-", "."))}>{added.has(r.symbol) ? "watching" : "+ watch"}</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        <p className="small muted" style={{ margin: "8px 0 0" }}>
          Fundamentals: the latest full calendar year in SEC XBRL filings (with the year before for growth) and the latest quarter-end
          balance sheet; fiscal years are mapped to the calendar year they mostly cover. Market caps from Yahoo. Banks' revenue = net interest
          + noninterest income; companies whose profit is over twice their revenue have revenue-based figures left blank.
        </p>
      </section>
    </div>
  );
}
