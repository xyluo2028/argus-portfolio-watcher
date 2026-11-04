from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.app import Argus
from argus.config import Settings
from argus.providers.base import Bar, ProviderError, Quote
from argus.services.market import MarketService

FIXTURES = Path(__file__).parent / "fixtures"


class FakeQuotes:
    """Deterministic quote provider; unknown symbols are omitted like real providers do."""

    def __init__(self, name: str, prices: dict[str, tuple[float, float]], fail: bool = False):
        self.name = name
        self.prices = prices
        self.fail = fail
        self.calls: list[list[str]] = []

    def get_quotes(self, symbols):
        self.calls.append(list(symbols))
        if self.fail:
            raise ProviderError(f"{self.name} down")
        now = datetime.now(UTC)
        return {s: Quote(s, p, pc, None, None, None, now, self.name)
                for s, (p, pc) in self.prices.items() if s in symbols}


class FakeHistory:
    name = "fake"

    def __init__(self, bars: list[Bar]):
        self.bars = bars
        self.calls = 0

    def get_history(self, symbol, start, end, interval):
        self.calls += 1
        return [b for b in self.bars if b.ts >= start]


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path, db_path=tmp_path / "test.sqlite", finnhub_api_key=None, sec_user_agent=None)


@pytest.fixture
def make_argus(settings):
    def _make(quote_providers=(), history=None, fundamentals=()):
        return Argus(settings, market_factory=lambda engine, st: MarketService(
            engine, st, list(quote_providers), history, list(fundamentals)))
    return _make


@pytest.fixture
def freeze_today(monkeypatch):
    """`freeze_today(date(2026, 10, 28))` makes `datetime.now()` in Argus and the tests return that
    day at noon New York time, the clock moving on from there, so date-dependent tests can be run
    on any calendar day. Every module that imported `datetime` gets a subclass whose now() is shifted."""
    import sys
    from datetime import date, time
    from zoneinfo import ZoneInfo

    real, frozen = datetime, []

    def _freeze(day: date):
        offset = real.combine(day, time(12), ZoneInfo("America/New_York")) - real.now(UTC)

        class Frozen(real):
            @classmethod
            def now(cls, tz=None):
                t = real.now(UTC) + offset
                return t.astimezone(tz) if tz else t.astimezone().replace(tzinfo=None)

        frozen.append(Frozen)
        for name, mod in list(sys.modules.items()):
            if name.split(".")[0] in ("argus", "tests") and getattr(mod, "datetime", None) in (real, *frozen):
                monkeypatch.setattr(mod, "datetime", Frozen)
        return day
    return _freeze
