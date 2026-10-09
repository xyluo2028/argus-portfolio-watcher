"""Research calculations for one company: quality scores (Piotroski F, Altman Z), an insider-trading
summary, valuation bands from ratio history, and a keyword-based tone for headlines.

Pure functions over plain data; argus.app gathers the inputs.
"""

from __future__ import annotations

import re
from datetime import date
from statistics import median

# -- statements helpers ------------------------------------------------------------------------

def _row(stmt: dict, *names: str, i: int = 0) -> float | None:
    """Value of the first row name present, for year index i (0 = latest)."""
    for n in names:
        vals = stmt.get(n)
        if vals and len(vals) > i and vals[i] is not None:
            return vals[i]
    return None


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


TOTAL_ASSETS = ("Total Assets",)
NET_INCOME = ("Net Income", "Net Income Common Stockholders")
CFO = ("Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
LT_DEBT = ("Long Term Debt", "Long Term Debt And Capital Lease Obligation")
CUR_ASSETS = ("Current Assets",)
CUR_LIAB = ("Current Liabilities",)
SHARES = ("Ordinary Shares Number", "Share Issued")
REVENUE = ("Total Revenue", "Operating Revenue")
GROSS = ("Gross Profit",)


def piotroski(st: dict) -> dict:
    """Piotroski F-score (0-9) from the two latest fiscal years. Each test passes, fails, or is
    unknown when a line is missing; the score counts passes over the known tests."""
    bs, inc, cf = st.get("balance", {}), st.get("income", {}), st.get("cashflow", {})
    if len(st.get("years", [])) < 2:
        return {"available": False, "reason": "Needs two annual reports."}

    def roa(i):
        return _div(_row(inc, *NET_INCOME, i=i), _row(bs, *TOTAL_ASSETS, i=i))

    def lev(i):
        return _div(_row(bs, *LT_DEBT, i=i) or 0.0, _row(bs, *TOTAL_ASSETS, i=i))

    def cur(i):
        return _div(_row(bs, *CUR_ASSETS, i=i), _row(bs, *CUR_LIAB, i=i))

    def gm(i):
        return _div(_row(inc, *GROSS, i=i), _row(inc, *REVENUE, i=i))

    def turn(i):
        return _div(_row(inc, *REVENUE, i=i), _row(bs, *TOTAL_ASSETS, i=i))

    ni, cfo, assets = _row(inc, *NET_INCOME), _row(cf, *CFO), _row(bs, *TOTAL_ASSETS)
    sh0, sh1 = _row(bs, *SHARES, i=0), _row(bs, *SHARES, i=1)

    def test(name, group, a, b, op):
        ok = None if a is None or b is None else op(a, b)
        return {"test": name, "group": group, "pass": ok}

    tests = [
        test("Positive net income (ROA > 0)", "Profitability", roa(0), 0, lambda a, b: a > b),
        test("Positive operating cash flow", "Profitability", cfo, 0, lambda a, b: a > b),
        test("ROA improved", "Profitability", roa(0), roa(1), lambda a, b: a > b),
        test("Cash flow exceeds net income (quality of earnings)", "Profitability", _div(cfo, assets), roa(0), lambda a, b: a > b),
        test("Long-term debt / assets fell", "Leverage & liquidity", lev(0), lev(1), lambda a, b: a < b),
        test("Current ratio improved", "Leverage & liquidity", cur(0), cur(1), lambda a, b: a > b),
        test("No new shares issued", "Leverage & liquidity", sh0, sh1, lambda a, b: a <= b * 1.005),
        test("Gross margin improved", "Efficiency", gm(0), gm(1), lambda a, b: a > b),
        test("Asset turnover improved", "Efficiency", turn(0), turn(1), lambda a, b: a > b),
    ]
    known = [t for t in tests if t["pass"] is not None]
    score = sum(1 for t in known if t["pass"])
    label = "strong" if score >= 7 else "weak" if score <= 3 else "average"
    return {"available": bool(known), "score": score, "out_of": len(known), "label": label, "tests": tests,
            "fiscal_years": st["years"][:2]}


def altman_z(st: dict, market_cap: float | None, sector: str | None = None) -> dict:
    """Original Altman Z for public companies; zones: >2.99 safe, 1.81-2.99 grey, <1.81 distress.
    Not meaningful for banks and insurers (their balance sheets don't fit the model)."""
    bs, inc = st.get("balance", {}), st.get("income", {})
    ta = _row(bs, *TOTAL_ASSETS)
    wc = _row(bs, "Working Capital")
    if wc is None and _row(bs, *CUR_ASSETS) is not None and _row(bs, *CUR_LIAB) is not None:
        wc = _row(bs, *CUR_ASSETS) - _row(bs, *CUR_LIAB)
    re_ = _row(bs, "Retained Earnings")
    ebit = _row(inc, "EBIT", "Operating Income")
    tl = _row(bs, "Total Liabilities Net Minority Interest", "Total Liabilities")
    sales = _row(inc, *REVENUE)
    parts = {"wc_ta": _div(wc, ta), "re_ta": _div(re_, ta), "ebit_ta": _div(ebit, ta),
             "mve_tl": _div(market_cap, tl), "sales_ta": _div(sales, ta)}
    if any(v is None for v in parts.values()):
        return {"available": False, "reason": "Missing statement lines.", "parts": parts}
    z = 1.2 * parts["wc_ta"] + 1.4 * parts["re_ta"] + 3.3 * parts["ebit_ta"] + 0.6 * parts["mve_tl"] + 1.0 * parts["sales_ta"]
    zone = "safe" if z > 2.99 else "grey" if z >= 1.81 else "distress"
    return {"available": True, "z": z, "zone": zone, "parts": parts,
            "caveat": "Not designed for financial companies." if sector in ("Financial Services", "Financials") else None}


# -- insiders ----------------------------------------------------------------------------------

CODES = {"P": "Buy", "S": "Sale", "A": "Award", "M": "Option exercise", "F": "Tax withholding", "G": "Gift",
         "D": "Disposition to issuer", "C": "Conversion", "X": "Option exercise", "J": "Other"}


def insider_summary(rows: list[dict], months: int = 12, today: date | None = None) -> dict:
    """Open-market buys and sales (codes P and S) over the window; awards, exercises, tax withholding
    and gifts are listed but don't count as conviction."""
    from argus.services.dividends import add_months

    cutoff = add_months(today or date.today(), -months)
    recent = [r for r in rows if r.get("transactionDate") and date.fromisoformat(r["transactionDate"]) >= cutoff]
    def value(r):
        return abs(r.get("change") or 0) * (r.get("transactionPrice") or 0)
    buys = [r for r in recent if r.get("transactionCode") == "P"]
    sells = [r for r in recent if r.get("transactionCode") == "S"]
    latest = sorted(recent, key=lambda r: (r.get("transactionDate") or "", r.get("filingDate") or ""), reverse=True)[:15]
    return {
        "since": cutoff.isoformat(),
        "buy_count": len(buys), "buy_value": sum(map(value, buys)), "buyers": len({r.get("name") for r in buys}),
        "sell_count": len(sells), "sell_value": sum(map(value, sells)), "sellers": len({r.get("name") for r in sells}),
        "recent": [{"date": r.get("transactionDate"), "name": r.get("name"), "code": r.get("transactionCode"),
                    "kind": CODES.get(r.get("transactionCode") or "", r.get("transactionCode")),
                    "shares": r.get("change"), "price": r.get("transactionPrice"), "value": value(r) or None,
                    "derivative": bool(r.get("isDerivative"))} for r in latest],
    }


# -- valuation bands ---------------------------------------------------------------------------

BAND_RATIOS = {"peTTM": "P/E", "psTTM": "P/S", "pb": "P/B", "evEbitdaTTM": "EV/EBITDA"}


def valuation_bands(series: dict[str, list[dict]], current: dict[str, float | None], years: int = 5,
                    today: date | None = None) -> list[dict]:
    """Quarter-end history of each ratio over `years`, with min / quartiles / max and where today's
    value sits. Negative values (losses) are left out of the bands."""
    today = today or date.today()
    start = date(today.year - years, today.month, 1)
    out = []
    for key, label in BAND_RATIOS.items():
        hist = sorted((date.fromisoformat(x["period"]), x["v"]) for x in series.get(key) or []
                      if x.get("v") is not None and date.fromisoformat(x["period"]) >= start)
        vals = sorted(v for _, v in hist if v > 0)
        if len(vals) < 4:
            continue
        q = lambda p: vals[min(len(vals) - 1, max(0, round(p * (len(vals) - 1))))]  # noqa: E731
        cur = current.get(key)
        rank = None if cur is None or cur <= 0 else sum(1 for v in vals if v <= cur) / len(vals) * 100
        out.append({"key": key, "label": label, "current": cur, "min": vals[0], "p25": q(0.25), "median": median(vals),
                    "p75": q(0.75), "max": vals[-1], "percentile": rank, "points": len(vals),
                    "history": [{"date": d.isoformat(), "v": v} for d, v in hist]})
    return out


# -- headline tone -----------------------------------------------------------------------------

POSITIVE = set("""beat beats beating surge surges surged soar soars soared jump jumps jumped rally rallies rallied gain gains
gained upgrade upgrades upgraded raise raises raised record strong stronger growth outperform outperforms bullish
boost boosts boosted expand expands expansion win wins won approval approved partnership breakthrough exceeds
exceeded tops topped rebound rebounds rebounded profit profitable buyback dividend hike optimism optimistic
accelerate accelerates momentum upbeat""".split())
NEGATIVE = set("""miss misses missed plunge plunges plunged drop drops dropped fall falls fell slump slumps slumped
downgrade downgrades downgraded cut cuts weak weaker loss losses lawsuit sue sued probe investigation recall
bearish selloff sell-off warning warns warned layoff layoffs decline declines declined delay delays delayed fraud
bankruptcy halt halted underperform slowdown slows slowing concern concerns risk risks tumble tumbles tumbled
crash crashes sink sinks sank short-seller subpoena fine fined antitrust""".split())
WORD = re.compile(r"[a-z][a-z\-]+")


def tone(text: str) -> dict:
    """Count of finance words that usually read positive or negative. Crude by design: a hint for
    scanning headlines, not a judgment."""
    words = WORD.findall((text or "").lower())
    pos = sum(1 for w in words if w in POSITIVE)
    neg = sum(1 for w in words if w in NEGATIVE)
    score = 0.0 if pos + neg == 0 else (pos - neg) / (pos + neg)
    label = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
    return {"score": score, "label": label, "positive": pos, "negative": neg}
