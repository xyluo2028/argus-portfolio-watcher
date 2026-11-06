"""Dividend analysis: forward income and yield per holding, and this calendar year's dividends
(estimated received so far + projected for the rest of the year), all by ex-date and before tax.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta
from statistics import mean, median, pstdev

from argus.market_calendar import NY, session_before, session_on_or_after
from argus.models import TxnType

FREQ_NAMES = {12: "monthly", 4: "quarterly", 2: "semiannual", 1: "annual"}
LOOKBACK_DAYS = 400  # a payer with nothing in this window is treated as not paying
LUMPY_CV = 0.25  # payments this dispersed (stdev / mean) over a year aren't a rate to extrapolate
MATCH_DAYS = 120  # a DIVIDEND transaction records the latest ex-date this far back (pay dates trail ex-dates)
SAME_DATE_DAYS = 10  # a month's ex-dates a year apart this close are the payer's calendar, not chance


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    last_day = (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def _month_end(d: date) -> date:
    """The last trading day of d's month."""
    return session_before(date(d.year + (d.month == 12), d.month % 12 + 1, 1))


def _month_start(d: date) -> date:
    """The first trading day of d's month."""
    return session_on_or_after(d.replace(day=1))


def anchor(ex_dates: list[date]) -> str | None:
    """Where a payer's ex-dates sit in the month: "end" for the last trading day (Realty Income),
    "start" for the first (Vanguard's bond funds), else None (the same day of the month). The last
    ex-date and all but one of the last six must fit, so one odd December date doesn't break it but
    a payer on the 2nd isn't taken for a first-day payer because the 1st was a Sunday a few times."""
    recent = ex_dates[-6:]
    for name, fits in (("end", _month_end), ("start", _month_start)):
        if len(recent) >= 3 and recent[-1] == fits(recent[-1]) and sum(d != fits(d) for d in recent) <= 1:
            return name
    return None


def next_ex(last_d: date, months: int, anchored: str | None) -> date:
    """The estimated ex-date `months` after `last_d`: the same day of the month, moved to the next
    trading day when that's a weekend or holiday (funds go ex on business days), or the month's
    last / first trading day for a payer anchored there, so a month-end payer's 10-30 (a Friday)
    projects 12-31, not 12-30, and its 02-26 projects 03-31, not 03-26."""
    d = add_months(last_d, months)
    return _month_end(d) if anchored == "end" else _month_start(d) if anchored == "start" else session_on_or_after(d)


def _month_key(d: date) -> int:
    return d.year * 12 + d.month - 1


def _roll(d: date, before: date, months: int, anchored: str | None) -> date:
    """Past ex-date `d` (matched by `before` a year earlier) moved `months` ahead: the month's last /
    first trading day if it was one (for an anchored payer, or both years), the same weekday if it
    was that both years (SPY's third Friday, SCHD's Wednesday), else the same day; on a trading day
    and kept in its month (a Saturday the 28th moves back to Friday, not into the next month)."""
    t = add_months(d, months)
    if (anchored == "end" or before == _month_end(before)) and d == _month_end(d):
        return _month_end(t)
    if (anchored == "start" or before == _month_start(before)) and d == _month_start(d):
        return _month_start(t)
    if d.weekday() == before.weekday():
        w = t + timedelta(days=(d.weekday() - t.weekday() + 3) % 7 - 3)
        t = w if w.month == t.month else t
    s = session_on_or_after(t)
    return s if s.month == t.month else session_before(t)


def schedule(ex_dates: list[date], freq: int, last_d: date, anchored: str | None, until: date) -> list[date]:
    """Estimated ex-dates after `last_d` up to `until`. A month whose ex-dates in the latest year of
    history match the year before (as many, each within SAME_DATE_DAYS) follows that calendar,
    including none: Vanguard's and Schwab's bond funds go ex on 12-01 and again around 12-18 and skip
    January, SCHD goes ex around 12-10 although its other quarters are near the 24th. Any other month
    gets the step estimate: every 12/freq months from the last ex-date on the payer's usual day
    (see next_ex). In `last_d`'s own month only the calendar's dates after those already paid count."""
    steps, k = [], 1
    while (e := next_ex(last_d, 12 // freq * k, anchored)) <= until:
        steps.append(e)
        k += 1
    by_month: dict[int, list[date]] = {}
    for d in sorted(ex_dates):
        by_month.setdefault(_month_key(d), []).append(d)
    ago = add_months(last_d, -12)
    if not any(abs((d - ago).days) <= SAME_DATE_DAYS for d in ex_dates):
        return steps  # the latest ex-date breaks last year's calendar (PEGA moved 10-01 to 08-17)
    first, last = min(by_month), _month_key(last_d)
    out = []
    for m in range(last, _month_key(until) + 1):
        years = 1  # the latest same month that's wholly before last_d's month
        while m - 12 * years >= last:
            years += 1
        t = m - 12 * years
        a, b = by_month.get(t, []), by_month.get(t - 12, [])
        known = t - 12 > first and len(a) == len(b) and all(
            abs((add_months(y, 12) - x).days) <= SAME_DATE_DAYS for x, y in zip(a, b))
        if not known:
            out += [e for e in steps if _month_key(e) == m]
            continue
        # (both years on the first trading day: kept even while the anchor can't be read from the
        # latest dates, as BND's last ex-date is 12-18 until February's arrives)
        rolled = [_roll(x, y, 12 * years, anchored) for x, y in zip(a, b)]
        out += rolled[len(by_month.get(m, [])):] if m == last else rolled
    return sorted(d for d in out if last_d < d <= until)


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


def _year(pays: list[tuple[date, float]], today: date) -> list[float]:
    return [a for d, a in pays if d > today - timedelta(days=365)]


def _rhythm(pays: list[tuple[date, float]], today: date):
    """(freq, period, last ex-date, last amount, trailing 12m, stale, per payment, anchor) from sorted
    `pays`, or None for a payer with nothing in the lookback window."""
    recent = [(d, a) for d, a in pays if d > today - timedelta(days=LOOKBACK_DAYS)]
    if not recent:
        return None
    freq = frequency([d for d, _ in recent])
    period = timedelta(days=round(365 / freq))
    last_d, last_amt = recent[-1]
    year = _year(pays, today)
    trailing = sum(year)
    stale = today - last_d > period * 2 + timedelta(days=30)  # missed two payments: don't extrapolate
    per_payment = trailing / freq if lumpy(year) else last_amt  # projected at the year's average if lumpy
    return freq, period, last_d, last_amt, trailing, stale, per_payment, anchor([d for d, _ in recent])


def _passed(freq: int, last_d: date, per_payment: float, stale: bool, today: date,
            announced: Iterable[date], anchored: str | None = None,
            ex_dates: list[date] | None = None) -> list[tuple[date, float, bool]]:
    """Ex-dates that have passed but the provider's history doesn't show (Yahoo lags days behind the
    ex-date, while quotes' previous close already drops by the dividend, and it sometimes drops a
    recent row it served before): (ex-date, projected cash per share, whether the date is estimated).
    A declared one counts as is. The estimated ex-dates (see schedule) are walked from the last paid one
    up to today, so a history that is missing its last row still counts the payment after it; each
    one a declared date doesn't replace counts. They count only while the newest of them is within
    half a period of grace (about two weeks for a monthly payer, six for a quarterly one): later than
    that, the history hasn't merely lagged, the payer more likely skipped or stopped, so nothing is
    counted. When the history catches up, its row (within half a period) becomes the last ex-date and
    replaces the estimate, with the real amount."""
    half = timedelta(days=round(365 / freq)) / 2
    declared = [a for a in sorted(set(announced)) if last_d + half <= a <= today]
    out = [(a, per_payment, False) for a in declared]
    if not stale:
        steps = schedule(ex_dates or [], freq, last_d, anchored, today)
        if steps and today <= steps[-1] + half:
            out += [(e, per_payment, True) for e in steps if all(abs(e - a) >= half for a in declared)]
    return sorted(out)


def merge_history(stored: list[tuple[str, float]], fetched: list[tuple[str, float]],
                  today: date) -> list[tuple[str, float]]:
    """A refreshed dividend history merged into the stored one. Yahoo sometimes drops a recent row it
    served the day before (SGOV's 10-01 went missing overnight), so a stored ex-date the new answer
    lacks is kept while it's in the lookback window, unless the new answer has a row within a week of
    it (the same payment, re-dated). A new amount for the same date overwrites the stored one."""
    new = [(d, a) for d, a in fetched]
    seen = [date.fromisoformat(d) for d, _ in new]
    cutoff = today - timedelta(days=LOOKBACK_DAYS)
    kept = [(d, a) for d, a in stored
            if (x := date.fromisoformat(d)) > cutoff and all(abs((x - n).days) > 7 for n in seen)]
    return sorted([*new, *kept])


def pending(history: list[tuple[str, float]], today: date, announced: Iterable[date] = ()) -> list[tuple[str, float]]:
    """Passed ex-dates missing from `history` (see _passed), as (ex-date ISO, cash per share) rows."""
    pays = sorted((date.fromisoformat(d), a) for d, a in history)
    if (r := _rhythm(pays, today)) is None:
        return []
    freq, _, last_d, _, _, stale, per_payment, anchored = r
    return [(d.isoformat(), a) for d, a, _ in
            _passed(freq, last_d, per_payment, stale, today, announced, anchored, [d for d, _ in pays])]


def analyze_holding(history: list[tuple[str, float]], qty: float, qty_at: Callable[[date], float],
                    today: date, announced: Iterable[date] = (), until: date | None = None) -> dict:
    """`history`: (ex-date ISO, cash per share), any order. `qty_at(d)`: shares held going into day d.
    `announced`: ex-dates the company has declared (calendar), which replace the estimated ones.
    Projects to Dec 31, or to `until` when that's later (a window that crosses the year end)."""
    pays = sorted((date.fromisoformat(d), a) for d, a in history)
    r = _rhythm(pays, today)
    if r is None:
        return {"pays": False, "frequency": None, "rate": 0.0, "trailing_12m": 0.0,
                "received": [], "projected": [], "last_ex_date": pays[-1][0].isoformat() if pays else None}
    freq, period, last_d, last_amt, trailing, stale, per_payment, anchored = r
    rate = trailing if stale or lumpy(_year(pays, today)) else last_amt * freq

    year_start, year_end = date(today.year, 1, 1), date(today.year, 12, 31)
    horizon = max(until or year_end, year_end)
    received = [{"ex_date": d.isoformat(), "per_share": a, "shares": q, "amount": q * a}
                for d, a in pays if year_start <= d <= today and (q := qty_at(d)) > 0]
    projected = []
    if not stale:  # with no shares (a watchlist) this still gives the expected dates, at $0
        # The payer's own calendar where its history repeats, else every 12/freq months (see schedule).
        for nxt in schedule([d for d, _ in pays], freq, last_d, anchored, horizon):
            if today < nxt:
                projected.append({"ex_date": nxt.isoformat(), "per_share": per_payment, "shares": qty,
                                  "amount": qty * per_payment, "estimated_date": True})
    # A declared ex-date is the payment the estimate guessed at: it replaces any estimate within half
    # a period of it (KO's 12-01 replaces a 12-15 guess), at the projected amount per share. One the
    # history already has is skipped; one that's passed before the history shows it is received (below).
    half = period / 2
    for a in sorted(set(announced)):
        if a < last_d + half or a > horizon:
            continue
        projected = [x for x in projected if abs(date.fromisoformat(x["ex_date"]) - a) >= half]
        if a > today:
            projected.append({"ex_date": a.isoformat(), "per_share": per_payment, "shares": qty,
                              "amount": qty * per_payment, "estimated_date": False})
    for d, per_share, est in _passed(freq, last_d, per_payment, stale, today, announced, anchored,
                                     [d for d, _ in pays]):
        if d >= year_start and (q := qty_at(d)) > 0:
            received.append({"ex_date": d.isoformat(), "per_share": per_share, "shares": q,
                             "amount": q * per_share, "estimated": True, "estimated_date": est})
    projected.sort(key=lambda x: x["ex_date"])
    return {"pays": True, "frequency": FREQ_NAMES[freq], "rate": rate, "trailing_12m": trailing,
            "last_ex_date": last_d.isoformat(), "last_amount": last_amt, "irregular": stale,
            "per_payment": per_payment, "received": received, "projected": projected}


def analyze(rows: list[dict], histories: dict[str, list[tuple[str, float]]],
            qty_at: Callable[[str, date], float], today: date,
            announced: dict[str, Iterable[date]] | None = None) -> dict:
    """`rows`: portfolio summary positions (symbol, name, qty, avg_cost, cost_basis, price, market_value).
    `announced`: declared ex-dates per symbol (see analyze_holding)."""
    holdings = []
    months = [{"month": m, "received": 0.0, "projected": 0.0} for m in range(1, 13)]
    tot = {"annual_income": 0.0, "received": 0.0, "projected": 0.0}
    year_end = date(today.year, 12, 31).isoformat()
    for r in rows:
        sym = r["symbol"]
        # Projected a year ahead so the next ex-date is known in December too; totals stay this year's.
        h = analyze_holding(histories.get(sym, []), r["qty"], lambda d, s=sym: qty_at(s, d), today,
                            (announced or {}).get(sym, ()), add_months(today, 12))
        this_year = [x for x in h["projected"] if x["ex_date"] <= year_end]
        price, avg_cost = r.get("price"), r.get("avg_cost")
        income = h["rate"] * r["qty"]
        received = sum(x["amount"] for x in h["received"])
        projected = sum(x["amount"] for x in this_year)
        for x in h["received"]:
            months[int(x["ex_date"][5:7]) - 1]["received"] += x["amount"]
        for x in this_year:
            months[int(x["ex_date"][5:7]) - 1]["projected"] += x["amount"]
        tot["annual_income"] += income
        tot["received"] += received
        tot["projected"] += projected
        nxt = h["projected"][0] if h["projected"] else None
        next_ex = nxt["ex_date"] if nxt else None
        holdings.append({
            "symbol": sym, "name": r.get("name"), "qty": r["qty"], "pays": h["pays"], "frequency": h["frequency"],
            "rate": h["rate"], "trailing_12m": h["trailing_12m"], "last_ex_date": h["last_ex_date"],
            "last_amount": h.get("last_amount"), "irregular": h.get("irregular", False),
            "next_ex_date_est": next_ex, "next_ex_date_announced": bool(nxt) and not nxt["estimated_date"],
            "annual_income": income,
            "yield_pct": h["rate"] / price * 100 if price else None,
            "yield_on_cost_pct": h["rate"] / avg_cost * 100 if avg_cost else None,
            "received_ytd": received, "projected_rest_of_year": projected,
            "events": sorted(h["received"], key=lambda x: x["ex_date"]) + this_year,
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


def accrue(txns: Iterable, histories: dict[str, list[tuple[str, float]]], today: date,
           announced: dict[str, Iterable[date]] | None = None) -> list[dict]:
    """Dividends earned by holding through an ex-date, from the payment history: shares held going
    into the ex-date × cash per share. Estimates until a DIVIDEND transaction records the payment,
    so an ex-date matched by one (the latest ex-date on or before it, within MATCH_DAYS) is skipped.
    A passed ex-date the history doesn't show yet (see `pending`; `announced` as in analyze) accrues
    at the projected amount, marked `estimated`, until the history's own row replaces it.

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
        hist = histories.get(sym, [])
        extra = pending(hist, today, (announced or {}).get(sym, ()))
        guessed = {date.fromisoformat(iso) for iso, _ in extra}
        pays = sorted((d, a) for iso, a in [*hist, *extra]
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
                            "amount": qty * per_share} | ({"estimated": True} if ex in guessed else {}))
    out.sort(key=lambda x: (x["ex_date"], x["symbol"]))
    return out
