"""Portfolio performance: daily value, time-weighted return (TWR), benchmark comparison.

Portfolios hold positions only (no cash), so each day's return treats money moving in
and out of positions as external flows:

    r_d = (V_d + Out_d) / (V_{d-1} + In_d) - 1

    In_d  = buy cost (incl. fees) + OPENING lots at that day's close
    Out_d = sell proceeds (net of fees) + dividends - standalone fees
    V_d   = sum(qty held at the close of d * close_d)

OPENING lots enter at market value, not their (old) cost, so importing a holding
bought years ago doesn't show up as a one-day gain. Chaining (1 + r_d) gives the
TWR index; deposits never count as performance.

Closes are split-adjusted (Yahoo), so quantities before a recorded SPLIT are scaled
by the split ratio to stay on the same basis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from argus.market_calendar import NY
from argus.models import TxnType
from argus.services.lots import TxnLike

TRADING_DAYS = 252


@dataclass
class DayPoint:
    d: date
    value: float
    flow_in: float
    flow_out: float
    ret: float | None  # daily TWR return; None before the first holding
    index: float  # cumulative TWR index, starts at 1.0
    bench_index: float | None


def txn_session(ts: datetime, sessions: list[date]) -> date | None:
    """The trading session a transaction settles into: its NY date, or the next session."""
    d = ts.astimezone(NY).date()
    for s in sessions:
        if s >= d:
            return s
    return None


def _split_factors(txns: list[TxnLike]) -> dict[str, list[tuple[date, float]]]:
    out: dict[str, list[tuple[date, float]]] = {}
    for t in txns:
        if t.type == TxnType.SPLIT:
            out.setdefault(t.symbol, []).append((t.ts.astimezone(NY).date(), t.qty))
    return out


def compute_series(txns: Iterable[TxnLike], sessions: list[date], closes: dict[str, dict[date, float]],
                   bench: dict[date, float] | None = None) -> list[DayPoint]:
    """Replay transactions over `sessions` (ascending trading days)."""
    txns = sorted(txns, key=lambda t: (t.ts, t.id or 0))
    if not txns or not sessions:
        return []
    splits = _split_factors(txns)

    def adj(sym: str, when: date) -> float:
        # Pre-split quantities are scaled up to match split-adjusted closes.
        f = 1.0
        for d, ratio in splits.get(sym, []):
            if d > when:
                f *= ratio
        return f

    by_day: dict[date, list[TxnLike]] = {}
    for t in txns:
        s = txn_session(t.ts, sessions)
        if s is not None:
            by_day.setdefault(s, []).append(t)

    qty: dict[str, float] = {}
    last_close: dict[str, float] = {}
    prev_value = 0.0
    index = 1.0
    bench_base = None
    points: list[DayPoint] = []
    started = False

    for d in sessions:
        for sym, series in closes.items():
            if d in series:
                last_close[sym] = series[d]
        flow_in = flow_out = 0.0
        for t in by_day.get(d, []):
            kind = TxnType(t.type)
            if kind == TxnType.BUY:
                qty[t.symbol] = qty.get(t.symbol, 0.0) + t.qty
                flow_in += t.qty * t.price + (t.fee or 0.0)
            elif kind == TxnType.OPENING:
                qty[t.symbol] = qty.get(t.symbol, 0.0) + t.qty
                px = last_close.get(t.symbol, t.price)
                flow_in += t.qty * adj(t.symbol, d) * px
            elif kind == TxnType.SELL:
                qty[t.symbol] = qty.get(t.symbol, 0.0) - t.qty
                flow_out += t.qty * t.price - (t.fee or 0.0)
            elif kind == TxnType.DIVIDEND:
                flow_out += t.amount
            elif kind == TxnType.FEE:
                flow_out -= t.amount
            elif kind == TxnType.SPLIT:
                # Share count changes, value doesn't: adj() stops scaling from this day on.
                qty[t.symbol] = qty.get(t.symbol, 0.0) * t.qty

        value = sum(q * adj(sym, d) * last_close.get(sym, 0.0) for sym, q in qty.items() if abs(q) > 1e-9)
        base = prev_value + flow_in
        ret = None
        if base > 0:
            ret = (value + flow_out) / base - 1
            index *= 1 + ret
            started = True
        if started:
            b = None
            if bench and d in bench:
                bench_base = bench_base or bench[d]
                b = bench[d] / bench_base
            points.append(DayPoint(d, value, flow_in, flow_out, ret, index, b))
        prev_value = value
    return points


def summarize(points: list[DayPoint], risk_free_annual: float = 0.0) -> dict:
    """Stats over a (possibly rebased) slice of the series."""
    if not points:
        return {}
    start, end = points[0], points[-1]
    # Returns within the slice exclude the first day's own return (the slice starts at its close).
    rets = [p.ret for p in points[1:] if p.ret is not None]
    twr = end.index / start.index - 1
    peak, mdd = start.index, 0.0
    for p in points:
        peak = max(peak, p.index)
        mdd = min(mdd, p.index / peak - 1)
    vol = None
    sharpe = None
    if len(rets) >= 2:
        mean = sum(rets) / len(rets)
        sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
        vol = sd * math.sqrt(TRADING_DAYS)
        if sd > 0:
            sharpe = (mean - risk_free_annual / TRADING_DAYS) / sd * math.sqrt(TRADING_DAYS)
    bench = None
    if start.bench_index and end.bench_index:
        bench = end.bench_index / start.bench_index - 1
    days = (end.d - start.d).days
    return {
        "start": start.d.isoformat(),
        "end": end.d.isoformat(),
        "sessions": len(points),
        "twr_pct": twr * 100,
        "benchmark_pct": bench * 100 if bench is not None else None,
        "excess_pct": (twr - bench) * 100 if bench is not None else None,
        "cagr_pct": ((1 + twr) ** (365 / days) - 1) * 100 if days >= 365 else None,
        "max_drawdown_pct": mdd * 100,
        "volatility_pct": vol * 100 if vol is not None else None,
        "sharpe": sharpe,
        "net_invested": (net := sum(p.flow_in - p.flow_out for p in points[1:])),
        # Dollar profit over the slice: what the positions gained beyond money added.
        "gain": end.value - start.value - net,
        "start_value": start.value,
        "end_value": end.value,
    }
