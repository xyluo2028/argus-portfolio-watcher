import { useEffect, useState } from "react";
import { api, type CompanyProfile } from "../api";

const host = (url: string) => url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");

/** What the company does and where it is. */
export function CompanyCard({ symbol }: { symbol: string }) {
  const [p, setP] = useState<CompanyProfile | null>(null);
  const [failed, setFailed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setP(null);
    setFailed(false);
    setExpanded(false);
    api.profile(symbol).then(setP, () => setFailed(true));
  }, [symbol]);

  if (failed) return null;
  if (!p) return <section className="card"><h2>Company</h2><p className="muted">Loading…</p></section>;

  const fund = p.quote_type === "ETF" || p.quote_type === "MUTUALFUND";
  const hq = [p.address, p.city, [p.state, p.zip].filter(Boolean).join(" "), p.country].filter(Boolean).join(", ");
  const ceo = p.officers?.find((o) => /\bCEO\b|Chief Executive/i.test(o.title ?? "")) ?? p.officers?.[0];
  const facts: [string, React.ReactNode][] = [
    ...(fund
      ? [["Fund family", p.fund_family], ["Category", p.category]] as [string, React.ReactNode][]
      : [["Headquarters", hq], ["Industry", [p.sector, p.industry].filter(Boolean).join(" · ")],
         ["Employees", p.employees?.toLocaleString()], [ceo?.title?.split(/[,&]/)[0] || "Leader", ceo?.name]] as [string, React.ReactNode][]),
    ["Website", p.website && <a href={p.website} target="_blank" rel="noreferrer">{host(p.website)}</a>],
    ["Listed since", p.ipo],
  ];

  return (
    <section className="card">
      <div className="row" style={{ marginBottom: 10, gap: 10 }}>
        {p.logo && <img src={p.logo} alt="" width={28} height={28} style={{ borderRadius: 6, objectFit: "contain", background: "#fff" }} />}
        <h2 style={{ margin: 0 }}>{p.name ?? symbol}{p.country && !fund ? <span className="muted"> · {p.country}</span> : null}</h2>
      </div>
      {p.summary && (
        <>
          <p className={expanded ? undefined : "clamp-4"} style={{ marginTop: 0 }}>{p.summary}</p>
          {p.summary.length > 360 && (
            <button className="btn ghost" style={{ marginTop: -6, marginBottom: 8, paddingLeft: 0 }} onClick={() => setExpanded((x) => !x)}>
              {expanded ? "Show less" : "Read more"}
            </button>
          )}
        </>
      )}
      <div className="stats">
        {facts.filter(([, v]) => v).map(([k, v]) => (
          <div className="stat" key={k}><div className="k">{k}</div><div className="v" style={{ fontWeight: 500 }}>{v}</div></div>
        ))}
      </div>
    </section>
  );
}
