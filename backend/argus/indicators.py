"""Technical indicators over closing prices (pandas; no third-party TA library).

Spec strings: sma20, ema50, rsi14, macd (12,26,9), bb20 (20, 2σ), atr14.
Each returns aligned lists; leading values without enough history are None.
"""

from __future__ import annotations

import re

import pandas as pd

from argus.errors import ArgusError
from argus.providers.base import Bar

_SPEC = re.compile(r"^(sma|ema|rsi|bb|atr)(\d{1,3})$|^macd$")


def _clean(s: pd.Series) -> list[float | None]:
    return [None if pd.isna(v) else round(float(v), 4) for v in s]


def sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).mean()


def ema(close: pd.Series, n: int) -> pd.Series:
    return close.ewm(span=n, adjust=False, min_periods=n).mean()


def wilder(x: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing: seeded with the simple mean of the first n values, then
    avg = (prev * (n - 1) + x) / n. (pandas' ewm seeds from the first value instead,
    which gives visibly different early readings.)"""
    vals = x.to_numpy(dtype=float)
    out = [float("nan")] * len(vals)
    start = next((i for i, v in enumerate(vals) if v == v), None)  # first non-NaN
    if start is None or len(vals) - start < n:
        return pd.Series(out, index=x.index)
    avg = float(vals[start:start + n].mean())
    out[start + n - 1] = avg
    for i in range(start + n, len(vals)):
        avg = (avg * (n - 1) + vals[i]) / n
        out[i] = avg
    return pd.Series(out, index=x.index)


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = wilder(delta.clip(lower=0), n)
    loss = wilder(-delta.clip(upper=0), n)
    out = 100 - 100 / (1 + gain / loss)
    return out.where(loss != 0, 100.0).where(gain.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, pd.Series]:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return {"macd": line, "signal": sig, "hist": line - sig}


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> dict[str, pd.Series]:
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return {"mid": mid, "upper": mid + k * sd, "lower": mid - k * sd}


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev = close.shift()
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    tr.iloc[0] = float("nan")  # no previous close for the first bar
    return wilder(tr, n)


def compute(bars: list[Bar], specs: list[str]) -> dict[str, list[float | None] | dict[str, list[float | None]]]:
    df = pd.DataFrame({"h": [b.h for b in bars], "l": [b.l for b in bars], "c": [b.c for b in bars]})
    out: dict = {}
    for raw in specs:
        spec = raw.strip().lower()
        m = _SPEC.match(spec)
        if not m:
            raise ArgusError("INVALID_ARG", f"Unknown indicator '{raw}'.",
                             hint="Use sma<N>, ema<N>, rsi<N>, bb<N>, atr<N> or macd, e.g. sma50,rsi14.")
        kind, n = (m.group(1), int(m.group(2))) if m.group(1) else ("macd", 0)
        if kind != "macd" and not 1 < n <= 400:
            raise ArgusError("INVALID_ARG", f"Indicator period out of range in '{raw}'.")
        if kind == "sma":
            out[spec] = _clean(sma(df.c, n))
        elif kind == "ema":
            out[spec] = _clean(ema(df.c, n))
        elif kind == "rsi":
            out[spec] = _clean(rsi(df.c, n))
        elif kind == "atr":
            out[spec] = _clean(atr(df.h, df.l, df.c, n))
        elif kind == "bb":
            out[spec] = {k: _clean(v) for k, v in bollinger(df.c, n).items()}
        else:
            out[spec] = {k: _clean(v) for k, v in macd(df.c).items()}
    return out
