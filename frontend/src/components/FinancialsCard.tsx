import { useEffect, useState } from "react";
import { ApiError, api, type EarningsHistory, type EarningsReport, type Financials } from "../api";
import { big, pct, tone } from "../format";
import { RevenueColumns } from "./RevenueColumns";

const TIMING: Record<string, string> = { amc: "after close", bmo: "before open", dmh: "during market" };
const shortDate = (d: string) =>
  new Date(`${d}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" });
const longDate = (d: string) =>
  new Date(`${d}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric" });
const eps = (v: number | null | undefined) => (v == null ? "–" : v.toFixed(2));

function Verdict({ label, result, surprise }: { label?: string; result: EarningsReport["eps_result"]; surprise: number | null }) {
  if (!result) return null;
  const text = result === "beat" ? "Beat" : result === "miss" ? "Miss" : "In line";
  return (
    <span className={`verdict ${result}`}>
      {label ? `${label} ` : ""}{label ? text.toLowerCase() : text}{result !== "in_line" && surprise != null ? ` ${pct(surprise, 1)}` : ""}
    </span>
  );
}

function Reaction({ r }: { r: EarningsReport["reaction"] }) {
  if (!r) return <>–</>;
  const title = `From the ${r.base_date} close${r.date ? ` to the ${r.date} close` : " to the latest price"}`;
  return (
    <span title={title}>
      <span className={tone(r.close_pct)}>{pct(r.close_pct, 1)}</span>
      {r.provisional
        ? <span className="ext-line">{r.label ?? "so far"}</span>
        : r.open_pct != null && <span className="ext-line">open {pct(r.open_pct, 1)}</span>}
    </span>
  );
}

/** SEC-reported quarters/years; quarters also show the earnings report: estimates vs actuals, beat or
 * miss, and how the stock reacted. */
export function FinancialsCard({ symbol }: { symbol: string }) {
  const [period, setPeriod] = useState<"quarterly" | "annual">("quarterly");
  const [fin, setFin] = useState<Financials | null>(null);
  const [err, setErr] = useState<ApiError | null>(null);
  const [earnings, setEarnings] = useState<EarningsHistory | null>(null);

  useEffect(() => {
    setErr(null);
    api.financials(symbol, period).then(setFin, (e) => { setFin(null); setErr(e); });
  }, [symbol, period]);

  useEffect(() => {
    setEarnings(null);
    api.earningsHistory(symbol).then(setEarnings, () => setEarnings(null));
  }, [symbol]);

  const quarterly = period === "quarterly";
  const byPeriod = new Map((earnings?.reports ?? []).map((r) => [r.period_end, r]));
  const show = quarterly && byPeriod.size > 0;
  const reportedBasis = show && [...byPeriod.values()].some((r) => r.eps_basis === "reported");
  const next = earnings?.next;

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Reported financials {fin?.company ? <span className="muted small">· {fin.company} · SEC EDGAR</span> : null}</h2>
        <div className="seg">
          {(["quarterly", "annual"] as const).map((p) => (
            <button key={p} aria-pressed={period === p} onClick={() => setPeriod(p)}>{p === "quarterly" ? "Quarterly" : "Annual"}</button>
          ))}
        </div>
      </div>
      {next && (
        <p className="small" style={{ marginTop: 0 }}>
          <span className="muted">Next report</span> {longDate(next.date)}{next.timing ? `, ${TIMING[next.timing]}` : ""}
          {next.eps_estimate != null && <> · <span className="muted">EPS est.</span> {eps(next.eps_estimate)}</>}
          {next.revenue_estimate != null && <> · <span className="muted">revenue est.</span> {big(next.revenue_estimate)}</>}
        </p>
      )}
      {err ? <p className="muted">{err.message}</p> : fin ? (
        <>
          <RevenueColumns periods={fin.periods} />
          <div className="table-wrap">
            <table>
              <thead><tr>
                <th>Period end</th><th>Revenue</th><th>Gross %</th><th>Operating %</th><th>Net income</th><th>EPS (dil.)</th>
                {show && <>
                  <th title="Consensus EPS estimate before the report">EPS est.</th>
                  <th title="EPS on the basis analysts estimate (adjusted where the source reports it)">EPS actual</th>
                  <th>Result</th>
                  <th title="Close-to-close move across the report: before the open, that day vs the prior close; after the close, the next day vs that day's close">Reaction</th>
                </>}
                <th>FCF</th>
              </tr></thead>
              <tbody>
                {fin.periods.map((p) => {
                  const e = show ? byPeriod.get(p.period_end) : undefined;
                  return (
                    <tr key={p.period_end} style={{ cursor: "default" }}>
                      <td>
                        {p.period_end}
                        {e && <span className="ext-line">reported {shortDate(e.report_date)}{e.timing ? `, ${TIMING[e.timing]}` : ""}</span>}
                      </td>
                      <td>
                        {big(p.revenue)}
                        {e?.revenue_estimate != null && <span className="ext-line">est. {big(e.revenue_estimate)}</span>}
                      </td>
                      <td>{p.gross_margin_pct == null ? "–" : p.gross_margin_pct.toFixed(1)}</td>
                      <td>{p.operating_margin_pct == null ? "–" : p.operating_margin_pct.toFixed(1)}</td>
                      <td className={tone(p.net_income)}>{big(p.net_income)}</td>
                      <td>{p.eps_diluted == null ? "–" : p.eps_diluted.toFixed(2)}</td>
                      {show && <>
                        <td>{eps(e?.eps_estimate)}</td>
                        <td>{eps(e?.eps_actual)}{e?.eps_basis === "reported" ? "†" : ""}</td>
                        <td>
                          {e ? <>
                            <Verdict result={e.eps_result} surprise={e.eps_surprise_pct} />
                            {e.revenue_result && <span className="ext-line"><Verdict label="Revenue" result={e.revenue_result} surprise={e.revenue_surprise_pct} /></span>}
                            {!e.eps_result && !e.revenue_result && "–"}
                          </> : "–"}
                        </td>
                        <td><Reaction r={e?.reaction ?? null} /></td>
                      </>}
                      <td>{big(p.free_cash_flow)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {show && (
            <p className="small muted" style={{ marginBottom: 0 }}>
              Estimates and adjusted EPS: Finnhub (recent quarters) and Yahoo
              {reportedBasis ? "; † Yahoo's reported EPS, which can be GAAP, so one-time items may show as a miss" : ""}.
              Revenue estimates are kept from each report on, so older quarters have none.
            </p>
          )}
        </>
      ) : <p className="muted">Loading…</p>}
    </section>
  );
}
