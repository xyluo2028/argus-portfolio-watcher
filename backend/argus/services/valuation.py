"""Inputs for the DCF calculator, an exit-multiple discounted cash flow: grow a metric (free cash flow,
operating cash flow, net income or revenue) for some years, value the company at an exit multiple of
it, and discount that price and the dividends paid on the way back to today at the return you want.

This module gathers what the inputs are filled from: each metric's trailing value, its yearly
history, the multiples the stock has traded at and how fast the metric grew, plus analysts' growth
estimates. The projection itself runs in the browser (frontend/src/dcf.ts), so it follows every input
as you type."""

from __future__ import annotations

from datetime import date
from itertools import pairwise
from statistics import median

from argus.errors import ArgusError
from argus.providers.sec_edgar import _is_quarter
from argus.services.research import cagr

METRICS = {"free_cash_flow": "Free cash flow", "operating_cash_flow": "Operating cash flow",
           "net_income": "Net income", "revenue": "Revenue"}
# Finnhub's quarterly ratio history has these multiples; P/OCF is derived from P/S.
FINNHUB_MULTIPLE = {"net_income": "peTTM", "revenue": "psTTM", "free_cash_flow": "pfcfTTM"}
HISTORY_YEARS = 10  # multiples shown
STATS_YEARS = 5  # multiples the median and range are taken over
MATCH_DAYS = 10  # Finnhub's quarter ends can differ from the filing's by a few days
STALE_DAYS = 100  # a metric's latest figure may trail the newest filing by at most about a quarter

# A saved model: the metric and these numbers, nothing else.
INPUT_FIELDS = ("base", "years", "growth", "decay", "multiple", "target_return", "dps", "dividend_growth", "share_change")


def ttm_series(quarters: list[dict], field: str) -> dict[date, float]:
    """Trailing-four-quarter sums of `field` at each quarter end with four back-to-back quarters that
    all have it (SEC data can skip a quarter)."""
    q = sorted((date.fromisoformat(p["period_end"]), p.get(field)) for p in quarters)
    out = {}
    for i in range(3, len(q)):
        win = q[i - 3:i + 1]
        if any(v is None for _, v in win) or not all(_is_quarter((b - a).days) for (a, _), (b, _) in pairwise(win)):
            continue
        out[win[-1][0]] = sum(v for _, v in win)
    return out


def _near(points: dict[date, float], d: date) -> float | None:
    best = min(points, key=lambda k: abs((k - d).days), default=None)
    return points[best] if best is not None and abs((best - d).days) <= MATCH_DAYS else None


def multiple_history(field: str, series: dict[str, list[dict]], quarters: list[dict]) -> list[tuple[date, float]]:
    """Price ÷ the trailing metric at each quarter end, oldest first. Finnhub's P/E, P/S and P/FCF are
    used as they are; P/OCF is P/S × revenue ÷ operating cash flow over the same four quarters.
    Quarters where the metric was negative (no meaningful multiple) are left out."""
    def points(key):
        return {date.fromisoformat(x["period"]): float(x["v"]) for x in series.get(key) or []
                if isinstance(x.get("v"), (int, float)) and x.get("period")}
    if key := FINNHUB_MULTIPLE.get(field):
        pts = points(key).items()
    else:
        ps, rev, m = points("psTTM"), ttm_series(quarters, "revenue"), ttm_series(quarters, field)
        pts = [(d, p * rev[d] / m[d]) for d in m if m[d] > 0 and d in rev and (p := _near(ps, d)) is not None]
    return sorted((d, v) for d, v in pts if v > 0)


def multiple_stats(hist: list[tuple[date, float]], current: float | None, today: date) -> dict:
    start = date(today.year - STATS_YEARS, today.month, 1)
    recent = sorted(v for d, v in hist if d >= start)
    q = lambda p: recent[min(len(recent) - 1, max(0, round(p * (len(recent) - 1))))]  # noqa: E731
    shown = date(today.year - HISTORY_YEARS, today.month, 1)
    return {"current": current, "points": len(recent),
            "median_5y": median(recent) if len(recent) >= 4 else None,
            "p25_5y": q(0.25) if len(recent) >= 4 else None, "p75_5y": q(0.75) if len(recent) >= 4 else None,
            "history": [{"date": d.isoformat(), "v": round(v, 2)} for d, v in hist if d >= shown]}


def analyst_growth(field: str, analyst: dict) -> tuple[float | None, str | None]:
    """Analysts' expected growth for the metric, in percent, and what it is. Revenue uses the revenue
    estimate for next fiscal year; the earnings and cash-flow metrics use the long-term (5-year) EPS
    growth when Yahoo has it, else next year's EPS growth."""
    def pct(v):
        return v * 100 if isinstance(v, (int, float)) else None
    if field == "revenue":
        g = pct(((analyst.get("revenue_estimate") or {}).get("+1y") or {}).get("growth"))
        return g, "analysts' revenue growth, next fiscal year" if g is not None else None
    ltg = pct(((analyst.get("growth_estimates") or {}).get("LTG") or {}).get("stockTrend"))
    if ltg is not None:
        return ltg, "analysts' long-term EPS growth, per year"
    g = pct(((analyst.get("earnings_estimate") or {}).get("+1y") or {}).get("growth"))
    return g, "analysts' EPS growth, next fiscal year" if g is not None else None


def share_change(statements: dict) -> tuple[float | None, int | None]:
    """Yearly change in the diluted share count (negative = buybacks), from Yahoo's annual statements,
    which are split-adjusted (SEC's counts are as filed, so a split looks like a share issue)."""
    years = statements.get("years") or []
    vals = (statements.get("income") or {}).get("Diluted Average Shares") or []
    pts = [(date.fromisoformat(y), v) for y, v in zip(years, vals) if isinstance(v, (int, float)) and v > 0]
    if len(pts) < 2:
        return None, None
    (d1, new), (d0, old) = pts[0], pts[-1]
    n = round((d1 - d0).days / 365.25)
    return (((new / old) ** (1 / n) - 1) * 100, n) if n >= 1 else (None, None)


def build(symbol: str, price: float | None, metrics: dict, quarterly: dict, annual: dict,
          series: dict, analyst: dict, statements: dict, info: dict, today: date) -> dict:
    """Everything the calculator fills its inputs from, for one company."""
    units = quarterly.get("units") or annual.get("units") or {}
    quarters = quarterly.get("periods") or []
    years = sorted(annual.get("periods") or [], key=lambda p: p["period_end"])
    cap = metrics.get("market_cap")
    shares = cap / price if cap and price else info.get("sharesOutstanding")
    # A metric whose newest figure trails the newest filing has stopped being reported under the tags
    # read (Amazon's capex since 2017): it has no current value rather than a years-old one.
    newest = max((date.fromisoformat(p["period_end"]) for p in [*quarters, *years]), default=None)
    out = {}
    for field, label in METRICS.items():
        ttm = ttm_series(quarters, field)
        last = next((p for p in reversed(years) if p.get(field) is not None), None)
        base = base_end = basis = None
        if ttm and (newest - max(ttm)).days <= STALE_DAYS:
            end = max(ttm)
            base, base_end, basis = ttm[end], end.isoformat(), "last four quarters"
        elif last and (newest - date.fromisoformat(last["period_end"])).days <= STALE_DAYS:
            base, base_end, basis = last[field], last["period_end"], "last fiscal year"
        unit_field = "operating_cash_flow" if field == "free_cash_flow" else field
        hist = [(date.fromisoformat(p["period_end"]), p.get(field)) for p in years]
        g, g_basis = analyst_growth(field, analyst)
        out[field] = {
            "label": label, "currency": (units.get(unit_field) or "USD"),
            "base": base, "base_end": base_end, "base_basis": basis,
            "annual": [{"period_end": d.isoformat(), "value": v} for d, v in hist[-HISTORY_YEARS:] if v is not None],
            "growth": {"hist_3y": cagr(hist, 3), "hist_5y": cagr(hist, 5), "analyst": g, "analyst_basis": g_basis},
            "multiple": multiple_stats(multiple_history(field, series, quarters),
                                       cap / base if cap and base and base > 0 else None, today),
        }
    sc, sc_years = share_change(statements)
    dy = metrics.get("dividend_yield_pct")
    return {
        "symbol": symbol, "company": annual.get("company") or quarterly.get("company"), "price": price,
        "market_cap": cap, "shares": shares,
        "dps": dy * price / 100 if dy and price else 0.0, "dividend_growth_5y": metrics.get("dividend_growth_5y_pct"),
        "share_change": sc, "share_change_years": sc_years,
        "analyst_target": info.get("targetMeanPrice"), "analyst_count": info.get("numberOfAnalystOpinions"),
        "metrics": out,
    }


def clean_inputs(raw: dict) -> dict:
    """A saved model, checked: the metric and finite numbers within sane bounds."""
    if not isinstance(raw, dict) or raw.get("metric") not in METRICS:
        raise ArgusError("INVALID_ARG", f"metric must be one of: {', '.join(METRICS)}.")
    out: dict = {"metric": raw["metric"]}
    for k in INPUT_FIELDS:
        v = raw.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v != v or abs(v) == float("inf"):
            raise ArgusError("INVALID_ARG", f"{k} must be a number.")
        out[k] = float(v)
    if not 1 <= out["years"] <= 30:
        raise ArgusError("INVALID_ARG", "years must be between 1 and 30.")
    out["years"] = int(out["years"])
    return out
