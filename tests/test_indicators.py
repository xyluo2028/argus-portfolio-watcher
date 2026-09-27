from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from argus.errors import ArgusError
from argus.indicators import compute, rsi
from argus.providers.base import Bar


def bars(closes):
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    return [Bar(t0 + timedelta(days=i), c, c + 1, c - 1, c, 100) for i, c in enumerate(closes)]


def test_sma_and_warmup_nones():
    out = compute(bars([1, 2, 3, 4, 5]), ["sma3"])
    assert out["sma3"] == [None, None, 2.0, 3.0, 4.0]


def test_rsi_extremes_and_textbook_value():
    assert rsi(pd.Series(range(1, 40)), 14).iloc[-1] == 100.0  # only gains
    # Wilder's worked example (first RSI value ~70.53 on this 15-close series).
    closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    assert rsi(pd.Series(closes), 14).iloc[-1] == pytest.approx(70.53, abs=0.1)


def test_macd_and_bollinger_shapes():
    out = compute(bars([float(i % 7) + 50 for i in range(60)]), ["macd", "bb20"])
    assert set(out["macd"]) == {"macd", "signal", "hist"} and len(out["macd"]["hist"]) == 60
    bb = out["bb20"]
    i = 30
    assert bb["lower"][i] < bb["mid"][i] < bb["upper"][i]


def test_bad_spec_is_rejected():
    with pytest.raises(ArgusError):
        compute(bars([1, 2, 3]), ["foo7"])


def test_history_indicators_use_warmup_before_period(make_argus):
    from tests.conftest import FakeHistory
    now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    hist = FakeHistory([Bar(now - timedelta(days=i), 1, 2, 0.5, float(400 - i), 100) for i in range(400, -1, -1)])
    a = make_argus(history=hist)
    out = a.history("AAA", "1mo", "1d", ["sma200"])
    assert len(out["indicators"]["sma200"]) == len(out["bars"])
    assert out["indicators"]["sma200"][0] is not None  # warmed up from earlier cached bars
