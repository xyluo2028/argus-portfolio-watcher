"""Screener over the US-listed universe, built on SEC XBRL "frames" (one fact per company per period)
plus a Yahoo batch quote for price, market cap and exchange.

Fundamentals are the latest full calendar year (with the year before for growth) and the most recent
quarter-end balance sheet each company filed. Companies whose fiscal year doesn't end near December
are placed in the calendar year their fiscal year mostly covers (SEC's own alignment). The universe
is rebuilt weekly in the background; prices refresh every few hours.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

log = logging.getLogger("argus.screener")

REVENUE = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
           "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet",
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
FUNDAMENTALS_MAX_AGE_S = 7 * 24 * 3600
PRICES_MAX_AGE_S = 4 * 3600

# Fields a screen can filter or sort on, with a label and unit for the UI.
FIELDS = {
    "market_cap": ("Market cap", "$"), "price": ("Price", "$"),
    "revenue": ("Revenue", "$"), "revenue_growth_pct": ("Revenue growth", "%"),
    "net_income": ("Net income", "$"), "earnings_growth_pct": ("Earnings growth", "%"),
    "gross_margin_pct": ("Gross margin", "%"), "operating_margin_pct": ("Operating margin", "%"),
    "net_margin_pct": ("Net margin", "%"), "fcf_margin_pct": ("FCF margin", "%"), "fcf_yield_pct": ("FCF yield", "%"),
    "pe": ("P/E", "x"), "ps": ("P/S", "x"), "pb": ("P/B", "x"),
    "roe_pct": ("ROE", "%"), "roa_pct": ("ROA", "%"), "debt_to_equity": ("Liabilities / equity", "x"),
    "current_ratio": ("Current ratio", "x"),
}


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def _pct(a, b):
    v = _div(a, b)
    return v * 100 if v is not None else None


def _growth(now, before):
    return (now / before - 1) * 100 if now is not None and before not in (None, 0) and before > 0 else None


def build_rows(tickers: list[dict], annual: dict[str, dict[int, float]], prior: dict[str, dict[int, float]],
               instant: dict[str, dict[int, float]]) -> list[dict]:
    """One row per company (its first-listed ticker) with any annual figure. Prices come later."""
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
        fcf = a["cfo"] - (a.get("capex") or 0) if a.get("cfo") is not None else None
        rev = a.get("revenue")
        # Profit more than twice revenue (mark-to-market gains, a mis-tagged revenue line): margins
        # and revenue multiples would mislead, so leave them out for this company.
        odd = rev is not None and a.get("net_income") is not None and abs(a["net_income"]) > 2 * abs(rev)
        if odd:
            a = a | {"revenue": None, "gross_profit": None, "operating_income": None}
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
                 "ps": _div(mcap, r["revenue"]) if (r.get("revenue") or 0) > 0 else None,
                 "pb": _div(mcap, r["equity"]) if (r.get("equity") or 0) > 0 else None,
                 "fcf_yield_pct": _pct(r.get("fcf"), mcap)}
        out.append(r)
    return out


def screen(rows: list[dict], filters: dict[str, list], sort: str = "market_cap", descending: bool = True,
           limit: int = 100, include_otc: bool = False) -> dict:
    """`filters`: {field: [min, max]} (either bound may be null). Rows missing a filtered field drop out."""
    unknown = [f for f in [*filters, sort] if f not in FIELDS]
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(unknown)}")
    hits = []
    for r in rows:
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

    def status(self) -> dict:
        u = self.load()
        if not u:
            return {"built": False}
        return {"built": True, "fundamentals_at": u["fundamentals_at"], "prices_at": u.get("prices_at"),
                "fiscal_year": u["fiscal_year"], "companies": len(u["rows"]),
                "stale": time.time() - u["fundamentals_ts"] > FUNDAMENTALS_MAX_AGE_S,
                "prices_stale": time.time() - u.get("prices_ts", 0) > PRICES_MAX_AGE_S}

    def build(self, progress: Callable[[str], None] = lambda _: None, today: date | None = None) -> dict:
        """Fetch frames (about 40 SEC requests, each cached a week) and prices; save the universe."""
        today = today or datetime.now(UTC).date()
        year = today.year - 1  # the latest calendar year most companies have reported in full
        progress("SEC ticker map")
        tickers = self.sec.company_tickers()

        def best(concepts: tuple[str, ...], period: str) -> dict[int, float]:
            """The largest value across alternative tags: companies often tag a revenue *component*
            (e.g. contract revenue at a REIT) besides the total, and the total is never smaller."""
            out: dict[int, float] = {}
            for c in concepts:
                for cik, f in self.sec.frame(c, "USD", period).items():
                    if f["val"] is not None and (cik not in out or f["val"] > out[cik]):
                        out[cik] = f["val"]
            return out

        def revenue(period: str) -> dict[int, float]:
            out = best(REVENUE, period)
            nii, fees = (self.sec.frame(c, "USD", period) for c in BANK_REVENUE)
            for cik in nii.keys() & fees.keys():
                bank = (nii[cik]["val"] or 0) + (fees[cik]["val"] or 0)
                if bank > out.get(cik, 0):
                    out[cik] = bank
            return out

        annual, prior = {}, {}
        progress(f"annual figures, calendar {year}")
        annual["revenue"] = revenue(f"CY{year}")
        prior["revenue"] = revenue(f"CY{year - 1}")
        for k, concepts in ANNUAL.items():
            annual[k] = best(concepts, f"CY{year}")
        prior["net_income"] = best(ANNUAL["net_income"], f"CY{year - 1}")

        progress("latest balance sheets")
        quarters = []  # the three most recent quarter ends, newest first
        y, q = today.year, (today.month - 1) // 3  # the quarter before the current one
        for _ in range(3):
            if q == 0:
                y, q = y - 1, 4
            quarters.append(f"CY{y}Q{q}I")
            q -= 1
        instant: dict[str, dict[int, float]] = {}
        for k, concept in INSTANT.items():
            merged: dict[int, float] = {}
            for period in quarters:  # newest first: keep each company's latest
                for cik, f in self.sec.frame(concept, "USD", period).items():
                    merged.setdefault(cik, f["val"])
            instant[k] = merged

        rows = build_rows(tickers, annual, prior, instant)
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
