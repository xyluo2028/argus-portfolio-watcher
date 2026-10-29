"""Market data: provider fallback chains plus SQLite caching.

Freshness rules:
- Quotes: served from cache if fetched within `quote_max_age_s`, or if the market
  is closed and the cached quote already reflects the last session's close.
- Daily bars: cached permanently; only bars after the last cached one are fetched.
- Fundamentals: cached for `fundamentals_max_age_s` (default 24h).
"""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.sqlite import insert

from argus.config import Settings
from argus.db import session_scope, upsert
from argus.errors import ArgusError
from argus.market_calendar import NY, market_status
from argus.models import ExtQuote, Fundamental, Instrument, PriceBar, QuoteCache, RefreshLog
from argus.providers.base import Bar, ProviderError, Quote
from argus.providers.sec_edgar import freshness, ttm_figures, ttm_free_cash_flow

METRIC_FIELDS = (
    "pe_ttm", "pe_forward", "peg", "peg_ttm", "pb", "ps_ttm", "ev_ebitda", "eps_ttm", "eps_forward", "market_cap",
    "revenue_ttm", "revenue_growth_yoy_pct", "gross_margin_pct", "operating_margin_pct", "net_margin_pct",
    "roe_pct", "fcf_ttm", "debt_to_equity", "dividend_yield_pct", "beta", "high_52w", "low_52w",
    "expense_ratio_pct", "net_assets", "ytd_return_pct", "return_3y_pct", "return_5y_pct",
    "revenue_growth_q_yoy_pct", "revenue_growth_3y_pct", "revenue_growth_5y_pct", "eps_growth_yoy_pct",
    "eps_growth_q_yoy_pct", "eps_growth_3y_pct", "eps_growth_5y_pct", "roa_pct", "roi_pct",
    "payout_ratio_pct", "dividend_growth_5y_pct", "return_1w_pct", "return_3m_pct", "return_6m_pct",
    "return_ytd_price_pct", "return_1y_pct", "rel_sp500_1y_pct", "sma50", "sma200", "roic_pct", "fcf_margin_pct",
    "ocf_margin_pct",
)

# Fields denominated in the share's price currency. Finnhub reports foreign issuers' home listing
# (VIST in MXN, CNQ in CAD) while Yahoo reports the US listing in USD, so these prefer Yahoo.
# Ratios (P/E, P/B, margins...) are unit-free and keep the provider order.
PRICE_CURRENCY_FIELDS = {"high_52w", "low_52w", "market_cap", "eps_ttm", "eps_forward", "revenue_ttm", "fcf_ttm",
                         "sma50", "sma200"}
# Pre/post-market prices are re-fetched this often during those sessions, and while closed
# (overnight, weekends) only to catch the last after-hours prints.
EXT_MAX_AGE = {"pre": 60, "post": 60, "closed": 30 * 60}
BATCH_FIRST_MIN = 5  # quote lookups at least this big go to a batch provider first
# Trailing figures SEC's quarters supply when they're at least as recent as the providers', so the
# valuation card agrees with the quarterly statements (Yahoo's revenue and Finnhub's quarterly growth can
# lag a 10-Q by weeks; Finnhub's margins too). fcf_ttm and fcf_margin_pct come from SEC whenever it has them.
SEC_WINDOW_FIELDS = ("revenue_ttm", "eps_ttm", "revenue_growth_q_yoy_pct", "gross_margin_pct",
                     "operating_margin_pct", "net_margin_pct", "ocf_margin_pct")
SEC_PERIOD_SLACK_DAYS = 7  # 52/53-week fiscal quarters end on slightly different dates
FUNDAMENTALS_VERSION = 10 # bump to invalidate cached rows when merge rules change

log = logging.getLogger("argus.market")

PERIODS = {"1d": 1, "5d": 7, "1mo": 31, "3mo": 92, "6mo": 183, "1y": 366, "2y": 731, "5y": 1827, "10y": 3653}



def sec_coverage(meta: dict | None) -> dict | None:
    """The quarters SEC-based fundamentals cover: the latest SEC quarter with its age and `stale` flag
    (computed now, not when cached), the four quarter ends in the SEC FCF TTM (newest first), and those
    behind SEC's revenue, EPS, growth and margin figures (`ttm_quarters`; null when the providers' were newer)."""
    if not meta:
        return None
    quarters = meta.get("fcf_ttm_quarters")
    return freshness(meta.get("latest_period")) | {
        "fcf_ttm_quarters": quarters, "fcf_ttm_through": quarters[0] if quarters else None,
        "ttm_quarters": meta.get("ttm_quarters")}


def with_fcf_margin(metrics: dict, sources: dict) -> tuple[dict, dict]:
    """FCF margin from a single source: SEC's own (FCF ÷ revenue over its quarters) when it has one,
    else the provider's FCF over that same provider's revenue. Never one source's FCF over another's
    revenue (Yahoo FCF ÷ SEC revenue when SEC lacks capex): that stays blank."""
    if sources.get("fcf_margin_pct") == "sec" and metrics.get("fcf_margin_pct") is not None:
        return metrics, sources
    metrics, sources = dict(metrics), dict(sources)
    metrics.pop("fcf_margin_pct", None)
    sources.pop("fcf_margin_pct", None)
    fcf, rev, src = metrics.get("fcf_ttm"), metrics.get("revenue_ttm"), sources.get("fcf_ttm")
    if fcf is not None and rev and src and src == sources.get("revenue_ttm"):
        metrics["fcf_margin_pct"], sources["fcf_margin_pct"] = fcf / rev * 100, src
    return metrics, sources


def provider_ahead_of_sec(sec_latest: str | None, provider_periods: list[str]) -> bool:
    """Whether a provider's trailing figures run through a newer quarter than SEC's: an earnings release
    is out but its 10-Q isn't in SEC's XBRL yet. Without a provider period, SEC counts as behind only
    once it's stale (a newer report overdue)."""
    if sec_latest is None:
        return True
    if not provider_periods:
        return freshness(sec_latest)["stale"]
    slack = timedelta(days=SEC_PERIOD_SLACK_DAYS)
    return max(date.fromisoformat(p) for p in provider_periods) > date.fromisoformat(sec_latest) + slack


def _aware(dt: datetime) -> datetime:
    """Aggregates (min/max) bypass the UTC column type and come back naive."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

class MarketService:
    def __init__(self, engine: Engine, settings: Settings, quote_providers: list, history_provider,
                 fundamentals_providers: list, sec=None, directory=None, profile_provider=None, figi=None):
        self.engine = engine
        self.settings = settings
        self.quote_providers = quote_providers
        self.history_provider = history_provider
        self.fundamentals_providers = fundamentals_providers
        self.sec = sec
        self.directory = directory  # FinnhubProvider (symbol_directory) or None
        self.profile_provider = profile_provider  # YahooProvider (get_info) or None
        self.figi = figi  # OpenFigiProvider (ISIN/CUSIP -> ticker) or None

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
        providers = self.quote_providers
        if len(missing) >= BATCH_FIRST_MIN:
            # Many symbols: a batch provider answers in one request and spares Finnhub's 60 calls/minute
            # for streaming, metrics and events.
            providers = sorted(providers, key=lambda p: not getattr(p, "batch_quotes", False))
        for provider in providers:
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
        return self.attach_extended(quotes, status), errors

    def attach_extended(self, quotes: dict[str, Quote], status: dict | None = None) -> dict[str, Quote]:
        """Add pre-market / after-hours prices traded since the last regular close (none during the
        regular session). Cached; refreshed from Yahoo in one batch when stale. Best effort."""
        status = status or market_status()
        if status["session"] == "regular" or not quotes:
            return {s: q.without_ext() if q.ext_price is not None else q for s, q in quotes.items()}
        now = datetime.now(UTC)
        since = datetime.fromisoformat(status["last_close"])
        max_age = timedelta(seconds=EXT_MAX_AGE[status["session"]])
        with session_scope(self.engine) as s:
            rows = {r.symbol: (r.session, r.price, r.as_of, r.fetched_at)
                    for r in s.scalars(select(ExtQuote).where(ExtQuote.symbol.in_(list(quotes))))}
        stale = [sym for sym in quotes if sym not in rows or now - rows[sym][3] > max_age]
        fetch = getattr(self.profile_provider, "get_extended", None)
        if stale and fetch:
            try:
                got = fetch(stale)
            except ProviderError as e:  # keep serving what's cached
                log.warning("extended-hours quotes: %s", e)
            else:
                self.store_extended({sym: got.get(sym) for sym in stale}, now)
                for sym in stale:
                    if sym in got:
                        rows[sym] = (*got[sym], now)
        out = {}
        for sym, q in quotes.items():
            ext = rows.get(sym)
            if ext and ext[2] > since and (q.ext_as_of is None or ext[2] > q.ext_as_of):
                q = replace(q, ext_session=ext[0], ext_price=ext[1], ext_as_of=ext[2])
            elif q.ext_as_of is not None and q.ext_as_of <= since:
                q = q.without_ext()
            out[sym] = q
        return out

    def store_extended(self, ext: dict[str, tuple[str, float, datetime] | Quote | None], now: datetime | None = None) -> None:
        """Cache extended-hours prices; None records that a symbol had none (so it isn't re-asked)."""
        now = now or datetime.now(UTC)
        rows = []
        for sym, e in ext.items():
            if isinstance(e, Quote):
                e = (e.ext_session, e.ext_price, e.ext_as_of) if e.ext_price is not None else None
            # "none" rows keep the fetch time but an as_of that never counts as recent.
            rows.append(dict(symbol=sym, session=e[0] if e else "none", price=e[1] if e else 0.0,
                             as_of=e[2] if e else datetime(1970, 1, 1, tzinfo=UTC), fetched_at=now))
        if rows:
            with session_scope(self.engine) as s:
                stmt = insert(ExtQuote).values(rows)
                s.execute(stmt.on_conflict_do_update(index_elements=["symbol"], set_={
                    c: stmt.excluded[c] for c in rows[0] if c != "symbol"}))

    def cached_quotes(self, symbols: list[str], max_age_s: int) -> dict[str, Quote]:
        """Quotes already in the cache and younger than `max_age_s`; never calls a provider."""
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            return {r.symbol: Quote(r.symbol, r.price, r.prev_close, r.open, r.high, r.low, r.as_of, r.source, r.delayed)
                    for r in s.scalars(select(QuoteCache).where(QuoteCache.symbol.in_(symbols)))
                    if (now - r.fetched_at).total_seconds() <= max_age_s}

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
        if period not in PERIODS and period not in ("max", "ytd"):
            raise ArgusError("INVALID_ARG", f"Unknown period '{period}'.", hint=f"Use one of {', '.join(PERIODS)}, ytd, max")
        now = datetime.now(UTC)
        if period == "max":
            start = datetime(1970, 1, 2, tzinfo=UTC)
        elif period == "ytd":
            start = datetime(now.astimezone(NY).year, 1, 1, tzinfo=NY).astimezone(UTC)
        else:
            start = now - timedelta(days=PERIODS[period])
        if interval != "1d":
            return self._fetch_history(symbol, start, None, interval)
        self._ensure_daily_bars([symbol], start)
        with session_scope(self.engine) as s:
            rows = s.execute(select(PriceBar.ts, PriceBar.o, PriceBar.h, PriceBar.l, PriceBar.c, PriceBar.v).where(
                PriceBar.symbol == symbol, PriceBar.interval == "1d", PriceBar.ts >= start).order_by(PriceBar.ts))
            return [Bar(*r) for r in rows]

    def daily_closes(self, symbol: str, start: date) -> dict[date, float]:
        """Close per New York trading date from `start` on (cached daily bars)."""
        return self.daily_closes_many([symbol], start).get(symbol, {})

    def daily_closes_many(self, symbols: list[str], start: date) -> dict[str, dict[date, float]]:
        """Closes for many symbols at once: missing history downloads in parallel, then one query
        reads everything. (SQLite reads stay on this thread: Python's sqlite3 hands the GIL back and
        forth per row, so threaded reads of big results run many times slower than sequential ones.)"""
        start_dt = datetime.combine(start - timedelta(days=7), datetime.min.time(), UTC)
        self._ensure_daily_bars(symbols, start_dt)
        out: dict[str, dict[date, float]] = {s: {} for s in symbols}
        with session_scope(self.engine) as s:
            for sym, ts, c in s.execute(select(PriceBar.symbol, PriceBar.ts, PriceBar.c).where(
                    PriceBar.symbol.in_(symbols), PriceBar.interval == "1d", PriceBar.ts >= start_dt)
                    .order_by(PriceBar.symbol, PriceBar.ts)):
                d = ts.astimezone(NY).date()
                if d >= start:
                    out[sym][d] = c
        return out

    def _ensure_daily_bars(self, symbols: list[str], start: datetime) -> None:
        """Download whatever daily history the cache lacks from `start` to the last close."""
        now = datetime.now(UTC)
        last_session = datetime.fromisoformat(market_status(now)["last_close"]) - timedelta(hours=12)
        with session_scope(self.engine) as s:
            cov = {sym: (lo, hi) for sym, lo, hi in s.execute(
                select(PriceBar.symbol, func.min(PriceBar.ts), func.max(PriceBar.ts))
                .where(PriceBar.symbol.in_(symbols), PriceBar.interval == "1d").group_by(PriceBar.symbol))}
            # "Yahoo has nothing before X": recent listings would otherwise re-download on every call.
            listed = {r.key.split(":", 1)[1]: r.at for r in s.scalars(select(RefreshLog).where(
                RefreshLog.key.in_([f"bars-first:{x}" for x in symbols])))}
        todo: dict[str, datetime] = {}
        for sym in symbols:
            first, last = cov.get(sym, (None, None))
            first, last = (_aware(first), _aware(last)) if first else (None, None)
            earliest = _aware(listed[sym]) if sym in listed else None
            if first is None:
                todo[sym] = start
            elif first > start + timedelta(days=5) and not (earliest and first <= earliest + timedelta(days=1)):
                todo[sym] = start
            elif last < last_session:
                todo[sym] = last - timedelta(days=3)  # re-fetch a few bars to pick up late corrections
        if not todo:
            return
        if len(todo) == 1:
            fetched = {sym: self._fetch_history(sym, frm, None, "1d") for sym, frm in todo.items()}
        else:
            with ThreadPoolExecutor(max_workers=8) as pool:  # network only; storing happens below
                fetched = dict(zip(todo, pool.map(lambda kv: self._fetch_history(kv[0], kv[1], None, "1d"),
                                                  todo.items())))
        for sym, bars in fetched.items():
            self._store_bars(sym, "1d", bars)
            if bars and todo[sym] == start and bars[0].ts > start + timedelta(days=5):
                with session_scope(self.engine) as s:
                    upsert(s, RefreshLog, key=f"bars-first:{sym}", at=bars[0].ts)

    def _fetch_history(self, symbol, start, end, interval) -> list[Bar]:
        if self.history_provider is None:
            raise ArgusError("NOT_CONFIGURED", "No price history provider.")
        try:
            return self.history_provider.get_history(symbol, start, end, interval)
        except ProviderError as e:
            raise ArgusError("PROVIDER_ERROR", str(e), hint="Yahoo may be rate limiting; retry shortly.") from e

    def _store_bars(self, symbol: str, interval: str, bars: list[Bar]) -> None:
        # A bar without a real close can't be stored (the column is NOT NULL, and SQLite turns NaN into
        # NULL) and would fail the whole batch, so it's dropped; the next fetch can bring it back.
        ok = lambda v: v is not None and math.isfinite(v)  # noqa: E731
        bars = [b for b in bars if ok(b.c)]
        if not bars:
            return
        rows = [dict(symbol=symbol, interval=interval, ts=b.ts, o=b.o if ok(b.o) else b.c, h=b.h if ok(b.h) else b.c,
                     l=b.l if ok(b.l) else b.c, c=b.c, v=b.v if ok(b.v) else 0.0) for b in bars]
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
        cached = self.cached_fundamentals([symbol]).get(symbol)
        if cached and cached["fresh"] and not refresh:
            metrics, sources, as_of = cached["metrics"], cached["sources"], cached["as_of"]
        else:
            fetched, errors = self._fetch_fundamentals(symbol)
            if fetched:
                metrics, sources, as_of = self._store_fundamentals(symbol, *fetched, errors, cached)
            elif cached:
                metrics, sources, as_of = cached["metrics"], cached["sources"], cached["as_of"]  # stale beats nothing
            else:
                raise ArgusError("PROVIDER_ERROR", f"No fundamentals for {symbol}.", hint="; ".join(errors.values()) or None)
        wanted = fields or list(METRIC_FIELDS)
        return {
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "metrics": {f: metrics.get(f) for f in wanted},
            "sources": {f: sources[f] for f in wanted if f in sources},
            "sec": sec_coverage(sources.get("_sec")),
        }

    def cached_fundamentals(self, symbols: list[str]) -> dict[str, dict]:
        """Whatever the cache holds for these symbols, in one query; `fresh` says if it's current."""
        now = datetime.now(UTC)
        out: dict[str, dict] = {}
        with session_scope(self.engine) as s:
            for row in s.scalars(select(Fundamental).where(Fundamental.symbol.in_(symbols))):
                fresh = row.sources.get("_version") == FUNDAMENTALS_VERSION and \
                    now - row.as_of < timedelta(seconds=self.settings.fundamentals_max_age_s)
                out[row.symbol] = {"metrics": row.metrics, "sources": row.sources, "as_of": row.as_of, "fresh": fresh}
        return out

    def refresh_fundamentals(self, symbols: list[str], workers: int = 6) -> dict[str, str]:
        """Fetch and store fundamentals for many symbols: network calls in parallel (Finnhub's own
        rate limiter paces them), writes on this thread. Returns {symbol: error} for failures."""
        if not symbols:
            return {}
        with ThreadPoolExecutor(max_workers=min(workers, len(symbols))) as pool:
            results = dict(zip(symbols, pool.map(self._fetch_fundamentals, symbols)))
        cached = self.cached_fundamentals(symbols)
        failed = {}
        for sym, (fetched, errors) in results.items():
            if fetched:
                self._store_fundamentals(sym, *fetched, errors, cached.get(sym))
            else:
                failed[sym] = "; ".join(errors.values()) or "no data"
        return failed

    def fetch_fundamentals(self, symbol: str) -> tuple[tuple[dict, dict] | None, dict[str, str]]:
        """The network half of a refresh, safe on a worker thread; hand the result to
        save_fundamentals on the calling thread."""
        return self._fetch_fundamentals(symbol)

    def save_fundamentals(self, symbol: str, result: tuple[tuple[dict, dict] | None, dict[str, str]]) -> dict | None:
        """Store what fetch_fundamentals got; returns the cached entry (stale if the fetch got nothing)."""
        fetched, errors = result
        cached = self.cached_fundamentals([symbol]).get(symbol)
        if not fetched:
            return cached
        metrics, sources, as_of = self._store_fundamentals(symbol, *fetched, errors, cached)
        return {"metrics": metrics, "sources": sources, "as_of": as_of, "fresh": True}

    def _sec_metrics(self, symbol: str) -> dict:
        """Figures Argus computes from SEC filings, which beat the providers' versions: Yahoo's
        freeCashflow is levered FCF (after interest), a fraction of MSFT's reported OCF - capex."""
        if self.sec is None or not self.settings.sec_user_agent:
            return {}
        try:
            fin = self.sec.get_financials(symbol, "quarterly", 8)  # 5 for the quarter's growth
        except ProviderError as e:
            if "not found in EDGAR" in str(e) or "no XBRL" in str(e):
                return {}  # ETFs, funds and foreign filers: the providers' figures stand
            raise
        fcf = ttm_free_cash_flow(fin)
        ttm = ttm_figures(fin)
        # Which quarters the SEC figures cover, kept beside the sources (see sec_coverage).
        last4 = [p["period_end"] for p in fin["periods"][:4]]
        meta = {"latest_period": fin["periods"][0]["period_end"] if fin.get("periods") else None,
                "fcf_ttm_quarters": last4 if fcf else None,
                "ttm_quarters": last4 if any(f in ttm for f in SEC_WINDOW_FIELDS) else None}
        return {"_sec": meta} | ({"fcf_ttm": fcf[0]} if fcf else {}) | ttm

    def _fetch_fundamentals(self, symbol: str) -> tuple[tuple[dict, dict] | None, dict[str, str]]:
        """Ask every fundamentals provider and SEC at once (network only) and merge: SEC-derived
        figures first, then first non-null wins, except price-currency fields, where Yahoo goes
        first. None if nobody had anything."""
        def ask(source):
            name, get = source
            try:
                return name, get(symbol), None
            except ProviderError as e:
                return name, None, str(e)
        askers = [("sec", self._sec_metrics), *((p.name, p.get_metrics) for p in self.fundamentals_providers)]
        with ThreadPoolExecutor(max_workers=len(askers)) as pool:
            answers = list(pool.map(ask, askers))
        by_provider = {name: m for name, m, _ in answers if m is not None}
        errors = {name: e for name, _, e in answers if e}  # provider -> error
        sec = by_provider.get("sec")
        if sec and sec.get("_sec"):
            periods = [m["_period_end"] for n, m in by_provider.items() if n != "sec" and m.get("_period_end")]
            if provider_ahead_of_sec(sec["_sec"]["latest_period"], periods):
                # One window per figure family: the providers' newer quarter, not SEC's older one.
                by_provider["sec"] = {k: v for k, v in sec.items() if k not in SEC_WINDOW_FIELDS} | {
                    "_sec": sec["_sec"] | {"ttm_quarters": None}}
        names = [p.name for p in self.fundamentals_providers if p.name in by_provider]
        metrics, sources = {}, {}
        for field in METRIC_FIELDS:
            order = sorted(names, key=lambda n: n != "yahoo") if field in PRICE_CURRENCY_FIELDS else names
            order = ["sec", *order] if "sec" in by_provider else order
            for n in order:
                v = by_provider[n].get(field)
                if v is not None:
                    metrics[field], sources[field] = v, n
                    break
        if metrics and by_provider.get("sec", {}).get("_sec"):
            sources["_sec"] = by_provider["sec"]["_sec"]
        return ((metrics, sources) if metrics else None), errors

    def _store_fundamentals(self, symbol: str, metrics: dict, sources: dict, errors: dict[str, str] | None = None,
                            previous: dict | None = None) -> tuple[dict, dict, datetime]:
        """Store a fresh merge. Fields from a provider that failed this time keep their last values
        (a Finnhub rate-limit hiccup shouldn't blank growth and momentum for a day). SEC's figures also
        beat the fallback a provider supplied this time."""
        if errors and previous:
            metrics, sources = dict(metrics), dict(sources)
            for field, src in previous["sources"].items():
                if field == "_sec":  # SEC's coverage goes with its kept figures
                    if "sec" in errors:
                        sources.setdefault(field, src)
                    continue
                if src in errors and (field not in metrics or src == "sec") and previous["metrics"].get(field) is not None:
                    metrics[field], sources[field] = previous["metrics"][field], src
        metrics, sources = with_fcf_margin(metrics, sources)
        as_of = datetime.now(UTC)
        sources = sources | {"_version": FUNDAMENTALS_VERSION}
        with session_scope(self.engine) as s:
            upsert(s, Fundamental, symbol=symbol, as_of=as_of, metrics=metrics, sources=sources)
        return metrics, sources, as_of

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
            known = {i.symbol: i for i in s.scalars(select(Instrument).where(Instrument.symbol.in_(symbols)))}
        rows = []
        for sym in symbols:
            inst = known.get(sym) or Instrument(symbol=sym)
            row = dict(symbol=sym, type=inst.type, name=inst.name, sector=inst.sector, industry=inst.industry)
            if info := directory.get(sym):
                row["type"], row["name"] = inst.type or info.type, inst.name or info.name
            if self.profile_provider is not None and not inst.sector:
                try:
                    prof = self.profile_provider.get_info(sym)
                except ProviderError:
                    prof = {}
                row["sector"] = prof.get("sector") or ("ETF" if prof.get("quoteType") == "ETF" else None)
                row["industry"] = prof.get("industry") or prof.get("category")
            rows.append(row)
        # Upserted in a fresh transaction (portfolio loads call this concurrently), after the fetches.
        with session_scope(self.engine) as s:
            for row in rows:
                upsert(s, Instrument, **row, updated_at=datetime.now(UTC))
