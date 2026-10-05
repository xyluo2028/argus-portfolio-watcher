"""Provider-neutral market data types.

Each adapter implements only what its source supports; `MarketService` chooses
the order of adapters per data type and falls back when one fails.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Protocol, runtime_checkable


class ProviderError(Exception):
    """A provider could not serve the request (network, rate limit, unknown symbol...)."""


@dataclass
class Quote:
    symbol: str
    price: float
    prev_close: float | None
    open: float | None
    high: float | None
    low: float | None
    as_of: datetime
    source: str
    delayed: bool = False
    # Pre-market or after-hours trading since the last regular close; `price` stays the regular one.
    ext_price: float | None = None
    ext_as_of: datetime | None = None
    ext_session: str | None = None  # "pre" | "post"

    @property
    def change(self) -> float | None:
        return None if self.prev_close is None else self.price - self.prev_close

    @property
    def change_pct(self) -> float | None:
        if not self.prev_close:
            return None
        return (self.price / self.prev_close - 1) * 100

    @property
    def ext_change(self) -> float | None:
        """Extended-hours move from the regular price (the last close)."""
        return None if self.ext_price is None else self.ext_price - self.price

    @property
    def ext_change_pct(self) -> float | None:
        return None if self.ext_price is None or not self.price else (self.ext_price / self.price - 1) * 100

    def without_ext(self) -> Quote:
        return replace(self, ext_price=None, ext_as_of=None, ext_session=None)

    def to_dict(self) -> dict:
        from argus.market_calendar import session_date  # base types stay import-light

        d = asdict(self)
        d["as_of"] = self.as_of.isoformat()
        d["ext_as_of"] = self.ext_as_of.isoformat() if self.ext_as_of else None
        d["ext_change"] = self.ext_change
        d["ext_change_pct"] = self.ext_change_pct
        # Trading day the price belongs to; fetch-time stamps (Yahoo) on a weekend map to Friday.
        d["session_date"] = session_date(self.as_of).isoformat()
        d["change"] = self.change
        d["change_pct"] = self.change_pct
        return d


@dataclass
class Bar:
    ts: datetime
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    v: float


@dataclass
class SymbolInfo:
    symbol: str
    name: str | None
    type: str | None
    exchange: str | None = None


@runtime_checkable
class QuoteProvider(Protocol):
    name: str

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Return quotes for the symbols it could resolve; missing keys mean unknown or failed."""
        ...


@runtime_checkable
class HistoryProvider(Protocol):
    name: str

    def get_history(self, symbol: str, start: datetime, end: datetime | None, interval: str) -> list[Bar]: ...


@runtime_checkable
class FundamentalsProvider(Protocol):
    name: str

    def get_metrics(self, symbol: str) -> dict[str, float | None]:
        """Normalized metric names (see `argus.services.market.METRIC_FIELDS`)."""
        ...
