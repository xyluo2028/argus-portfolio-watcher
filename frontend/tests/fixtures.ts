import type { Page } from "@playwright/test";

const asOf = "2026-10-30T20:00:00Z";
const portfolio = { id: 1, name: "growth", benchmark: "SPY" };
const market = {
  session: "closed", is_trading_day: false, is_half_day: false, now: "2026-11-02T00:00:00Z",
  next_open: "2026-11-02T14:30:00Z", next_close: "2026-11-02T21:00:00Z",
  last_close: asOf, last_session: "2026-10-30",
};
const quote = {
  symbol: "TEST", price: 7.38, prev_close: 7.25, open: 7.22, high: 7.45, low: 7.18,
  change: 0.13, change_pct: 1.79, as_of: asOf, session_date: "2026-10-30", source: "fixture",
  delayed: false, ext_price: null,
};
const position = {
  symbol: "TEST", name: "Example company with a long name", type: "Common Stock", sector: "Technology",
  qty: 100, avg_cost: 6, cost_basis: 600, realized_pnl: 0, first_opened: "2026-01-01", lot_count: 1,
  price: 7.38, market_value: 738, unrealized_pnl: 138, unrealized_pct: 23, day_pnl: 13,
  change_pct: 1.79, weight_pct: 100, lots: [],
};
const summary = {
  portfolio, market, as_of: asOf, positions: [position],
  totals: { market_value: 1234567.89, cost_basis: 1000000, day_pnl: 2345, day_pnl_pct: 1.79,
    unrealized_pnl: 234567.89, unrealized_pct: 23.46, realized_pnl: 15000, dividends: 200,
    dividends_accrued: 0, position_count: 1, fully_priced: true, ext_pnl: null },
};
const days = Array.from({ length: 90 }, (_, i) => new Date(Date.UTC(2026, 6, i + 1)).toISOString().slice(0, 10));
const concentration = { top1_pct: 100, top5_pct: 100, effective_positions: 1, positions: 1, hhi: 1 };
const status = { built: true, building: false, fiscal_year: 2025, companies: 5000, fields: Object.fromEntries(
  ["market_cap", "revenue_growth_pct", "net_margin_pct", "roe_pct", "debt_to_equity"].map((key) =>
    [key, { label: key.replaceAll("_", " "), unit: key.endsWith("pct") ? "%" : "x" }])) };

/** All data stays in the browser test: no live API, credentials, or user records are accessed. */
export async function mockApi(page: Page) {
  const control = { failNextHistory: false, historyDelay: new Map<string, number>() };
  await page.addInitScript(() => localStorage.setItem("argus.theme", "dark"));
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const json = (body: unknown, status = 200) => route.fulfill({ status, json: body });
    if (path === "/api/stream") return route.fulfill({ contentType: "text/event-stream", body:
      `event: update\ndata: ${JSON.stringify({ version: 1, market, stream: { state: "disabled", symbols: 0 },
        quotes: { TEST: quote }, alerts_fired: [], portfolio: summary })}\n\n` });
    if (path === "/api/screener") return json(route.request().method() === "POST" ? { status, matches: 0, rows: [] } : status);
    if (route.request().method() !== "GET") throw new Error(`Unexpected API mutation: ${path}`);
    if (path === "/api/auth/status") return json({ required: false, authenticated: true, methods: [], account: null });
    if (path === "/api/portfolios") return json([portfolio]);
    if (path === "/api/portfolios/growth") return json(summary);
    if (path.endsWith("/performance")) return json({ portfolio: "growth", benchmark: "SPY", summary: { start: days[0],
      twr_pct: 23, benchmark_pct: 10, excess_pct: 13, gain: 138, max_drawdown_pct: -5 },
      series: days.map((d, i) => ({ d, value: 600 + i, twr_pct: i / 4, bench_pct: i / 8 })) });
    if (path.startsWith("/api/history/")) {
      const period = url.searchParams.get("period")!;
      const interval = url.searchParams.get("interval")!;
      if (control.historyDelay.has(period)) await new Promise((resolve) => setTimeout(resolve, control.historyDelay.get(period)));
      if (control.failNextHistory) {
        control.failNextHistory = false;
        return json({ error: { code: "UNAVAILABLE", message: "Price history temporarily unavailable." } }, 503);
      }
      const bars = days.map((d, i) => ({ ts: interval === "1d" ? `${d}T20:00:00Z`
        : new Date(Date.UTC(2026, 9, 30, 13, 30 + i * 5)).toISOString(),
        o: 6 + Math.sin(i / 8), h: 6.3 + Math.sin(i / 8), l: 5.8 + Math.sin(i / 8), c: 6.1 + Math.sin(i / 8), v: 1000000 + i * 1000 }));
      return json({ symbol: "TEST", period, interval, bars, indicators: {
        sma20: bars.map((b) => b.c), sma50: bars.map((b) => b.c + 0.1), sma200: bars.map((b) => b.c + 0.2),
        rsi14: bars.map((_, i) => 50 + Math.sin(i / 8) * 20),
      } });
    }
    if (path.startsWith("/api/returns/")) return json({ bases: Object.fromEntries(
      ["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "5Y", "Max"].map((r) => [r, { date: days[0], close: 6 }])),
      last_close: { date: "2026-10-30", close: 7.38 } });
    if (path === "/api/quotes") return json({ quotes: [quote], errors: {} });
    if (path.startsWith("/api/fundamentals/")) return json({ symbol: "TEST", as_of: asOf,
      metrics: { pe_ttm: 18, high_52w: 9.24, low_52w: 4.75 }, sources: {} });
    if (path.startsWith("/api/fundamental-series/")) return json({ ratios: { pe_ttm: days.map((d) => [d, 18]) },
      medians: { pe_ttm: 17 }, revenue: [], labels: {}, errors: {} });
    if (path.startsWith("/api/profile/")) return json({ name: position.name, quote_type: "EQUITY", sector: "Technology",
      summary: "An example business used to check phone layouts.", suggested_peers: [], country: "US" });
    if (path.startsWith("/api/holdings/")) return json({ fund: false });
    if (path.startsWith("/api/financials/")) return json({ periods: [
      { period_end: "2026-06-30", revenue: 500000000, net_income: 20000000 },
      { period_end: "2026-03-31", revenue: 400000000, net_income: 15000000 }], units: {}, stale: false });
    if (path.startsWith("/api/research/")) return json({ fund: false, analysts: null });
    if (path.startsWith("/api/peers/")) return json({ symbol: "TEST", peers: [], custom: false, rows: [], fields: [], errors: {} });
    if (path === "/api/search") return json([{ symbol: "AAPL", name: "Apple Inc.", type: "Common Stock" }]);
    if (path === "/api/events") return json({ upcoming: [], recent: [], as_of: asOf });
    if (path === "/api/notes") return json([]);
    if (path === "/api/alerts") return json({ alerts: [], fired: [], kinds: {
      price_above: { label: "Price crosses above {t}", unit: "$" } } });
    if (path === "/api/watchlists/Watchlist") return json({ watchlist: "Watchlist", errors: {},
      items: [{ symbol: "TEST", note: "Long-term watch", metrics: {}, quote }] });
    if (path.endsWith("/transactions")) return json([]);
    if (path === "/api/compare/history") return json({ period: url.searchParams.get("period"),
      series: { TEST: days.map((d, i) => [d, 6 + i / 20]), AAPL: days.map((d, i) => [d, 150 + i]) } });
    if (path === "/api/compare") return json({ rows: [position, { ...position, symbol: "AAPL", name: "Apple Inc." }],
      pending: [], errors: {}, fields: [] });
    if (path.endsWith("/exposure")) return json({ concentration, by_type: [{ key: "Stocks", weight_pct: 100 }],
      by_sector_direct: [{ key: "Technology", weight_pct: 100 }], by_sector_lookthrough: [{ key: "Technology", weight_pct: 100 }],
      by_symbol: [{ key: "TEST", weight_pct: 100 }], funds_without_profile: [],
      top_stock_exposure: [{ symbol: "TEST", direct: 738, via_etfs: 0, via: [], total: 738, total_pct: 100 }], notes: [] });
    if (path.endsWith("/drift")) return json({ rows: [{ key: "TEST", weight_pct: 100 }], warnings: [], tolerance_pp: 5 });
    if (path.endsWith("/risk")) return json({ available: false, reason: "No risk history in test data." });
    if (path.endsWith("/dividends")) return json({ year: 2026, as_of: asOf, holdings: [],
      totals: { annual_income: 0, payers: 0, positions: 1, received: 0, projected: 0, year_total: 0 },
      by_month: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, received: 0, projected: 0 })) });
    if (path === "/api/market-context") return json({ gauges: [], periods: ["1D", "1M", "YTD"], errors: {},
      sectors: [{ symbol: "XLK", name: "Technology", returns: { "1D": 1, "1M": 5, YTD: 12 } }],
      breadth: { equal_vs_cap: {}, small_vs_large: {}, sectors: 11, sectors_above_50d: 8, sectors_above_200d: 7 } });
    return json({ error: { code: "FIXTURE_MISSING", message: `No test data for ${path}` } }, 404);
  });
  return control;
}
