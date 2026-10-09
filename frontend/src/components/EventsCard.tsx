import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type CalEvent } from "../api";
import { big, pct } from "../format";

const KIND = { earnings: "Earnings", ex_dividend: "Ex-dividend", dividend_pay: "Dividend paid" } as const;
const HOUR: Record<string, string> = { bmo: "before open", amc: "after close", dmh: "during hours" };

function day(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric" });
}

/** Upcoming earnings and dividends, and results reported in the last week: for one symbol, one
 * portfolio's holdings, or (no portfolio, or the All view) every holding plus the watchlist. */
export function EventsCard({ symbol, portfolio }: { symbol?: string; portfolio?: string }) {
  const [data, setData] = useState<{ upcoming: CalEvent[]; recent: CalEvent[] } | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setData(null);
    setFailed(false);
    let stale = false;
    api.events(symbol ? 60 : 14, 7, symbol ? { symbol } : { portfolio })
      .then((d) => !stale && setData(d), () => !stale && setFailed(true));
    return () => { stale = true; };
  }, [symbol, portfolio]);

  if (failed) return null;
  const upcoming = data?.upcoming ?? [];
  const recent = (data?.recent ?? []).filter((e) => e.kind === "earnings" && e.epsActual != null);

  return (
    <section className="card">
      <h2>{symbol ? "Events" : "Coming up"} <span className="muted small">· earnings &amp; dividends{symbol ? "" : ", next 14 days"}</span></h2>
      {!data ? <p className="muted">Loading…</p> : upcoming.length === 0 && recent.length === 0 ? (
        <p className="muted">Nothing scheduled.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <tbody>
              {upcoming.map((e) => (
                <tr key={`${e.symbol}-${e.kind}-${e.date}`} style={{ cursor: "default" }}>
                  <td className="text-2">{day(e.date)}</td>
                  <td style={{ textAlign: "left" }}>{symbol ? "" : <Link to={`/t/${e.symbol}`} className="sym">{e.symbol}</Link>}</td>
                  <td style={{ textAlign: "left" }}>{KIND[e.kind]}{e.hour && HOUR[e.hour] ? <span className="muted"> · {HOUR[e.hour]}</span> : null}</td>
                  <td className="small text-2">
                    {e.kind === "earnings" && e.epsEstimate != null ? `EPS est. ${e.epsEstimate.toFixed(2)}` : ""}
                    {e.kind === "earnings" && e.revenueEstimate ? ` · rev est. ${big(e.revenueEstimate)}` : ""}
                  </td>
                </tr>
              ))}
              {recent.map((e) => (
                <tr key={`r-${e.symbol}-${e.date}`} style={{ cursor: "default" }}>
                  <td className="muted">{day(e.date)}</td>
                  <td style={{ textAlign: "left" }}>{symbol ? "" : <Link to={`/t/${e.symbol}`} className="sym">{e.symbol}</Link>}</td>
                  <td style={{ textAlign: "left" }}>Reported</td>
                  <td className="small">
                    EPS {e.epsActual!.toFixed(2)} vs {e.epsEstimate?.toFixed(2) ?? "–"}
                    {e.epsSurprisePct != null && (
                      <span className={e.epsSurprisePct >= 0 ? "up" : "down"}> ({e.epsSurprisePct >= 0 ? "beat" : "miss"} {pct(e.epsSurprisePct, 1)})</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
