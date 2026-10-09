"""Dividend analysis: forward income and yield per holding, and this calendar year's dividends
(estimated received so far + projected for the rest of the year), all by ex-date and before tax.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from statistics import median

FREQ_NAMES = {12: "monthly", 4: "quarterly", 2: "semiannual", 1: "annual"}
LOOKBACK_DAYS = 400  # a payer with nothing in this window is treated as not paying


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
    trailing = sum(a for d, a in recent if d > today - timedelta(days=365))
    stale = today - last_d > period * 2 + timedelta(days=30)  # missed two payments: don't extrapolate
    rate = trailing if stale else last_amt * freq

    year_start, year_end = date(today.year, 1, 1), date(today.year, 12, 31)
    received = [{"ex_date": d.isoformat(), "per_share": a, "shares": q, "amount": q * a}
                for d, a in pays if year_start <= d <= today and (q := qty_at(d)) > 0]
    projected = []
    if not stale:  # with no shares (a watchlist) this still gives the expected dates, at $0
        # Same day of the month as the last ex-date, every 12/freq months (payers keep their rhythm).
        step, k = 12 // freq, 1
        while (nxt := add_months(last_d, step * k)) <= year_end:
            if nxt > today:
                projected.append({"ex_date": nxt.isoformat(), "per_share": last_amt, "shares": qty,
                                  "amount": qty * last_amt, "estimated_date": True})
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
