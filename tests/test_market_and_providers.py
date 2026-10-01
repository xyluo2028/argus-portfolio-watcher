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
    assert "eps_diluted" not in q["2025-12-31"]  # EPS isn't additive: no derived Q4
    annual = build_financials(facts, "annual")["periods"][0]
    assert (annual["revenue"], annual["eps_diluted"]) == (460, 4.2)


def test_sec_prefers_restated_value():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        _fact("2025-01-01", "2025-03-31", 100, filed="2025-05-01"),
        _fact("2025-01-01", "2025-03-31", 95, filed="2026-05-01"),
    ]}}}}}
    assert build_financials(facts)["periods"][0]["revenue"] == 95
    json.dumps(build_financials(facts))  # serializable


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
