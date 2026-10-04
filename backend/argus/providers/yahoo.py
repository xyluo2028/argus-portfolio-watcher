"""yfinance adapter: price history, fallback quotes, and metrics Finnhub's free tier lacks.

yfinance scrapes Yahoo's unofficial API; every call is wrapped so a breakage
surfaces as ProviderError and callers fall back or serve cache.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from argus.providers.base import Bar, ProviderError, Quote
from argus.symbols import to_yahoo

logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def _yf():
    import yfinance  # imported lazily: it is slow to import and not needed for most commands

    return yfinance


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _px(v) -> float | None:
    """Yahoo prices arrive as float32 noise (225.07000732...); 4 decimals covers sub-dollar stocks."""
    f = _num(v)
    return None if f is None else round(f, 4)


def _pct(v) -> float | None:
    f = _num(v)
    return None if f is None else f * 100


# funds_data keys -> the sector names Yahoo uses for individual stocks.
YAHOO_FUND_SECTORS = {
    "realestate": "Real Estate", "consumer_cyclical": "Consumer Cyclical", "basic_materials": "Basic Materials",
    "consumer_defensive": "Consumer Defensive", "technology": "Technology",
    "communication_services": "Communication Services", "financial_services": "Financial Services",
    "healthcare": "Healthcare", "industrials": "Industrials", "energy": "Energy", "utilities": "Utilities",
}


class YahooProvider:
    name = "yahoo"

    def get_quotes(self, symbols: list[str], native: bool = False) -> dict[str, Quote]:
        """`native` takes Yahoo's own symbols as given (e.g. foreign listings like 2330.TW)."""
        yf = _yf()
        out: dict[str, Quote] = {}
        now = datetime.now(UTC)
        for s in symbols:
            try:
                fi = yf.Ticker(s if native else to_yahoo(s)).fast_info
                price = _px(fi.get("lastPrice"))
                if not price:
                    continue
                out[s] = Quote(
                    symbol=s,
                    price=price,
                    # Not "previousClose": that one is derived from adjusted history and drifts
                    # after dividends (e.g. GOOGL 341.38 vs the real 342.36 close).
                    prev_close=_px(fi.get("regularMarketPreviousClose")),
                    open=_px(fi.get("open")),
                    high=_px(fi.get("dayHigh")),
                    low=_px(fi.get("dayLow")),
                    as_of=now,
                    source=self.name,
                    delayed=False,
                )
            except Exception:  # noqa: BLE001 - yfinance raises many types; one bad symbol must not stop the batch
                continue
        return out

    def get_history(self, symbol: str, start: datetime, end: datetime | None, interval: str = "1d") -> list[Bar]:
        yf = _yf()
        try:
            # Split-adjusted, not dividend-adjusted: charts show prices as traded.
            df = yf.Ticker(to_yahoo(symbol)).history(start=start, end=end, interval=interval, auto_adjust=False)
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"yahoo history {symbol}: {e}") from e
        if df is None or df.empty:
            return []
        bars = []
        for ts, row in df.iterrows():
            bars.append(Bar(ts.to_pydatetime().astimezone(UTC), float(row["Open"]), float(row["High"]),
                            float(row["Low"]), float(row["Close"]), float(row.get("Volume") or 0)))
        return bars

    def get_info(self, symbol: str) -> dict:
        try:
            return _yf().Ticker(to_yahoo(symbol)).info or {}
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"yahoo info {symbol}: {e}") from e

    def get_calendar(self, symbol: str) -> dict:
        """Upcoming dates: 'Earnings Date' (list), 'Ex-Dividend Date', 'Dividend Date'."""
        try:
            cal = _yf().Ticker(to_yahoo(symbol)).calendar
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"yahoo calendar {symbol}: {e}") from e
        return cal if isinstance(cal, dict) else {}

    def get_fund_profile(self, symbol: str) -> dict:
        """ETF sector weights (Yahoo sector names, fractions summing to ~1), top holdings (Yahoo
        symbols), asset classes and bond ratings (fractions). Empty for anything that isn't a fund."""
        try:
            fd = _yf().Ticker(to_yahoo(symbol)).funds_data
            sectors = fd.sector_weightings or {}
            th = fd.top_holdings
        except Exception:  # noqa: BLE001 - yfinance raises for non-funds; treat as "no profile"
            return {}
        holdings = []
        if th is not None and not th.empty:
            for sym, row in th.iterrows():
                holdings.append({"symbol": str(sym), "name": row.get("Name"), "weight": float(row.get("Holding Percent") or 0)})
        out = {"sectors": {YAHOO_FUND_SECTORS.get(k, k): float(v) for k, v in sectors.items() if v},
               "top_holdings": holdings}
        for key in ("asset_classes", "bond_ratings"):
            try:
                out[key] = {k: float(v) for k, v in (getattr(fd, key) or {}).items() if _num(v)}
            except Exception:  # noqa: BLE001 - optional extras
                out[key] = {}
        return out

    def similar_etfs(self, category: str, limit: int = 20) -> list[str]:
        """US-listed ETFs in a Morningstar category (e.g. "Large Growth"), largest first."""
        yf = _yf()
        q = yf.ETFQuery
        try:
            r = yf.screen(q("and", [q("eq", ["categoryname", category]), q("eq", ["region", "us"])]),
                          size=limit, sortField="fundnetassets", sortAsc=False)
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"yahoo screen {category}: {e}") from e
        return [x["symbol"] for x in (r or {}).get("quotes", []) if x.get("symbol")]

    def get_metrics(self, symbol: str) -> dict[str, float | None]:
        return metrics_from_info(self.get_info(symbol))


def metrics_from_info(i: dict) -> dict[str, float | None]:
    """Map Yahoo `info` to normalized fields. Yahoo gives margins/growth as fractions."""
    d2e = _num(i.get("debtToEquity"))
    return {
        "pe_ttm": _num(i.get("trailingPE")),
        "pe_forward": _num(i.get("forwardPE")),
        "pb": _num(i.get("priceToBook")),
        "ps_ttm": _num(i.get("priceToSalesTrailing12Months")),
        "ev_ebitda": _num(i.get("enterpriseToEbitda")),
        "peg": _num(i.get("trailingPegRatio")),
        "eps_ttm": _num(i.get("trailingEps")),
        "eps_forward": _num(i.get("forwardEps")),
        "beta": _num(i.get("beta")),
        # Yahoo reports dividendYield already in percent (e.g. 0.44 means 0.44%).
        "dividend_yield_pct": _num(i.get("dividendYield")),
        "revenue_ttm": _num(i.get("totalRevenue")),
        "revenue_growth_yoy_pct": _pct(i.get("revenueGrowth")),
        "gross_margin_pct": _pct(i.get("grossMargins")),
        "operating_margin_pct": _pct(i.get("operatingMargins")),
        "net_margin_pct": _pct(i.get("profitMargins")),
        "roe_pct": _pct(i.get("returnOnEquity")),
        "fcf_ttm": _num(i.get("freeCashflow")),
        # Yahoo gives debt/equity x100.
        "debt_to_equity": d2e / 100 if d2e is not None else None,
        "market_cap": _num(i.get("marketCap")),
        "high_52w": _num(i.get("fiftyTwoWeekHigh")),
        "low_52w": _num(i.get("fiftyTwoWeekLow")),
        "expense_ratio_pct": _num(i.get("netExpenseRatio")),
        # Funds: assets under management; Yahoo gives ytdReturn in percent, multi-year averages as fractions.
        "net_assets": _num(i.get("totalAssets")),
        "ytd_return_pct": _num(i.get("ytdReturn")),
        "return_3y_pct": _pct(i.get("threeYearAverageReturn")),
        "return_5y_pct": _pct(i.get("fiveYearAverageReturn")),
    }
