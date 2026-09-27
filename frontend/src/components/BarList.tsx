import { money } from "../format";

export interface BarItem { label: string; value: number; other?: boolean }

/** Single-series horizontal bars (slot-1 hue), value labeled at the tip. */
export function BarList({ items, total }: { items: BarItem[]; total: number }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="bars" role="table" aria-label="Allocation">
      {items.map((i) => {
        const share = total ? (i.value / total) * 100 : 0;
        return (
          <div className="bar-row" role="row" key={i.label} title={`${i.label}: ${money(i.value)} (${share.toFixed(1)}%)`}>
            <span className="lbl" role="cell">{i.label}</span>
            <span className="track" role="cell">
              <span className={`fill ${i.other ? "other" : ""}`} style={{ width: `${(i.value / max) * 100}%`, display: "block" }} />
            </span>
            <span className="val" role="cell">{share.toFixed(1)}%</span>
          </div>
        );
      })}
    </div>
  );
}

/** Top-N items plus an "Other" remainder, so a long tail never becomes 50 slivers. */
export function topN(entries: [string, number][], n: number): BarItem[] {
  const sorted = [...entries].sort((a, b) => b[1] - a[1]);
  const head = sorted.slice(0, n).map(([label, value]) => ({ label, value }));
  const rest = sorted.slice(n).reduce((s, [, v]) => s + v, 0);
  return rest > 0 ? [...head, { label: `Other (${sorted.length - n})`, value: rest, other: true }] : head;
}
