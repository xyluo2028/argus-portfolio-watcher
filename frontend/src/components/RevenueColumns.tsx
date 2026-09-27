import { useState } from "react";
import type { FinancialPeriod } from "../api";
import { big } from "../format";

/** Single-series column chart of revenue (oldest -> newest), value labeled on the latest column only. */
export function RevenueColumns({ periods }: { periods: FinancialPeriod[] }) {
  const data = [...periods].reverse().filter((p) => p.revenue != null);
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);
  if (data.length === 0) return null;

  const W = 480, H = 160, pad = { l: 44, r: 8, t: 16, b: 22 };
  const max = Math.max(...data.map((d) => d.revenue!));
  const ticks = [0, max / 2, max];
  const band = (W - pad.l - pad.r) / data.length;
  const bw = Math.min(24, band * 0.6);
  const y = (v: number) => pad.t + (H - pad.t - pad.b) * (1 - v / max);

  return (
    <div style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Revenue by period">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="var(--grid)" strokeWidth={1} />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize={10} fill="var(--muted)">{big(v)}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad.l + band * i + (band - bw) / 2;
          const top = y(d.revenue!);
          const h = y(0) - top;
          const r = Math.min(4, h);
          const last = i === data.length - 1;
          return (
            <g key={d.period_end}
               onMouseMove={(e) => setHover({ i, x: e.clientX, y: e.clientY })} onMouseLeave={() => setHover(null)}>
              {/* hit target wider than the mark */}
              <rect x={pad.l + band * i} y={pad.t} width={band} height={H - pad.t - pad.b} fill="transparent" />
              <path d={`M${x},${y(0)} V${top + r} Q${x},${top} ${x + r},${top} H${x + bw - r} Q${x + bw},${top} ${x + bw},${top + r} V${y(0)} Z`}
                    fill="var(--series-1)" opacity={hover && hover.i !== i ? 0.55 : 1} />
              <text x={x + bw / 2} y={H - 6} textAnchor="middle" fontSize={10} fill="var(--muted)">
                {d.period_end.slice(2, 7)}
              </text>
              {last && <text x={x + bw / 2} y={top - 4} textAnchor="middle" fontSize={10} fill="var(--text-2)">{big(d.revenue)}</text>}
            </g>
          );
        })}
      </svg>
      {hover && (
        <div className="tooltip" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          <div><strong>{data[hover.i].period_end}</strong></div>
          <div>Revenue {big(data[hover.i].revenue)}</div>
          {data[hover.i].net_margin_pct != null && <div>Net margin {data[hover.i].net_margin_pct!.toFixed(1)}%</div>}
        </div>
      )}
    </div>
  );
}
