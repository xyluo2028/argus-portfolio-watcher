"""Earnings reports matched to reported quarters: estimate vs actual (EPS, revenue when known),
beat or miss, and the stock's price reaction across the report.

Sources, best first for each field:
- Finnhub earnings calendar (`earnings` events): EPS and revenue estimate/actual, adjusted basis.
  The free calendar only reaches back a few weeks, but stored rows accumulate from then on.
- Finnhub EPS history (`eps_result`, last 4 quarters): adjusted EPS actual vs estimate.
- Yahoo earnings dates (`eps_report`): report time and EPS for many years; its reported EPS is
  sometimes GAAP (e.g. a one-time tax charge), so it is flagged `eps_basis: "reported"`.

Reaction: a report before the open (or during the day) moves that day's close vs the prior close;
one after the close moves the next session's close vs that day's. Until that session has
closed, the latest price (after-hours/pre-market included) gives a provisional figure.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from argus.market_calendar import NY
from argus.providers.base import Quote

MATCH_DAYS = 100  # a quarter's report comes within ~100 days of its period end
IN_LINE = 0.005  # |actual - estimate| below this (per share) counts as in line


def timing(at: datetime | None, hour: str | None) -> str | None:
    """bmo (before the open), amc (after the close), dmh (during market hours) or None (unknown)."""
    if hour in ("bmo", "amc", "dmh"):
        return hour
    if at is None:
        return None
    t = at.astimezone(NY).time()
    if t == time(0, 0):
        return None
    return "bmo" if t < time(9, 30) else "amc" if t >= time(16, 0) else "dmh"


def verdict(actual: float | None, estimate: float | None, tolerance: float = IN_LINE) -> str | None:
    if actual is None or estimate is None:
        return None
    if abs(actual - estimate) < tolerance:
        return "in_line"
    return "beat" if actual > estimate else "miss"


def surprise_pct(actual: float | None, estimate: float | None) -> float | None:
    if actual is None or estimate is None or estimate == 0:
        return None
    return (actual - estimate) / abs(estimate) * 100


def reaction(report: date, when: str | None, bars: dict[date, tuple[float, float]], today: date,
             quote: Quote | None = None, session: str = "closed") -> dict | None:
    """Price move across a report. `bars` maps trading date -> (open, close).

    Unknown timing spans both possibilities: prior close -> next session's close."""
    sessions = sorted(bars)
    before = [d for d in sessions if d < report]
    if when == "amc":
        base_day = report if report in bars else (before[-1] if before else None)
        after = [d for d in sessions if d > report]
    elif when in ("bmo", "dmh"):
        base_day = before[-1] if before else None
        after = [d for d in sessions if d >= report]
    else:
        base_day = before[-1] if before else None
        after = [d for d in sessions if d > report]
    if base_day is None:
        return None
    base = bars[base_day][1]
    out = {"base_date": base_day.isoformat(), "base_close": base}
    if after:
        day = after[0]
        o, c = bars[day]
        # Today's bar is still moving until the regular session closes.
        provisional = day == today and session in ("pre", "regular")
        return out | {"date": day.isoformat(), "open_pct": (o / base - 1) * 100, "close_pct": (c / base - 1) * 100,
                      "provisional": provisional, "label": "today" if provisional else None}
    # The reacting session hasn't traded yet: use the latest price, after-hours/pre-market included.
    if quote is None or report < today - timedelta(days=4):
        return None
    live = quote.ext_price if quote.ext_price is not None else quote.price
    label = {"pre": "pre-market", "post": "after hours"}.get(quote.ext_session or "", "latest")
    return out | {"date": None, "open_pct": None, "close_pct": (live / base - 1) * 100, "provisional": True,
                  "label": label}


def _pair_results(reports: list[date], results: dict[date, dict]) -> dict[date, dict]:
    """Finnhub EPS results by report date. A result's `period` is a quarter end near its report but
    not reliably the fiscal one (NVDA's quarter ended Jul 26 is filed as Sep 30), so pair each with
    a report from 100 days before to 45 days after it, closest pairs first, each used once."""
    pairs = sorted((abs((p - r).days), r, p) for r in reports for p in results if -100 <= (p - r).days <= 45)
    out: dict[date, dict] = {}
    taken: set[date] = set()
    for _, r, p in pairs:
        if r not in out and p not in taken:
            out[r] = results[p]
            taken.add(p)
    return out


def build(periods: list[str], yahoo: list[dict], calendar: list[dict], results: list[dict],
          bars: dict[date, tuple[float, float]], today: date, quote: Quote | None = None,
          session: str = "closed") -> dict:
    """Match reports to quarter ends (`periods`, ISO dates) and describe each.

    yahoo: [{"date", "hour", "eps_estimate", "eps_actual"}]; calendar: earnings events (Finnhub field
    names); results: Finnhub EPS history ({"period", "epsActual", "epsEstimate"}). Returns
    {"reports": [one per matched period, newest first], "next": the next scheduled report or None}."""
    reports: dict[date, dict] = {}
    for r in yahoo:
        d = date.fromisoformat(r["date"])
        reports[d] = {"date": d, "hour": r.get("hour"), "yahoo": r}
    for e in calendar:
        d = date.fromisoformat(e["date"])
        # The same report may sit a day apart in the two sources (time zones, late filings).
        same = next((k for k in reports if abs((k - d).days) <= 2), None)
        if same is None:
            reports[d] = {"date": d, "hour": e.get("hour"), "calendar": e}
        else:
            reports[same]["calendar"] = e
            reports[same]["hour"] = e.get("hour") or reports[same]["hour"]
    by_period = {date.fromisoformat(r["period"]): r for r in results if r.get("period")}
    paired = _pair_results([d for d in reports if d <= today], by_period)

    out = []
    for p in sorted({date.fromisoformat(x) for x in periods}, reverse=True):
        due = sorted(d for d in reports if p < d <= p + timedelta(days=MATCH_DAYS) and d <= today)
        if not due:
            continue
        rep = reports[due[0]]
        cal, yh = rep.get("calendar") or {}, rep.get("yahoo") or {}
        fin = paired.get(rep["date"], {})
        if cal.get("epsActual") is not None:
            eps_est, eps_act, basis = cal.get("epsEstimate"), cal["epsActual"], "adjusted"
        elif fin.get("epsActual") is not None:
            eps_est, eps_act, basis = fin.get("epsEstimate"), fin["epsActual"], "adjusted"
        else:
            eps_est, eps_act, basis = yh.get("eps_estimate"), yh.get("eps_actual"), "reported"
        if eps_act is None:
            basis = None
        rev_est, rev_act = cal.get("revenueEstimate"), cal.get("revenueActual")
        when = timing(None, rep.get("hour"))
        out.append({
            "period_end": p.isoformat(), "report_date": rep["date"].isoformat(), "timing": when,
            "eps_estimate": eps_est, "eps_actual": eps_act, "eps_basis": basis,
            "eps_surprise_pct": surprise_pct(eps_act, eps_est), "eps_result": verdict(eps_act, eps_est),
            "revenue_estimate": rev_est, "revenue_actual": rev_act,
            "revenue_surprise_pct": surprise_pct(rev_act, rev_est),
            # Revenue is "in line" within 0.1% of the estimate.
            "revenue_result": verdict(rev_act, rev_est, abs(rev_est) * 0.001 if rev_est else IN_LINE),
            "reaction": reaction(rep["date"], when, bars, today, quote, session),
        })

    upcoming = sorted(d for d in reports if d >= today and not (d == today and _reported(reports[d])))
    nxt = None
    if upcoming:
        rep = reports[upcoming[0]]
        cal, yh = rep.get("calendar") or {}, rep.get("yahoo") or {}
        nxt = {"date": rep["date"].isoformat(), "timing": timing(None, rep.get("hour")),
               "eps_estimate": cal.get("epsEstimate") if cal.get("epsEstimate") is not None else yh.get("eps_estimate"),
               "revenue_estimate": cal.get("revenueEstimate")}
    return {"reports": out, "next": nxt}


def _reported(rep: dict) -> bool:
    return (rep.get("calendar") or {}).get("epsActual") is not None or \
        (rep.get("yahoo") or {}).get("eps_actual") is not None
