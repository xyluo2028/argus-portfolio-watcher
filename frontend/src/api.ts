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
  alerts_fired?: FiredAlert[];
  portfolio?: Summary;
}

export class ApiError extends Error {
  constructor(public code: string, message: string, public hint?: string) {
    super(message);
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  const body = await r.json().catch(() => ({}));
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
  transactions: (name: string, includeDeleted = false, symbol?: string) => {
    const qs = new URLSearchParams();
    if (includeDeleted) qs.set("include_deleted", "true");
    if (symbol) qs.set("symbol", symbol);
    const q = qs.toString();
    return get<Txn[]>(`/api/portfolios/${enc(name)}/transactions${q ? `?${q}` : ""}`);
  },
  importInvesting: (body: { filename: string; content: string; portfolio?: string; opening_through?: string; dry_run: boolean }) =>
    send<ImportReport>("POST", "/api/import/investing", body),
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
  peers: (symbol: string) => get<Peers>(`/api/peers/${enc(symbol)}`),
  setPeers: (symbol: string, peers: string[] | null) => send<Peers>("PUT", `/api/peers/${enc(symbol)}`, { peers }),
  compare: (symbols: string[]) => get<CompareResult>(`/api/compare?symbols=${symbols.map(enc).join(",")}`),
  search: (q: string, limit = 8) => get<SearchHit[]>(`/api/search?q=${enc(q)}&limit=${limit}`),
  events: (daysAhead = 14, daysBack = 7) =>
    get<{ as_of: string; upcoming: CalEvent[]; recent: CalEvent[] }>(`/api/events?days_ahead=${daysAhead}&days_back=${daysBack}`),
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
  exposure: (name: string) => get<Exposure>(`/api/portfolios/${enc(name)}/exposure`),
  drift: (name: string, level: string) => get<Drift>(`/api/portfolios/${enc(name)}/drift?level=${level}`),
  setTargets: (name: string, level: string, weights: Record<string, number>, dryRun: boolean) =>
    send<Drift>("PUT", `/api/portfolios/${enc(name)}/targets`, { level, weights, dry_run: dryRun }),
  simulate: (name: string, trades: SimTrade[]) => send<SimResult>("POST", `/api/portfolios/${enc(name)}/simulate`, { trades }),
  quotes: (symbols: string[]) =>
    get<{ quotes: Quote[]; errors: Record<string, string> }>(`/api/quotes?symbols=${symbols.map(enc).join(",")}`),
};
