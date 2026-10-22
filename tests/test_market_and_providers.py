import dataclasses
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from argus.providers.base import Bar, SymbolInfo
from argus.providers.finnhub import FinnhubProvider
from argus.providers.sec_edgar import build_financials
from tests.conftest import FakeHistory, FakeQuotes


def test_quote_fallback_and_cache(make_argus):
    primary = FakeQuotes("primary", {"AAA": (10, 9)})
    backup = FakeQuotes("backup", {"AAA": (99, 98), "BBB": (20, 19)})
    a = make_argus([primary, backup])

    quotes, errors = a.market.get_quotes(["AAA", "BBB", "ZZZ"])
    assert quotes["AAA"].source == "primary" and quotes["BBB"].source == "backup"
    assert set(errors) == {"ZZZ"}
    assert backup.calls == [["BBB", "ZZZ"]]

    a.market.get_quotes(["AAA", "BBB"])  # served from cache
    assert len(primary.calls) == 1


def test_provider_outage_falls_back(make_argus):
    a = make_argus([FakeQuotes("down", {}, fail=True), FakeQuotes("up", {"AAA": (1, 1)})])
    quotes, errors = a.market.get_quotes(["AAA"])
    assert quotes["AAA"].source == "up" and errors == {}


def test_daily_history_is_cached(make_argus):
    now = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    bars = [Bar(now - timedelta(days=i), 1, 2, 0.5, 1.5, 100) for i in range(400, -1, -1)]
    hist = FakeHistory(bars)
    a = make_argus(history=hist)
    first = a.market.get_history("AAA", "1y")
    second = a.market.get_history("AAA", "6mo")
    assert hist.calls == 1
    assert 360 <= len(first) <= 367 and len(second) < len(first)


def test_finnhub_quote_parsing_and_unknown_symbol():
    def handler(req: httpx.Request):
        sym = req.url.params["symbol"]
        body = ({"c": 341.07, "d": 5.15, "dp": 1.53, "h": 341.67, "l": 334.53, "o": 336.04, "pc": 335.92,
                 "t": 1790366400} if sym == "AAPL" else {"c": 0, "d": None, "dp": None, "h": 0, "l": 0, "o": 0,
                                                         "pc": 0, "t": 0})
        assert req.headers["X-Finnhub-Token"] == "test-key"
        return httpx.Response(200, json=body)

    client = httpx.Client(base_url="https://finnhub.test", transport=httpx.MockTransport(handler))
    fh = FinnhubProvider("test-key", client=client)
    q = fh.get_quotes(["AAPL", "NOPE"])
    assert list(q) == ["AAPL"]
    assert q["AAPL"].prev_close == 335.92 and q["AAPL"].change_pct == pytest.approx(1.5331, abs=1e-3)
    assert q["AAPL"].as_of == datetime(2026, 9, 25, 20, tzinfo=UTC)


def test_finnhub_metrics_mapping():
    metric = {"peTTM": 28.3, "pb": 45.1, "marketCapitalization": 5430000, "netProfitMarginTTM": 55.8}
    client = httpx.Client(base_url="https://finnhub.test",
                          transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"metric": metric})))
    m = FinnhubProvider("k", client=client).get_metrics("NVDA")
    assert m["pe_ttm"] == 28.3 and m["market_cap"] == 5.43e12 and m["net_margin_pct"] == 55.8
    assert m["ps_ttm"] is None


@pytest.mark.parametrize("growth, peg_ttm", [(0.87, 112.93), (-21.7, None), (0.0, None), (None, None)])
def test_finnhub_peg_is_trailing_and_kept_apart_from_the_expected_peg(growth, peg_ttm):
    # NOW, Oct 2026: GAAP EPS growth of 0.87% makes the trailing PEG 112.93.
    metric = {"peTTM": 86.67, "pegTTM": 112.93, "epsGrowthTTMYoy": growth}
    client = httpx.Client(base_url="https://finnhub.test",
                          transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"metric": metric})))
    m = FinnhubProvider("k", client=client).get_metrics("NOW")
    assert "peg" not in m  # "peg" is the expected-growth PEG, from Yahoo only
    assert m["peg_ttm"] == peg_ttm


def test_peg_column_never_falls_back_to_the_trailing_one(make_argus):
    class Finnhub:
        name = "finnhub"

        def get_metrics(self, symbol):
            return {"pe_ttm": 86.67, "peg_ttm": 112.93}

    class Yahoo:
        name = "yahoo"

        def __init__(self, peg):
            self.peg = peg

        def get_metrics(self, symbol):
            return {"pe_forward": 28.6, "peg": self.peg}

    a = make_argus(fundamentals=[Finnhub(), Yahoo(1.01)])
    m = a.market.get_fundamentals("NOW", ["peg", "peg_ttm"])
    assert (m["metrics"], m["sources"]) == ({"peg": 1.01, "peg_ttm": 112.93}, {"peg": "yahoo", "peg_ttm": "finnhub"})
    b = make_argus(fundamentals=[Finnhub(), Yahoo(None)])  # same database: use a fresh symbol
    assert b.market.get_fundamentals("XYZ", ["peg"])["metrics"]["peg"] is None


def _fact(start, end, val, form="10-Q", filed="2026-01-01"):
    return {"start": start, "end": end, "val": val, "form": form, "filed": filed}


def test_sec_quarters_derive_q4_and_ytd_cash_flow():
    facts = {"entityName": "TestCo", "facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            _fact("2025-01-01", "2025-03-31", 100), _fact("2025-04-01", "2025-06-30", 110),
            _fact("2025-07-01", "2025-09-30", 120),
            # Q4 is only filed as part of the full year:
            _fact("2025-01-01", "2025-12-31", 460, form="10-K", filed="2026-02-01"),
            # 6- and 9-month YTD duplicates of the same quarters must not double count:
            _fact("2025-01-01", "2025-06-30", 210), _fact("2025-01-01", "2025-09-30", 330),
        ]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
            _fact("2025-01-01", "2025-03-31", 30), _fact("2025-01-01", "2025-06-30", 70),
            _fact("2025-01-01", "2025-09-30", 100),
            _fact("2025-01-01", "2025-12-31", 150, form="10-K"),
        ]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            _fact("2025-01-01", "2025-03-31", 1.0), _fact("2025-01-01", "2025-12-31", 4.2, form="10-K"),
        ]}},
    }}}
    q = {p["period_end"]: p for p in build_financials(facts, "quarterly")["periods"]}
    assert [q[e]["revenue"] for e in ("2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31")] == [100, 110, 120, 130]
    assert [q[e]["operating_cash_flow"] for e in ("2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31")] == [30, 40, 30, 50]
    assert "eps_diluted" not in q["2025-12-31"]  # Q2 and Q3 EPS missing: nothing to derive Q4 from
    annual = build_financials(facts, "annual")["periods"][0]
    assert (annual["revenue"], annual["eps_diluted"]) == (460, 4.2)


def test_sec_derives_fiscal_q4_eps():
    """10-Ks report EPS for the full year only; quarterly statements fill fiscal Q4 from it."""
    ni = lambda *rows: [_fact(s, e, v, form="10-K" if e == "2025-09-30" else "10-Q") for s, e, v in rows]  # noqa: E731
    eps = [  # fiscal year Oct-Sep, with a reported quarter outside it that must be left alone
        _fact("2024-10-01", "2024-12-31", 1.0), _fact("2025-01-01", "2025-03-31", 1.1),
        _fact("2025-04-01", "2025-06-30", 1.2), _fact("2024-10-01", "2025-09-30", 4.6, form="10-K"),
        _fact("2025-10-01", "2025-12-31", 1.4),
    ]
    facts = {"facts": {"us-gaap": {
        "NetIncomeLoss": {"units": {"USD": ni(("2024-10-01", "2024-12-31", 100), ("2025-01-01", "2025-03-31", 110),
                                               ("2025-04-01", "2025-06-30", 120), ("2024-10-01", "2025-06-30", 330),
                                               ("2024-10-01", "2025-09-30", 460),
                                               ("2025-10-01", "2025-12-31", 140))}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
    }}}
    q = {p["period_end"]: p for p in build_financials(facts, "quarterly")["periods"]}
    assert (q["2025-09-30"]["eps_diluted"], q["2025-09-30"]["eps_diluted_derived"]) == (1.3, "annual_less_quarters")
    assert [q[e]["eps_diluted"] for e in ("2024-12-31", "2025-03-31", "2025-06-30", "2025-12-31")] == [1.0, 1.1, 1.2, 1.4]
    assert not any("eps_diluted_derived" in q[e] for e in ("2024-12-31", "2025-03-31", "2025-06-30", "2025-12-31"))
    assert build_financials(facts, "annual")["periods"][0]["eps_diluted"] == 4.6

    # The 9-month year-to-date figure shares the 10-K's basis, so it wins over the quarters (here a
    # pre-IPO Q1 on another share basis that would wreck the subtraction):
    eps[0] = _fact("2024-10-01", "2024-12-31", 9000.0)
    ytd = _fact("2024-10-01", "2025-06-30", 3.25)
    facts["facts"]["us-gaap"]["EarningsPerShareDiluted"]["units"]["USD/shares"] = [*eps, ytd]
    p = {p["period_end"]: p for p in build_financials(facts)["periods"]}["2025-09-30"]
    assert (p["eps_diluted"], p["eps_diluted_derived"]) == (1.35, "annual_less_ytd")

    # A tagged 3-month diluted share count beats both: Q4 net income (460 - 330) / 104 shares.
    facts["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"] = {"units": {"shares": [
        _fact("2025-07-01", "2025-09-30", 104, form="10-K"), _fact("2024-10-01", "2025-09-30", 100, form="10-K")]}}
    p = {p["period_end"]: p for p in build_financials(facts)["periods"]}["2025-09-30"]
    assert (p["eps_diluted"], p["eps_diluted_derived"]) == (1.25, "net_income_per_share")

    # Without Q4 net income there's no quarter row to fill, and nothing is invented:
    del facts["facts"]["us-gaap"]["NetIncomeLoss"]
    assert "2025-09-30" not in {p["period_end"] for p in build_financials(facts)["periods"]}


def _cash_flow_facts(ocf_ytd, capex_ytd):
    """Calendar-2025 10-Q YTD cash flow plus the 10-K year; Q4 is derived by differencing."""
    ends = ("2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31")
    rows = lambda vals: [_fact("2025-01-01", e, v, form="10-K" if e.endswith("12-31") else "10-Q")  # noqa: E731
                         for e, v in zip(ends, vals)]
    return {"facts": {"us-gaap": {
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": rows(ocf_ytd)}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": rows(capex_ytd)}},
    }}}


def test_sec_ttm_free_cash_flow_sums_four_quarters():
    from argus.providers.sec_edgar import ttm_free_cash_flow

    # Quarterly OCF 30/40/30/50, capex 10/10/5/15: FCF 20+30+25+35.
    facts = _cash_flow_facts((30, 70, 100, 150), (10, 20, 25, 40))
    assert ttm_free_cash_flow(build_financials(facts, "quarterly", 4)) == (110, "2025-12-31")
    # Three quarters aren't a year:
    assert ttm_free_cash_flow(build_financials(_cash_flow_facts((30, 70, 100), (10, 20, 25)))) is None
    # A gap between quarters isn't a trailing year either:
    gap = {"units": {"operating_cash_flow": "USD", "capex": "USD"}, "periods": [
        {"period_end": e, "free_cash_flow": 1.0} for e in ("2025-12-31", "2025-09-30", "2025-06-30", "2024-12-31")]}
    assert ttm_free_cash_flow(gap) is None
    # Nor are foreign-currency filings next to US-dollar prices:
    eur = facts | {"facts": {"us-gaap": {k: {"units": {"EUR": v["units"]["USD"]}}
                                         for k, v in facts["facts"]["us-gaap"].items()}}}
    assert ttm_free_cash_flow(build_financials(eur)) is None


class _FakeSec:
    def __init__(self, facts=None, error=None):
        self.facts, self.error = facts, error

    def get_financials(self, symbol, period="quarterly", limit=8):
        from argus.providers.base import ProviderError

        if self.error:
            raise ProviderError(self.error)
        return build_financials(self.facts, period, limit)


def test_fcf_ttm_comes_from_sec_quarters_else_provider(settings):
    from argus.db import make_engine
    from argus.services.market import MarketService

    st = dataclasses.replace(settings, sec_user_agent="argus test@example.com")
    engine = make_engine(st.db_path)
    yahoo = _Fund("yahoo", {"fcf_ttm": 16.5, "revenue_ttm": 440.0})
    sec = _FakeSec(_cash_flow_facts((30, 70, 100, 150), (10, 20, 25, 40)))
    m = MarketService(engine, st, [], None, [yahoo], sec=sec)
    out = m.get_fundamentals("MSFT", ["fcf_ttm", "revenue_ttm"])
    assert out["metrics"] == {"fcf_ttm": 110, "revenue_ttm": 440.0}
    assert out["sources"] == {"fcf_ttm": "sec", "revenue_ttm": "yahoo"}

    # An SEC hiccup keeps yesterday's SEC figure rather than switching to the provider's:
    sec.error = "sec https://data.sec.gov/...: HTTP 503"
    out = m.get_fundamentals("MSFT", ["fcf_ttm"], refresh=True)
    assert (out["metrics"]["fcf_ttm"], out["sources"]["fcf_ttm"]) == (110, "sec")

    # Not in EDGAR (an ETF), or too few quarters: the provider's figure, labeled as such.
    sec.error = "sec: SPY not found in EDGAR (ETFs and funds have no financials)."
    out = m.get_fundamentals("SPY", ["fcf_ttm"])
    assert (out["metrics"]["fcf_ttm"], out["sources"]["fcf_ttm"]) == (16.5, "yahoo")
    sec.error, sec.facts = None, _cash_flow_facts((30, 70), (10, 20))
    out = m.get_fundamentals("NEWCO", ["fcf_ttm"])
    assert (out["metrics"]["fcf_ttm"], out["sources"]["fcf_ttm"]) == (16.5, "yahoo")
    # Without SEC_USER_AGENT there's no SEC path at all:
    plain = MarketService(engine, settings, [], None, [yahoo], sec=_FakeSec(error="must not be called"))
    assert plain.get_fundamentals("KO", ["fcf_ttm"])["sources"]["fcf_ttm"] == "yahoo"


def test_sec_prefers_restated_value():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        _fact("2025-01-01", "2025-03-31", 100, filed="2025-05-01"),
        _fact("2025-01-01", "2025-03-31", 95, filed="2026-05-01"),
    ]}}}}}
    assert build_financials(facts)["periods"][0]["revenue"] == 95
    json.dumps(build_financials(facts))  # serializable


def test_sec_revenue_including_assessed_tax_only_fills_gaps():
    incl = "RevenueFromContractWithCustomerIncludingAssessedTax"
    # Rambus and BioCryst tag revenue only this way:
    only = {"facts": {"us-gaap": {incl: {"units": {"USD": [
        _fact("2025-01-01", "2025-03-31", 100), _fact("2025-01-01", "2025-06-30", 210),
        _fact("2025-01-01", "2025-12-31", 460, form="10-K"),
    ]}}, "GrossProfit": {"units": {"USD": [_fact("2025-01-01", "2025-03-31", 60)]}}}}}
    q = {p["period_end"]: p for p in build_financials(only)["periods"]}
    assert (q["2025-03-31"]["revenue"], q["2025-06-30"]["revenue"]) == (100, 110)
    assert q["2025-03-31"]["gross_margin_pct"] == 60
    assert build_financials(only, "annual")["periods"][0]["revenue"] == 460
    # It's gross of sales taxes, so a net figure wins wherever the company tags one:
    both = {"facts": {"us-gaap": {
        incl: {"units": {"USD": [_fact("2025-01-01", "2025-03-31", 101), _fact("2025-04-01", "2025-06-30", 112)]}},
        "Revenues": {"units": {"USD": [_fact("2025-04-01", "2025-06-30", 110)]}},
    }}}
    q = {p["period_end"]: p["revenue"] for p in build_financials(both)["periods"]}
    assert q == {"2025-06-30": 110, "2025-03-31": 101}


def test_screener_revenue_covers_statement_tags():
    from argus.providers.sec_edgar import CONCEPTS
    from argus.services.screener import REVENUE

    revenue = next(c for c in CONCEPTS if c.field == "revenue")
    us_gaap = [t for t in (*revenue.tags, *revenue.fallback) if t != "Revenue"]  # ifrs-full has no frames
    assert set(us_gaap) <= set(REVENUE)


class _Fund:
    def __init__(self, name, data):
        self.name, self.data = name, data

    def get_metrics(self, symbol):
        return self.data


def test_price_currency_fields_prefer_yahoo_ratios_keep_order(make_argus):
    fh = _Fund("finnhub", {"pe_ttm": 9.0, "high_52w": 1425.0, "low_52w": 617.0, "market_cap": 1.4e11})
    yh = _Fund("yahoo", {"pe_ttm": 8.8, "high_52w": 81.4, "low_52w": 33.5, "market_cap": 7.5e9, "pe_forward": 7.0})
    a = make_argus(fundamentals=[fh, yh])
    out = a.market.get_fundamentals("VIST")
    assert out["metrics"]["pe_ttm"] == 9.0 and out["sources"]["pe_ttm"] == "finnhub"
    assert out["metrics"]["high_52w"] == 81.4 and out["sources"]["market_cap"] == "yahoo"
    assert out["metrics"]["pe_forward"] == 7.0 and "_version" not in out["sources"]


def test_finnhub_symbol_directory_follows_redirect_to_file(tmp_path):
    rows = [{"symbol": "AAPL", "description": "APPLE INC", "type": "Common Stock", "mic": "XNAS"}]

    def handler(request):
        if request.url.path == "/stock/symbol":
            return httpx.Response(302, headers={"location": "https://static.finnhub.test/USf.json"})
        return httpx.Response(200, json=rows)

    client = httpx.Client(base_url="https://finnhub.test", transport=httpx.MockTransport(handler))
    d = FinnhubProvider("k", cache_dir=tmp_path, client=client).symbol_directory()
    assert d["AAPL"].name == "APPLE INC" and d["AAPL"].exchange == "XNAS"


class FakeDirectory:
    def __init__(self, rows):
        self.rows = {r[0]: SymbolInfo(*r) for r in rows}

    def symbol_directory(self):
        return self.rows


def test_search_ranking(settings):
    from argus.db import make_engine
    from argus.services.market import MarketService

    m = MarketService(make_engine(settings.db_path), settings, [], None, [], directory=FakeDirectory([
        ("APPLF", "ALPHAPOLIS CO LTD", "Common Stock", "OOTC"),
        ("AIT", "APPLIED INDUSTRIAL TECH", "Common Stock", "XNYS"),
        ("AAPL", "APPLE INC", "Common Stock", "XNAS"),
        ("AAPX", "T-REX 2X LONG APPLE", "ETP", "BATS"),
        ("BRKU", "DIREXION DAILY BRKB BULL", "ETP", "XNAS"),
        ("BRK.B", "BERKSHIRE HATHAWAY INC-CL B", "Common Stock", "XNYS"),
        ("SB.PRC", "SAFE BULKERS PFD C", "Common Stock", "XNYS"),
        ("S", "SENTINELONE INC", "Common Stock", "XNYS"),
        ("SOFI", "SOFI TECHNOLOGIES", "Common Stock", "XNAS"),
    ]))
    syms = lambda q, **kw: [r["symbol"] for r in m.search(q, 5, **kw)]  # noqa: E731
    assert syms("appl") == ["AAPL", "AAPX", "AIT", "APPLF"]  # closest name word, stock before ETP, OTC last
    assert syms("brk")[0] == "BRK.B"                           # share class counts as a 3-letter ticker
    assert syms("s") == ["S", "SOFI", "SB.PRC"]                 # exact first, preferreds last
    assert syms("s", prefer={"SOFI"})[:2] == ["S", "SOFI"] and syms("so", prefer={"SOFI"})[0] == "SOFI"
    assert syms("  ") == []


def test_sec_prefers_report_filings_over_later_proxy_copies():
    from argus.providers.sec_edgar import _duration_rows

    rows = [{"start": "2024-01-29", "end": "2025-01-26", "val": 72.88, "form": "10-K", "filed": "2025-02-26"},
            {"start": "2024-01-29", "end": "2025-01-26", "val": 72.88, "form": "DEF 14A", "filed": "2026-05-12"},
            {"start": "2023-01-30", "end": "2024-01-28", "val": 29.0, "form": "10-K", "filed": "2024-02-21"},
            {"start": "2023-01-30", "end": "2024-01-28", "val": 29.76, "form": "10-K/A", "filed": "2024-06-01"}]
    d = _duration_rows(rows)
    from datetime import date as D
    assert d[(D(2024, 1, 29), D(2025, 1, 26))] == (72.88, "10-K")       # the proxy copy doesn't displace it
    assert d[(D(2023, 1, 30), D(2024, 1, 28))] == (29.76, "10-K/A")     # a later report (restatement) still wins
