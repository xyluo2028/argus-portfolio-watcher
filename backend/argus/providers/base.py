"""Provider-neutral market data types.

Each adapter implements only what its source supports; `MarketService` chooses
the order of adapters per data type and falls back when one fails.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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

    @property
    def change(self) -> float | None:
        return None if self.prev_close is None else self.price - self.prev_close

    @property
    def change_pct(self) -> float | None:
        if not self.prev_close:
            return None
        return (self.price / self.prev_close - 1) * 100

    def to_dict(self) -> dict:
        d = asdict(self)
        d["as_of"] = self.as_of.isoformat()
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
