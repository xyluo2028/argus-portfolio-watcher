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

    assert a.set_peers("COHR", None) == {"symbol": "COHR", "peers": ["APH", "GLW"], "custom": False}


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
