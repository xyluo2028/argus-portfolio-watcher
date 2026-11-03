"""SEC EDGAR adapter: XBRL "companyfacts" (official reported financials) and N-PORT
(a fund's complete holdings), both free.

EDGAR requires a descriptive User-Agent with contact info and allows 10 req/s.
10-Q cash-flow facts are year-to-date, and Q4 is rarely filed as a 3-month
value, so single quarters are derived by differencing cumulative periods.

N-PORT is filed monthly but only each quarter's last month is public, about 60 days
later, so holdings are 2-5 months old. Unit investment trusts (e.g. SPY, DIA) don't file it.
"""

from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path

import httpx

from argus.providers.base import ProviderError

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FRAMES_MAX_AGE_S = 7 * 24 * 3600
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
TICKERS_MAX_AGE_S = 7 * 24 * 3600
FACTS_MAX_AGE_S = 24 * 3600
FUND_TICKERS_URL = "https://www.sec.gov/files/company_tickers_mf.json"
FILINGS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
NPORT_LATEST_MAX_AGE_S = 24 * 3600
NPORT_KEEP = 500  # holdings kept per fund (by weight); the rest only count toward totals
# A 10-Q is due 40-45 days after the quarter and a 10-K 60-90 days after the year, so a latest period
# older than this means SEC's XBRL data lacks a newer report. That happens: companyfacts can lag a
# filing by months (KO's and NEE's Q2 2026 10-Qs were filed in July and still missing in October).
STALE_QUARTER_DAYS = 135
STALE_YEAR_DAYS = 365 + 100


@dataclass(frozen=True)
class Concept:
    field: str
    tags: tuple[str, ...]  # tried in order across us-gaap then ifrs-full
    additive: bool = True  # EPS is not: YTD differencing doesn't apply (see _derive_q4_eps)
    fallback: tuple[str, ...] = ()  # only fill periods the chosen tag leaves empty


# Revenue tags, shared with the screener. Revenue including assessed tax (sales taxes, VAT) is gross of
# tax, so it only counts when a company tags nothing else for the period, as Rambus and BioCryst do.
REVENUE_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet")
REVENUE_FALLBACK_TAGS = ("RevenueFromContractWithCustomerIncludingAssessedTax",)

CONCEPTS: tuple[Concept, ...] = (
    Concept("revenue", (*REVENUE_TAGS, "Revenue"), fallback=REVENUE_FALLBACK_TAGS),  # "Revenue": ifrs-full
    Concept("gross_profit", ("GrossProfit",)),
    Concept("operating_income", ("OperatingIncomeLoss", "ProfitLossFromOperatingActivities")),
    Concept("net_income", ("NetIncomeLoss", "ProfitLossAttributableToOwnersOfParent", "ProfitLoss")),
    Concept("eps_diluted", ("EarningsPerShareDiluted", "DilutedEarningsLossPerShare"), additive=False),
    Concept("operating_cash_flow", ("NetCashProvidedByUsedInOperatingActivities",
                                    "CashFlowsFromUsedInOperatingActivities")),
    Concept("capex", ("PaymentsToAcquirePropertyPlantAndEquipment",
                      "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities")),
)

# Weighted diluted share count, for a fiscal Q4 the filer tags as a 3-month period.
DILUTED_SHARES_TAGS = ("WeightedAverageNumberOfDilutedSharesOutstanding", "AdjustedWeightedAverageShares")

ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
# Financial reports. The same fact also turns up in proxy statements (DEF 14A), 8-Ks and registration
# statements filed later; those must not displace the report's copy.
REPORT_FORMS = ANNUAL_FORMS | {"10-Q", "10-Q/A", "6-K", "6-K/A", "10-KT", "10-QT"}


class SecEdgarProvider:
    name = "sec"

    def __init__(self, user_agent: str | None, cache_dir: Path | None = None, client: httpx.Client | None = None):
        self._ua = user_agent
        self._cache_dir = cache_dir
        self._client = client or httpx.Client(timeout=20.0)

    def _fetch_json(self, url: str, cache_name: str, max_age: int) -> dict:
        cache = self._cache_dir / "sec" / cache_name if self._cache_dir else None
        if cache and cache.exists() and time.time() - cache.stat().st_mtime < max_age:
            return json.loads(cache.read_text())
        if not self._ua:
            raise ProviderError("SEC EDGAR needs SEC_USER_AGENT in .env, e.g. 'argus you@example.com'.")
        try:
            r = self._client.get(url, headers={"User-Agent": self._ua, "Accept-Encoding": "gzip"})
        except httpx.HTTPError as e:
            raise ProviderError(f"sec {url}: {e}") from e
        if r.status_code == 404:
            raise ProviderError("sec: no XBRL financials for this company (ETFs and funds have none).")
        if r.status_code != 200:
            raise ProviderError(f"sec {url}: HTTP {r.status_code}")
        data = r.json()
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data))
        return data

    def _fetch_text(self, url: str, params: dict | None = None) -> str:
        if not self._ua:
            raise ProviderError("SEC EDGAR needs SEC_USER_AGENT in .env, e.g. 'argus you@example.com'.")
        try:
            r = self._client.get(url, params=params, timeout=60.0,
                                 headers={"User-Agent": self._ua, "Accept-Encoding": "gzip"})
        except httpx.HTTPError as e:
            raise ProviderError(f"sec {url}: {e}") from e
        if r.status_code != 200:
            raise ProviderError(f"sec {url}: HTTP {r.status_code}")
        return r.text

    def fund_series(self, symbol: str) -> str | None:
        """The fund series (e.g. S000006416) an ETF or mutual fund ticker belongs to."""
        doc = self._fetch_json(FUND_TICKERS_URL, "company_tickers_mf.json", TICKERS_MAX_AGE_S)
        want = symbol.upper().replace(".", "-")
        i, s = doc["fields"].index("symbol"), doc["fields"].index("seriesId")
        return next((row[s] for row in doc["data"] if str(row[i]).upper() == want), None)

    def fund_holdings(self, symbol: str) -> dict | None:
        """Complete holdings from the latest public N-PORT filing, or None if the fund files none.
        Parsed filings are cached for good (they never change); the latest-filing lookup for a day."""
        series = self.fund_series(symbol)
        if series is None:
            return None
        latest = self._cache_dir / "sec" / f"nport-latest-{series}.json" if self._cache_dir else None
        if latest and latest.exists() and time.time() - latest.stat().st_mtime < NPORT_LATEST_MAX_AGE_S:
            filing = json.loads(latest.read_text())
        else:
            atom = self._fetch_text(FILINGS_URL, {"action": "getcompany", "CIK": series, "type": "NPORT-P",
                                                  "dateb": "", "owner": "include", "count": "1", "output": "atom"})
            href = re.search(r"<filing-href>(.*?)</filing-href>", atom)
            filed = re.search(r"<filing-date>(.*?)</filing-date>", atom)
            filing = {"index": href.group(1), "filed": filed.group(1) if filed else None} if href else None
            if latest:
                latest.parent.mkdir(parents=True, exist_ok=True)
                latest.write_text(json.dumps(filing))
        if filing is None:
            return None
        folder = filing["index"].rsplit("/", 1)[0]
        parsed = self._cache_dir / "sec" / f"nport-{folder.rsplit('/', 1)[1]}.json" if self._cache_dir else None
        if parsed and parsed.exists():
            data = json.loads(parsed.read_text())
        else:
            data = parse_nport(self._fetch_text(f"{folder}/primary_doc.xml"))
            if parsed:
                parsed.write_text(json.dumps(data))
        return {"series_id": series, "filed": filing["filed"], **data}

    def cik_for(self, symbol: str) -> int | None:
        rows = self._fetch_json(TICKERS_URL, "company_tickers.json", TICKERS_MAX_AGE_S)
        want = symbol.upper().replace(".", "-")
        for row in rows.values():
            if row.get("ticker", "").upper() == want:
                return int(row["cik_str"])
        return None

    def company_tickers(self) -> list[dict]:
        """SEC's ticker map: [{"cik", "ticker", "name"}], in SEC's own order (roughly largest first).
        A company with several share classes appears once per ticker."""
        rows = self._fetch_json(TICKERS_URL, "company_tickers.json", TICKERS_MAX_AGE_S)
        return [{"cik": int(r["cik_str"]), "ticker": r["ticker"], "name": r.get("title")} for r in rows.values()]

    def frame(self, concept: str, unit: str, period: str, taxonomy: str = "us-gaap") -> dict[int, dict]:
        """One XBRL fact per company for a period ("CY2025" = a calendar year, "CY2026Q1I" = an
        instant at that quarter's end): {cik: {"val", "end", "start"?}}. Cached for a week; a period
        nobody reported yet comes back empty."""
        url = f"https://data.sec.gov/api/xbrl/frames/{taxonomy}/{concept}/{unit}/{period}.json"
        try:
            data = self._fetch_json(url, f"frames/{taxonomy}-{concept}-{unit}-{period}.json", FRAMES_MAX_AGE_S)
        except ProviderError as e:
            if "no XBRL" in str(e):  # 404: nobody has reported this concept for this period (yet)
                return {}
            raise
        return {int(r["cik"]): {"val": r["val"], "end": r.get("end"), "start": r.get("start")} for r in data.get("data", [])}

    def get_financials(self, symbol: str, period: str = "quarterly", limit: int = 8) -> dict:
        cik = self.cik_for(symbol)
        if cik is None:
            raise ProviderError(f"sec: {symbol} not found in EDGAR (ETFs and funds have no financials).")
        facts = self._fetch_json(FACTS_URL.format(cik=cik), f"CIK{cik:010d}.json", FACTS_MAX_AGE_S)
        return build_financials(facts, period=period, limit=limit)


def _pick_series(facts: dict, concept: Concept) -> tuple[list[dict], str | None]:
    """Choose the candidate tag with the most recent data.

    Filers switch tags over time (e.g. Revenues -> RevenueFromContractWith...), so
    the first tag that exists may be a stale series.
    """
    best: tuple[str, list[dict], str] | None = None
    for taxonomy in ("us-gaap", "ifrs-full"):
        tax = facts.get("facts", {}).get(taxonomy, {})
        for tag in concept.tags:
            for unit, rows in tax.get(tag, {}).get("units", {}).items():
                if not rows:
                    continue
                latest = max(r.get("end", "") for r in rows)
                if best is None or latest > best[0]:
                    best = (latest, rows, unit)
    return (best[1], best[2]) if best else ([], None)


def _duration_rows(rows: list[dict]) -> dict[tuple[date, date], tuple[float, str]]:
    """Dedupe by (start, end): financial reports over other filings, then the latest (restatements win)."""
    best: dict[tuple[date, date], tuple[float, str, tuple[bool, str]]] = {}
    for r in rows:
        if "start" not in r:
            continue
        key = (date.fromisoformat(r["start"]), date.fromisoformat(r["end"]))
        form = r.get("form", "")
        rank = (form in REPORT_FORMS, r.get("filed", ""))
        if key not in best or rank > best[key][2]:
            best[key] = (float(r["val"]), form, rank)
    return {k: (v[0], v[1]) for k, v in best.items()}


def _is_quarter(days: int) -> bool:
    return 80 <= days <= 100


def _is_year(days: int) -> bool:
    return 350 <= days <= 380


def series_for(rows: list[dict], period: str, additive: bool) -> dict[date, float]:
    durations = _duration_rows(rows)
    if period == "annual":
        return {end: v for (start, end), (v, form) in durations.items()
                if _is_year((end - start).days) and (form in ANNUAL_FORMS or not form)}

    quarters: dict[date, float] = {
        end: v for (start, end), (v, _) in durations.items() if _is_quarter((end - start).days)
    }
    if additive:
        # Cumulative facts sharing a start date: YTD(n) - YTD(n-1) is a single quarter.
        by_start: dict[date, list[tuple[date, float]]] = {}
        for (start, end), (v, _) in durations.items():
            if (end - start).days <= 380:
                by_start.setdefault(start, []).append((end, v))
        for series in by_start.values():
            series.sort()
            for (e1, v1), (e2, v2) in zip(series, series[1:]):
                if _is_quarter((e2 - e1).days) and e2 not in quarters:
                    quarters[e2] = v2 - v1
    return quarters


def freshness(latest_period: str | None, period: str = "quarterly", today: date | None = None) -> dict:
    """How old SEC's latest period is, and `stale` once a newer report should have been filed."""
    if latest_period is None:
        return {"latest_period": None, "latest_period_age_days": None, "stale": False}
    age = ((today or date.today()) - date.fromisoformat(latest_period)).days
    limit = STALE_QUARTER_DAYS if period == "quarterly" else STALE_YEAR_DAYS
    return {"latest_period": latest_period, "latest_period_age_days": age, "stale": age > limit}


def build_financials(facts: dict, period: str = "quarterly", limit: int = 8, today: date | None = None) -> dict:
    if period not in ("quarterly", "annual"):
        raise ValueError("period must be 'quarterly' or 'annual'")
    by_end: dict[date, dict] = {}
    units: dict[str, str] = {}
    for concept in CONCEPTS:
        rows, unit = _pick_series(facts, concept)
        values = series_for(rows, period, concept.additive)
        if concept.fallback:
            spare, spare_unit = _pick_series(facts, Concept(concept.field, concept.fallback, concept.additive))
            if unit is None or spare_unit == unit:
                unit = unit or spare_unit
                values = series_for(spare, period, concept.additive) | values
        if not values:
            continue
        units[concept.field] = unit or ""
        for end, v in values.items():
            by_end.setdefault(end, {"period_end": end.isoformat()})[concept.field] = v
    if period == "quarterly":
        _derive_q4_eps(facts, by_end, units)
    periods = [by_end[e] for e in sorted(by_end, reverse=True)[:limit]]
    for p in periods:
        if p.get("operating_cash_flow") is not None and p.get("capex") is not None:
            p["free_cash_flow"] = p["operating_cash_flow"] - p["capex"]
        if p.get("revenue"):
            for f, out in (("gross_profit", "gross_margin_pct"), ("operating_income", "operating_margin_pct"),
                           ("net_income", "net_margin_pct")):
                if p.get(f) is not None:
                    p[out] = p[f] / p["revenue"] * 100
    return {"company": facts.get("entityName"), "period": period, "units": units, "periods": periods,
            **freshness(periods[0]["period_end"] if periods else None, period, today)}


def _derive_q4_eps(facts: dict, by_end: dict[date, dict], units: dict[str, str]) -> None:
    """Fill diluted EPS for fiscal-Q4 quarters the 10-K reports only as a full year. Q4 net income over
    a tagged 3-month diluted share count is closest to what the company would report; otherwise the
    full year less the 9-month year-to-date figure (same filing basis, so a share split or IPO earlier
    in the year doesn't skew it), else less the three reported quarters. Either is off by a cent or so
    when the share count moves. `eps_diluted_derived` names the method; reported values stay as filed."""
    eps_rows, eps_unit = _pick_series(facts, next(c for c in CONCEPTS if c.field == "eps_diluted"))
    if not eps_rows:
        return
    durations = _duration_rows(eps_rows)
    quarters = sorted((s, e, v) for (s, e), (v, _) in durations.items() if _is_quarter((e - s).days))
    share_rows, _ = _pick_series(facts, Concept("diluted_shares", DILUTED_SHARES_TAGS, additive=False))
    q4_shares = {e: v for (s, e), (v, _) in _duration_rows(share_rows).items() if _is_quarter((e - s).days)}
    per_share_ok = units.get("net_income") is not None and eps_unit == f"{units['net_income']}/shares"
    for (start, end), (year_eps, form) in durations.items():
        p = by_end.get(end)
        if not _is_year((end - start).days) or (form and form not in ANNUAL_FORMS) or p is None \
                or p.get("eps_diluted") is not None:
            continue
        if per_share_ok and p.get("net_income") is not None and q4_shares.get(end):
            eps, method = p["net_income"] / q4_shares[end], "net_income_per_share"
        elif ytd := next((v for (s, e), (v, _) in durations.items()
                          if s == start and e < end and _is_quarter((end - e).days)), None):
            eps, method = year_eps - ytd, "annual_less_ytd"
        else:
            # Q1-Q3 back to back from the fiscal year's start, leaving one quarter before its end.
            chain, edge = [], start
            for s, e, v in quarters:
                if 0 <= (s - edge).days <= 7 and e < end and len(chain) < 3:
                    chain.append(v)
                    edge = e
            if len(chain) < 3 or not _is_quarter((end - edge).days):
                continue
            eps, method = year_eps - sum(chain), "annual_less_quarters"
        p["eps_diluted"], p["eps_diluted_derived"] = round(eps, 2), method
        units.setdefault("eps_diluted", eps_unit or "")


def ttm_free_cash_flow(financials: dict) -> tuple[float, str] | None:
    """Operating cash flow - capex over the last four reported quarters, with the latest quarter's end,
    from build_financials' quarterly output. None unless the four newest quarters all have it, are
    back to back and in USD (the figure sits beside prices and market cap)."""
    units = financials.get("units", {})
    if units.get("operating_cash_flow") != "USD" or units.get("capex") != "USD":
        return None
    last4 = _last_four_quarters(financials)
    if last4 is None or any(p.get("free_cash_flow") is None for p in last4):
        return None
    return sum(p["free_cash_flow"] for p in last4), last4[0]["period_end"]


def _last_four_quarters(financials: dict) -> list[dict] | None:
    """The four newest quarters of build_financials' quarterly output, if back to back."""
    last4 = financials.get("periods", [])[:4]
    if len(last4) < 4:
        return None
    ends = [date.fromisoformat(p["period_end"]) for p in last4]
    return last4 if all(_is_quarter((a - b).days) for a, b in pairwise(ends)) else None


def ttm_figures(financials: dict) -> dict[str, float]:
    """Trailing figures over the same four newest quarters as ttm_free_cash_flow, so they agree with
    each other and with the quarterly statements: revenue_ttm, eps_ttm (the quarters' diluted EPS
    summed), gross/operating/net margin and fcf_margin_pct (the quarters' sums ÷ their revenue) and
    revenue_growth_q_yoy_pct (the newest quarter vs the one ending a year earlier). Without capex in
    every quarter there's no FCF margin; ocf_margin_pct (operating cash flow ÷ revenue) stands in, so
    nothing divides another source's FCF by SEC revenue. A figure is left out when a quarter lacks it
    or it isn't in US dollars (it sits beside prices)."""
    units, out = financials.get("units", {}), {}
    last4 = _last_four_quarters(financials)
    usd_rev = units.get("revenue") == "USD"
    if last4 and usd_rev and all(p.get("revenue") for p in last4):
        rev = out["revenue_ttm"] = sum(p["revenue"] for p in last4)
        for f, key in (("gross_profit", "gross_margin_pct"), ("operating_income", "operating_margin_pct"),
                       ("net_income", "net_margin_pct"), ("operating_cash_flow", "ocf_margin_pct")):
            if units.get(f) == "USD" and all(p.get(f) is not None for p in last4):
                out[key] = sum(p[f] for p in last4) / rev * 100
        if fcf := ttm_free_cash_flow(financials):
            out["fcf_margin_pct"] = fcf[0] / rev * 100
            out.pop("ocf_margin_pct", None)
    if last4 and units.get("eps_diluted") == "USD/shares" and all(p.get("eps_diluted") is not None for p in last4):
        out["eps_ttm"] = round(sum(p["eps_diluted"] for p in last4), 4)
    periods = financials.get("periods", [])
    if periods and usd_rev and periods[0].get("revenue") is not None:
        newest = date.fromisoformat(periods[0]["period_end"])
        prior = next((p for p in periods[1:] if _is_year((newest - date.fromisoformat(p["period_end"])).days)), None)
        if prior and prior.get("revenue", 0) > 0:
            out["revenue_growth_q_yoy_pct"] = (periods[0]["revenue"] / prior["revenue"] - 1) * 100
    return out


def _num_or_none(v: str | None) -> float | None:
    try:
        return float(v) if v not in (None, "", "N/A") else None
    except ValueError:
        return None


def parse_nport(xml: str, keep: int = NPORT_KEEP) -> dict:
    """N-PORT primary_doc.xml -> report date, totals and holdings sorted by weight (percent of net
    assets; negative for shorts). Country and asset-category weights cover every holding."""
    root = ET.fromstring(xml.encode())
    text = lambda el, path: (el.findtext(path) or "").strip() or None  # noqa: E731
    holdings, countries, categories = [], {}, {}
    for inv in root.iterfind(".//{*}invstOrSec"):
        weight = _num_or_none(text(inv, "{*}pctVal")) or 0.0
        ids = inv.find("{*}identifiers")
        ident = lambda tag: (ids.find(f"{{*}}{tag}").get("value") if ids is not None and ids.find(f"{{*}}{tag}") is not None else None)  # noqa: E731
        h = {"name": text(inv, "{*}name"), "title": text(inv, "{*}title"), "cusip": text(inv, "{*}cusip"),
             "isin": ident("isin"), "ticker": ident("ticker"), "weight_pct": weight,
             "value_usd": _num_or_none(text(inv, "{*}valUSD")),
             "currency": text(inv, "{*}curCd") or (cc.get("curCd") if (cc := inv.find("{*}currencyConditional")) is not None else None),
             "asset_cat": text(inv, "{*}assetCat"), "issuer_cat": text(inv, "{*}issuerCat"),
             "country": text(inv, "{*}invCountry") if text(inv, "{*}invCountry") != "N/A" else None}
        if h["cusip"] in ("000000000", "N/A"):
            h["cusip"] = None
        debt = inv.find("{*}debtSec")
        if debt is not None:
            h["maturity"] = text(debt, "{*}maturityDt")
            h["coupon_pct"] = _num_or_none(text(debt, "{*}annualizedRt"))
        holdings.append(h)
        if h["country"]:
            countries[h["country"]] = countries.get(h["country"], 0.0) + weight
        if h["asset_cat"]:
            categories[h["asset_cat"]] = categories.get(h["asset_cat"], 0.0) + weight
    holdings.sort(key=lambda h: -h["weight_pct"])
    return {"as_of": text(root, ".//{*}repPdDate"), "net_assets": _num_or_none(text(root, ".//{*}netAssets")),
            "count": len(holdings), "holdings": holdings[:keep],
            "countries": dict(sorted(countries.items(), key=lambda kv: -kv[1])),
            "asset_categories": dict(sorted(categories.items(), key=lambda kv: -kv[1]))}
