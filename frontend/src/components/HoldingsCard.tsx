import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type FundHolding, type FundHoldings } from "../api";
import { big, pct, price, tone } from "../format";
import { BarList } from "./BarList";

const GAP = 2;
const TABLE_ROWS = 15;
const FULL_AT = 3; // a ±3% day is full color

type Named = FundHolding & { symbol: string };
interface Tile { h: Named; x: number; y: number; w: number; h_: number }

/** Squarified treemap: rows of tiles kept as close to square as possible. */
function squarify(items: Named[], width: number, height: number): Tile[] {
  const total = items.reduce((s, i) => s + i.weight_pct, 0) || 1;
  const scale = (width * height) / total;
  const out: Tile[] = [];
  let rest = items.map((h) => ({ h, area: h.weight_pct * scale }));
  let x = 0, y = 0, w = width, hgt = height;
  const worst = (row: { area: number }[], side: number) => {
    const sum = row.reduce((s, r) => s + r.area, 0);
    const max = Math.max(...row.map((r) => r.area)), min = Math.min(...row.map((r) => r.area));
    return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
  };
  while (rest.length) {
    const side = Math.min(w, hgt);
    let row = [rest[0]];
    let i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) row = [...row, rest[i++]];
    rest = rest.slice(i);
    const sum = row.reduce((s, r) => s + r.area, 0);
    if (w >= hgt) { // lay the row as a column on the left
      const cw = sum / hgt;
      let cy = y;
      for (const r of row) { const th = r.area / cw; out.push({ h: r.h, x, y: cy, w: cw, h_: th }); cy += th; }
      x += cw; w -= cw;
    } else { // as a row on top
      const rh = sum / w;
      let cx = x;
      for (const r of row) { const tw = r.area / rh; out.push({ h: r.h, x: cx, y, w: tw, h_: rh }); cx += tw; }
      y += rh; hgt -= rh;
    }
  }
  return out;
}

/** Diverging fill: gray at 0, up/down hue growing with the size of the move. */
function fill(change: number | null): { bg: string; strong: boolean } {
  if (change == null) return { bg: "var(--surface-2)", strong: false };
  const t = Math.min(Math.abs(change) / FULL_AT, 1);
  const hue = change >= 0 ? "var(--heat-up)" : "var(--heat-down)";
  return { bg: `color-mix(in oklab, ${hue} ${change === 0 ? 0 : Math.round(15 + t * 85)}%, var(--heat-mid))`, strong: t > 0.45 };
}

const RATINGS: [string, string][] = [["aaa", "AAA"], ["aa", "AA"], ["a", "A"], ["bbb", "BBB"], ["bb", "BB"],
  ["b", "B"], ["below_b", "Below B"], ["other", "Other"]];
const ASSETS: [string, string][] = [["stockPosition", "Stocks"], ["bondPosition", "Bonds"], ["cashPosition", "Cash"],
  ["preferredPosition", "Preferred"], ["convertiblePosition", "Convertible"], ["otherPosition", "Other"]];
const pctFmt = (v: number) => `${v.toFixed(1)}%`;
const regions = (() => { try { return new Intl.DisplayNames(["en"], { type: "region" }); } catch { return null; } })();
const countryName = (code: string | null) => {
  if (!code) return "–";
  try { return regions?.of(code) ?? code; } catch { return code; }
};
const longDate = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

/** A fund's holdings: the largest stocks as a heatmap (size = weight, color = today's move), every
 * holding in a table, plus sector, country and asset-mix weights. */
export function HoldingsCard({ symbol }: { symbol: string }) {
  const [data, setData] = useState<FundHoldings | null>(null);
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<{ h: Named; x: number; y: number } | null>(null);
  const [showAll, setShowAll] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setData(null);
    setShowAll(false);
    let stale = false;
    const load = () => api.holdings(symbol).then((d) => !stale && setData(d), () => undefined);
    load();
    const id = setInterval(load, 60000);
    return () => { stale = true; clearInterval(id); };
  }, [symbol]);

  const heat = (data?.holdings ?? []).filter((h): h is Named => !!h.symbol && h.kind === "stock" && h.weight_pct > 0)
    .slice(0, 50);

  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, [heat.length > 0]);

  if (!data || !data.fund) return null;
  const height = heat.length > 12 ? 400 : 260;
  const tiles = width ? squarify(heat, width, height) : [];
  const heatWeight = heat.reduce((s, h) => s + h.weight_pct, 0);
  const shown = (m: Record<string, number>, keys: [string, string][]) =>  // drop rows that round to 0.0%
    keys.filter(([k]) => (m[k] ?? 0) >= 0.05).map(([k, label]) => ({ label, value: m[k] }));
  const ratings = shown(data.bond_ratings, RATINGS);
  const assets = shown(data.asset_classes, ASSETS);
  const sectors = data.sectors.map((s) => ({ label: s.sector, value: s.weight_pct }));
  const countries = data.countries.length > 1 && data.countries[0].weight_pct < 97
    ? data.countries.map((c) => ({ label: c.country === "Other" ? "Other" : countryName(c.country), value: c.weight_pct,
                                   other: c.country === "Other" }))
    : [];
  const bonds = data.holdings.filter((h) => h.kind === "bond").length > data.holdings.length / 2;
  const rows = showAll ? data.holdings : data.holdings.slice(0, TABLE_ROWS);

  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Holdings {data.count > 0 && <span className="muted small">· {data.count.toLocaleString()}</span>}</h2>
        <span className="small muted">
          {data.source === "sec" && data.as_of
            ? <>SEC N-PORT filing · holdings as of {longDate(data.as_of)}{data.filed ? ` (filed ${longDate(data.filed)})` : ""}</>
            : data.source === "yahoo" ? "Yahoo · top 10 only" : null}
        </span>
      </div>
      {data.notes.map((n) => <p key={n} className="small muted" style={{ marginTop: 0 }}>{n}</p>)}

      {heat.length > 0 && (
        <>
          <div ref={box} className="treemap" style={{ height }} role="list" aria-label="Largest holdings"
               onMouseLeave={() => setHover(null)}>
            {tiles.map((t) => {
              const { bg, strong } = fill(t.h.change_pct);
              const tiny = t.w < 34 || t.h_ < 20;
              const small = t.w < 64 || t.h_ < 40;
              return (
                <div key={t.h.symbol} role="listitem" className={`tile ${strong ? "strong" : ""} ${t.h.us_listed ? "link" : ""}`}
                     style={{ left: t.x, top: t.y, width: Math.max(t.w - GAP, 0), height: Math.max(t.h_ - GAP, 0), background: bg,
                              padding: small ? 2 : undefined }}
                     aria-label={`${t.h.symbol} ${t.h.weight_pct.toFixed(2)}% of fund, ${pct(t.h.change_pct)} today`}
                     onMouseMove={(e) => setHover({ h: t.h, x: e.clientX, y: e.clientY })}
                     onClick={() => t.h.us_listed && navigate(`/t/${t.h.symbol}`)}>
                  {!tiny && <div className="sym" style={{ fontSize: small ? 10 : t.w > 140 && t.h_ > 80 ? 16 : 13 }}>{t.h.symbol}</div>}
                  {!small && <div className="chg">{pct(t.h.change_pct)}</div>}
                  {!small && t.h_ > 64 && <div className="wt">{t.h.weight_pct.toFixed(1)}%</div>}
                </div>
              );
            })}
          </div>
          <div className="row small muted" style={{ marginTop: 8, gap: 8 }}>
            <span>−{FULL_AT}%</span>
            <span className="heat-scale" aria-hidden />
            <span>+{FULL_AT}%</span>
            <span>· largest {heat.length} stocks = {heatWeight.toFixed(1)}% of the fund · size by weight (as filed), color by today's move · gray = no quote</span>
          </div>
        </>
      )}

      {data.holdings.length > 0 ? (
        <div className="table-wrap" style={{ marginTop: heat.length ? 14 : 0 }}>
          <table>
            <thead><tr>
              <th>#</th><th className="left">Holding</th>
              {bonds ? <><th>Coupon</th><th>Maturity</th></> : <><th className="left">Symbol</th><th className="left">Country</th></>}
              <th>Weight</th><th>Value</th>{!bonds && <th>Day %</th>}
            </tr></thead>
            <tbody>
              {rows.map((h, i) => (
                <tr key={`${i}-${h.symbol ?? h.name}`} style={{ cursor: h.us_listed ? "pointer" : "default" }}
                    onClick={() => h.us_listed && h.symbol && navigate(`/t/${h.symbol}`)}>
                  <td className="muted">{i + 1}</td>
                  <td className="left" style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }} title={h.name ?? undefined}>{h.name ?? "–"}</td>
                  {bonds
                    ? <><td>{h.coupon_pct == null ? "–" : `${h.coupon_pct.toFixed(2)}%`}</td><td>{h.maturity ?? "–"}</td></>
                    : <><td className="left">{h.symbol ? <span className="sym">{h.symbol}</span> : <span className="muted">–</span>}</td>
                        <td className="left">{countryName(h.country)}</td></>}
                  <td>{h.weight_pct.toFixed(2)}%</td>
                  <td>{h.value_usd == null ? "–" : `$${big(h.value_usd)}`}</td>
                  {!bonds && <td className={tone(h.change_pct)}>{pct(h.change_pct)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
          {data.holdings.length > TABLE_ROWS && (
            <div className="row small" style={{ marginTop: 8, gap: 10 }}>
              <button className="btn ghost" onClick={() => setShowAll((x) => !x)}>
                {showAll ? "Show fewer" : `Show all ${data.holdings.length.toLocaleString()}`}
              </button>
              {data.count > data.holdings.length && (
                <span className="muted">The largest {data.holdings.length.toLocaleString()} of {data.count.toLocaleString()} are listed; weights by country and sector cover all.</span>
              )}
            </div>
          )}
        </div>
      ) : (
        <p className="muted" style={{ marginTop: 0 }}>No individual holdings published for this fund.</p>
      )}

      {(sectors.length > 0 || countries.length > 0 || assets.length > 0 || ratings.length > 0) && (
        <div className="grid-2" style={{ marginTop: 14 }}>
          {sectors.length > 0 && (
            <div><h3 className="small muted" style={{ margin: "0 0 8px" }}>Sectors</h3>
              <BarList items={sectors} total={100} format={pctFmt} /></div>
          )}
          {countries.length > 0 && (
            <div><h3 className="small muted" style={{ margin: "0 0 8px" }}>Countries</h3>
              <BarList items={countries} total={100} format={pctFmt} /></div>
          )}
          {ratings.length > 0 && (
            <div><h3 className="small muted" style={{ margin: "0 0 8px" }}>
              Credit quality{data.bond_ratings.us_government ? ` · ${data.bond_ratings.us_government.toFixed(1)}% US government` : ""}</h3>
              <BarList items={ratings} total={100} format={pctFmt} /></div>
          )}
          {assets.length > 0 && (
            <div><h3 className="small muted" style={{ margin: "0 0 8px" }}>Asset mix</h3>
              <BarList items={assets} total={100} format={pctFmt} /></div>
          )}
        </div>
      )}

      {hover && (
        <div className="tooltip" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          <div><strong>{hover.h.symbol}</strong> {hover.h.name && <span className="muted">{hover.h.name}</span>}</div>
          <div>{hover.h.weight_pct.toFixed(2)}% of fund</div>
          <div>{price(hover.h.price)} · <span className={tone(hover.h.change_pct)}>{pct(hover.h.change_pct)}</span> today</div>
        </div>
      )}
    </section>
  );
}
