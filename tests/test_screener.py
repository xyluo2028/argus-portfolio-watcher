import pytest

from argus.services import screener as sc

TICKERS = [{"cik": 1, "ticker": "AAA", "name": "Alpha"}, {"cik": 1, "ticker": "AAA-B", "name": "Alpha"},
           {"cik": 2, "ticker": "BBB", "name": "Beta"}, {"cik": 3, "ticker": "CCC", "name": "Gamma"},
           {"cik": 4, "ticker": "DDD", "name": "No data"}]
ANNUAL = {"revenue": {1: 1000.0, 2: 500.0, 3: 10.0}, "net_income": {1: 200.0, 2: -50.0, 3: 900.0},
          "operating_income": {1: 250.0}, "gross_profit": {1: 600.0}, "cfo": {1: 300.0}, "capex": {1: 100.0}}
PRIOR = {"revenue": {1: 800.0, 2: 500.0}, "net_income": {1: 100.0}}
INSTANT = {"assets": {1: 2000.0}, "liabilities": {1: 1000.0}, "equity": {1: 1000.0, 2: -5.0},
           "current_assets": {1: 600.0}, "current_liabilities": {1: 300.0}, "cash": {}, "long_term_debt": {}}


def _rows():
    rows = sc.build_rows(TICKERS, ANNUAL, PRIOR, INSTANT)
    quotes = {"AAA": {"price": 50.0, "market_cap": 4000.0, "exchange": "NYSE", "exchange_code": "NYQ", "quote_type": "EQUITY"},
              "BBB": {"price": 5.0, "market_cap": 1000.0, "exchange": "Other OTC", "exchange_code": "PNK", "quote_type": "EQUITY"},
              "CCC": {"price": 9.0, "market_cap": 900.0, "exchange": "NasdaqGS", "exchange_code": "NMS", "quote_type": "EQUITY"}}
    return sc.add_prices(rows, quotes)


def test_build_rows_derives_ratios_one_row_per_company():
    rows = {r["symbol"]: r for r in _rows()}
    assert set(rows) == {"AAA", "BBB", "CCC"}  # one per CIK (first ticker); DDD has no figures
    a = rows["AAA"]
    assert a["revenue_growth_pct"] == pytest.approx(25) and a["earnings_growth_pct"] == pytest.approx(100)
    assert (a["gross_margin_pct"], a["net_margin_pct"], a["fcf_margin_pct"]) == pytest.approx((60, 20, 20))
    assert (a["roe_pct"], a["roa_pct"], a["debt_to_equity"], a["current_ratio"]) == pytest.approx((20, 10, 1, 2))
    assert (a["pe"], a["ps"], a["pb"], a["fcf_yield_pct"]) == pytest.approx((20, 4, 4, 5))
    b = rows["BBB"]
    assert b["pe"] is None and b["roe_pct"] is None and b["pb"] is None  # a loss, negative equity
    c = rows["CCC"]
    assert c["revenue_unreliable"] and c["net_margin_pct"] is None and c["ps"] is None  # profit 90x revenue


def test_screen_filters_sorts_and_skips_otc():
    rows = _rows()
    r = sc.screen(rows, {"market_cap": [500, None]}, sort="market_cap")
    assert [x["symbol"] for x in r["rows"]] == ["AAA", "CCC"]  # BBB is OTC
    assert [x["symbol"] for x in sc.screen(rows, {}, include_otc=True, sort="market_cap", descending=False)["rows"]] == ["CCC", "BBB", "AAA"]
    # BBB (a loss) has no P/E and drops out; CCC's P/E stands even though its revenue is unreliable
    assert {x["symbol"] for x in sc.screen(rows, {"pe": [None, 25]}, include_otc=True)["rows"]} == {"AAA", "CCC"}
    with pytest.raises(ValueError):
        sc.screen(rows, {"nope": [1, 2]})
