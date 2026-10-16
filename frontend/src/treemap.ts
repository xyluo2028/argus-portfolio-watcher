/** Treemap layout and heatmap colors shared by the ETF holdings and portfolio heatmaps. */

export interface Rect<T> { item: T; x: number; y: number; w: number; h: number }

/** Squarified treemap: rows of tiles kept as close to square as possible. Items should be sorted
 * largest first; non-positive weights are dropped. */
export function squarify<T>(items: T[], weight: (t: T) => number, x0: number, y0: number, width: number, height: number): Rect<T>[] {
  const kept = items.filter((t) => weight(t) > 0);
  const total = kept.reduce((s, t) => s + weight(t), 0);
  if (!total || width <= 0 || height <= 0) return [];
  const scale = (width * height) / total;
  const out: Rect<T>[] = [];
  let rest = kept.map((item) => ({ item, area: weight(item) * scale }));
  let x = x0, y = y0, w = width, h = height;
  const worst = (row: { area: number }[], side: number) => {
    const sum = row.reduce((s, r) => s + r.area, 0);
    const max = Math.max(...row.map((r) => r.area)), min = Math.min(...row.map((r) => r.area));
    return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
  };
  while (rest.length) {
    const side = Math.min(w, h);
    let row = [rest[0]];
    let i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) row = [...row, rest[i++]];
    rest = rest.slice(i);
    const sum = row.reduce((s, r) => s + r.area, 0);
    if (w >= h) { // lay the row as a column on the left
      const cw = sum / h;
      let cy = y;
      for (const r of row) { const th = r.area / cw; out.push({ item: r.item, x, y: cy, w: cw, h: th }); cy += th; }
      x += cw; w -= cw;
    } else { // as a row on top
      const rh = sum / w;
      let cx = x;
      for (const r of row) { const tw = r.area / rh; out.push({ item: r.item, x: cx, y, w: tw, h: rh }); cx += tw; }
      y += rh; h -= rh;
    }
  }
  return out;
}

/** Diverging fill: gray at 0, the up/down hue growing with the size of the move up to `fullAt`.
 * `strong` = dark enough to need white text. */
export function heatFill(change: number | null | undefined, fullAt: number): { bg: string; strong: boolean } {
  if (change == null || Number.isNaN(change)) return { bg: "var(--surface-2)", strong: false };
  const t = Math.min(Math.abs(change) / fullAt, 1);
  const hue = change >= 0 ? "var(--heat-up)" : "var(--heat-down)";
  return { bg: `color-mix(in oklab, ${hue} ${change === 0 ? 0 : Math.round(15 + t * 85)}%, var(--heat-mid))`, strong: t > 0.45 };
}
