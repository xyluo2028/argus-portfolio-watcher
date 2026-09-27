"""MCP server: Argus as tools for Claude and other agents.

Two transports share this module:
- stdio (`argus mcp`): spawned by Claude Desktop/Code; opens the same SQLite DB and
  fetches quotes on demand (cached), so it works whether or not `argus serve` runs.
- streamable HTTP at http://localhost:8787/mcp/ when mounted in `argus serve`; then
  tools read the live quote hub.

Conventions every tool follows (so agents don't have to guess):
- Values carry freshness: quotes include as_of, session_date and source.
- Writes default to dry_run=True and return a before/after preview; call again with
  dry_run=False to commit. Pass idempotency_key so a retry can't double-book a trade.
- Errors are "CODE: message (hint: ...)" with stable codes, e.g. INSUFFICIENT_SHARES.
"""

from __future__ import annotations

import functools
import inspect
import json
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from argus.app import Argus
from argus.errors import ArgusError
from argus.market_calendar import parse_ny_datetime
from argus.services.portfolio import TxnInput
from argus.symbols import normalize_symbol

INSTRUCTIONS = """Argus is the user's local portfolio monitor for US stocks and ETFs.
Start with list_portfolios, then get_portfolio for positions, weights, day and unrealized P&L.
Market data: get_quotes (batch), get_price_history (+ indicators), get_fundamentals, get_financials
(SEC filings), compare_symbols, get_performance (time-weighted return vs benchmark).
Writes (add_transaction, delete_transaction, watchlist_add/remove, create_portfolio) change the
user's records: preview with dry_run=True (the default), show the user the preview, and only then
call again with dry_run=False. Never place real brokerage orders; Argus only records trades.
Times are New York (ET). Percent fields end in _pct and are already x100."""

READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
DELETE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False)


def _round(v: Any) -> Any:
    """Trim float noise so responses stay small and readable."""
    if isinstance(v, float):
        return round(v, 4)
    if isinstance(v, dict):
        return {k: _round(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_round(x) for x in v]
    return v


def _tool(fn: Callable) -> Callable:
    """Return compact JSON text (the SDK would pretty-print, costing tokens), round floats,
    and turn ArgusError into a tool error the model can read."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs) -> str:
        try:
            return json.dumps(_round(fn(*args, **kwargs)), separators=(",", ":"), default=str)
        except ArgusError as e:
            raise ToolError(f"{e.code}: {e.message}" + (f" (hint: {e.hint})" if e.hint else "")) from e
    # Keep the parameter schema; the return is always JSON text.
    wrapper.__signature__ = inspect.signature(fn).replace(return_annotation=str)
    wrapper.__annotations__ = {**fn.__annotations__, "return": "str"}
    return wrapper


def create_mcp(argus: Argus | None = None, live_quotes: Callable[[], dict] | None = None) -> MCPServer:
    argus = argus or Argus()
    quotes_now = live_quotes or (lambda: None)
    mcp = MCPServer("argus", instructions=INSTRUCTIONS, version="0.1.0", log_level="WARNING")

    # -- read -----------------------------------------------------------------
    @mcp.tool(annotations=READ)
    @_tool
    def market_status() -> dict:
        """NYSE session now (pre | regular | post | closed), whether today is a trading/half day,
        last close and next open/close times (ISO, UTC)."""
        return argus.market_status()

    @mcp.tool(annotations=READ)
    @_tool
    def list_portfolios() -> list[dict]:
        """All portfolios with id, name and benchmark symbol."""
        return argus.portfolios.list_portfolios()

    @mcp.tool(annotations=READ)
    @_tool
    def get_portfolio(portfolio: str, include_lots: bool = False, top: int | None = None) -> dict:
        """Positions with qty, avg_cost, price, day_pnl, market_value, weight_pct, unrealized P&L,
        plus totals and market session. `top` keeps only the N largest positions (totals still
        cover everything). include_lots adds each open FIFO lot (OPENING = owned before import)."""
        out = argus.portfolio(portfolio, True, include_lots, quotes_now())
        if top:
            out["positions"] = out["positions"][:top]
        return out

    @mcp.tool(annotations=READ)
    @_tool
    def get_quotes(symbols: list[str]) -> dict:
        """Latest quotes for up to ~50 tickers in one call (price, prev_close, change_pct, as_of,
        session_date, source). Unknown tickers are listed under `errors`."""
        live = quotes_now() or {}
        out = argus.quotes(symbols)
        for q in out["quotes"]:  # prefer streamed prices when the server is running
            if q["symbol"] in live:
                q.update(live[q["symbol"]].to_dict())
        return out

    @mcp.tool(annotations=READ)
    @_tool
    def get_price_history(symbol: str, period: str = "6mo", interval: str = "1d",
                          indicators: list[str] | None = None, last: int | None = 60) -> dict:
        """OHLCV bars. period: 1d 5d 1mo 3mo 6mo 1y 2y 5y 10y max; interval: 1d, or 5m/15m/1h for
        short periods. indicators e.g. ["sma50","sma200","rsi14","macd","bb20","atr14"] are
        computed with full warm-up. `last` returns only the most recent N bars (None = all)."""
        out = argus.history(symbol, period, interval, indicators)
        if last:
            out["bars"] = out["bars"][-last:]
            for k, v in (out.get("indicators") or {}).items():
                out["indicators"][k] = ({kk: vv[-last:] for kk, vv in v.items()} if isinstance(v, dict) else v[-last:])
        return out

    @mcp.tool(annotations=READ)
    @_tool
    def get_fundamentals(symbol: str, fields: list[str] | None = None) -> dict:
        """Valuation & profitability: pe_ttm, pe_forward, peg, pb, ps_ttm, ev_ebitda, eps_ttm,
        market_cap, revenue_ttm, revenue_growth_yoy_pct, gross/operating/net_margin_pct, roe_pct,
        fcf_ttm, debt_to_equity, dividend_yield_pct, beta, high_52w, low_52w, expense_ratio_pct.
        Cached 24h; `sources` says which provider supplied each value."""
        return argus.market.get_fundamentals(normalize_symbol(symbol), fields)

    @mcp.tool(annotations=READ)
    @_tool
    def get_financials(symbol: str, period: str = "quarterly", limit: int = 8) -> dict:
        """Reported financials from SEC EDGAR (revenue, gross/operating/net income and margins,
        diluted EPS, operating cash flow, capex, free cash flow). period: quarterly | annual.
        Quarters not filed separately (usually Q4) are derived from annual minus 9-month totals.
        ETFs have none."""
        return argus.market.get_financials(normalize_symbol(symbol), period, limit)

    @mcp.tool(annotations=READ)
    @_tool
    def compare_symbols(symbols: list[str], fields: list[str] | None = None) -> dict:
        """Side-by-side price, day change and valuation metrics for 1-10 symbols."""
        return argus.compare(symbols, fields)

    @mcp.tool(annotations=READ)
    @_tool
    def get_performance(portfolio: str, range: str = "all", include_series: bool = False) -> dict:  # noqa: A002
        """Time-weighted return vs the portfolio's benchmark over 1mo | 3mo | ytd | 1y | all, with
        dollar gain, max drawdown, volatility and Sharpe (rf=0). Buys count as money in, so
        adding money isn't performance. include_series adds the daily points."""
        out = argus.performance(portfolio, range, quotes_now())
        if not include_series:
            out.pop("series", None)
        return out

    @mcp.tool(annotations=READ)
    @_tool
    def list_transactions(portfolio: str, symbol: str | None = None, include_deleted: bool = False) -> list[dict]:
        """The trade log (oldest first). `source` shows who recorded each entry: ui, cli, mcp or import."""
        return argus.portfolios.list_transactions(portfolio, symbol, include_deleted)

    @mcp.tool(annotations=READ)
    @_tool
    def get_watchlist(name: str = "Watchlist") -> dict:
        """Watchlist symbols with quote, note and key valuation metrics."""
        return argus.watchlist(name, quotes_now())

    @mcp.tool(annotations=READ)
    @_tool
    def search_symbol(query: str, limit: int = 10) -> list[dict]:
        """Find US tickers by symbol or company name."""
        return argus.market.search(query, limit)

    # -- write ----------------------------------------------------------------
    @mcp.tool(annotations=WRITE)
    @_tool
    def add_transaction(portfolio: str, type: str, symbol: str, qty: float = 0.0, price: float = 0.0,  # noqa: A002
                        fee: float = 0.0, amount: float = 0.0, date: str | None = None, note: str | None = None,
                        idempotency_key: str | None = None, dry_run: bool = True) -> dict:
        """Record a trade the user made at their broker (this never places an order).
        type: BUY | SELL | DIVIDEND (amount) | SPLIT (qty = new shares per old) | FEE (amount).
        date: YYYY-MM-DD (= that day's close) or YYYY-MM-DDTHH:MM, New York time; default now.
        Returns the position before/after. dry_run defaults to True: show the user the preview,
        then repeat with dry_run=False and the same idempotency_key to save it. Selling more than
        held fails with INSUFFICIENT_SHARES."""
        item = TxnInput(type=type, symbol=symbol, ts=parse_ny_datetime(date), qty=qty, price=price, fee=fee,
                        amount=amount, note=note, external_id=idempotency_key)
        return argus.portfolios.add_transactions(portfolio, [item], source="mcp", dry_run=dry_run)

    @mcp.tool(annotations=DELETE)
    @_tool
    def delete_transaction(txn_id: int, dry_run: bool = True) -> dict:
        """Soft-delete a transaction (kept in the audit log; hidden from positions). Refused if later
        trades depend on it. dry_run defaults to True."""
        return argus.portfolios.delete_transaction(txn_id, source="mcp", dry_run=dry_run)

    @mcp.tool(annotations=WRITE)
    @_tool
    def watchlist_add(symbols: list[str], note: str | None = None, name: str = "Watchlist") -> dict:
        """Add tickers to a watchlist (created if missing). Re-adding is a no-op; a note updates it."""
        return argus.watchlists.add(symbols, note, name, actor="mcp")

    @mcp.tool(annotations=DELETE)
    @_tool
    def watchlist_remove(symbols: list[str], name: str = "Watchlist") -> dict:
        """Remove tickers from a watchlist."""
        return argus.watchlists.remove(symbols, name, actor="mcp")

    @mcp.tool(annotations=WRITE)
    @_tool
    def create_portfolio(name: str, benchmark: str = "SPY") -> dict:
        """Create an empty portfolio with a benchmark for performance comparison."""
        return argus.portfolios.create_portfolio(name, benchmark, actor="mcp")

    # -- resources & prompts ---------------------------------------------------
    @mcp.resource("portfolio://{name}/summary", mime_type="application/json")
    def portfolio_resource(name: str) -> dict:
        """Current positions and totals for a portfolio."""
        return _round(argus.portfolio(name, True, False, quotes_now()))

    @mcp.prompt()
    def position_review(portfolio: str, symbol: str) -> str:
        """Review one holding: position, valuation, trend and recent financials."""
        return (f"Review my {symbol} position in the '{portfolio}' portfolio using Argus. Call get_portfolio "
                f"(include_lots=true) for my shares and cost, get_price_history for {symbol} over 1y with "
                "sma50, sma200 and rsi14, get_fundamentals, and get_financials (quarterly). Summarize: my P&L "
                "and weight, trend vs moving averages, valuation vs its growth, and the last 4 quarters. "
                "Be factual; note where data is missing. Don't give buy/sell instructions.")

    return mcp


def run_stdio() -> None:
    create_mcp().run("stdio")
