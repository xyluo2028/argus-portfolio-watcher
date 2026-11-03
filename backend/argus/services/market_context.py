"""Market context: the big gauges (indices, volatility, rates, USD/JPY, oil, gold, bitcoin), a fear &
greed meter, a sector heatmap, market breadth, the Treasury yield curve and the US economic calendar.

Breadth counts the 500 largest US-listed stocks (from the screener's universe, close to the S&P 500):
advancers vs decliners, above/below the 50- and 200-day averages, new 52-week highs and lows. Proxies
sit beside it: equal- vs cap-weighted S&P (RSP vs SPY), small vs large caps (IWM vs SPY), sectors
above their averages.

Fear & greed follows CNN's recipe with free data: seven readings, each scored 0 (fear) to 100 (greed),
averaged. Readings with a history are scored by where today falls in the last year (a percentile);
the two that come from today's breadth snapshot are shares (highs among highs + lows, stocks above
their 50-day average). CNN's put/call ratio is replaced by the VIX term structure (VIX ÷ VIX3M).
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from argus.market_calendar import session_date, sessions_between
from argus.services.dividends import add_months

NY, LONDON = ZoneInfo("America/New_York"), ZoneInfo("Europe/London")
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
FEAR_GREED = ["^VIX3M", "TLT", "HYG", "LQD"]  # with ^GSPC, ^VIX, SPY from the lists above
ALL_SYMBOLS = sorted({s for s, *_ in GAUGES} | {s for s, _ in SECTORS} | set(BREADTH) | set(FEAR_GREED))
HISTORY = "2y"  # a year of 125-day averages to rank today's reading against
BREADTH_UNIVERSE = 500
# Fields for the breadth snapshot (Yahoo's batch quote)
BREADTH_FIELDS = ("regularMarketPrice,regularMarketPreviousClose,regularMarketDayHigh,regularMarketDayLow,"
                  "fiftyDayAverage,twoHundredDayAverage,fiftyTwoWeekHigh,fiftyTwoWeekLow,regularMarketTime")
# The gauges' last price and previous close (Yahoo's batch quote). Daily bars alone go wrong for "1D":
# Yahoo sometimes returns a null close for a past session, and for futures, FX and crypto the bar for
# "today" holds the overnight price while the settle it moved from is gone.
QUOTE_FIELDS = "regularMarketPrice,regularMarketPreviousClose,regularMarketTime,quoteType"
FG_LABELS = [(25, "Extreme fear"), (45, "Fear"), (55, "Neutral"), (75, "Greed"), (101, "Extreme greed")]

PERIODS = ["1D", "1W", "1M", "3M", "YTD", "1Y"]
# Releases that move markets, matched as whole words. Fed speakers are left out except the Chair.
MAJOR = re.compile(r"\b(CPI|PPI|Nonfarm Payrolls|Unemployment Rate|GDP|PCE|Retail Sales|ISM|JOLTS|"
                   r"Michigan Consumer Sentiment|Initial Jobless Claims|Fed Chair|Powell|FOMC (Statement|Minutes|"
                   r"Economic Projections)|Fed Interest Rate Decision|Durable Goods|Housing Starts|"
                   r"Consumer Confidence|Average Hourly Earnings|Industrial Production|Employment Cost Index)\b", re.I)
SPEAKER = re.compile(r"\bSpeaks\b", re.I)
NOISE = re.compile(r"n\.s\.a|Cleveland", re.I)  # unadjusted and alternative variants
LEVEL = re.compile(r"\bIndex\b", re.I)  # mostly raw index levels ("CPI Index, s.a" 336.30)...
# ...except these, which are reported as % changes: the Fed's PCE gauge (m/m, y/y), ECI and the GDP deflator.
KEEP = re.compile(r"\b(PCE Price Index|Employment Cost Index|GDP Price Index)\b", re.I)
# The GDP report's price figures are quarterly annualized, unlike the monthly PCE release's.
QOQ_ANN = re.compile(r"^((Core )?PCE Prices|GDP Price Index)$", re.I)
CURVE_TENORS = ["1 Mo", "3 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]


def _noise(name: str) -> bool:
    return bool(NOISE.search(name) or (LEVEL.search(name) and not KEEP.search(name)))


def _label(e: dict) -> dict:
    name = (e["event"] or "").strip()
    return {**e, "event": f"{name} (QoQ ann.)"} if QOQ_ANN.match(name) else e


def _weekday(d: date, step: int) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=step)
    return d


def quote_sessions(row: dict) -> tuple[date, date] | None:
    """The session a quote's price belongs to and the one before it, whose close is the quote's
    previous close. Stocks, ETFs and indices follow the NYSE calendar; futures trade from 6 pm New
    York time for the next day's session; FX follows Yahoo's London day; crypto trades every day."""
    t = row.get("regularMarketTime")
    if not isinstance(t, (int, float)):
        return None
    ts = datetime.fromtimestamp(t, UTC)
    kind = row.get("quoteType")
    if kind == "CRYPTOCURRENCY":
        return ts.date(), ts.date() - timedelta(days=1)
    if kind in ("FUTURE", "CURRENCY"):
        if kind == "FUTURE":
            local = ts.astimezone(NY)
            d = local.date() + timedelta(days=local.hour >= 18)
        else:
            d = ts.astimezone(LONDON).date()
        d = _weekday(d, 1)
        return d, _weekday(d - timedelta(days=1), -1)
    d = session_date(ts)
    before = sessions_between(d - timedelta(days=10), d - timedelta(days=1))
    return (d, before[-1]) if before else None


def with_quote(closes: dict[date, float], row: dict | None) -> dict[date, float]:
    """Daily closes ending with the quote: its price on its session and its previous close on the
    session before, replacing whatever the bars hold there (or fill in when a bar is missing)."""
    price = _num((row or {}).get("regularMarketPrice"))
    sessions = quote_sessions(row) if price else None
    if not sessions or (closes and sessions[0] < max(closes) - timedelta(days=5)):  # a stale quote
        return closes
    d, before = sessions
    out = {k: v for k, v in closes.items() if k <= before}
    prev = _num(row.get("regularMarketPreviousClose"))
    if prev:
        out[before] = prev
    out[d] = price
    return out


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


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and v == v and v > 0 else None


def stock_breadth(rows: list[dict]) -> dict | None:
    """Counts over Yahoo quote rows (largest company first). A new 52-week high is a session high at
    the 52-week high; the averages are Yahoo's 50- and 200-day averages of the close."""
    n = adv = dec = 0
    above = {50: 0, 200: 0}
    have = {50: 0, 200: 0}
    highs, lows, seen = [], [], 0
    last_t = None
    for r in rows:
        price, prev = _num(r.get("regularMarketPrice")), _num(r.get("regularMarketPreviousClose"))
        if not price:
            continue
        n += 1
        if prev:
            adv += price > prev
            dec += price < prev
        for days, key in ((50, "fiftyDayAverage"), (200, "twoHundredDayAverage")):
            avg = _num(r.get(key))
            if avg:
                have[days] += 1
                above[days] += price > avg
        hi52, lo52 = _num(r.get("fiftyTwoWeekHigh")), _num(r.get("fiftyTwoWeekLow"))
        day_hi, day_lo = _num(r.get("regularMarketDayHigh")) or price, _num(r.get("regularMarketDayLow")) or price
        if hi52 and lo52:
            seen += 1
            if day_hi >= hi52 * 0.9995:
                highs.append(r["symbol"])
            elif day_lo <= lo52 * 1.0005:
                lows.append(r["symbol"])
        t = r.get("regularMarketTime")
        if isinstance(t, (int, float)) and (last_t is None or t > last_t):
            last_t = t
    if not n:
        return None
    share = lambda k, of: k / of * 100 if of else None  # noqa: E731
    return {
        "count": n,
        "as_of": datetime.fromtimestamp(last_t, UTC).isoformat() if last_t else None,
        "advancers": adv, "decliners": dec, "unchanged": n - adv - dec,
        "above_50d": above[50], "below_50d": have[50] - above[50], "pct_above_50d": share(above[50], have[50]),
        "above_200d": above[200], "below_200d": have[200] - above[200], "pct_above_200d": share(above[200], have[200]),
        "new_highs": len(highs), "new_lows": len(lows),
        "pct_new_highs": share(len(highs), seen), "pct_new_lows": share(len(lows), seen),
        "highs": highs[:12], "lows": lows[:12],
    }


def _series(c: dict[date, float]) -> tuple[list[date], list[float]]:
    days = sorted(c)
    return days, [c[d] for d in days]


def _rank(values: list[float], window: int = 252) -> float | None:
    """Where the last value falls among the last `window` (0-100, ties count half)."""
    hist = values[-window:]
    if len(hist) < 60:
        return None
    cur = hist[-1]
    return (sum(v < cur for v in hist) + 0.5 * sum(v == cur for v in hist)) / len(hist) * 100


def _ratio_series(a: dict[date, float], b: dict[date, float]) -> list[float]:
    return [a[d] / b[d] for d in sorted(a.keys() & b.keys()) if b[d]]


def _vs_average(values: list[float], n: int) -> list[float]:
    """Each close vs its own trailing n-day average (as a ratio minus one)."""
    out, run = [], sum(values[:n - 1]) if len(values) >= n else 0.0
    for i in range(n - 1, len(values)):
        run += values[i]
        out.append(values[i] / (run / n) - 1)
        run -= values[i - n + 1]
    return out


def _spread_20d(a: dict[date, float], b: dict[date, float]) -> list[float]:
    """20-day return of a minus 20-day return of b, in percentage points, over their shared days."""
    days = sorted(a.keys() & b.keys())
    return [((a[d] / a[p] - 1) - (b[d] / b[p] - 1)) * 100 for p, d in zip(days, days[20:]) if a[p] and b[p]]


def fg_label(score: float) -> str:
    return next(label for top, label in FG_LABELS if score < top)


def fear_greed(closes: dict[str, dict[date, float]], breadth: dict | None) -> dict | None:
    parts: list[dict] = []

    def add(key, label, score, detail):
        if score is not None:
            parts.append({"key": key, "label": label, "score": round(score, 1), "detail": detail})

    spx = closes.get("^GSPC") or {}
    if spx:
        dev = _vs_average(_series(spx)[1], 125)
        if dev:
            add("momentum", "Market momentum", _rank(dev),
                f"S&P 500 {abs(dev[-1]) * 100:.1f}% {'above' if dev[-1] >= 0 else 'below'} its 125-day average")
    if breadth and breadth["new_highs"] + breadth["new_lows"]:
        h, lo = breadth["new_highs"], breadth["new_lows"]
        add("strength", "Price strength", h / (h + lo) * 100, f"{h} new 52-week highs vs {lo} new lows")
    if breadth and breadth["pct_above_50d"] is not None:
        add("breadth", "Price breadth", breadth["pct_above_50d"],
            f"{breadth['pct_above_50d']:.0f}% of the {breadth['count']} largest stocks above their 50-day average")
    vix = closes.get("^VIX") or {}
    if vix:
        dev = _vs_average(_series(vix)[1], 50)
        r = _rank(dev)
        if r is not None:
            add("volatility", "Volatility", 100 - r,
                f"VIX {_series(vix)[1][-1]:.1f}, {abs(dev[-1]) * 100:.0f}% {'above' if dev[-1] >= 0 else 'below'} its 50-day average")
    term = _ratio_series(vix, closes.get("^VIX3M") or {})
    r = _rank(term)
    if r is not None:
        add("term", "Volatility term structure", 100 - r,
            f"VIX ÷ 3-month VIX {term[-1]:.2f}" + (" (inverted: near-term fear)" if term[-1] > 1 else ""))
    for key, label, a, b, what in (("safe_haven", "Safe-haven demand", "SPY", "TLT", "Stocks vs Treasuries"),
                                   ("junk", "Junk bond demand", "HYG", "LQD", "Junk vs investment-grade bonds")):
        sp = _spread_20d(closes.get(a) or {}, closes.get(b) or {})
        r = _rank(sp)
        if r is not None:
            add(key, label, r, f"{what} {'+' if sp[-1] >= 0 else '−'}{abs(sp[-1]):.1f} pp over 20 days")
    if not parts:
        return None
    score = sum(p["score"] for p in parts) / len(parts)
    for p in parts:
        p["rating"] = fg_label(p["score"])
    return {"score": round(score, 1), "rating": fg_label(score), "components": parts}


def build(closes: dict[str, dict[date, float]], curve: dict[date, dict[str, float]] | None,
          fomc: list[dict] | None, events: list[dict] | None, today: date, stocks: dict | None = None,
          quotes: list[dict] | None = None) -> dict:
    rows = {r.get("symbol"): r for r in quotes or []}
    closes = {s: with_quote(c, rows.get(s)) for s, c in closes.items()}
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
        "stocks": stocks,
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
        seen, upcoming, all_count = set(), [], len(events or [])
        events = [_label(e) for e in events or [] if not _noise(e["event"] or "")] if events is not None else None
        for e in events or []:
            name = e["event"] or ""
            if not MAJOR.search(name) or (SPEAKER.search(name) and not re.search(r"Powell|Fed Chair", name)):
                continue
            key = (e["date"], e["time_et"], name, e["consensus"], e["previous"])
            if key not in seen:  # Nasdaq lists some releases twice
                seen.add(key)
                upcoming.append(e)
        calendar = {
            "fomc": [m for m in (fomc or []) if m["date"] >= today.isoformat()][:4],
            "events": upcoming,
            "all_events": events or [],
            "all_count": all_count,
        }

    return {"as_of": today.isoformat(), "gauges": gauges, "sectors": sectors, "periods": PERIODS,
            "breadth": breadth, "fear_greed": fear_greed(closes, stocks), "yield_curve": yc, "calendar": calendar}
