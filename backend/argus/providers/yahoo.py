"""yfinance adapter: price history, fallback quotes, and metrics Finnhub's free tier lacks.

yfinance scrapes Yahoo's unofficial API; every call is wrapped so a breakage
surfaces as ProviderError and callers fall back or serve cache.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta

from argus.providers.base import Bar, ProviderError, Quote
from argus.symbols import to_yahoo

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
log = logging.getLogger("argus.yahoo")


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


QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
QUOTE_BATCH = 100  # symbols per request on Yahoo's quote endpoint
INFO_TTL_S = 6 * 3600


class YahooProvider:
    name = "yahoo"
    # MarketService puts this provider first for large lookups: one request covers 100 symbols.
    batch_quotes = True

    def __init__(self):
        # `info` feeds fundamentals, company profiles and sector lookups; one fetch serves all three.
        self._info: dict[str, tuple[float, dict]] = {}
        self._info_lock = threading.Lock()

    @staticmethod
    def _quote_rows(symbols: list[str], fields: str) -> list[dict]:
        """Yahoo's batch quote endpoint (the one its own site uses), 100 symbols per request."""
        from yfinance.data import YfData

        rows: list[dict] = []
        for i in range(0, len(symbols), QUOTE_BATCH):
            try:
                r = YfData().get(QUOTE_URL, params={"symbols": ",".join(symbols[i:i + QUOTE_BATCH]), "fields": fields})
                rows += r.json()["quoteResponse"]["result"]
            except Exception as e:  # noqa: BLE001 - network, auth crumb, or a changed payload
                raise ProviderError(f"yahoo quote batch: {e}") from e
        return rows

    def get_quotes(self, symbols: list[str], native: bool = False) -> dict[str, Quote]:
        """`native` takes Yahoo's own symbols as given (e.g. foreign listings like 2330.TW).
        One batch request per 100 symbols; falls back to per-symbol lookups if the batch fails."""
        names = {(s if native else to_yahoo(s)): s for s in symbols}
        try:
            rows = self._quote_rows(list(names), "regularMarketPrice,regularMarketPreviousClose,regularMarketOpen,"
                                                 "regularMarketDayHigh,regularMarketDayLow,regularMarketTime")
        except ProviderError as e:
            log.info("%s; falling back to per-symbol quotes", e)
            return self._quotes_one_by_one(symbols, native)
        out: dict[str, Quote] = {}
        now = datetime.now(UTC)
        for q in rows:
            sym, price = names.get(q.get("symbol")), _px(q.get("regularMarketPrice"))
            if not sym or not price:
                continue
            t = q.get("regularMarketTime")
            out[sym] = Quote(symbol=sym, price=price, prev_close=_px(q.get("regularMarketPreviousClose")),
                             open=_px(q.get("regularMarketOpen")), high=_px(q.get("regularMarketDayHigh")),
                             low=_px(q.get("regularMarketDayLow")),
                             as_of=datetime.fromtimestamp(t, UTC) if isinstance(t, (int, float)) else now,
                             source=self.name, delayed=False)
        return out

    def market_caps(self, symbols: list[str]) -> dict[str, dict]:
        """Price, market cap, exchange and quote type for Yahoo symbols as given, 100 per request.
        Batches run 4 at a time; a failed batch just leaves its symbols out."""
        fields = "regularMarketPrice,marketCap,exchange,fullExchangeName,quoteType,currency"
        chunks = [symbols[i:i + QUOTE_BATCH] for i in range(0, len(symbols), QUOTE_BATCH)]

        def one(chunk):
            try:
                return self._quote_rows(chunk, fields)
            except ProviderError as e:
                log.info("%s", e)
                return []
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = [r for batch in pool.map(one, chunks) for r in batch]
        return {r["symbol"]: {"price": _px(r.get("regularMarketPrice")), "market_cap": _num(r.get("marketCap")),
                              "exchange": r.get("fullExchangeName") or r.get("exchange"), "exchange_code": r.get("exchange"),
                              "quote_type": r.get("quoteType"), "currency": r.get("currency")}
                for r in rows if r.get("symbol")}

    def _quotes_one_by_one(self, symbols: list[str], native: bool) -> dict[str, Quote]:
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

    def get_extended(self, symbols: list[str]) -> dict[str, tuple[str, float, datetime]]:
        """Latest pre-market or after-hours trade per symbol: {symbol: (session, price, time)}.
        One batch request per 100 symbols (Yahoo's quote endpoint)."""
        out: dict[str, tuple[str, float, datetime]] = {}
        names = {to_yahoo(s): s for s in symbols}
        rows = self._quote_rows(list(names), "preMarketPrice,preMarketTime,postMarketPrice,postMarketTime")
        for q in rows:
            sym = names.get(q.get("symbol"))
            seen = [(t, session, _px(q.get(f"{session}MarketPrice")))
                    for session in ("pre", "post") if (t := q.get(f"{session}MarketTime"))]
            seen = [x for x in seen if x[2]]
            if sym and seen:
                t, session, price = max(seen)
                out[sym] = (session, price, datetime.fromtimestamp(t, UTC))
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

    def get_dividends(self, symbol: str, years: int = 3) -> list[tuple[str, float]]:
        """Cash dividends per share by ex-date (ISO date), oldest first, for the last `years`."""
        try:
            s = _yf().Ticker(to_yahoo(symbol)).dividends
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"yahoo dividends {symbol}: {e}") from e
        if s is None or s.empty:
            return []
        cutoff = datetime.now(UTC).date() - timedelta(days=366 * years)
        return [(ts.date().isoformat(), float(v)) for ts, v in s.items() if ts.date() >= cutoff and v > 0]

    def _memo(self, key: str, fn, ttl: float = INFO_TTL_S):
        now = time.monotonic()
        with self._info_lock:
            hit = self._info.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
        value = fn()
        with self._info_lock:
            self._info[key] = (now, value)
        return value

    def get_analyst(self, symbol: str) -> dict:
        """Recommendation counts by month, EPS estimate trend and revisions, top institutions."""
        def fetch():
            t = _yf().Ticker(to_yahoo(symbol))
            out: dict = {}
            for name, get in (("recommendations", lambda: t.recommendations), ("eps_trend", lambda: t.eps_trend),
                              ("eps_revisions", lambda: t.eps_revisions), ("institutions", lambda: t.institutional_holders)):
                try:
                    df = get()
                except Exception as e:  # noqa: BLE001 - each piece is optional
                    log.info("yahoo %s %s: %s", name, symbol, e)
                    df = None
                if df is None or getattr(df, "empty", True):
                    out[name] = None
                elif name in ("recommendations", "institutions"):
                    out[name] = [{k: (v.isoformat()[:10] if hasattr(v, "isoformat") else _num(v) if not isinstance(v, str) else v)
                                  for k, v in row.items()} for row in df.head(10).to_dict("records")]
                else:  # rows = horizons (0q, +1q, 0y, +1y), columns = measures
                    out[name] = {str(h): {str(k): (_num(v) if not isinstance(v, str) else v) for k, v in vals.items()}
                                 for h, vals in df.to_dict("index").items()}
            return out
        return self._memo(f"analyst:{symbol}", fetch)

    def get_statements(self, symbol: str) -> dict:
        """Annual statements, newest first: {"years": [...], "balance"|"income"|"cashflow": {row: [values]}}."""
        def fetch():
            t = _yf().Ticker(to_yahoo(symbol))
            out: dict = {"years": []}
            for name, get in (("balance", lambda: t.balance_sheet), ("income", lambda: t.income_stmt),
                              ("cashflow", lambda: t.cashflow)):
                try:
                    df = get()
                except Exception as e:  # noqa: BLE001
                    raise ProviderError(f"yahoo statements {symbol}: {e}") from e
                if df is None or df.empty:
                    out[name] = {}
                    continue
                cols = sorted(df.columns, reverse=True)
                out["years"] = out["years"] or [c.date().isoformat() for c in cols]
                out[name] = {str(row): [_num(df.at[row, c]) for c in cols] for row in df.index}
            return out
        return self._memo(f"statements:{symbol}", fetch, ttl=24 * 3600)

    def get_info(self, symbol: str) -> dict:
        """Yahoo's `info` (~0.4 s per call), kept in memory for a few hours."""
        now = time.monotonic()
        with self._info_lock:
            hit = self._info.get(symbol)
        if hit and now - hit[0] < INFO_TTL_S:
            return hit[1]
        try:
            info = _yf().Ticker(to_yahoo(symbol)).info or {}
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"yahoo info {symbol}: {e}") from e
        with self._info_lock:
            self._info[symbol] = (now, info)
        return info

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
        "sma50": _num(i.get("fiftyDayAverage")),
        "sma200": _num(i.get("twoHundredDayAverage")),
        "payout_ratio_pct": _pct(i.get("payoutRatio")),
        "expense_ratio_pct": _num(i.get("netExpenseRatio")),
        # Funds: assets under management; Yahoo gives ytdReturn in percent, multi-year averages as fractions.
        "net_assets": _num(i.get("totalAssets")),
        "ytd_return_pct": _num(i.get("ytdReturn")),
        "return_3y_pct": _pct(i.get("threeYearAverageReturn")),
        "return_5y_pct": _pct(i.get("fiveYearAverageReturn")),
    }
