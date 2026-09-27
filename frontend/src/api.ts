// Typed client for the Argus JSON API (backend/argus/api/server.py).

export type Session = "pre" | "regular" | "post" | "closed";

export interface MarketStatus {
  session: Session;
  is_trading_day: boolean;
  is_half_day: boolean;
  now: string;
  next_open: string;
  next_close: string;
  last_close: string;
  last_session: string;
}

export interface Quote {
  symbol: string;
  price: number;
  prev_close: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  as_of: string;
  session_date: string; // YYYY-MM-DD trading day this price belongs to
  source: string;
  delayed: boolean;
  change: number | null;
  change_pct: number | null;
}

export interface Lot {
  txn_id: number;
  kind: "OPENING" | "BUY";
  opened: string;
  qty: number;
  cost_per_share: number;
}

export interface Position {
  symbol: string;
  name: string | null;
  type: string | null;
  sector: string | null;
  qty: number;
  avg_cost: number | null;
  cost_basis: number;
  realized_pnl: number;
  first_opened: string;
  lot_count: number;
  price?: number;
  prev_close?: number | null;
  change_pct?: number | null;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pct?: number | null;
  day_pnl?: number;
  quote_as_of?: string;
  quote_source?: string;
  weight_pct: number | null;
  lots?: Lot[];
}

export interface Summary {
  portfolio: { id: number; name: string; benchmark: string };
  as_of: string;
  market: MarketStatus;
  totals: {
    market_value: number | null;
    cost_basis: number;
    day_pnl: number | null;
    day_pnl_pct: number | null;
    unrealized_pnl: number | null;
    unrealized_pct: number | null;
    realized_pnl: number;
    dividends: number;
    position_count: number;
    fully_priced: boolean;
  };
  positions: Position[];
  quote_errors?: Record<string, string>;
}

export interface PortfolioRef { id: number; name: string; benchmark: string }

export interface HistoryResponse {
  symbol: string;
  interval: string;
  period: string;
  bars: { ts: string; o: number; h: number; l: number; c: number; v: number }[];
  indicators?: Record<string, (number | null)[] | Record<string, (number | null)[]>>;
}

export interface Fundamentals {
  symbol: string;
  as_of: string;
  metrics: Record<string, number | null>;
  sources: Record<string, string>;
}

export interface FinancialPeriod {
  period_end: string;
  revenue?: number;
  gross_margin_pct?: number;
  operating_margin_pct?: number;
  net_margin_pct?: number;
  net_income?: number;
  eps_diluted?: number;
  free_cash_flow?: number;
}

export interface Financials {
  symbol: string;
  company: string | null;
  period: "quarterly" | "annual";
  units: Record<string, string>;
  periods: FinancialPeriod[];
}

export interface Performance {
  portfolio: string;
  range: string;
  benchmark: string;
  provisional_today: boolean;
  summary: {
    start?: string; end?: string; sessions?: number; twr_pct?: number; benchmark_pct?: number | null;
    excess_pct?: number | null; max_drawdown_pct?: number; volatility_pct?: number | null; sharpe?: number | null;
    gain?: number; net_invested?: number; start_value?: number; end_value?: number;
  };
  series: { d: string; value: number; twr_pct: number; bench_pct: number | null }[];
}

export interface StreamUpdate {
  version: number;
  market: MarketStatus;
  stream: { state: "disabled" | "idle" | "connected" | "reconnecting"; symbols: number };
  quotes: Record<string, Quote>;
  portfolio?: Summary;
}

export class ApiError extends Error {
  constructor(public code: string, message: string, public hint?: string) {
    super(message);
  }
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const e = body?.error ?? {};
    throw new ApiError(e.code ?? `HTTP_${r.status}`, e.message ?? r.statusText, e.hint);
  }
  return body as T;
}

const enc = encodeURIComponent;

export const api = {
  portfolios: () => get<PortfolioRef[]>("/api/portfolios"),
  portfolio: (name: string, lots = false) => get<Summary>(`/api/portfolios/${enc(name)}${lots ? "?lots=true" : ""}`),
  history: (symbol: string, period: string, interval: string, indicators: string[]) =>
    get<HistoryResponse>(
      `/api/history/${enc(symbol)}?period=${period}&interval=${interval}` +
        (indicators.length ? `&indicators=${indicators.join(",")}` : ""),
    ),
  fundamentals: (symbol: string) => get<Fundamentals>(`/api/fundamentals/${enc(symbol)}`),
  financials: (symbol: string, period: "quarterly" | "annual") =>
    get<Financials>(`/api/financials/${enc(symbol)}?period=${period}&limit=8`),
  performance: (name: string, range: string) =>
    get<Performance>(`/api/portfolios/${enc(name)}/performance?range=${range}`),
  quotes: (symbols: string[]) =>
    get<{ quotes: Quote[]; errors: Record<string, string> }>(`/api/quotes?symbols=${symbols.map(enc).join(",")}`),
};
