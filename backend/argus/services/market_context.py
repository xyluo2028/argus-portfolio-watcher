"""Market context: the big gauges (indices, volatility, rates, USD/JPY, oil, gold, bitcoin), a sector
heatmap, breadth proxies, the Treasury yield curve and the US economic calendar.

Breadth here is measured with proxies, not with all 500 S&P members: equal- vs cap-weighted S&P
(RSP vs SPY), small vs large caps (IWM vs SPY), and how many of the 11 sectors are above their
50- and 200-day averages.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from argus.services.dividends import add_months

GAUGES = [
    # Index levels, not the ETFs that track them (SPY, QQQ, IWM still feed the breadth gauges)
    ("^GSPC", "S&P 500", "level"), ("^NDX", "Nasdaq 100", "level"), ("^RUT", "Russell 2000", "level"),
    ("^VIX", "VIX (volatility)", "level"), ("^TNX", "10-year yield", "yield"), ("JPY=X", "USD/JPY", "level"),
    ("CL=F", "WTI crude oil", "$"), ("GC=F", "Gold", "$"), ("BTC-USD", "Bitcoin", "$"),
]
SECTORS = [("XLK", "Technology"), ("XLC", "Communication Services"), ("XLY", "Consumer Discretionary"),
           ("XLF", "Financials"), ("XLV", "Health Care"), ("XLI", "Industrials"), ("XLE", "Energy"),
           ("XLB", "Materials"), ("XLU", "Utilities"), ("XLP", "Consumer Staples"), ("XLRE", "Real Estate")]
BREADTH = ["RSP", "SPY", "IWM"]
ALL_SYMBOLS = sorted({s for s, *_ in GAUGES} | {s for s, _ in SECTORS} | set(BREADTH))

PERIODS = ["1D", "1W", "1M", "3M", "YTD", "1Y"]
# Releases that move markets, matched as whole words. Fed speakers are left out except the Chair.
MAJOR = re.compile(r"\b(CPI|PPI|Nonfarm Payrolls|Unemployment Rate|GDP|PCE|Retail Sales|ISM|JOLTS|"
                   r"Michigan Consumer Sentiment|Initial Jobless Claims|Fed Chair|Powell|FOMC (Statement|Minutes|"
                   r"Economic Projections)|Fed Interest Rate Decision|Durable Goods|Housing Starts|"
                   r"Consumer Confidence|Average Hourly Earnings|Industrial Production)\b", re.I)
SPEAKER = re.compile(r"\bSpeaks\b", re.I)
NOISE = re.compile(r"\bIndex\b|n\.s\.a|Cleveland", re.I)  # raw index levels and unadjusted variants
CURVE_TENORS = ["1 Mo", "3 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]


def _base(closes: dict[date, float], target: date) -> float | None:
    days = [d for d in closes if d <= target]
    return closes[max(days)] if days else None


def period_returns(closes: dict[date, float]) -> dict[str, float | None]:
    """Returns to the latest close for each period (price only)."""
    if len(closes) < 2:
        return {p: None for p in PERIODS}
    days = sorted(closes)
    last_d, last = days[-1], closes[days[-1]]
    bases = {
        "1D": closes[days[-2]],
        "1W": _base(closes, last_d - timedelta(days=7)),
        "1M": _base(closes, add_months(last_d, -1)),
        "3M": _base(closes, add_months(last_d, -3)),
        "YTD": _base(closes, date(last_d.year - 1, 12, 31)),
        "1Y": _base(closes, add_months(last_d, -12)),
    }
    return {p: ((last / b - 1) * 100 if b else None) for p, b in bases.items()}


def sma(closes: dict[date, float], n: int) -> float | None:
    vals = [closes[d] for d in sorted(closes)][-n:]
    return sum(vals) / n if len(vals) == n else None


def build(closes: dict[str, dict[date, float]], curve: dict[date, dict[str, float]] | None,
          fomc: list[dict] | None, events: list[dict] | None, today: date) -> dict:
    gauges = []
    for sym, label, kind in GAUGES:
        c = closes.get(sym) or {}
        if not c:
            continue
        days = sorted(c)
        r = period_returns(c)
        gauges.append({"symbol": sym, "label": label, "kind": kind, "last": c[days[-1]], "as_of": days[-1].isoformat(),
                       "change": c[days[-1]] - c[days[-2]] if len(days) > 1 else None, "returns": r,
                       "spark": [round(c[d], 4) for d in days[-63:]]})

    sectors = []
    for sym, name in SECTORS:
        c = closes.get(sym) or {}
        if not c:
            continue
        last = c[max(c)]
        s50, s200 = sma(c, 50), sma(c, 200)
        sectors.append({"symbol": sym, "name": name, "returns": period_returns(c),
                        "above_50d": s50 is not None and last > s50, "above_200d": s200 is not None and last > s200})

    def rel(a: str, b: str) -> dict[str, float | None]:
        ra, rb = period_returns(closes.get(a) or {}), period_returns(closes.get(b) or {})
        return {p: (ra[p] - rb[p] if ra[p] is not None and rb[p] is not None else None) for p in ("1M", "3M", "YTD", "1Y")}

    breadth = {
        "equal_vs_cap": rel("RSP", "SPY"),
        "small_vs_large": rel("IWM", "SPY"),
        "sectors_above_50d": sum(s["above_50d"] for s in sectors),
        "sectors_above_200d": sum(s["above_200d"] for s in sectors),
        "sectors": len(sectors),
    }

    yc = None
    if curve:
        days = sorted(curve)
        latest = days[-1]
        def at(target):
            d = max((x for x in days if x <= target), default=None)
            return (d, curve[d]) if d else None
        rows = {"today": (latest, curve[latest]), "1 month ago": at(add_months(latest, -1)), "1 year ago": at(add_months(latest, -12))}
        lines = [{"label": k, "date": v[0].isoformat(), "points": [{"tenor": t, "yield": v[1].get(t)} for t in CURVE_TENORS]}
                 for k, v in rows.items() if v]
        cur = curve[latest]
        spread = lambda a, b: (cur[a] - cur[b]) if cur.get(a) is not None and cur.get(b) is not None else None  # noqa: E731
        yc = {"as_of": latest.isoformat(), "lines": lines,
              "spread_10y_2y": spread("10 Yr", "2 Yr"), "spread_10y_3m": spread("10 Yr", "3 Mo")}

    calendar = None
    if events is not None or fomc is not None:
        seen, upcoming = set(), []
        for e in events or []:
            name = e["event"] or ""
            if not MAJOR.search(name) or NOISE.search(name) or (SPEAKER.search(name) and not re.search(r"Powell|Fed Chair", name)):
                continue
            key = (e["date"], e["time_et"], name, e["consensus"], e["previous"])
            if key not in seen:  # Nasdaq lists some releases twice
                seen.add(key)
                upcoming.append(e)
        calendar = {
            "fomc": [m for m in (fomc or []) if m["date"] >= today.isoformat()][:4],
            "events": upcoming,
            "all_events": [e for e in events or [] if not NOISE.search(e["event"] or "")],
            "all_count": len(events or []),
        }

    return {"as_of": today.isoformat(), "gauges": gauges, "sectors": sectors, "periods": PERIODS,
            "breadth": breadth, "yield_curve": yc, "calendar": calendar}
