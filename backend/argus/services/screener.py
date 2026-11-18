"""Screener over the US-listed universe, built on SEC XBRL "frames" (one fact per company per period)
plus a Yahoo batch quote for price, market cap and exchange.

Fundamentals are the latest full calendar year (with the year before for growth) and the most recent
quarter-end balance sheet each company filed. Companies whose fiscal year doesn't end near December
are placed in the calendar year their fiscal year mostly covers (SEC's own alignment). On top of the
year, quarterly frames give each company's latest quarter (revenue growth against the same quarter a
year earlier) and trailing-twelve-month revenue, operating income and net income, as the year plus
this year's quarters minus the same quarters a year earlier. The universe is rebuilt weekly in the
background; prices refresh every few hours.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from argus.providers.sec_edgar import REVENUE_FALLBACK_TAGS, REVENUE_TAGS, STALE_QUARTER_DAYS

log = logging.getLogger("argus.screener")

# The statements' revenue tags plus ones that may be a component; safe here since a screen takes the largest.
REVENUE = (*REVENUE_TAGS, *REVENUE_FALLBACK_TAGS,
           "OperatingLeasesIncomeStatementLeaseRevenue", "RevenuesNetOfInterestExpense")
# Banks rarely tag total revenue: it is net interest income plus noninterest income.
BANK_REVENUE = ("InterestIncomeExpenseNet", "NoninterestIncome")
ANNUAL = {"net_income": ("NetIncomeLoss",), "operating_income": ("OperatingIncomeLoss",),
          "gross_profit": ("GrossProfit",), "cfo": ("NetCashProvidedByUsedInOperatingActivities",),
          "capex": ("PaymentsToAcquirePropertyPlantAndEquipment",)}
INSTANT = {"assets": "Assets", "liabilities": "Liabilities", "equity": "StockholdersEquity",
           "current_assets": "AssetsCurrent", "current_liabilities": "LiabilitiesCurrent",
           "cash": "CashAndCashEquivalentsAtCarryingValue", "long_term_debt": "LongTermDebtNoncurrent"}
OTC_CODES = {"PNK", "OQX", "OQB", "OTC", "OBB", "OEM", "OGM"}  # Yahoo exchange codes for OTC markets
QUARTERLY = ("revenue", "operating_income", "net_income")  # the flows summed into TTM figures
FUNDAMENTALS_MAX_AGE_S = 7 * 24 * 3600
PRICES_MAX_AGE_S = 4 * 3600

# Fields a screen can filter or sort on, with a label and unit for the UI.
FIELDS = {
    "market_cap": ("Market cap", "$"), "price": ("Price", "$"),
    "revenue": ("Revenue", "$"), "revenue_growth_pct": ("Revenue growth", "%"),
    "revenue_growth_q_yoy_pct": ("Revenue growth", "%"),
    "net_income": ("Net income", "$"), "earnings_growth_pct": ("Earnings growth", "%"),
    "gross_margin_pct": ("Gross margin", "%"), "operating_margin_pct": ("Operating margin", "%"),
    "net_margin_pct": ("Net margin", "%"), "fcf_margin_pct": ("FCF margin", "%"), "fcf_yield_pct": ("FCF yield", "%"),
    "operating_margin_ttm_pct": ("Operating margin TTM", "%"),
    "pe": ("P/E", "x"), "pe_ttm": ("P/E TTM", "x"), "ps": ("P/S", "x"), "pb": ("P/B", "x"),
    "roe_pct": ("ROE", "%"), "roe_ttm_pct": ("ROE TTM", "%"), "roa_pct": ("ROA", "%"), "debt_to_equity": ("Liabilities / equity", "x"),
    "current_ratio": ("Current ratio", "x"),
}
# The period each field covers: the calendar-aligned fiscal year, the latest quarter, the trailing
# twelve months to it, or the latest balance sheet (ROE/ROA put a year's income over it). Shown in the
# table header so a FY figure is never read as current.
PERIODS = {"revenue": "fy", "revenue_growth_pct": "fy", "net_income": "fy", "earnings_growth_pct": "fy",
           "gross_margin_pct": "fy", "operating_margin_pct": "fy", "net_margin_pct": "fy", "fcf_margin_pct": "fy",
           "fcf_yield_pct": "fy", "pe": "fy", "ps": "fy", "roe_pct": "fy", "roa_pct": "fy",
           "revenue_growth_q_yoy_pct": "quarter", "operating_margin_ttm_pct": "ttm", "pe_ttm": "ttm", "roe_ttm_pct": "ttm",
           "pb": "mrq", "debt_to_equity": "mrq", "current_ratio": "mrq"}
# Withheld from a row whose latest quarter is stale (see screen): figures that would pass for current.
QUARTER_FIGURES = ("revenue_growth_q_yoy_pct", "revenue_ttm", "net_income_ttm", "operating_margin_ttm_pct",
                   "roe_ttm_pct", "pe_ttm")


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def _pct(a, b):
    v = _div(a, b)
    return v * 100 if v is not None else None


def _growth(now, before):
    return (now / before - 1) * 100 if now is not None and before not in (None, 0) and before > 0 else None


def _plausible_income(income, revenue):
    """Net income, or None when it is under 0.1% of revenue in size. SEC frames serve each company's
    latest-filed fact, and for NetIncomeLoss that is often the proxy statement's pay-versus-performance
    table, tagged in the filer's presentation units (thousands or millions) as if they were dollars:
    a figure 1000x or 1e6x too small. The frames API doesn't say which filing a fact came from, so
    reject on scale; a genuine near-breakeven year loses its (meaningless anyway) P/E and growth."""
    if income is not None and revenue and abs(income) < abs(revenue) / 1000:
        return None
    return income


def _quarter_label(period: str) -> str:
    """"CY2026Q3" -> "Q3 2026"."""
    return f"{period[6:]} {period[2:6]}"


def _quarter_end(period: str) -> str:
    """"CY2026Q3" -> "2026-09-30", for a fact whose frame row carries no end date."""
    y, q = int(period[2:6]), int(period[7:])
    return (date(y + q // 4, q % 4 * 3 + 1, 1) - timedelta(days=1)).isoformat()


def _closing_quarter(fy_end: str | None, fiscal_year: int) -> tuple[int, int]:
    """The calendar quarter a fiscal year's last quarter is aligned to: the one whose end is nearest the
    fiscal year's end (a year to 1 Feb closes in Q4, one to 28 Feb in Q1, one to 27 Jun in Q2)."""
    if not fy_end:
        return fiscal_year, 4
    d = date.fromisoformat(fy_end)
    ends = [(y, q, date(y, 3 * q, 30 if q in (2, 3) else 31)) for y in (d.year - 1, d.year) for q in (1, 2, 3, 4)]
    y, q, _ = min(ends, key=lambda e: abs((e[2] - d).days))
    return y, q


def latest_quarters(frames: dict[str, dict[str, dict[int, float]]], periods: list[str], fiscal_year: int,
                    fy_end: dict[int, str] | None = None, ends: dict[str, dict[int, str]] | None = None) -> dict[int, dict]:
    """Each company's latest quarter and what its TTM flows add to the fiscal year. `frames`:
    {concept: {"CY2026Q3": {cik: value}}} for the quarters in `periods` (newest first, calendar-aligned
    like the annual frames) and the same quarters a year earlier. The latest quarter is the newest one
    with revenue. TTM to it is the fiscal year plus the quarters since the year closed minus the same
    quarters a year before, every one of them needed (so at most len(periods) of them); when the latest
    quarter closes the year, it is the year itself. The year is added in build_rows, once it is checked.
    `revenue_q_max` (the largest quarter of the fiscal year) and `revenue_q_max_ttm` (of the TTM window)
    are floors for the year and the TTM revenue. `ends`: {period: {cik: the revenue fact's end date}},
    so `end` is the company's own quarter end (a fiscal quarter can end weeks off the calendar one)."""
    rev, fy_end, ends = frames.get("revenue", {}), fy_end or {}, ends or {}
    out: dict[int, dict] = {}
    for cik in set().union(*(rev.get(p, {}).keys() for p in periods)):
        period = next(p for p in periods if cik in rev.get(p, {}))
        y, q = int(period[2:6]), int(period[7:])
        row = {"period": period, "end": ends.get(period, {}).get(cik) or _quarter_end(period),
               "revenue": rev[period][cik], "revenue_prev": rev.get(f"CY{y - 1}Q{q}", {}).get(cik)}
        cy, cq = _closing_quarter(fy_end.get(cik), fiscal_year)
        since = (y * 4 + q) - (cy * 4 + cq)  # quarters reported since the fiscal year closed
        in_year = [v for p, by_cik in rev.items() if p.startswith(f"CY{fiscal_year}Q") and (v := by_cik.get(cik)) is not None]
        if in_year:
            row["revenue_q_max"] = max(in_year)
        row["revenue_q_max_ttm"] = rev[period][cik]
        if 0 <= since <= len(periods):
            span = [(y * 4 + q - 1 - j) for j in range(since)]  # quarter indices, newest first
            span = [(f"CY{i // 4}Q{i % 4 + 1}", f"CY{i // 4 - 1}Q{i % 4 + 1}") for i in span]
            for concept in QUARTERLY:
                f = frames.get(concept, {})
                vals = [(f.get(now, {}).get(cik), f.get(then, {}).get(cik)) for now, then in span]
                if all(a is not None and b is not None for a, b in vals):
                    row[f"{concept}_delta"] = sum(a - b for a, b in vals)
                    if concept == "revenue" and vals:
                        row["revenue_q_max_ttm"] = max(a for a, _ in vals)
        out[cik] = row
    return out


def build_rows(tickers: list[dict], annual: dict[str, dict[int, float]], prior: dict[str, dict[int, float]],
               instant: dict[str, dict[int, float]], quarters: dict[int, dict] | None = None,
               fiscal_year: int | None = None, fy_end: dict[int, str] | None = None) -> list[dict]:
    """One row per company (its first-listed ticker) with any annual figure. Prices come later.
    `quarters` comes from latest_quarters; `fy_end` is the end date of each company's fiscal year."""
    quarters, fy_end = quarters or {}, fy_end or {}
    seen: set[int] = set()
    rows = []
    for t in tickers:
        cik = t["cik"]
        if cik in seen:
            continue
        seen.add(cik)
        a = {k: v.get(cik) for k, v in annual.items()}
        if a.get("revenue") is None and a.get("net_income") is None:
            continue
        p = {k: v.get(cik) for k, v in prior.items()}
        i = {k: v.get(cik) for k, v in instant.items()}
        a["net_income"] = _plausible_income(a.get("net_income"), a.get("revenue"))
        p["net_income"] = _plausible_income(p.get("net_income"), p.get("revenue") or a.get("revenue"))
        fcf = a["cfo"] - (a.get("capex") or 0) if a.get("cfo") is not None else None
        rev = a.get("revenue")
        # Profit more than twice revenue (mark-to-market gains, a mis-tagged revenue line): margins
        # and revenue multiples would mislead, so leave them out for this company.
        odd = rev is not None and a.get("net_income") is not None and abs(a["net_income"]) > 2 * abs(rev)
        lq = quarters.get(cik, {})
        # A year smaller than one of its quarters is a mis-tagged fact (FIX's Q1 2026 10-Q tagged
        # Q1 2025's revenue, operating income and gross profit as calendar 2025's, and SEC's frame
        # serves it); the lines filed with it go too.
        if rev is not None and lq.get("revenue_q_max") is not None and rev < lq["revenue_q_max"]:
            odd = True
        if odd:
            a = a | {"revenue": None, "gross_profit": None, "operating_income": None}
        ttm = {k: a[k] + lq[f"{k}_delta"] if a.get(k) is not None and f"{k}_delta" in lq else None for k in QUARTERLY}
        ttm["net_income"] = _plausible_income(ttm["net_income"], ttm["revenue"])
        if ttm["revenue"] is not None and ttm["revenue"] < (lq.get("revenue_q_max_ttm") or 0):
            odd = True  # twelve months can't be less than one of their quarters: tags mixed across periods
            ttm = dict.fromkeys(QUARTERLY)
        if ttm["revenue"] is not None and ttm["revenue"] <= 0:  # tags mixed across periods
            ttm = dict.fromkeys(QUARTERLY)
        rows.append({
            "symbol": t["ticker"], "name": t["name"], "cik": cik,
            "revenue": a.get("revenue"), "revenue_prev": p.get("revenue"), "revenue_unreliable": odd,
            "revenue_growth_pct": _growth(a.get("revenue"), p.get("revenue")),
            "net_income": a.get("net_income"), "net_income_prev": p.get("net_income"),
            "earnings_growth_pct": _growth(a.get("net_income"), p.get("net_income")),
            "gross_margin_pct": _pct(a.get("gross_profit"), a.get("revenue")),
            "operating_margin_pct": _pct(a.get("operating_income"), a.get("revenue")),
            "net_margin_pct": _pct(a.get("net_income"), a.get("revenue")),
            "fcf": fcf, "fcf_margin_pct": _pct(fcf, a.get("revenue")),
            "roe_pct": _pct(a.get("net_income"), i.get("equity")) if (i.get("equity") or 0) > 0 else None,
            "roa_pct": _pct(a.get("net_income"), i.get("assets")),
            "debt_to_equity": _div(i.get("liabilities"), i.get("equity")) if (i.get("equity") or 0) > 0 else None,
            "current_ratio": _div(i.get("current_assets"), i.get("current_liabilities")),
            "equity": i.get("equity"), "cash": i.get("cash"),
            "fiscal_year": fiscal_year, "fiscal_year_end": fy_end.get(cik),
            "latest_quarter": _quarter_label(lq["period"]) if lq else None, "quarter_end": lq.get("end"),
            "revenue_q": lq.get("revenue"), "revenue_q_prev": lq.get("revenue_prev"),
            "revenue_growth_q_yoy_pct": _growth(lq.get("revenue"), lq.get("revenue_prev")),
            "ttm_through": _quarter_label(lq["period"]) if any(v is not None for v in ttm.values()) else None,
            "revenue_ttm": ttm["revenue"], "net_income_ttm": ttm["net_income"],
            "operating_margin_ttm_pct": _pct(ttm["operating_income"], ttm["revenue"]),
            "roe_ttm_pct": _pct(ttm["net_income"], i.get("equity")) if (i.get("equity") or 0) > 0 else None,
        })
    return rows


def add_prices(rows: list[dict], quotes: dict[str, dict]) -> list[dict]:
    """Price, market cap, exchange and the valuation ratios that need them."""
    out = []
    for r in rows:
        q = quotes.get(r["symbol"]) or {}
        mcap = q.get("market_cap")
        r = r | {"price": q.get("price"), "market_cap": mcap, "exchange": q.get("exchange"),
                 "otc": q.get("exchange_code") in OTC_CODES, "quote_type": q.get("quote_type"),
                 "pe": _div(mcap, r["net_income"]) if (r.get("net_income") or 0) > 0 else None,
                 "pe_ttm": _div(mcap, r.get("net_income_ttm")) if (r.get("net_income_ttm") or 0) > 0 else None,
                 "ps": _div(mcap, r["revenue"]) if (r.get("revenue") or 0) > 0 else None,
                 "pb": _div(mcap, r["equity"]) if (r.get("equity") or 0) > 0 else None,
                 "fcf_yield_pct": _pct(r.get("fcf"), mcap)}
        out.append(r)
    return out


def with_staleness(row: dict, today: date) -> dict:
    """`quarter_stale` once the latest quarter ended more than STALE_QUARTER_DAYS ago: a newer 10-Q is due
    but SEC's XBRL frames lack it (they can lag a filing by months: D's Q2 and Q3 2026 10-Qs, filed in
    July and October, were still missing in November). Its latest-quarter and TTM figures are withheld
    so they neither pass a filter nor read as current; `latest_quarter` and `quarter_end` say why."""
    end = row.get("quarter_end")
    stale = end is not None and (today - date.fromisoformat(end)).days > STALE_QUARTER_DAYS
    return row | {"quarter_stale": stale} | (dict.fromkeys(QUARTER_FIGURES) if stale else {})


def screen(rows: list[dict], filters: dict[str, list], sort: str = "market_cap", descending: bool = True,
           limit: int = 100, include_otc: bool = False, today: date | None = None) -> dict:
    """`filters`: {field: [min, max]} (either bound may be null). Rows missing a filtered field drop out,
    as do a stale quarter's figures (see with_staleness)."""
    unknown = [f for f in [*filters, sort] if f not in FIELDS]
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
    today = today or datetime.now(UTC).date()
    hits = []
    for r in rows:
        r = with_staleness(r, today)
        if not include_otc and r.get("otc"):
            continue
        if r.get("quote_type") not in (None, "EQUITY"):
            continue
        ok = True
        for f, (lo, hi) in filters.items():
            v = r.get(f)
            if v is None or (lo is not None and v < lo) or (hi is not None and v > hi):
                ok = False
                break
        if ok:
            hits.append(r)
    hits.sort(key=lambda r: (r.get(sort) is None, -(r.get(sort) or 0) if descending else (r.get(sort) or 0)))
    return {"matches": len(hits), "rows": hits[:limit]}


class ScreenerService:
    """Builds and caches the universe (JSON under the cache dir); `screen` filters it."""

    def __init__(self, cache_dir: Path, sec, yahoo):
        self.path = cache_dir / "screener_universe.json"
        self.sec, self.yahoo = sec, yahoo
        self._mem: dict | None = None

    def load(self) -> dict | None:
        if self._mem is None and self.path.exists():
            self._mem = json.loads(self.path.read_text())
        return self._mem

    def largest(self, n: int) -> list[str]:
        """The n largest listed (not OTC) operating companies by market cap, largest first."""
        u = self.load()
        if not u:
            return []
        rows = [r for r in u["rows"] if r.get("market_cap") and not r.get("otc") and r.get("quote_type") == "EQUITY"]
        return [r["symbol"] for r in sorted(rows, key=lambda r: -r["market_cap"])[:n]]

    def status(self) -> dict:
        u = self.load()
        if not u:
            return {"built": False}
        return {"built": True, "fundamentals_at": u["fundamentals_at"], "prices_at": u.get("prices_at"),
                "fiscal_year": u["fiscal_year"], "companies": len(u["rows"]),
                "stale": time.time() - u["fundamentals_ts"] > FUNDAMENTALS_MAX_AGE_S,
                "prices_stale": time.time() - u.get("prices_ts", 0) > PRICES_MAX_AGE_S}

    def build(self, progress: Callable[[str], None] = lambda _: None, today: date | None = None) -> dict:
        """Fetch frames (about 100 SEC requests, each cached a week) and prices; save the universe."""
        today = today or datetime.now(UTC).date()
        year = today.year - 1  # the latest calendar year most companies have reported in full
        progress("SEC ticker map")
        tickers = self.sec.company_tickers()

        fy_end: dict[int, str] = {}
        q_ends: dict[str, dict[int, str]] = {}  # each quarter's revenue fact end dates

        def best(concepts: tuple[str, ...], period: str, ends: dict[int, str] | None = None) -> dict[int, float]:
            """The largest value across alternative tags: companies often tag a revenue *component*
            (e.g. contract revenue at a REIT) besides the total, and the total is never smaller."""
            out: dict[int, float] = {}
            for c in concepts:
                for cik, f in self.sec.frame(c, "USD", period).items():
                    if f["val"] is not None and (cik not in out or f["val"] > out[cik]):
                        out[cik] = f["val"]
                        if ends is not None and f.get("end"):
                            ends[cik] = f["end"]
            return out

        def revenue(period: str, ends: dict[int, str] | None = None) -> dict[int, float]:
            out = best(REVENUE, period, ends)
            nii, fees = (self.sec.frame(c, "USD", period) for c in BANK_REVENUE)
            for cik in nii.keys() & fees.keys():
                bank = (nii[cik]["val"] or 0) + (fees[cik]["val"] or 0)
                if bank > out.get(cik, 0):
                    out[cik] = bank
                    if ends is not None and nii[cik].get("end"):
                        ends[cik] = nii[cik]["end"]
            return out

        annual, prior = {}, {}
        progress(f"annual figures, calendar {year}")
        annual["revenue"] = revenue(f"CY{year}", fy_end)
        prior["revenue"] = revenue(f"CY{year - 1}")
        for k, concepts in ANNUAL.items():
            annual[k] = best(concepts, f"CY{year}")
        prior["net_income"] = best(ANNUAL["net_income"], f"CY{year - 1}")

        recent = []  # the three most recent calendar quarters, newest first ("CY2026Q3")
        y, q = today.year, (today.month - 1) // 3  # the quarter before the current one
        for _ in range(3):
            if q == 0:
                y, q = y - 1, 4
            recent.append(f"CY{y}Q{q}")
            q -= 1
        progress("latest quarters")
        # Those quarters and the same ones a year earlier: latest-quarter growth and, with the
        # year, TTM flows (any quarters of the year after `year` are among them).
        flows = {"revenue": lambda p: revenue(p, q_ends.setdefault(p, {})), "operating_income": lambda p: best(ANNUAL["operating_income"], p),
                 "net_income": lambda p: best(ANNUAL["net_income"], p)}
        periods = [*recent, *(f"CY{int(p[2:6]) - 1}{p[6:]}" for p in recent)]
        frames = {k: {p: fetch(p) for p in periods} for k, fetch in flows.items()}
        latest = latest_quarters(frames, recent, year, fy_end, q_ends)

        progress("latest balance sheets")
        quarters = [f"{p}I" for p in recent]  # their quarter-end instants
        instant: dict[str, dict[int, float]] = {}
        for k, concept in INSTANT.items():
            merged: dict[int, float] = {}
            for period in quarters:  # newest first: keep each company's latest
                for cik, f in self.sec.frame(concept, "USD", period).items():
                    merged.setdefault(cik, f["val"])
            instant[k] = merged

        rows = build_rows(tickers, annual, prior, instant, latest, year, fy_end)
        universe = {"fiscal_year": year, "fundamentals_at": datetime.now(UTC).isoformat(),
                    "fundamentals_ts": time.time(), "rows": rows}
        self._save(universe)
        return self.refresh_prices(progress)

    def refresh_prices(self, progress: Callable[[str], None] = lambda _: None) -> dict:
        u = self.load()
        if not u:
            raise RuntimeError("Build the universe first.")
        progress(f"prices for {len(u['rows'])} companies")
        quotes = self.yahoo.market_caps([r["symbol"] for r in u["rows"]])
        u = u | {"rows": add_prices(u["rows"], quotes), "prices_at": datetime.now(UTC).isoformat(), "prices_ts": time.time()}
        self._save(u)
        return self.status()

    def _save(self, universe: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(universe))
        tmp.replace(self.path)
        self._mem = universe
