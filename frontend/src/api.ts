// Typed client for the Argus JSON API (backend/argus/api/server.py).

// Read-only combined view of every portfolio, served by the backend under this name.
export const ALL = "all";

export interface SearchHit { symbol: string; name: string | null; type: string | null }

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
  // Pre-market / after-hours trading since the last regular close (`price` stays the regular one).
  ext_price: number | null;
  ext_as_of: string | null;
  ext_session: ExtSession | null;
  ext_change: number | null;
  ext_change_pct: number | null;
}

export type ExtSession = "pre" | "post";

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
  ext_price?: number;
  ext_change_pct?: number | null;
  ext_session?: ExtSession;
  ext_as_of?: string;
  ext_pnl?: number;
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
    ext_pnl: number | null;
    ext_pnl_pct: number | null;
    ext_session: ExtSession | null;
    ext_coverage_pct: number | null;
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

export type EarningsResult = "beat" | "miss" | "in_line" | null;
export interface EarningsReport {
  period_end: string; report_date: string; timing: "bmo" | "amc" | "dmh" | null;
  eps_estimate: number | null; eps_actual: number | null; eps_basis: "adjusted" | "reported" | null;
  eps_surprise_pct: number | null; eps_result: EarningsResult;
  revenue_estimate: number | null; revenue_actual: number | null; revenue_surprise_pct: number | null;
  revenue_result: EarningsResult;
  reaction: {
    base_date: string; base_close: number; date: string | null; open_pct: number | null; close_pct: number;
    provisional: boolean; label: string | null;
  } | null;
}
export interface EarningsHistory {
  symbol: string; as_of: string; reports: EarningsReport[];
  next: { date: string; timing: "bmo" | "amc" | "dmh" | null; eps_estimate: number | null; revenue_estimate: number | null } | null;
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
  alerts_fired?: FiredAlert[];
  portfolio?: Summary;
}

export class ApiError extends Error {
  constructor(public code: string, message: string, public hint?: string) {
    super(message);
  }
}

/** Fired when the server wants a token (ARGUS_TOKEN set and the cookie missing or stale). */
export const UNAUTHORIZED_EVENT = "argus:unauthorized";

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  const body = await r.json().catch(() => ({}));
  if (r.status === 401 && !path.startsWith("/api/auth/")) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  if (!r.ok) {
    const e = body?.error ?? {};
    throw new ApiError(e.code ?? `HTTP_${r.status}`, e.message ?? r.statusText, e.hint);
  }
  return body as T;
}

const enc = encodeURIComponent;
const send = <T>(method: string, path: string, body?: unknown) =>
  get<T>(path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });

export interface Txn {
  id: number; type: string; symbol: string; qty: number; price: number; fee: number; amount: number;
  ts: string; note: string | null; source: string; external_id: string | null; deleted: boolean;
  portfolio?: string | null;
}

export interface ImportReport {
  portfolio: string | null; dry_run: boolean; lots: number; symbols: number;
  by_type: { OPENING: number; BUY: number }; opening_through: string | null;
  checks: { check: string; ok: boolean; detail: string }[];
  lot_preview: { symbol: string; type: string; date: string; qty: number; price: number }[];
  status: "ok" | "blocked"; creates_portfolio?: boolean; inserted?: number; skipped_existing?: number;
}

export interface RestoreReport {
  created_at: string | null; dry_run: boolean; replace: boolean;
  will_remove: Record<string, number>; counts: Record<string, number>; backup?: string;
}

export interface TxnEdit { qty?: number; price?: number; fee?: number; date?: string; note?: string; dry_run: boolean }
export interface TxnEditResult {
  dry_run: boolean; before: Txn; after?: Txn; position: { before: PositionPreview; after: PositionPreview };
}

export interface TxnDraft {
  type: string; symbol: string; qty?: number; price?: number; fee?: number; amount?: number;
  date?: string; note?: string; idempotency_key?: string; dry_run?: boolean;
}

export interface PositionPreview { symbol: string; qty: number; avg_cost: number | null; cost_basis: number; realized_pnl: number }

export interface TxnResult {
  portfolio: string; dry_run: boolean; to_insert: number; skipped_existing: string[]; inserted_ids: number[];
  positions: { before: PositionPreview; after: PositionPreview }[];
}

export interface WatchItem {
  symbol: string; note: string | null; added_at: string; quote: Quote | null; metrics: Record<string, number | null> | null;
}

export interface CalEvent {
  symbol: string; kind: "earnings" | "ex_dividend" | "dividend_pay"; date: string; hour: string | null; held: boolean;
  epsEstimate?: number; epsActual?: number; epsSurprisePct?: number; revenueEstimate?: number; revenueActual?: number;
}

export interface AlertRule {
  id: number; symbol: string; kind: string; threshold: number; unit: string; label: string; note: string | null;
  active: boolean; created_by: string; last_fired?: { session_date: string; message: string };
}

export interface FiredAlert { alert_id: number; symbol: string; kind: string; message: string; note: string | null; session_date?: string; ts?: string }

export interface NoteItem {
  id: number; symbol: string; kind: "thesis" | "note"; text: string; review_on: string | null; archived: boolean;
  created_by: string; created_at: string; updated_at: string;
}

export interface WeightRow { key: string; value: number; weight_pct: number }
export interface Concentration { top1_pct: number; top5_pct: number; top10_pct: number; hhi: number; effective_positions: number; positions: number }

export interface Exposure {
  portfolio: string; total_value: number; by_type: WeightRow[]; by_sector_direct: WeightRow[];
  by_sector_lookthrough: WeightRow[]; concentration: Concentration; funds_without_profile: string[];
  top_stock_exposure: { symbol: string; name?: string; direct: number; via_etfs: number; via: string[]; total: number; total_pct: number }[];
}

export interface DriftRow { key: string; value: number; weight_pct: number; target_pct: number | null; drift_pp?: number; trade_to_target?: number; outside_band?: boolean }
export interface Drift { portfolio: string; level: string; total_value: number; tolerance_pp: number; targets_sum_pct: number; untargeted_pct: number; rows: DriftRow[]; warnings: string[]; dry_run?: boolean }

export interface SimTrade { symbol: string; side: "BUY" | "SELL"; qty?: number; amount?: number; price?: number }
export interface SimResult {
  trades: { symbol: string; side: string; qty: number; price: number }[]; net_cash: number; realized_pnl_from_trades: number;
  value_before: number | null; value_after: number;
  positions_changed: { symbol: string; weight_before: number | null; weight_after: number; qty_after: number }[];
  concentration_before: Concentration; concentration_after: Concentration; sector_lookthrough_after: WeightRow[];
}

export interface CompareResult { fields: string[]; rows: Record<string, number | string | null>[]; errors: Record<string, string> }

export interface CompanyProfile {
  symbol: string; as_of: string; name?: string; summary?: string; quote_type?: string;
  sector?: string; industry?: string; country?: string; city?: string; state?: string; address?: string; zip?: string;
  website?: string; employees?: number; officers?: { name: string | null; title: string | null }[];
  ipo?: string; logo?: string; fund_family?: string; category?: string; suggested_peers: string[];
}
export interface Peers extends CompareResult {
  symbol: string; peers: string[]; custom: boolean; kind: "stock" | "fund"; category: string | null;
}

export interface FundHolding {
  symbol: string | null; name: string | null; weight_pct: number; us_listed: boolean;
  value_usd: number | null; country: string | null; kind: "stock" | "bond" | "other";
  maturity?: string | null; coupon_pct?: number | null; price: number | null; change_pct: number | null;
}
export interface FundHoldings {
  symbol: string; fund: boolean; source: "sec" | "yahoo" | null; as_of: string | null; filed: string | null;
  count: number; holdings: FundHolding[]; sectors: { sector: string; weight_pct: number }[];
  countries: { country: string; weight_pct: number }[]; asset_classes: Record<string, number>;
  bond_ratings: Record<string, number>; notes: string[]; errors: Record<string, string>;
}

export interface DividendHolding {
  symbol: string; name: string | null; qty: number; pays: boolean; frequency: string | null; rate: number;
  trailing_12m: number; last_ex_date: string | null; last_amount: number | null; irregular: boolean;
  next_ex_date_est: string | null; annual_income: number; yield_pct: number | null; yield_on_cost_pct: number | null;
  received_ytd: number; projected_rest_of_year: number;
}
export interface Dividends {
  portfolio: string; year: number; as_of: string;
  totals: { annual_income: number; received: number; projected: number; year_total: number;
            yield_pct: number | null; yield_on_cost_pct: number | null; payers: number; positions: number };
  by_month: { month: number; received: number; projected: number }[];
  holdings: DividendHolding[];
}

export interface EarningsRow {
  symbol: string;
  last: { date: string | null; period?: string; quarter?: number; year?: number; epsActual?: number | null;
          epsEstimate?: number | null; epsSurprisePct?: number | null; revenueActual?: number | null } | null;
  next: { date: string; hour?: string | null; epsEstimate?: number | null; revenueEstimate?: number | null;
          quarter?: number; year?: number } | null;
}

export interface ReturnBases {
  symbol: string; anchor: string; session: string;
  bases: Record<string, { date: string; close: number } | null>;
  last_close: { date: string; close: number } | null;
}

export interface RiskReport {
  portfolio: string; available: boolean; reason?: string; fully_priced?: boolean;
  as_of: string; lookback_days: number; benchmark: string; total_value: number;
  beta: number; volatility_pct: number; benchmark_volatility_pct: number; max_drawdown_pct: number;
  var: Record<"95" | "99", { var_pct: number; cvar_pct: number; var_value: number; cvar_value: number }>;
  positions: { symbol: string; weight_pct: number; risk_pct: number; beta: number; vol_pct: number; history_days: number; proxied: boolean }[];
  correlation: { symbols: string[]; matrix: (number | null)[][] };
  scenarios: { key: string; label: string; start: string | null; end: string | null; spy_pct: number; portfolio_pct: number; value: number; proxied: string[] }[];
  factors: { from: string; to: string; days: number; r2: number; alpha_annual_pct: number;
             loadings: { factor: string; label: string; beta: number; t: number }[] } | null;
}

export interface Research {
  symbol: string; as_of: string; fund: boolean; price: number | null; errors: Record<string, string>;
  analysts: { count: number | null; rating: string | null; rating_mean: number | null; target_mean: number | null;
              target_median: number | null; target_high: number | null; target_low: number | null; upside_pct?: number;
              trend: { period: string; strongBuy: number; buy: number; hold: number; sell: number; strongSell: number }[] } | null;
  estimates: { trend: Record<string, Record<string, number | null>> | null; revisions: Record<string, Record<string, number | null>> | null } | null;
  insiders: { since: string; buy_count: number; buy_value: number; buyers: number; sell_count: number; sell_value: number; sellers: number;
              recent: { date: string; name: string; code: string; kind: string; shares: number; price: number | null; value: number | null; derivative: boolean }[] } | null;
  ownership: { institutions_pct: number | null; insiders_pct: number | null;
               top: { Holder: string; pctHeld: number | null; Shares: number | null; Value: number | null; pctChange: number | null; "Date Reported": string }[] };
  short_interest: { shares_short: number | null; prior_month: number | null; pct_float: number | null; days_to_cover: number | null; as_of: string | null; change_pct?: number };
  valuation: { key: string; label: string; current: number | null; min: number; p25: number; median: number; p75: number; max: number;
               percentile: number | null; points: number }[] | null;
  quality: { piotroski: { available: boolean; reason?: string; score: number; out_of: number; label: string; fiscal_years: string[];
                          tests: { test: string; group: string; pass: boolean | null }[] };
             altman: { available: boolean; reason?: string; z?: number; zone?: string; caveat?: string | null; parts: Record<string, number | null> } } | null;
  news: { ts: string; headline: string; source: string; url: string; tone: { score: number; label: string } }[];
  news_tone: { positive: number; neutral: number; negative: number };
}

export interface EconEvent { date: string; time_et: string | null; event: string; actual: string | null; consensus: string | null; previous: string | null }

export interface MarketContext {
  as_of: string; periods: string[]; errors: Record<string, string>;
  gauges: { symbol: string; label: string; kind: string; last: number; as_of: string; change: number | null;
            returns: Record<string, number | null>; spark: number[] }[];
  sectors: { symbol: string; name: string; returns: Record<string, number | null>; above_50d: boolean; above_200d: boolean }[];
  breadth: { equal_vs_cap: Record<string, number | null>; small_vs_large: Record<string, number | null>;
             sectors_above_50d: number; sectors_above_200d: number; sectors: number };
  yield_curve: { as_of: string; spread_10y_2y: number | null; spread_10y_3m: number | null;
                 lines: { label: string; date: string; points: { tenor: string; yield: number | null }[] }[] } | null;
  calendar: { fomc: { date: string; days: string; month: string; projections: boolean }[];
              events: EconEvent[]; all_events: EconEvent[]; all_count: number } | null;
}

export interface ScreenerStatus {
  built: boolean; building: boolean; progress: string | null; fiscal_year?: number; companies?: number;
  fundamentals_at?: string; prices_at?: string; fields: Record<string, { label: string; unit: "$" | "%" | "x" }>;
}
export type ScreenRow = Record<string, number | string | boolean | null> & { symbol: string; name: string | null; exchange: string | null };
export interface ScreenResult { status: ScreenerStatus; matches: number; rows: ScreenRow[] }

export const api = {
  portfolios: () => get<PortfolioRef[]>("/api/portfolios"),
  portfolio: (name: string, lots = false) => get<Summary>(`/api/portfolios/${enc(name)}${lots ? "?lots=true" : ""}`),
  history: (symbol: string, period: string, interval: string, indicators: string[]) =>
    get<HistoryResponse>(
      `/api/history/${enc(symbol)}?period=${period}&interval=${interval}` +
        (indicators.length ? `&indicators=${indicators.join(",")}` : ""),
    ),
  fundamentals: (symbol: string) => get<Fundamentals>(`/api/fundamentals/${enc(symbol)}`),
  earningsHistory: (symbol: string) => get<EarningsHistory>(`/api/earnings/${enc(symbol)}`),
  financials: (symbol: string, period: "quarterly" | "annual") =>
    get<Financials>(`/api/financials/${enc(symbol)}?period=${period}&limit=8`),
  performance: (name: string, range: string) =>
    get<Performance>(`/api/portfolios/${enc(name)}/performance?range=${range}`),
  transactions: (name: string, includeDeleted = false, symbol?: string) => {
    const qs = new URLSearchParams();
    if (includeDeleted) qs.set("include_deleted", "true");
    if (symbol) qs.set("symbol", symbol);
    const q = qs.toString();
    return get<Txn[]>(`/api/portfolios/${enc(name)}/transactions${q ? `?${q}` : ""}`);
  },
  importInvesting: (body: { filename: string; content: string; portfolio?: string; opening_through?: string; dry_run: boolean }) =>
    send<ImportReport>("POST", "/api/import/investing", body),
  authStatus: () => get<{ required: boolean; authenticated: boolean }>("/api/auth/status"),
  login: (token: string) => send<{ ok: boolean }>("POST", "/api/auth/login", { token }),
  logout: () => send<{ ok: boolean }>("POST", "/api/auth/logout"),
  snapshotUrl: "/api/snapshot",
  restoreSnapshot: (doc: unknown, replace: boolean, dryRun: boolean) =>
    send<RestoreReport>("POST", `/api/snapshot/restore?replace=${replace}&dry_run=${dryRun}`, doc),
  editTransaction: (id: number, edit: TxnEdit) => send<TxnEditResult>("PATCH", `/api/transactions/${id}`, edit),
  addTransaction: (name: string, draft: TxnDraft) =>
    send<TxnResult>("POST", `/api/portfolios/${enc(name)}/transactions`, draft),
  deleteTransaction: (id: number, dryRun: boolean) =>
    send<{ deleted: Txn; dry_run: boolean }>("DELETE", `/api/transactions/${id}?dry_run=${dryRun}`),
  watchlist: (name = "Watchlist") => get<{ watchlist: string; items: WatchItem[]; errors: Record<string, string> }>(`/api/watchlists/${enc(name)}`),
  watchAdd: (symbols: string[], note?: string, name = "Watchlist") =>
    send<{ added: string[]; already_present: string[] }>("POST", `/api/watchlists/${enc(name)}`, { symbols, note }),
  watchRemove: (symbol: string, name = "Watchlist") => send<unknown>("DELETE", `/api/watchlists/${enc(name)}/${enc(symbol)}`),
  profile: (symbol: string) => get<CompanyProfile>(`/api/profile/${enc(symbol)}`),
  holdings: (symbol: string) => get<FundHoldings>(`/api/holdings/${enc(symbol)}`),
  screenerStatus: () => get<ScreenerStatus>("/api/screener"),
  screen: (body: { filters: Record<string, (number | null)[]>; sort: string; descending: boolean; limit?: number; include_otc?: boolean }) =>
    send<ScreenResult>("POST", "/api/screener", body),
  marketContext: () => get<MarketContext>("/api/market-context"),
  research: (symbol: string) => get<Research>(`/api/research/${enc(symbol)}`),
  returnBases: (symbol: string) => get<ReturnBases>(`/api/returns/${enc(symbol)}`),
  peers: (symbol: string) => get<Peers>(`/api/peers/${enc(symbol)}`),
  setPeers: (symbol: string, peers: string[] | null) => send<Peers>("PUT", `/api/peers/${enc(symbol)}`, { peers }),
  compare: (symbols: string[]) => get<CompareResult>(`/api/compare?symbols=${symbols.map(enc).join(",")}`),
  search: (q: string, limit = 8) => get<SearchHit[]>(`/api/search?q=${enc(q)}&limit=${limit}`),
  events: (daysAhead = 14, daysBack = 7, scope: { portfolio?: string; symbol?: string } = {}) => {
    const qs = new URLSearchParams({ days_ahead: String(daysAhead), days_back: String(daysBack) });
    if (scope.portfolio) qs.set("portfolio", scope.portfolio);
    if (scope.symbol) qs.set("symbol", scope.symbol);
    return get<{ as_of: string; upcoming: CalEvent[]; recent: CalEvent[] }>(`/api/events?${qs}`);
  },
  alerts: (includeInactive = false) =>
    get<{ alerts: AlertRule[]; fired: FiredAlert[]; kinds: Record<string, { label: string; unit: string }> }>(
      `/api/alerts${includeInactive ? "?include_inactive=true" : ""}`),
  createAlert: (body: { symbol: string; kind: string; threshold: number; note?: string }) =>
    send<AlertRule>("POST", "/api/alerts", body),
  toggleAlert: (id: number, active: boolean) => send<AlertRule>("PATCH", `/api/alerts/${id}?active=${active}`),
  notes: (symbol?: string) => get<NoteItem[]>(`/api/notes${symbol ? `?symbol=${enc(symbol)}` : ""}`),
  addNote: (body: { symbol: string; text: string; kind: "thesis" | "note"; review_on?: string }) =>
    send<NoteItem>("POST", "/api/notes", body),
  updateNote: (id: number, body: { text?: string; review_on?: string; clear_review?: boolean; archived?: boolean }) =>
    send<NoteItem>("PATCH", `/api/notes/${id}`, body),
  watchlistFundamentals: (name = "Watchlist") =>
    get<{ symbols: string[]; pending: string[]; metrics: Record<string, Record<string, number | null>> }>(
      `/api/watchlists/${enc(name)}/fundamentals`),
  watchlistDividends: (name = "Watchlist") => get<Dividends>(`/api/watchlists/${enc(name)}/dividends`),
  watchlistEarnings: (name = "Watchlist") => get<{ as_of: string; rows: EarningsRow[] }>(`/api/watchlists/${enc(name)}/earnings`),
  portfolioFundamentals: (name: string) =>
    get<{ symbols: string[]; pending: string[]; metrics: Record<string, Record<string, number | null>> }>(
      `/api/portfolios/${enc(name)}/fundamentals`),
  earnings: (name: string) => get<{ portfolio: string; as_of: string; rows: EarningsRow[] }>(`/api/portfolios/${enc(name)}/earnings`),
  dividends: (name: string) => get<Dividends>(`/api/portfolios/${enc(name)}/dividends`),
  risk: (name: string) => get<RiskReport>(`/api/portfolios/${enc(name)}/risk`),
  exposure: (name: string) => get<Exposure>(`/api/portfolios/${enc(name)}/exposure`),
  drift: (name: string, level: string) => get<Drift>(`/api/portfolios/${enc(name)}/drift?level=${level}`),
  setTargets: (name: string, level: string, weights: Record<string, number>, dryRun: boolean) =>
    send<Drift>("PUT", `/api/portfolios/${enc(name)}/targets`, { level, weights, dry_run: dryRun }),
  simulate: (name: string, trades: SimTrade[]) => send<SimResult>("POST", `/api/portfolios/${enc(name)}/simulate`, { trades }),
  quotes: (symbols: string[]) =>
    get<{ quotes: Quote[]; errors: Record<string, string> }>(`/api/quotes?symbols=${symbols.map(enc).join(",")}`),
};
