import pytest

from argus.errors import ArgusError
from tests.conftest import FakeQuotes


class FakeYahoo:
    def __init__(self):
        self.calls = 0

    def get_info(self, symbol):
        self.calls += 1
        return {"longName": "Coherent Corp.", "longBusinessSummary": "Lasers and optics.", "country": "United States",
                "city": "Saxonburg", "state": "PA", "fullTimeEmployees": 51478, "website": "https://www.coherent.com",
                "companyOfficers": [{"name": "Jim Anderson", "title": "CEO", "age": 60}]}


class FakeFinnhub:
    def get_profile(self, symbol):
        return {"ipo": "1987-10-13", "weburl": "https://other.example", "logo": ""}

    def get_peers(self, symbol):
        return ["APH", "COHR", "GLW", "IGM.TO"]

    def symbol_directory(self):
        return {}  # unavailable: falls back to dropping exchange-suffixed tickers


@pytest.fixture
def a(make_argus):
    a = make_argus([FakeQuotes("fake", {s: (100, 99) for s in ("COHR", "APH", "GLW", "LITE")})])
    a.market.profile_provider, a.market.directory = FakeYahoo(), FakeFinnhub()
    return a


def test_profile_merges_providers_and_is_cached(a):
    p = a.company_profile("cohr")
    assert p["city"] == "Saxonburg" and p["ipo"] == "1987-10-13" and p["website"] == "https://www.coherent.com"
    assert p["officers"] == [{"name": "Jim Anderson", "title": "CEO"}] and "logo" not in p
    assert p["suggested_peers"] == ["APH", "GLW"]  # the symbol itself is dropped
    a.company_profile("COHR")
    assert a.market.profile_provider.calls == 1


def test_peers_suggested_then_custom_then_reset(a):
    r = a.peers("COHR")
    assert (r["custom"], r["peers"]) == (False, ["APH", "GLW"])
    assert [row["symbol"] for row in r["rows"]] == ["COHR", "APH", "GLW"] and r["rows"][1]["price"] == 100

    assert a.set_peers("COHR", ["lite", "APH", "COHR", "LITE"])["peers"] == ["LITE", "APH"]
    assert a.peers("COHR", with_metrics=False)["custom"]
    with pytest.raises(ArgusError) as e:
        a.set_peers("COHR", ["LITM"])
    assert e.value.code == "UNKNOWN_SYMBOL" and a.peers("COHR", with_metrics=False)["peers"] == ["LITE", "APH"]

    assert a.set_peers("COHR", None) == {"symbol": "COHR", "peers": ["APH", "GLW"], "custom": False,
                                         "kind": "stock", "category": None}


def test_peer_lists_travel_in_snapshots(a, tmp_path):
    a.set_peers("COHR", ["LITE"])
    a.snapshots.dump(tmp_path / "s.json")
    assert a.snapshots.load(tmp_path / "s.json")["counts"]["peer_list"] == 1


def test_suggested_peers_keep_only_us_exchange_listings(a):
    from argus.providers.base import SymbolInfo

    class Dir(FakeFinnhub):
        def get_peers(self, symbol):
            return ["IGM.TO", "APH", "ONEXF", "GLW", "U.UN.TO"]

        def symbol_directory(self):
            return {"APH": SymbolInfo("APH", "AMPHENOL", "Common Stock", "XNYS"),
                    "GLW": SymbolInfo("GLW", "CORNING", "Common Stock", "XNYS"),
                    "ONEXF": SymbolInfo("ONEXF", "ONEX CORP", "Common Stock", "OOTC")}

    a.market.directory = Dir()
    assert a.company_profile("BN")["suggested_peers"] == ["APH", "GLW"]


class FakeFundYahoo:
    """QQQ-like fund whose category holds a near-clone, a looser match and a fund listing nothing."""
    PROFILES = {
        "QQQ": [("NVDA", 0.09), ("AAPL", 0.07), ("MSFT", 0.06), ("2330.TW", 0.01)],
        "QQQM": [("NVDA", 0.09), ("AAPL", 0.07), ("MSFT", 0.06)],
        "VUG": [("NVDA", 0.12), ("META", 0.04)],
        "BIGB": [],
    }

    def __init__(self):
        self.native = []

    def get_info(self, symbol):
        return {"longName": f"{symbol} Fund", "quoteType": "ETF", "category": "Large Growth", "fundFamily": "Invesco"}

    def similar_etfs(self, category, limit):
        assert category == "Large Growth"
        return ["BIGB", "VUG", "QQQ", "QQQM", "XYZ.TO"]  # largest first; includes the fund itself

    def get_fund_profile(self, symbol):
        rows = self.PROFILES.get(symbol)
        if rows is None:
            return {}
        return {"sectors": {"Technology": 0.6, "Healthcare": 0.1},
                "top_holdings": [{"symbol": s, "name": s, "weight": w} for s, w in rows],
                "asset_classes": {"stockPosition": 0.99, "cashPosition": 0.01}, "bond_ratings": {}}

    def get_quotes(self, symbols, native=False):
        from datetime import UTC, datetime
        from argus.providers.base import Quote
        if native:
            self.native += symbols
        return {s: Quote(s, 1000.0, 990.0, None, None, None, datetime.now(UTC), "yahoo", False) for s in symbols}


@pytest.fixture
def fund(make_argus):
    a = make_argus([FakeQuotes("fake", {s: (100, 98) for s in ("QQQ", "QQQM", "VUG", "BIGB", "NVDA", "AAPL", "MSFT")})])
    a.market.profile_provider, a.market.directory = FakeFundYahoo(), None
    return a


def test_fund_peers_come_from_the_category_most_overlap_first(fund):
    p = fund.company_profile("QQQ")
    assert p["suggested_peers"] == ["QQQM", "VUG", "BIGB"]  # overlap 22%, 9%, none; foreign and self dropped
    r = fund.peers("QQQ")
    assert (r["kind"], r["category"]) == ("fund", "Large Growth")
    assert "net_assets" in r["fields"] and "pe_forward" not in r["fields"]
    assert {row["symbol"]: row["overlap_pct"] for row in r["rows"]} == {"QQQ": None, "QQQM": 22.0, "VUG": 9.0,
                                                                        "BIGB": None}


def test_holdings_fall_back_to_yahoo_top_10_and_quote_foreign_listings_natively(fund):
    h = fund.fund_holdings("qqq")
    assert (h["fund"], h["source"], h["count"]) == (True, "yahoo", 4)
    assert [x["symbol"] for x in h["holdings"]] == ["NVDA", "AAPL", "MSFT", "2330.TW"]
    nvda, tsmc = h["holdings"][0], h["holdings"][3]
    assert (nvda["weight_pct"], nvda["change_pct"], nvda["us_listed"]) == (9.0, pytest.approx(1.0101, abs=1e-3), True)
    assert (tsmc["price"], tsmc["us_listed"]) == (1000.0, False)
    assert fund.market.profile_provider.native == ["2330.TW"]  # only the foreign listing keeps Yahoo's form
    assert h["sectors"][0] == {"sector": "Technology", "weight_pct": 60.0}
    assert h["asset_classes"] == {"stockPosition": 99.0, "cashPosition": 1.0}


NPORT_XML = """<?xml version="1.0"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/nport"><formData>
 <genInfo><repPdDate>2026-06-30</repPdDate></genInfo>
 <fundInfo><netAssets>1000000.00</netAssets></fundInfo>
 <invstOrSecs>
  <invstOrSec><name>Toyota Motor Corp</name><title>Toyota</title><cusip>000000000</cusip>
   <identifiers><isin value="JP3633400001"/></identifiers><valUSD>20000</valUSD><pctVal>2.0</pctVal>
   <currencyConditional curCd="JPY" exchangeRt="150"/><assetCat>EC</assetCat><invCountry>JP</invCountry></invstOrSec>
  <invstOrSec><name>Linde PLC</name><cusip>G54950103</cusip><identifiers><isin value="IE000S9YS762"/></identifiers>
   <valUSD>50000</valUSD><pctVal>5.0</pctVal><curCd>USD</curCd><assetCat>EC</assetCat><invCountry>IE</invCountry></invstOrSec>
  <invstOrSec><name>Apple Inc.</name><cusip>037833100</cusip><identifiers><isin value="US0378331005"/><ticker value="AAPL"/></identifiers>
   <valUSD>70000</valUSD><pctVal>7.0</pctVal><curCd>USD</curCd><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
  <invstOrSec><name>Samsung Electronics GDR</name><identifiers><isin value="KR7005930003"/></identifiers>
   <valUSD>10000</valUSD><pctVal>1.0</pctVal><curCd>USD</curCd><assetCat>EC</assetCat><invCountry>US</invCountry></invstOrSec>
  <invstOrSec><name>Samsung Electronics</name><identifiers><isin value="KR7005930003"/></identifiers>
   <valUSD>15000</valUSD><pctVal>1.5</pctVal><currencyConditional curCd="KRW"/><assetCat>EC</assetCat><invCountry>KR</invCountry></invstOrSec>
  <invstOrSec><name>United States Treasury</name><cusip>91282CGH8</cusip><identifiers><isin value="US91282CGH88"/></identifiers>
   <valUSD>30000</valUSD><pctVal>3.0</pctVal><curCd>USD</curCd><assetCat>DBT</assetCat><invCountry>US</invCountry>
   <debtSec><maturityDt>2028-01-31</maturityDt><annualizedRt>3.5</annualizedRt></debtSec></invstOrSec>
  <invstOrSec><name>Cash fund</name><valUSD>4000</valUSD><pctVal>0.4</pctVal><curCd>USD</curCd>
   <assetCat>STIV</assetCat><invCountry>N/A</invCountry></invstOrSec>
 </invstOrSecs></formData></edgarSubmission>"""


def test_parse_nport_reads_every_holding():
    from argus.providers.sec_edgar import parse_nport

    d = parse_nport(NPORT_XML)
    assert (d["as_of"], d["net_assets"], d["count"]) == ("2026-06-30", 1000000.0, 7)
    assert [h["name"] for h in d["holdings"][:3]] == ["Apple Inc.", "Linde PLC", "United States Treasury"]
    toyota = next(h for h in d["holdings"] if h["name"].startswith("Toyota"))
    assert (toyota["currency"], toyota["cusip"], toyota["isin"]) == ("JPY", None, "JP3633400001")
    bond = d["holdings"][2]
    assert (bond["maturity"], bond["coupon_pct"], bond["asset_cat"]) == ("2028-01-31", 3.5, "DBT")
    assert d["countries"] == {"US": 11.0, "IE": 5.0, "JP": 2.0, "KR": 1.5}  # cash fund has no country
    assert parse_nport(NPORT_XML, keep=2)["count"] == 7


def test_pick_listing_follows_the_currency_held():
    from argus.providers.openfigi import pick_listing, yahoo_symbol

    toyota = [{"ticker": "TOYOF", "exchCode": "US"}, {"ticker": "7203", "exchCode": "JT"}, {"ticker": "7203", "exchCode": "JP"}]
    assert pick_listing(toyota, "JPY", "JP") == ("7203", "JP")
    assert pick_listing(toyota, None, None, isin="JP3633400001") == ("7203", "JP")  # the ISIN names the country
    assert pick_listing(toyota, "USD", "JP") == ("TOYOF", "US")
    assert pick_listing([{"ticker": "2330", "exchCode": "TT (Taiwan Stock Exchange)"}], "TWD", "TW") == ("2330", "TT")
    assert pick_listing([{"ticker": "X", "exchCode": "ZZ"}], "USD", "US") is None
    assert [yahoo_symbol(*x) for x in [("BRK/B", "US"), ("700", "HK"), ("BP/", "LN"), ("BBD/B", "CN"), ("7203", "JP")]] == \
        ["BRK.B", "0700.HK", "BP.L", "BBD-B.TO", "7203.T"]
    assert yahoo_symbol("X", "ZZ") is None


class FakeSec:
    def fund_holdings(self, symbol):
        from argus.providers.sec_edgar import parse_nport
        return {"series_id": "S1", "filed": "2026-08-28", **parse_nport(NPORT_XML)}


class FakeFigi:
    batch = 2

    def __init__(self, fail_after=None):
        self.jobs, self.fail_after = [], fail_after

    def map(self, items):
        from argus.providers.base import ProviderError
        if self.fail_after is not None and len(self.jobs) >= self.fail_after:
            raise ProviderError("openfigi: rate limited")
        self.jobs += [(i["id_type"], i["id"]) for i in items]
        known = {"JP3633400001": ("7203", "JP"), "G54950103": ("LIN", "US"), "KR7005930003": ("005930", "KS")}
        return {i["id"]: known.get(i["id"]) for i in items}


def test_holdings_from_nport_get_tickers_once_and_merge_duplicate_lines(fund):
    fund.market.sec, fund.market.figi = FakeSec(), FakeFigi()
    h = fund.fund_holdings("QQQ")
    assert (h["source"], h["as_of"], h["filed"], h["count"]) == ("sec", "2026-06-30", "2026-08-28", 7)
    rows = {r["name"]: r for r in h["holdings"]}
    assert (rows["Apple Inc."]["symbol"], rows["Apple Inc."]["us_listed"]) == ("AAPL", True)  # the filing's own ticker
    assert (rows["Linde PLC"]["symbol"], rows["Linde PLC"]["us_listed"]) == ("LIN", True)
    assert rows["Toyota Motor Corp"]["symbol"] == "7203.T"
    # Both Samsung lines become one row; the GDR (USD, no CUSIP) is matched to the home listing.
    samsung = [r for r in h["holdings"] if r["symbol"] == "005930.KS"]
    assert len(samsung) == 1 and samsung[0]["weight_pct"] == 2.5 and samsung[0]["value_usd"] == 25000
    assert samsung[0]["country"] == "KR"
    assert rows["United States Treasury"]["symbol"] is None and rows["United States Treasury"]["kind"] == "bond"
    assert ("ID_CINS", "G54950103") in fund.market.figi.jobs  # a CUSIP starting with a letter is a CINS
    assert rows["Toyota Motor Corp"]["change_pct"] == pytest.approx(1.0101, abs=1e-3)
    assert h["countries"][0] == {"country": "US", "weight_pct": 11.0}

    asked = len(fund.market.figi.jobs)
    fund.fund_holdings("QQQ")
    assert len(fund.market.figi.jobs) == asked  # mappings are cached


def test_rate_limited_ticker_lookup_leaves_the_rest_for_later(fund):
    fund.market.sec, fund.market.figi = FakeSec(), FakeFigi(fail_after=2)
    h = fund.fund_holdings("QQQ")
    assert any("reload" in n for n in h["notes"])
    assert sum(1 for r in h["holdings"] if r["symbol"]) == 3  # AAPL from the filing + the first batch of two
    fund.market.figi.fail_after = None
    assert sum(1 for r in fund.fund_holdings("QQQ")["holdings"] if r["symbol"]) == 4


def test_holdings_of_a_stock_are_empty(a):
    h = a.fund_holdings("COHR")
    assert (h["fund"], h["holdings"], h["source"]) == (False, [], None)
