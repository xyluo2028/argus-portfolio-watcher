// One definition per indicator, shared by the dashboard's tabs and the stock page, so both show the
// same figures under the same names. Values come from /api/fundamentals (and the portfolio and
// watchlist variants), which add the computed ones (1M return, price CAGR, FCF margin).
import { big, money, pct, ratio } from "./format";

export type Metrics = Record<string, number | null | undefined>;
type Kind = "big" | "money" | "ratio1" | "ratio2" | "pct" | "pct2" | "signed";

export interface MetricDef {
  key: string;
  /** Table header (dashboard) */
  short: string;
  /** Stat label (stock page) */
  label: string;
  title?: string;
  kind: Kind;
  /** Needs the live price (distance from the 52-week high, from moving averages). */
  fromPrice?: (m: Metrics, price: number | null | undefined) => number | null;
}

const rel = (a: number | null | undefined, b: number | null | undefined) => (a != null && b ? (a / b - 1) * 100 : null);

const DEFS: MetricDef[] = [
  // valuation & size
  { key: "market_cap", short: "Mkt cap", label: "Market cap", kind: "big" },
  { key: "revenue_ttm", short: "Revenue", label: "Revenue (TTM)", kind: "big" },
  { key: "eps_ttm", short: "EPS", label: "EPS (TTM)", kind: "money" },
  { key: "pe_ttm", short: "P/E", label: "P/E (TTM)", kind: "ratio1", title: "Price ÷ trailing 12-month earnings" },
  { key: "pe_forward", short: "Fwd P/E", label: "P/E (forward)", kind: "ratio1", title: "Price ÷ next 12 months' estimated earnings" },
  { key: "peg", short: "PEG", label: "PEG", kind: "ratio2", title: "P/E ÷ expected EPS growth; below 1 can mean growth is cheap" },
  { key: "ps_ttm", short: "P/S", label: "P/S (TTM)", kind: "ratio1" },
  { key: "pb", short: "P/B", label: "P/B", kind: "ratio1" },
  { key: "ev_ebitda", short: "EV/EBITDA", label: "EV/EBITDA", kind: "ratio1" },
  { key: "debt_to_equity", short: "Debt/Eq", label: "Debt / equity", kind: "ratio2" },
  { key: "fcf_ttm", short: "FCF", label: "Free cash flow (TTM)", kind: "big" },
  // growth (YoY = trailing 12 months or latest quarter vs a year earlier; CAGR = compound annual rate)
  { key: "revenue_growth_yoy_pct", short: "Rev YoY", label: "Revenue growth YoY", kind: "signed", title: "Trailing 12 months vs a year earlier" },
  { key: "revenue_growth_q_yoy_pct", short: "Rev Q YoY", label: "Revenue growth, latest quarter", kind: "signed", title: "Latest quarter vs the same quarter a year earlier" },
  { key: "revenue_growth_3y_pct", short: "Rev CAGR 3Y", label: "Revenue CAGR 3Y", kind: "signed", title: "Compound annual growth over 3 years" },
  { key: "revenue_growth_5y_pct", short: "Rev CAGR 5Y", label: "Revenue CAGR 5Y", kind: "signed", title: "Compound annual growth over 5 years" },
  { key: "eps_growth_yoy_pct", short: "EPS YoY", label: "EPS growth YoY", kind: "signed" },
  { key: "eps_growth_q_yoy_pct", short: "EPS Q YoY", label: "EPS growth, latest quarter", kind: "signed" },
  { key: "eps_growth_3y_pct", short: "EPS CAGR 3Y", label: "EPS CAGR 3Y", kind: "signed" },
  { key: "eps_growth_5y_pct", short: "EPS CAGR 5Y", label: "EPS CAGR 5Y", kind: "signed" },
  // profitability
  { key: "gross_margin_pct", short: "Gross", label: "Gross margin", kind: "pct" },
  { key: "operating_margin_pct", short: "Operating", label: "Operating margin", kind: "pct" },
  { key: "net_margin_pct", short: "Net", label: "Net margin", kind: "pct" },
  { key: "fcf_margin_pct", short: "FCF margin", label: "FCF margin", kind: "pct", title: "Free cash flow ÷ revenue (TTM)" },
  { key: "roe_pct", short: "ROE", label: "Return on equity", kind: "pct" },
  { key: "roa_pct", short: "ROA", label: "Return on assets", kind: "pct" },
  { key: "roic_pct", short: "ROIC", label: "Return on invested capital", kind: "pct", title: "Operating profit after tax ÷ debt + equity (TTM)" },
  // momentum (to the latest close; price-relative ones use the live price)
  { key: "return_1w_pct", short: "1W", label: "1 week", kind: "signed" },
  { key: "return_1m_pct", short: "1M", label: "1 month", kind: "signed" },
  { key: "return_3m_pct", short: "3M", label: "3 months", kind: "signed" },
  { key: "return_6m_pct", short: "6M", label: "6 months", kind: "signed" },
  { key: "return_ytd_price_pct", short: "YTD", label: "Year to date", kind: "signed" },
  { key: "return_1y_pct", short: "1Y", label: "1 year", kind: "signed" },
  { key: "cagr_3y_pct", short: "CAGR 3Y", label: "Price CAGR 3Y", kind: "signed", title: "Compound annual price return over 3 years (no dividends)" },
  { key: "cagr_5y_pct", short: "CAGR 5Y", label: "Price CAGR 5Y", kind: "signed", title: "Compound annual price return over 5 years (no dividends)" },
  { key: "rel_sp500_1y_pct", short: "vs S&P 1Y", label: "vs S&P 500, 1 year", kind: "signed" },
  { key: "from_52w_high", short: "From 52W high", label: "From 52-week high", kind: "signed", fromPrice: (m, p) => rel(p, m.high_52w) },
  { key: "vs_sma50", short: "vs 50D avg", label: "vs 50-day average", kind: "signed", fromPrice: (m, p) => rel(p, m.sma50) },
  { key: "vs_sma200", short: "vs 200D avg", label: "vs 200-day average", kind: "signed", fromPrice: (m, p) => rel(p, m.sma200) },
  // dividends & risk
  { key: "dividend_yield_pct", short: "Yield (TTM)", label: "Dividend yield (TTM)", kind: "pct2", title: "Dividends paid over the last 12 months ÷ price" },
  { key: "payout_ratio_pct", short: "Payout", label: "Payout ratio", kind: "pct", title: "Dividends as a share of earnings (TTM)" },
  { key: "dividend_growth_5y_pct", short: "Div CAGR 5Y", label: "Dividend CAGR 5Y", kind: "signed" },
  { key: "beta", short: "Beta", label: "Beta", kind: "ratio2" },
  // funds
  { key: "expense_ratio_pct", short: "Expense ratio", label: "Expense ratio", kind: "pct2" },
  { key: "net_assets", short: "Net assets", label: "Net assets", kind: "big" },
  { key: "ytd_return_pct", short: "YTD (total)", label: "YTD total return", kind: "signed" },
  { key: "return_3y_pct", short: "3Y avg", label: "3-year average return", kind: "signed" },
  { key: "return_5y_pct", short: "5Y avg", label: "5-year average return", kind: "signed" },
];

export const METRICS: Record<string, MetricDef> = Object.fromEntries(DEFS.map((d) => [d.key, d]));

/** The same groups name the dashboard's tabs and the stock page's sections. */
export const GROUPS = {
  Financials: ["market_cap", "revenue_ttm", "eps_ttm", "pe_ttm", "pe_forward", "peg", "ps_ttm", "pb", "ev_ebitda", "debt_to_equity", "fcf_ttm"],
  Growth: ["revenue_growth_yoy_pct", "revenue_growth_q_yoy_pct", "revenue_growth_3y_pct", "revenue_growth_5y_pct",
           "eps_growth_yoy_pct", "eps_growth_q_yoy_pct", "eps_growth_3y_pct", "eps_growth_5y_pct"],
  Profitability: ["gross_margin_pct", "operating_margin_pct", "net_margin_pct", "fcf_margin_pct", "roe_pct", "roa_pct", "roic_pct"],
  Momentum: ["return_1w_pct", "return_1m_pct", "return_3m_pct", "return_6m_pct", "return_ytd_price_pct", "return_1y_pct",
             "cagr_3y_pct", "cagr_5y_pct", "rel_sp500_1y_pct", "from_52w_high", "vs_sma50", "vs_sma200"],
  "Dividends & risk": ["dividend_yield_pct", "payout_ratio_pct", "dividend_growth_5y_pct", "beta"],
  Fund: ["expense_ratio_pct", "net_assets", "ytd_return_pct", "return_3y_pct", "return_5y_pct"],
} as const;
export type GroupName = keyof typeof GROUPS;

export function metricValue(key: string, m: Metrics | undefined, price?: number | null): number | null {
  const d = METRICS[key];
  if (!d || !m) return null;
  const v = d.fromPrice ? d.fromPrice(m, price) : m[key];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function formatMetric(key: string, v: number | null): string {
  if (v == null) return "–";
  switch (METRICS[key]?.kind) {
    case "big": return big(v);
    case "money": return money(v);
    case "ratio1": return ratio(v, 1);
    case "ratio2": return ratio(v, 2);
    case "pct": return `${v.toFixed(1)}%`;
    case "pct2": return `${v.toFixed(2)}%`;
    case "signed": return pct(v, 1);
    default: return String(v);
  }
}

/** Signed figures get a direction color; plain percentages only turn red when negative. */
export function metricTone(key: string, v: number | null): string | undefined {
  if (v == null) return undefined;
  const kind = METRICS[key]?.kind;
  if (kind === "signed") return v > 0 ? "up" : v < 0 ? "down" : undefined;
  if (kind === "pct") return v < 0 ? "down" : undefined;
  return undefined;
}
