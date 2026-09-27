import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, api, type CompareResult } from "../api";
import { big, pct, price, ratio } from "../format";

const LABELS: Record<string, [string, (v: number | null) => string]> = {
  price: ["Price", price],
  change_pct: ["Day %", (v) => pct(v)],
  market_cap: ["Market cap", big],
  pe_ttm: ["P/E (TTM)", (v) => ratio(v, 1)],
  pe_forward: ["P/E (forward)", (v) => ratio(v, 1)],
  peg: ["PEG", ratio],
  pb: ["P/B", (v) => ratio(v, 1)],
  ps_ttm: ["P/S (TTM)", (v) => ratio(v, 1)],
  ev_ebitda: ["EV/EBITDA", (v) => ratio(v, 1)],
  revenue_growth_yoy_pct: ["Revenue growth YoY", (v) => pct(v, 1)],
  gross_margin_pct: ["Gross margin", (v) => (v == null ? "–" : `${v.toFixed(1)}%`)],
  net_margin_pct: ["Net margin", (v) => (v == null ? "–" : `${v.toFixed(1)}%`)],
  roe_pct: ["ROE", (v) => (v == null ? "–" : `${v.toFixed(1)}%`)],
  dividend_yield_pct: ["Dividend yield", (v) => (v == null ? "–" : `${v.toFixed(2)}%`)],
  beta: ["Beta", ratio],
};

export function Compare({ portfolio }: { portfolio: string }) {
  const [params, setParams] = useSearchParams();
  const [input, setInput] = useState(params.get("s") ?? "");
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Default: the five largest holdings.
  useEffect(() => {
    if (params.get("s")) return;
    api.portfolio(portfolio).then((s) => {
      const top = s.positions.slice(0, 5).map((p) => p.symbol).join(", ");
      setInput(top);
      setParams({ s: top }, { replace: true });
    }, () => undefined);
  }, [portfolio, params, setParams]);

  useEffect(() => {
    const syms = (params.get("s") ?? "").split(/[\s,]+/).filter(Boolean);
    if (!syms.length) return;
    setLoading(true);
    setError(null);
    api.compare(syms).then(setResult, (e: ApiError) => setError(e.message)).finally(() => setLoading(false));
  }, [params]);

  const metrics = result ? ["price", "change_pct", ...result.fields] : [];

  return (
    <div className="stack">
      <section className="card">
        <h2>Compare up to 10 symbols</h2>
        <form className="row" onSubmit={(e) => { e.preventDefault(); setParams({ s: input }); }}>
          <input className="input" value={input} onChange={(e) => setInput(e.target.value)} aria-label="Symbols"
                 placeholder="NVDA, AMD, AVGO" style={{ flex: 3 }} />
          <button className="btn primary">Compare</button>
        </form>
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      </section>
      {result && (
        <section className="card" style={{ opacity: loading ? 0.6 : 1 }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Metric</th>{result.rows.map((r) => <th key={String(r.symbol)}><Link to={`/t/${r.symbol}`}>{String(r.symbol)}</Link></th>)}</tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={m} style={{ cursor: "default" }}>
                    <td className="text-2">{LABELS[m]?.[0] ?? m}</td>
                    {result.rows.map((r) => {
                      const v = r[m] as number | null | undefined;
                      return <td key={String(r.symbol)}>{(LABELS[m]?.[1] ?? ratio)(v ?? null)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {Object.keys(result.errors).length > 0 && (
            <p className="small muted">Missing data: {Object.entries(result.errors).map(([s, e]) => `${s} (${e})`).join("; ")}</p>
          )}
        </section>
      )}
    </div>
  );
}
