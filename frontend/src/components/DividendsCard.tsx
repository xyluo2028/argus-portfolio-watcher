import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Dividends } from "../api";
import { money } from "../format";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const pctCell = (v: number | null | undefined) => (v == null ? "–" : `${v.toFixed(2)}%`);
const compact = (v: number) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}K` : `$${v.toFixed(v >= 100 ? 0 : 2)}`);

/** Forward dividend income and yield, and this year's dividends by month (received vs projected). */
export function DividendsCard({ portfolio }: { portfolio: string }) {
  const [d, setD] = useState<Dividends | null>(null);
  const [failed, setFailed] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let stale = false;
    setD(null);
    setFailed(false);
    api.dividends(portfolio).then((x) => !stale && setD(x), () => !stale && setFailed(true));
    return () => { stale = true; };
  }, [portfolio]);

  if (failed) return null;
  if (!d) return <section className="card"><h2>Dividends</h2><p className="muted">Loading dividends… (the first load fetches each holding's history)</p></section>;

  const t = d.totals;
  const max = Math.max(...d.by_month.map((m) => m.received + m.projected), 0.01);
  const payers = d.holdings.filter((h) => h.pays);
  const rows = showAll ? d.holdings : payers;
  const thisMonth = Number(d.as_of.slice(5, 7));

  return (
    <section className="card">
      <h2>Dividends <span className="muted small">· before tax, by ex-date</span></h2>

      <div className="tiles" style={{ marginBottom: 16 }}>
        <div className="tile">
          <div className="label">Forward annual income</div>
          <div className="value">{money(t.annual_income)}</div>
          <div className="delta muted">{t.payers} of {t.positions} holdings pay</div>
        </div>
        <div className="tile">
          <div className="label">Yield</div>
          <div className="value">{pctCell(t.yield_pct)}</div>
          <div className="delta muted">{pctCell(t.yield_on_cost_pct)} on cost</div>
        </div>
        <div className="tile">
          <div className="label">{d.year} so far (est.)</div>
          <div className="value">{money(t.received)}</div>
          <div className="delta muted">from ex-dates you held through</div>
        </div>
        <div className="tile">
          <div className="label">{d.year} expected total</div>
          <div className="value">{money(t.year_total)}</div>
          <div className="delta muted">+{money(t.projected)} projected by Dec 31</div>
        </div>
      </div>

      <div className="row small text-2" style={{ gap: 14, marginBottom: 6 }} aria-hidden>
        <span><span className="swatch received" /> Received (est.)</span>
        <span><span className="swatch projected" /> Projected</span>
      </div>
      <div className="div-chart" role="img"
           aria-label={`Dividends by month in ${d.year}: ${d.by_month.filter((m) => m.received + m.projected > 0)
             .map((m) => `${MONTHS[m.month - 1]} ${money(m.received + m.projected)}`).join(", ") || "none"}`}>
        {d.by_month.map((m) => {
          const total = m.received + m.projected;
          return (
            <div key={m.month} className="div-col" tabIndex={total > 0 ? 0 : -1}
                 title={`${MONTHS[m.month - 1]} ${d.year}: received ${money(m.received)}, projected ${money(m.projected)}`}>
              <div className="div-bars">
                {total > 0 && <span className="div-cap">{compact(total)}</span>}
                {m.projected > 0 && <div className="div-seg projected" style={{ height: `${(m.projected / max) * 100}%` }} />}
                {m.received > 0 && <div className="div-seg received" style={{ height: `${(m.received / max) * 100}%` }} />}
              </div>
              <div className={`div-month${m.month === thisMonth ? " now" : ""}`}>{MONTHS[m.month - 1]}</div>
              <div className="div-tip" role="tooltip">
                <strong>{MONTHS[m.month - 1]} {d.year}</strong>
                <div><span className="swatch received" /> Received {money(m.received)}</div>
                <div><span className="swatch projected" /> Projected {money(m.projected)}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table>
          <thead><tr>
            <th>Symbol</th><th>Pays</th><th>Annual / share</th><th>Yield</th><th>Yield on cost</th>
            <th>Annual income</th><th>{d.year} received</th><th>Rest of {d.year}</th><th>Next ex-date</th>
          </tr></thead>
          <tbody>
            {rows.map((h) => (
              <tr key={h.symbol} style={{ cursor: "default" }} className={h.pays ? undefined : "muted"}>
                <td><Link to={`/t/${h.symbol}`}>{h.symbol}</Link></td>
                <td>{h.pays ? h.frequency : "–"}{h.irregular && <span className="muted" title="Missed recent payments; not projected"> · irregular</span>}</td>
                <td>{h.pays ? `$${h.rate.toFixed(h.rate < 1 ? 3 : 2)}` : "–"}</td>
                <td>{h.pays ? pctCell(h.yield_pct) : "–"}</td>
                <td>{h.pays ? pctCell(h.yield_on_cost_pct) : "–"}</td>
                <td>{h.pays ? money(h.annual_income) : "–"}</td>
                <td>{h.received_ytd ? money(h.received_ytd) : "–"}</td>
                <td>{h.projected_rest_of_year ? money(h.projected_rest_of_year) : "–"}</td>
                <td>{h.next_ex_date_est ? <span title="Estimated from the payment rhythm">~{h.next_ex_date_est.slice(5)}</span> : "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
        <p className="small muted" style={{ margin: 0 }}>
          Annual rate = latest payment × payments per year. “Received” counts each ex-date you held shares through (your
          recorded lots only); payment usually follows 1–4 weeks later.
        </p>
        {d.holdings.length > payers.length && (
          <button className="btn ghost small" onClick={() => setShowAll((x) => !x)}>
            {showAll ? "Payers only" : `Show all ${d.holdings.length}`}
          </button>
        )}
      </div>
    </section>
  );
}
