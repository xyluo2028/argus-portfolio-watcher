"""Market data: provider fallback chains plus SQLite caching.

Freshness rules:
- Quotes: served from cache if fetched within `quote_max_age_s`, or if the market
  is closed and the cached quote already reflects the last session's close.
- Daily bars: cached permanently; only bars after the last cached one are fetched.
- Fundamentals: cached for `fundamentals_max_age_s` (default 24h).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Engine, select
from sqlalchemy.dialects.sqlite import insert

from argus.config import Settings
from argus.db import session_scope
from argus.errors import ArgusError
from argus.market_calendar import NY, market_status
from argus.models import Fundamental, Instrument, PriceBar, QuoteCache
from argus.providers.base import Bar, ProviderError, Quote

METRIC_FIELDS = (
    "pe_ttm", "pe_forward", "peg", "pb", "ps_ttm", "ev_ebitda", "eps_ttm", "eps_forward", "market_cap",
    "revenue_ttm", "revenue_growth_yoy_pct", "gross_margin_pct", "operating_margin_pct", "net_margin_pct",
    "roe_pct", "fcf_ttm", "debt_to_equity", "dividend_yield_pct", "beta", "high_52w", "low_52w",
    "expense_ratio_pct",
)

# Fields denominated in the share's price currency. Finnhub reports foreign issuers' home listing
# (VIST in MXN, CNQ in CAD) while Yahoo reports the US listing in USD, so these prefer Yahoo.
# Ratios (P/E, P/B, margins...) are unit-free and keep the provider order.
PRICE_CURRENCY_FIELDS = {"high_52w", "low_52w", "market_cap", "eps_ttm", "eps_forward", "revenue_ttm", "fcf_ttm"}
FUNDAMENTALS_VERSION = 2  # bump to invalidate cached rows when merge rules change

PERIODS = {"1d": 1, "5d": 7, "1mo": 31, "3mo": 92, "6mo": 183, "1y": 366, "2y": 731, "5y": 1827, "10y": 3653}


class MarketService:
    def __init__(self, engine: Engine, settings: Settings, quote_providers: list, history_provider,
                 fundamentals_providers: list, sec=None, directory=None, profile_provider=None):
        self.engine = engine
        self.settings = settings
        self.quote_providers = quote_providers
        self.history_provider = history_provider
        self.fundamentals_providers = fundamentals_providers
        self.sec = sec
        self.directory = directory  # FinnhubProvider (symbol_directory) or None
        self.profile_provider = profile_provider  # YahooProvider (get_info) or None

    # -- quotes ---------------------------------------------------------------
    def get_quotes(self, symbols: list[str], max_age_s: int | None = None) -> tuple[dict[str, Quote], dict[str, str]]:
        """Return (quotes, errors). Errors map symbol -> reason for symbols no provider resolved."""
        symbols = list(dict.fromkeys(symbols))
        max_age = timedelta(seconds=self.settings.quote_max_age_s if max_age_s is None else max_age_s)
        now = datetime.now(UTC)
        status = market_status(now)
        last_close = datetime.fromisoformat(status["last_close"])

        quotes: dict[str, Quote] = {}
        with session_scope(self.engine) as s:
            for row in s.scalars(select(QuoteCache).where(QuoteCache.symbol.in_(symbols))):
                fresh = now - row.fetched_at <= max_age
                settled = status["session"] == "closed" and row.as_of >= last_close - timedelta(minutes=1)
                if fresh or settled:
                    quotes[row.symbol] = Quote(row.symbol, row.price, row.prev_close, row.open, row.high, row.low,
                                               row.as_of, row.source, row.delayed)

        missing = [s for s in symbols if s not in quotes]
        errors: dict[str, str] = {}
        for provider in self.quote_providers:
            if not missing:
                break
            try:
                got = provider.get_quotes(missing)
            except ProviderError as e:
                for sym in missing:
                    errors[sym] = str(e)
                continue
            quotes.update(got)
            self.store_quotes(got.values())
            missing = [s for s in missing if s not in got]
        for sym in missing:
            errors.setdefault(sym, "unknown symbol or no provider returned a quote")
        for sym in quotes:
            errors.pop(sym, None)
        return quotes, errors

    def store_quotes(self, quotes) -> None:
        rows = [dict(symbol=q.symbol, price=q.price, prev_close=q.prev_close, open=q.open, high=q.high, low=q.low,
                     as_of=q.as_of, source=q.source, delayed=q.delayed, fetched_at=datetime.now(UTC))
                for q in quotes]
        if not rows:
            return
        with session_scope(self.engine) as s:
            stmt = insert(QuoteCache).values(rows)
            s.execute(stmt.on_conflict_do_update(index_elements=["symbol"], set_={
                c: stmt.excluded[c] for c in rows[0] if c != "symbol"}))

    # -- history --------------------------------------------------------------
    def get_history(self, symbol: str, period: str = "1y", interval: str = "1d") -> list[Bar]:
        if period not in PERIODS and period != "max":
            raise ArgusError("INVALID_ARG", f"Unknown period '{period}'.", hint=f"Use one of {', '.join(PERIODS)}, max")
        now = datetime.now(UTC)
        start = datetime(1970, 1, 2, tzinfo=UTC) if period == "max" else now - timedelta(days=PERIODS[period])
        if interval != "1d":
            return self._fetch_history(symbol, start, None, interval)

        with session_scope(self.engine) as s:
            cached = list(s.scalars(select(PriceBar).where(PriceBar.symbol == symbol, PriceBar.interval == "1d")
                                    .order_by(PriceBar.ts)))
        first = cached[0].ts if cached else None
        last = cached[-1].ts if cached else None
        last_session = datetime.fromisoformat(market_status(now)["last_close"]) - timedelta(hours=12)
        fetch_from = None
        if not cached or first > start + timedelta(days=5):
            fetch_from = start
        elif last < last_session:
            fetch_from = last - timedelta(days=3)  # re-fetch a few bars to pick up late corrections
        if fetch_from is not None:
            self._store_bars(symbol, "1d", self._fetch_history(symbol, fetch_from, None, "1d"))
        with session_scope(self.engine) as s:
            rows = s.scalars(select(PriceBar).where(PriceBar.symbol == symbol, PriceBar.interval == "1d",
                                                    PriceBar.ts >= start).order_by(PriceBar.ts))
            return [Bar(r.ts, r.o, r.h, r.l, r.c, r.v) for r in rows]

    def daily_closes(self, symbol: str, start: date) -> dict[date, float]:
        """Close per New York trading date from `start` on (cached daily bars)."""
        days = (datetime.now(UTC).date() - start).days + 7
        period = next((p for p, n in PERIODS.items() if n >= days), "max")
        return {b.ts.astimezone(NY).date(): b.c for b in self.get_history(symbol, period, "1d")
                if b.ts.astimezone(NY).date() >= start}

    def _fetch_history(self, symbol, start, end, interval) -> list[Bar]:
        try:
            return self.history_provider.get_history(symbol, start, end, interval)
        except ProviderError as e:
            raise ArgusError("PROVIDER_ERROR", str(e), hint="Yahoo may be rate limiting; retry shortly.") from e

    def _store_bars(self, symbol: str, interval: str, bars: list[Bar]) -> None:
        if not bars:
            return
        rows = [dict(symbol=symbol, interval=interval, ts=b.ts, o=b.o, h=b.h, l=b.l, c=b.c, v=b.v) for b in bars]
        with session_scope(self.engine) as s:
            for i in range(0, len(rows), 500):
                stmt = insert(PriceBar).values(rows[i:i + 500])
                s.execute(stmt.on_conflict_do_update(index_elements=["symbol", "interval", "ts"], set_={
                    c: stmt.excluded[c] for c in ("o", "h", "l", "c", "v")}))

    # -- fundamentals ---------------------------------------------------------
    def get_fundamentals(self, symbol: str, fields: list[str] | None = None, refresh: bool = False) -> dict:
        unknown = [f for f in fields or [] if f not in METRIC_FIELDS]
        if unknown:
            raise ArgusError("INVALID_ARG", f"Unknown fields: {', '.join(unknown)}", hint=f"Valid: {', '.join(METRIC_FIELDS)}")
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            row = s.get(Fundamental, symbol)
            cached = (row.metrics, row.sources, row.as_of) if row else None
        fresh = cached and cached[1].get("_version") == FUNDAMENTALS_VERSION and \
            now - cached[2] < timedelta(seconds=self.settings.fundamentals_max_age_s)
        if fresh and not refresh:
            metrics, sources, as_of = cached
        else:
            by_provider: dict[str, dict] = {}
            errors = []
            for provider in self.fundamentals_providers:
                try:
                    by_provider[provider.name] = provider.get_metrics(symbol)
                except ProviderError as e:
                    errors.append(str(e))
            metrics, sources = {}, {}
            names = [p.name for p in self.fundamentals_providers if p.name in by_provider]
            for field in METRIC_FIELDS:
                order = sorted(names, key=lambda n: n != "yahoo") if field in PRICE_CURRENCY_FIELDS else names
                for n in order:
                    v = by_provider[n].get(field)
                    if v is not None:
                        metrics[field], sources[field] = v, n
                        break
            if not metrics:
                if cached:
                    metrics, sources, as_of = cached  # stale beats nothing
                else:
                    raise ArgusError("PROVIDER_ERROR", f"No fundamentals for {symbol}.", hint="; ".join(errors) or None)
            else:
                as_of = now
                sources["_version"] = FUNDAMENTALS_VERSION
                with session_scope(self.engine) as s:
                    s.merge(Fundamental(symbol=symbol, as_of=as_of, metrics=metrics, sources=sources))
        wanted = fields or list(METRIC_FIELDS)
        return {
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "metrics": {f: metrics.get(f) for f in wanted},
            "sources": {f: sources[f] for f in wanted if f in sources},
        }

    def get_financials(self, symbol: str, period: str = "quarterly", limit: int = 8) -> dict:
        if self.sec is None:
            raise ArgusError("NOT_CONFIGURED", "SEC EDGAR provider is not configured.")
        if not self.settings.sec_user_agent:
            raise ArgusError("NOT_CONFIGURED", "Reported financials need SEC_USER_AGENT in .env.",
                             hint='SEC asks for a contact, e.g. SEC_USER_AGENT="argus you@example.com"; then restart.')
        try:
            return {"symbol": symbol, "source": "sec", **self.sec.get_financials(symbol, period, limit)}
        except ProviderError as e:
            raise ArgusError("PROVIDER_ERROR", str(e)) from e

    # -- symbols --------------------------------------------------------------
    def search(self, query: str, limit: int = 10, prefer: set[str] | frozenset[str] = frozenset()) -> list[dict]:
        """Rank: exact ticker, then `prefer` (e.g. held/watched), listed before OTC, ticker prefix before a
        company-name word (closest word length first), stocks before funds, preferred shares last."""
        if self.directory is None:
            raise ArgusError("NOT_CONFIGURED", "Symbol search needs FINNHUB_API_KEY.")
        q = query.strip().upper()
        if not q:
            return []
        try:
            entries = self.directory.symbol_directory().values()
        except ProviderError as e:
            raise ArgusError("PROVIDER_ERROR", f"Symbol directory unavailable: {e}") from e
        scored = []
        for e in entries:
            name = (e.name or "").upper()
            word_len = 0
            if e.symbol.startswith(q):
                tier = 0
            elif words := [w for w in name.split() if w.startswith(q)]:
                tier, word_len = 1, min(map(len, words))
            elif len(q) >= 4 and q in name:
                tier = 2
            else:
                continue
            stock_first = 0 if tier == 0 or e.type in ("Common Stock", "ADR") else 1 if e.type == "ETP" else 2
            scored.append(((e.symbol != q, e.symbol not in prefer, ".PR" in e.symbol, e.exchange == "OOTC",
                            tier, word_len, stock_first, len(e.symbol.split(".")[0]), e.symbol), e))
        scored.sort(key=lambda x: x[0])
        return [{"symbol": e.symbol, "name": e.name, "type": e.type} for _, e in scored[:limit]]

    def refresh_instruments(self, symbols: list[str]) -> None:
        """Fill instrument type and sector/industry from the symbol directory and Yahoo profile."""
        directory = {}
        if self.directory is not None:
            try:
                directory = self.directory.symbol_directory()
            except ProviderError:
                directory = {}
        with session_scope(self.engine) as s:
            for sym in symbols:
                inst = s.get(Instrument, sym) or Instrument(symbol=sym)
                info = directory.get(sym)
                if info:
                    inst.type = inst.type or info.type
                    inst.name = inst.name or info.name
                if self.profile_provider is not None and not inst.sector:
                    try:
                        prof = self.profile_provider.get_info(sym)
                    except ProviderError:
                        prof = {}
                    inst.sector = prof.get("sector") or ("ETF" if prof.get("quoteType") == "ETF" else None)
                    inst.industry = prof.get("industry") or prof.get("category")
                s.merge(inst)
