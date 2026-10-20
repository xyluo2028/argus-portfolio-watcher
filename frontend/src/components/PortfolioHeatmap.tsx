import { useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Position } from "../api";
import { extLabel, money, pct, price, tone } from "../format";
import { heatFill, squarify } from "../treemap";

const GAP = 2;
const HEADER = 18; // sector label strip

type Color = "day" | "ext" | "total";
const COLOR: Record<Color, { fullAt: number; value: (p: Position) => number | null | undefined }> = {
  day: { fullAt: 3, value: (p) => p.change_pct },
  ext: { fullAt: 3, value: (p) => p.ext_change_pct },
  total: { fullAt: 40, value: (p) => p.unrealized_pct },
};
const KEY = "argus.heatmap.color";

/** The portfolio as a treemap: one tile per position sized by its value, colored by today's move
 * (or the pre-market/after-hours move, or total return), grouped into sector blocks. */
export function PortfolioHeatmap({ positions }: { positions: Position[] }) {
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState<{ p: Position; x: number; y: number } | null>(null);
  const [color, setColor] = useState<Color>(() => {
    try { return (localStorage.getItem(KEY) as Color) || "day"; } catch { return "day"; }
  });
  const box = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const rows = positions.filter((p) => (p.market_value ?? 0) > 0);
  const shown = rows.length > 0;
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, [shown]);

  const hasExt = rows.some((p) => p.ext_change_pct != null);
  const mode: Color = color === "ext" && !hasExt ? "day" : color;
  const pick = (c: Color) => {
    setColor(c);
    try { localStorage.setItem(KEY, c); } catch { /* ignore */ }
  };

  const total = rows.reduce((s, p) => s + (p.market_value ?? 0), 0);
  const dayPnl = rows.reduce((s, p) => s + (p.day_pnl ?? 0), 0);
  const height = Math.max(320, Math.min(560, Math.round(width * 0.55)));

  // Sector blocks first (largest first), then positions inside each; one sector = no blocks.
  const groups = new Map<string, Position[]>();
  for (const p of rows) {
    const k = p.sector ?? "Unclassified";
    groups.set(k, [...(groups.get(k) ?? []), p]);
  }
  const sectors = [...groups.entries()].map(([name, ps]) => ({
    name, ps: ps.sort((a, b) => (b.market_value ?? 0) - (a.market_value ?? 0)),
    value: ps.reduce((s, p) => s + (p.market_value ?? 0), 0),
  })).sort((a, b) => b.value - a.value);
  const blocks = width ? (sectors.length > 1 ? squarify(sectors, (g) => g.value, 0, 0, width, height)
    : sectors.map((g) => ({ item: g, x: 0, y: 0, w: width, h: height }))) : [];
  const labeled = (b: { w: number; h: number }) => sectors.length > 1 && b.w > 70 && b.h > 44;

  const { fullAt, value } = COLOR[mode];
  const unit = mode === "total" ? "total return" : mode === "ext" ? extLabel(rows.find((p) => p.ext_session)?.ext_session).toLowerCase() : "today";

  return (
    <div>
      <div className="row small" style={{ justifyContent: "space-between", marginBottom: 8, gap: 10 }}>
        <span className="muted">
          {rows.length} position{rows.length === 1 ? "" : "s"} · {money(total, { whole: true })} ·{" "}
          <span className={tone(dayPnl)}>{money(dayPnl, { signed: true, whole: true })}</span> today
        </span>
        <div className="seg" role="group" aria-label="Color by">
          <button aria-pressed={mode === "day"} onClick={() => pick("day")}>Day %</button>
          {hasExt && <button aria-pressed={mode === "ext"} onClick={() => pick("ext")}>{extLabel(rows.find((p) => p.ext_session)?.ext_session)}</button>}
          <button aria-pressed={mode === "total"} onClick={() => pick("total")}>Total P&amp;L %</button>
        </div>
      </div>

      {rows.length === 0 ? <p className="muted">No priced positions match the filter.</p> : (
        <div ref={box} className="treemap portfolio-heatmap" style={{ height }} onMouseLeave={() => setHover(null)}>
          {blocks.map((b) => {
            const head = labeled(b) ? HEADER : 0;
            const tiles = squarify(b.item.ps, (p) => p.market_value ?? 0, b.x, b.y + head, b.w, b.h - head);
            return (
              <div key={b.item.name} role="list" aria-label={`${b.item.name}, ${((b.item.value / total) * 100).toFixed(1)}%`}>
                {head > 0 && (
                  <div className="sector-label" style={{ left: b.x, top: b.y, width: b.w - GAP }}>
                    {b.item.name} <span className="muted">{((b.item.value / total) * 100).toFixed(1)}%</span>
                  </div>
                )}
                {tiles.map((t) => {
                  const v = value(t.item);
                  const { bg, strong } = heatFill(v, fullAt);
                  const tiny = t.w < 34 || t.h < 20;
                  const small = t.w < 64 || t.h < 40;
                  return (
                    <div key={t.item.symbol} role="listitem" className={`tile link ${strong ? "strong" : ""}`}
                         style={{ left: t.x, top: t.y, width: Math.max(t.w - GAP, 0), height: Math.max(t.h - GAP, 0), background: bg,
                                  padding: small ? 2 : undefined }}
                         aria-label={`${t.item.symbol} ${money(t.item.market_value, { whole: true })}, ${pct(v)} ${unit}`}
                         onMouseMove={(e) => setHover({ p: t.item, x: e.clientX, y: e.clientY })}
                         onClick={() => navigate(`/t/${t.item.symbol}`)}>
                      {!tiny && <div className="sym" style={{ fontSize: small ? 10 : t.w > 140 && t.h > 80 ? 16 : 13 }}>{t.item.symbol}</div>}
                      {!small && <div className="chg">{pct(v, mode === "total" ? 1 : 2)}</div>}
                      {!small && t.h > 64 && <div className="wt">{(((t.item.market_value ?? 0) / total) * 100).toFixed(1)}%</div>}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      {rows.length > 0 && (
        <div className="row small muted" style={{ marginTop: 8, gap: 8 }}>
          <span>−{fullAt}%</span>
          <span className="heat-scale" aria-hidden />
          <span>+{fullAt}%</span>
          <span>· size by value, color by {unit} · weights are of the positions shown · click a tile to open it</span>
        </div>
      )}

      {hover && (
        <div className="tooltip" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          <div><strong>{hover.p.symbol}</strong> {hover.p.name && <span className="muted">{hover.p.name}</span>}</div>
          <div>{money(hover.p.market_value)} · {(((hover.p.market_value ?? 0) / total) * 100).toFixed(1)}% · {price(hover.p.price)}</div>
          <div>Today <span className={tone(hover.p.change_pct)}>{pct(hover.p.change_pct)}</span>{" "}
            (<span className={tone(hover.p.day_pnl)}>{money(hover.p.day_pnl, { signed: true })}</span>)</div>
          {hover.p.ext_change_pct != null && (
            <div>{extLabel(hover.p.ext_session)} <span className={tone(hover.p.ext_change_pct)}>{pct(hover.p.ext_change_pct)}</span></div>
          )}
          <div>Total <span className={tone(hover.p.unrealized_pct)}>{pct(hover.p.unrealized_pct, 1)}</span>{" "}
            (<span className={tone(hover.p.unrealized_pnl)}>{money(hover.p.unrealized_pnl, { signed: true })}</span>)</div>
          {hover.p.sector && <div className="muted">{hover.p.sector}</div>}
        </div>
      )}
    </div>
  );
}
