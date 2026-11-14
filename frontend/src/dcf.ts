import type { DcfData, DcfInputs, DcfMetricKey } from "./api";

/** The calculator's model, an exit-multiple discounted cash flow:
 *  - the metric grows `growth`% in year 1, each later year's rate shrinking by `decay`% of the one before;
 *  - the share count changes `share_change`% a year (negative = buybacks), the dividend `dividend_growth`%;
 *  - the price in the final year is the metric × the exit multiple ÷ the shares then;
 *  - fair value is that price and the dividends on the way, each discounted at your target return.
 * Fair value is therefore the most you can pay and still earn the target return. */
export interface DcfYear { year: number; growth: number; metric: number; shares: number; price: number; dividend: number }
export interface DcfResult {
  rows: DcfYear[]; futurePrice: number; dividends: number; fairValue: number;
  upsidePct: number; cagrPct: number | null; futureChangePct: number;
}

export function project(inp: DcfInputs, price: number, shares: number): DcfResult | null {
  if (!(price > 0) || !(shares > 0) || !(inp.base > 0) || !(inp.years >= 1)) return null;
  const r = inp.target_return / 100;
  const rows: DcfYear[] = [];
  let metric = inp.base, sh = shares, dps = inp.dps, g = inp.growth / 100, divPv = 0, divs = 0;
  for (let t = 1; t <= inp.years; t++) {
    if (t > 1) g *= 1 - inp.decay / 100;
    metric *= 1 + g;
    sh *= 1 + inp.share_change / 100;
    dps *= 1 + inp.dividend_growth / 100;
    divs += dps;
    divPv += dps / (1 + r) ** t;
    rows.push({ year: t, growth: g * 100, metric, shares: sh, price: (metric * inp.multiple) / sh, dividend: dps });
  }
  const futurePrice = rows[rows.length - 1].price;
  const fairValue = futurePrice / (1 + r) ** inp.years + divPv;
  const end = futurePrice + divs;
  return {
    rows, futurePrice, dividends: divs, fairValue,
    upsidePct: (fairValue / price - 1) * 100,
    futureChangePct: (futurePrice / price - 1) * 100,
    cagrPct: end > 0 ? ((end / price) ** (1 / inp.years) - 1) * 100 : null,
  };
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const round = (v: number, step = 0.1) => Number((Math.round(v / step) * step).toFixed(2));
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b);
  return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null;
};

export const METRIC_ORDER: DcfMetricKey[] = ["free_cash_flow", "operating_cash_flow", "net_income", "revenue"];
export const MULTIPLE_LABEL: Record<DcfMetricKey, string> = {
  free_cash_flow: "P/FCF", operating_cash_flow: "P/OCF", net_income: "P/E", revenue: "P/S",
};

/** The first metric with a positive current value, in the order cash flow first. */
export function defaultMetric(d: DcfData): DcfMetricKey {
  return METRIC_ORDER.find((k) => (d.metrics[k].base ?? 0) > 0) ?? "revenue";
}

/** Growth from history: the 5-year rate, else the 3-year one. */
export function historicalGrowth(d: DcfData, k: DcfMetricKey): number | null {
  const g = d.metrics[k].growth;
  return g.hist_5y ?? g.hist_3y;
}

/** Starting inputs for a metric: growth is the middle of the 5- and 3-year history and analysts'
 * estimate (one outlier, like a rebound from a bad year, doesn't set it), held within -10..30%;
 * the exit multiple is the 5-year median, else today's. */
export function defaults(d: DcfData, k: DcfMetricKey): DcfInputs {
  const m = d.metrics[k];
  const gs = [m.growth.hist_5y, m.growth.hist_3y, m.growth.analyst].filter((x): x is number => x != null);
  const multiple = m.multiple.median_5y ?? m.multiple.current ?? 15;
  return {
    metric: k, base: m.base ?? 0, years: 5,
    growth: round(clamp(median(gs) ?? 5, -10, 30)), decay: 0,
    multiple: round(clamp(multiple, 1, 200)), target_return: 10,
    dps: round(d.dps, 0.01), dividend_growth: round(clamp(d.dividend_growth_5y ?? 0, 0, 15)),
    share_change: round(clamp(d.share_change ?? 0, -10, 10)),
  };
}
