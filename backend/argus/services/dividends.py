"""Dividend analysis: forward income and yield per holding, and this calendar year's dividends
(estimated received so far + projected for the rest of the year), all by ex-date and before tax.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta
from statistics import mean, median, pstdev

from argus.market_calendar import NY
from argus.models import TxnType

FREQ_NAMES = {12: "monthly", 4: "quarterly", 2: "semiannual", 1: "annual"}
LOOKBACK_DAYS = 400  # a payer with nothing in this window is treated as not paying
LUMPY_CV = 0.25  # payments this dispersed (stdev / mean) over a year aren't a rate to extrapolate
MATCH_DAYS = 120  # a DIVIDEND transaction records the latest ex-date this far back (pay dates trail ex-dates)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    last_day = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def frequency(ex_dates: list[date]) -> int:
    """Payments per year from the typical gap between recent ex-dates."""
    recent = ex_dates[-7:]
    if len(recent) < 2:
        return 1
    gap = median((b - a).days for a, b in zip(recent, recent[1:]))
    return 12 if gap <= 45 else 4 if gap <= 120 else 2 if gap <= 240 else 1


def lumpy(amounts: list[float]) -> bool:
    """Payments that swing up and down a lot (TIPS ETFs pay out inflation accruals), so one payment
    times the frequency says little. A one-way move (a raise or a cut) is a new rate, not lumpiness."""
    if len(amounts) < 4 or not (m := mean(amounts)) > 0:
        return False
    steps = [b - a for a, b in zip(amounts, amounts[1:])]
    one_way = all(x >= 0 for x in steps) or all(x <= 0 for x in steps)
    return not one_way and pstdev(amounts) / m > LUMPY_CV


def analyze_holding(history: list[tuple[str, float]], qty: float, qty_at: Callable[[date], float],
                    today: date) -> dict:
    """`history`: (ex-date ISO, cash per share), any order. `qty_at(d)`: shares held going into day d."""
    pays = sorted((date.fromisoformat(d), a) for d, a in history)
    recent = [(d, a) for d, a in pays if d > today - timedelta(days=LOOKBACK_DAYS)]
    if not recent:
        return {"pays": False, "frequency": None, "rate": 0.0, "trailing_12m": 0.0,
                "received": [], "projected": [], "last_ex_date": pays[-1][0].isoformat() if pays else None}

    freq = frequency([d for d, _ in recent])
    period = timedelta(days=round(365 / freq))
    last_d, last_amt = recent[-1]
    year = [a for d, a in recent if d > today - timedelta(days=365)]
    trailing = sum(year)
    stale = today - last_d > period * 2 + timedelta(days=30)  # missed two payments: don't extrapolate
    uneven = lumpy(year)
    rate = trailing if stale or uneven else last_amt * freq
    per_payment = trailing / freq if uneven else last_amt  # projected at the year's average if lumpy

    year_start, year_end = date(today.year, 1, 1), date(today.year, 12, 31)
    received = [{"ex_date": d.isoformat(), "per_share": a, "shares": q, "amount": q * a}
                for d, a in pays if year_start <= d <= today and (q := qty_at(d)) > 0]
    projected = []
    if not stale:  # with no shares (a watchlist) this still gives the expected dates, at $0
        # Same day of the month as the last ex-date, every 12/freq months (payers keep their rhythm).
        step, k = 12 // freq, 1
        while (nxt := add_months(last_d, step * k)) <= year_end:
            if nxt > today:
                projected.append({"ex_date": nxt.isoformat(), "per_share": per_payment, "shares": qty,
                                  "amount": qty * per_payment, "estimated_date": True})
            k += 1
    return {"pays": True, "frequency": FREQ_NAMES[freq], "rate": rate, "trailing_12m": trailing,
            "last_ex_date": last_d.isoformat(), "last_amount": last_amt, "irregular": stale,
            "received": received, "projected": projected}


def analyze(rows: list[dict], histories: dict[str, list[tuple[str, float]]],
            qty_at: Callable[[str, date], float], today: date) -> dict:
    """`rows`: portfolio summary positions (symbol, name, qty, avg_cost, cost_basis, price, market_value)."""
    holdings = []
    months = [{"month": m, "received": 0.0, "projected": 0.0} for m in range(1, 13)]
    tot = {"annual_income": 0.0, "received": 0.0, "projected": 0.0}
    for r in rows:
        sym = r["symbol"]
        h = analyze_holding(histories.get(sym, []), r["qty"], lambda d, s=sym: qty_at(s, d), today)
        price, avg_cost = r.get("price"), r.get("avg_cost")
        income = h["rate"] * r["qty"]
        received = sum(x["amount"] for x in h["received"])
        projected = sum(x["amount"] for x in h["projected"])
        for x in h["received"]:
            months[int(x["ex_date"][5:7]) - 1]["received"] += x["amount"]
        for x in h["projected"]:
            months[int(x["ex_date"][5:7]) - 1]["projected"] += x["amount"]
        tot["annual_income"] += income
        tot["received"] += received
        tot["projected"] += projected
        next_ex = h["projected"][0]["ex_date"] if h["projected"] else None
        holdings.append({
            "symbol": sym, "name": r.get("name"), "qty": r["qty"], "pays": h["pays"], "frequency": h["frequency"],
            "rate": h["rate"], "trailing_12m": h["trailing_12m"], "last_ex_date": h["last_ex_date"],
            "last_amount": h.get("last_amount"), "irregular": h.get("irregular", False),
            "next_ex_date_est": next_ex, "annual_income": income,
            "yield_pct": h["rate"] / price * 100 if price else None,
            "yield_on_cost_pct": h["rate"] / avg_cost * 100 if avg_cost else None,
            "received_ytd": received, "projected_rest_of_year": projected,
            "events": h["received"] + h["projected"],
        })

    mv = sum(r.get("market_value") or 0 for r in rows)
    cost = sum(r.get("cost_basis") or 0 for r in rows)
    holdings.sort(key=lambda x: (-x["annual_income"], x["symbol"]))
    return {
        "year": today.year,
        "as_of": today.isoformat(),
        "totals": tot | {
            "year_total": tot["received"] + tot["projected"],
            "yield_pct": tot["annual_income"] / mv * 100 if mv else None,
            "yield_on_cost_pct": tot["annual_income"] / cost * 100 if cost else None,
            "payers": sum(1 for h in holdings if h["pays"]), "positions": len(holdings),
        },
        "by_month": months,
        "holdings": holdings,
    }


def accrue(txns: Iterable, histories: dict[str, list[tuple[str, float]]], today: date) -> list[dict]:
    """Dividends earned by holding through an ex-date, from the payment history: shares held going
    into the ex-date × cash per share. Estimates until a DIVIDEND transaction records the payment,
    so an ex-date matched by one (the latest ex-date on or before it, within MATCH_DAYS) is skipped.

    `txns` are one portfolio's (FIFO-free: only share counts matter). Histories are split-adjusted
    per share, so shares held before a later recorded SPLIT are scaled by its ratio.
    """
    by_sym: dict[str, list] = {}
    for t in txns:
        by_sym.setdefault(t.symbol, []).append(t)
    out = []
    for sym, ts in by_sym.items():
        ts.sort(key=lambda t: (t.ts, t.id or 0))
        first = ts[0].ts.astimezone(NY).date()
        pays = sorted((d, a) for iso, a in histories.get(sym, [])
                      if first < (d := date.fromisoformat(iso)) <= today and a > 0)
        if not pays:
            continue
        recorded = set()
        for t in ts:
            if TxnType(t.type) == TxnType.DIVIDEND:
                d = t.ts.astimezone(NY).date()
                prior = [ex for ex, _ in pays if ex <= d]
                if prior and (d - prior[-1]).days <= MATCH_DAYS:
                    recorded.add(prior[-1])
        for ex, per_share in pays:
            if ex in recorded:
                continue
            cutoff = datetime.combine(ex, datetime.min.time(), NY)
            qty, later_splits = 0.0, 1.0
            for t in ts:
                kind = TxnType(t.type)
                if kind == TxnType.SPLIT:
                    if t.ts < cutoff:
                        qty *= t.qty
                    else:
                        later_splits *= t.qty
                elif t.ts < cutoff and kind in (TxnType.BUY, TxnType.OPENING):
                    qty += t.qty
                elif t.ts < cutoff and kind == TxnType.SELL:
                    qty -= t.qty
            qty *= later_splits
            if qty > 1e-9:
                out.append({"symbol": sym, "ex_date": ex.isoformat(), "per_share": per_share, "shares": qty,
                            "amount": qty * per_share})
    out.sort(key=lambda x: (x["ex_date"], x["symbol"]))
    return out
