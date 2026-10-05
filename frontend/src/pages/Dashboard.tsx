import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ALL, ApiError, api, type StreamUpdate, type Summary } from "../api";
import { BarList, topN } from "../components/BarList";
import { EventsCard } from "../components/EventsCard";
import { HoldingsTable } from "../components/HoldingsTable";
import { PerformanceCard } from "../components/PerformanceCard";
import { extLabel, money, pct, tone } from "../format";

interface Props {
  portfolio: string;
  live: StreamUpdate | null;
}

export function Dashboard({ portfolio, live }: Props) {
  const [initial, setInitial] = useState<Summary | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    setInitial(null);
    setError(null);
    api.portfolio(portfolio).then(setInitial, setError);
  }, [portfolio]);

  // Prefer the pushed summary (recomputed server-side on every price change).
  const summary = live?.portfolio?.portfolio.name === portfolio ? live.portfolio : initial;
  const benchmark = summary ? live?.quotes[summary.portfolio.benchmark] : undefined;

  const allocation = useMemo(() => {
    if (!summary) return null;
    const byPosition = summary.positions.map((p) => [p.symbol, p.market_value ?? p.cost_basis] as [string, number]);
    const sectors = new Map<string, number>();
    for (const p of summary.positions) {
      const k = p.sector ?? "Unclassified";
      sectors.set(k, (sectors.get(k) ?? 0) + (p.market_value ?? p.cost_basis));
    }
    const total = byPosition.reduce((s, [, v]) => s + v, 0);
    return { positions: topN(byPosition, 10), sectors: topN([...sectors.entries()], 8), total };
  }, [summary]);

  if (error) return <div className="error">{error.message}{error.hint ? ` — ${error.hint}` : ""}</div>;
  if (!summary || !allocation) return <p className="muted">Loading portfolio…</p>;

  const t = summary.totals;
  return (
    <div className="stack">
      <section className="card">
        <div className="hero-label">{summary.portfolio.name === ALL ? "All portfolios" : summary.portfolio.name} · total value</div>
        <div className="hero-value">{money(t.market_value)}</div>
        <div className={`hero-delta ${tone(t.day_pnl)}`}>
          {money(t.day_pnl, { signed: true })} ({pct(t.day_pnl_pct)}) {["closed", "pre"].includes(summary.market.session) ? "last session" : "today"}
        </div>
        {t.ext_pnl != null && (
          <div className="ext-hero">
            <span className="muted">{extLabel(t.ext_session)}</span>{" "}
            <span className={tone(t.ext_pnl)}>{money(t.ext_pnl, { signed: true })} ({pct(t.ext_pnl_pct)})</span>
            {t.ext_coverage_pct != null && t.ext_coverage_pct < 99.5 && (
              <span className="muted small"> · positions worth {t.ext_coverage_pct.toFixed(0)}% of the portfolio traded</span>
            )}
          </div>
        )}
      </section>

      <section className="tiles" aria-label="Key figures">
        <div className="tile">
          <div className="label">Unrealized P&amp;L</div>
          <div className={`value ${tone(t.unrealized_pnl)}`}>{money(t.unrealized_pnl, { signed: true, whole: true })}</div>
          <div className={`delta ${tone(t.unrealized_pct)}`}>{pct(t.unrealized_pct)} on cost</div>
        </div>
        <div className="tile">
          <div className="label">Cost basis</div>
          <div className="value">{money(t.cost_basis, { whole: true })}</div>
          <div className="delta muted">{t.position_count} positions</div>
        </div>
        <div className="tile">
          <div className="label">Realized P&amp;L</div>
          <div className={`value ${tone(t.realized_pnl)}`}>{money(t.realized_pnl, { signed: true, whole: true })}</div>
          <div className="delta muted">FIFO, since import</div>
        </div>
        <div className="tile">
          <div className="label">Portfolio vs {summary.portfolio.benchmark}, {["closed", "pre"].includes(summary.market.session) ? "last session" : "today"}</div>
          <div className="value">
            <span className={tone(t.day_pnl_pct)}>{pct(t.day_pnl_pct)}</span>
            <span className="muted"> / </span>
            <span className={tone(benchmark?.change_pct)}>{pct(benchmark?.change_pct)}</span>
          </div>
          <div className="delta muted">day change</div>
        </div>
      </section>

      {live?.alerts_fired && live.alerts_fired.length > 0 && (
        <section className="card alert-strip" aria-live="polite">
          <strong>Alerts this session</strong>
          <ul>{live.alerts_fired.slice(0, 5).map((a) => <li key={a.alert_id}>{a.message}{a.note ? <span className="muted"> · {a.note}</span> : null}</li>)}</ul>
          <Link to="/alerts" className="small">All alerts →</Link>
        </section>
      )}

      {summary.quote_errors && Object.keys(summary.quote_errors).length > 0 && (
        <div className="error">No quote for {Object.keys(summary.quote_errors).join(", ")}; their value is missing from totals.</div>
      )}

      {/* Refetch once per session day (and when the session changes), not on every tick. */}
      <PerformanceCard portfolio={portfolio} refreshKey={`${summary.market.last_session}-${summary.market.session}`} />

      <section className="card">
        <h2>Holdings</h2>
        <HoldingsTable positions={summary.positions} />
      </section>

      <EventsCard portfolio={portfolio} />

      <section className="grid-2">
        <div className="card">
          <h2>Largest positions</h2>
          <BarList items={allocation.positions} total={allocation.total} />
        </div>
        <div className="card">
          <h2>By sector</h2>
          <BarList items={allocation.sectors} total={allocation.total} />
          <p className="small muted">ETFs are grouped as “ETF”.</p>
        </div>
      </section>
    </div>
  );
}
