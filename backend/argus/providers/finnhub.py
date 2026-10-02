"""Finnhub REST adapter (free tier: 60 calls/min, real-time US quotes, basic financials)."""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from argus.providers.base import ProviderError, Quote, SymbolInfo

BASE_URL = "https://finnhub.io/api/v1"
DIRECTORY_MAX_AGE_S = 7 * 24 * 3600

# Finnhub metric name(s) -> normalized field. First non-null candidate wins.
# Percent-valued fields stay in percent; market cap arrives in millions.
_METRIC_MAP: dict[str, tuple[str, ...]] = {
    "pe_ttm": ("peTTM", "peBasicExclExtraTTM", "peExclExtraTTM"),
    "pb": ("pb", "pbQuarterly", "pbAnnual"),
    "ps_ttm": ("psTTM", "psAnnual"),
    "ev_ebitda": ("evEbitdaTTM", "currentEv/ebitdaTTM"),
    "peg": ("pegTTM",),
    "eps_ttm": ("epsTTM", "epsExclExtraItemsTTM", "epsBasicExclExtraItemsTTM"),
    "beta": ("beta",),
    "dividend_yield_pct": ("currentDividendYieldTTM", "dividendYieldIndicatedAnnual"),
    "revenue_growth_yoy_pct": ("revenueGrowthTTMYoy",),
    "gross_margin_pct": ("grossMarginTTM",),
    "operating_margin_pct": ("operatingMarginTTM",),
    "net_margin_pct": ("netProfitMarginTTM",),
    "roe_pct": ("roeTTM",),
    "debt_to_equity": ("totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"),
    "high_52w": ("52WeekHigh",),
    "low_52w": ("52WeekLow",),
}


class _RateLimiter:
    """Token bucket under Finnhub's 60/min limit, spaced to stay below the 30/s burst cap.

    A full bucket lets a ~50-symbol refresh finish in about two seconds.
    """

    def __init__(self, per_minute: int = 55, per_second: int = 20):
        self.capacity = float(per_minute)
        self.tokens = float(per_minute)
        self.refill_per_s = per_minute / 60.0
        self.min_gap = 1.0 / per_second
        self._last = time.monotonic()
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.refill_per_s)
            self._last = now
            delay = max(0.0, self._last_call + self.min_gap - now)
            if self.tokens < 1:
                delay = max(delay, (1 - self.tokens) / self.refill_per_s)
            if delay:
                time.sleep(delay)
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self._last) * self.refill_per_s)
                self._last = now
            self.tokens -= 1
            self._last_call = now


class FinnhubProvider:
    name = "finnhub"

    def __init__(self, api_key: str, cache_dir: Path | None = None, client: httpx.Client | None = None,
                 per_minute: int = 55):
        self._key = api_key
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=10.0)
        self._directory: tuple[float, dict[str, SymbolInfo]] | None = None
        self._cache_dir = cache_dir
        self._limiter = _RateLimiter(per_minute)

    def _get(self, path: str, timeout: float | None = None, **params) -> dict | list:
        for attempt in range(3):
            self._limiter.wait()
            try:
                r = self._client.get(path, params=params, headers={"X-Finnhub-Token": self._key},
                                     follow_redirects=True, **({"timeout": timeout} if timeout else {}))
            except httpx.HTTPError as e:
                raise ProviderError(f"finnhub {path}: {e}") from e
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            if r.status_code in (401, 403):
                raise ProviderError(f"finnhub {path}: HTTP {r.status_code}. Check FINNHUB_API_KEY, or this "
                                    "endpoint needs a paid plan.")
            if r.status_code != 200:
                raise ProviderError(f"finnhub {path}: HTTP {r.status_code}")
            return r.json()
        raise ProviderError(f"finnhub {path}: rate limited")

    # -- quotes -------------------------------------------------------------
    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        for s in symbols:
            d = self._get("/quote", symbol=s)
            if not isinstance(d, dict) or not d.get("c"):
                continue  # c == 0 means Finnhub doesn't know the symbol
            out[s] = Quote(
                symbol=s,
                price=float(d["c"]),
                prev_close=_num(d.get("pc")),
                open=_num(d.get("o")),
                high=_num(d.get("h")),
                low=_num(d.get("l")),
                as_of=datetime.fromtimestamp(d.get("t") or time.time(), UTC),
                source=self.name,
                delayed=False,
            )
        return out

    # -- fundamentals -------------------------------------------------------
    def get_metrics(self, symbol: str) -> dict[str, float | None]:
        d = self._get("/stock/metric", symbol=symbol, metric="all")
        raw = (d or {}).get("metric") or {}
        out: dict[str, float | None] = {}
        for field, candidates in _METRIC_MAP.items():
            out[field] = next((_num(raw[c]) for c in candidates if _num(raw.get(c)) is not None), None)
        cap = _num(raw.get("marketCapitalization"))
        out["market_cap"] = cap * 1e6 if cap is not None else None
        return out

    def get_profile(self, symbol: str) -> dict:
        d = self._get("/stock/profile2", symbol=symbol)
        return d if isinstance(d, dict) else {}

    def get_peers(self, symbol: str) -> list[str]:
        """Same-sub-industry companies (Finnhub's grouping); may include the symbol itself."""
        d = self._get("/stock/peers", symbol=symbol)
        return [x for x in d if isinstance(x, str)] if isinstance(d, list) else []

    # -- events & news --------------------------------------------------------
    def earnings_calendar(self, symbol: str, start: date, end: date) -> list[dict]:
        """Scheduled/reported earnings: date, hour (bmo/amc/dmh), EPS and revenue estimate/actual."""
        d = self._get("/calendar/earnings", symbol=symbol, **{"from": start.isoformat(), "to": end.isoformat()})
        return list((d or {}).get("earningsCalendar") or [])

    def earnings_surprises(self, symbol: str) -> list[dict]:
        """Last ~4 reported quarters: actual vs estimate EPS and surprise %."""
        d = self._get("/stock/earnings", symbol=symbol)
        return d if isinstance(d, list) else []

    def company_news(self, symbol: str, start: date, end: date) -> list[dict]:
        d = self._get("/company-news", symbol=symbol, **{"from": start.isoformat(), "to": end.isoformat()})
        return d if isinstance(d, list) else []

    # -- symbol directory ---------------------------------------------------
    def symbol_directory(self) -> dict[str, SymbolInfo]:
        """All US symbols (one call, cached on disk for a week and in memory)."""
        if self._directory and time.time() - self._directory[0] < DIRECTORY_MAX_AGE_S:
            return self._directory[1]
        cache = self._cache_dir / "finnhub_us_symbols.json" if self._cache_dir else None
        rows, fetched_at = None, time.time()
        if cache and cache.exists() and time.time() - cache.stat().st_mtime < DIRECTORY_MAX_AGE_S:
            rows, fetched_at = json.loads(cache.read_text()), cache.stat().st_mtime
        if rows is None:
            # Finnhub answers with a redirect to a multi-MB file download.
            rows = self._get("/stock/symbol", timeout=60.0, exchange="US")
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(rows))
        directory = {
            r["symbol"]: SymbolInfo(r["symbol"], r.get("description"), r.get("type"), r.get("mic"))
            for r in rows
            if r.get("symbol")
        }
        self._directory = (fetched_at, directory)
        return directory


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # drop NaN
