import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Position } from "../api";
import { money, pct, price, tone } from "../format";

type Key = "symbol" | "qty" | "avg_cost" | "price" | "change_pct" | "day_pnl" | "market_value" | "weight_pct" |
  "unrealized_pnl" | "unrealized_pct";

const COLS: { key: Key; label: string }[] = [
  { key: "symbol", label: "Symbol" },
  { key: "qty", label: "Qty" },
  { key: "avg_cost", label: "Avg cost" },
  { key: "price", label: "Price" },
  { key: "change_pct", label: "Day %" },
  { key: "day_pnl", label: "Day P&L" },
  { key: "market_value", label: "Value" },
  { key: "weight_pct", label: "Weight" },
  { key: "unrealized_pnl", label: "P&L" },
  { key: "unrealized_pct", label: "P&L %" },
];

export function HoldingsTable({ positions }: { positions: Position[] }) {
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: "market_value", dir: -1 });
  const navigate = useNavigate();

  // Remember the last price per symbol so a change can flash the row once.
  const lastPrice = useRef<Record<string, number>>({});
  const flashes: Record<string, string> = {};
  for (const p of positions) {
    const prev = lastPrice.current[p.symbol];
    if (prev != null && p.price != null && p.price !== prev) flashes[p.symbol] = p.price > prev ? "flash-up" : "flash-down";
    if (p.price != null) lastPrice.current[p.symbol] = p.price;
  }

  const rows = useMemo(() => {
    const val = (p: Position) => (p[sort.key] ?? (sort.key === "symbol" ? "" : -Infinity)) as number | string;
    return [...positions].sort((a, b) => {
      const x = val(a), y = val(b);
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
    });
  }, [positions, sort]);

  const onSort = (key: Key) =>
    setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: key === "symbol" ? 1 : -1 }));

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {COLS.map((c) => (
              <th key={c.key} onClick={() => onSort(c.key)}
                  aria-sort={sort.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : undefined}>
                {c.label}{sort.key === c.key ? (sort.dir === 1 ? " ↑" : " ↓") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            // Keyed by symbol+price so the flash animation restarts on each change.
            <tr key={`${p.symbol}-${p.price}`} className={flashes[p.symbol]} tabIndex={0}
                onClick={() => navigate(`/t/${p.symbol}`)}
                onKeyDown={(e) => e.key === "Enter" && navigate(`/t/${p.symbol}`)}>
              <td><span className="sym">{p.symbol}</span><span className="name">{p.name ?? ""}</span></td>
              <td>{p.qty.toLocaleString("en-US", { maximumFractionDigits: 4 })}</td>
              <td>{price(p.avg_cost)}</td>
              <td>{price(p.price)}</td>
              <td className={tone(p.change_pct)}>{pct(p.change_pct)}</td>
              <td className={tone(p.day_pnl)}>{money(p.day_pnl, { signed: true })}</td>
              <td>{money(p.market_value)}</td>
              <td>{p.weight_pct == null ? "–" : `${p.weight_pct.toFixed(1)}%`}</td>
              <td className={tone(p.unrealized_pnl)}>{money(p.unrealized_pnl, { signed: true })}</td>
              <td className={tone(p.unrealized_pct)}>{pct(p.unrealized_pct, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
