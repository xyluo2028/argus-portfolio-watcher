from datetime import date

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


def test_build_rows_rejects_net_income_in_thousands():
    # Proxy pay-versus-performance tables tag net income in thousands as dollars, and SEC frames
    # serve the latest filing: LOAR-like 72,146 on $496M revenue, ESTC-like prior year = this year / 1000.
    tickers = [{"cik": 1, "ticker": "LOAR", "name": "Loar"}, {"cik": 2, "ticker": "ESTC", "name": "Elastic"}]
    annual = {"revenue": {1: 496_283_000.0, 2: 1_739_331_000.0}, "net_income": {1: 72_146.0, 2: 367_766_000.0}}
    prior = {"revenue": {1: 402_819_000.0, 2: 1_483_296_000.0}, "net_income": {1: 22_231.0, 2: 367_766.0}}
    rows = {r["symbol"]: r for r in sc.add_prices(sc.build_rows(tickers, annual, prior, {}), {
        "LOAR": {"market_cap": 5.9e9, "quote_type": "EQUITY"}, "ESTC": {"market_cap": 1e10, "quote_type": "EQUITY"}})}
    loar, estc = rows["LOAR"], rows["ESTC"]
    assert loar["net_income"] is None and loar["pe"] is None and loar["net_margin_pct"] is None
    assert loar["revenue"] == 496_283_000.0 and loar["ps"] == pytest.approx(5.9e9 / 496_283_000)
    assert estc["net_income"] == 367_766_000.0 and estc["pe"] == pytest.approx(1e10 / 367_766_000)
    assert estc["net_income_prev"] is None and estc["earnings_growth_pct"] is None


def test_screen_filters_sorts_and_skips_otc():
    rows = _rows()
    r = sc.screen(rows, {"market_cap": [500, None]}, sort="market_cap")
    assert [x["symbol"] for x in r["rows"]] == ["AAA", "CCC"]  # BBB is OTC
    assert [x["symbol"] for x in sc.screen(rows, {}, include_otc=True, sort="market_cap", descending=False)["rows"]] == ["CCC", "BBB", "AAA"]
    # BBB (a loss) has no P/E and drops out; CCC's P/E stands even though its revenue is unreliable
    assert {x["symbol"] for x in sc.screen(rows, {"pe": [None, 25]}, include_otc=True)["rows"]} == {"AAA", "CCC"}
    with pytest.raises(ValueError):
        sc.screen(rows, {"nope": [1, 2]})


# Quarterly frames for an INCY-like company (cik 1): FY2025 looked great, the latest quarter swung to a
# loss. Revenue in quarters 1-3 of 2026 and 2025 (and nothing for Q4: few companies file one).
Q_FRAMES = {
    "revenue": {"CY2026Q3": {1: 300.0, 2: 90.0}, "CY2026Q2": {1: 280.0, 2: 85.0, 3: 50.0}, "CY2026Q1": {1: 260.0, 2: 80.0},
                "CY2025Q3": {1: 250.0}, "CY2025Q2": {1: 240.0, 3: 40.0}, "CY2025Q1": {1: 230.0}},
    "operating_income": {"CY2026Q3": {1: -200.0}, "CY2026Q2": {1: 60.0}, "CY2026Q1": {1: 50.0},
                         "CY2025Q3": {1: 70.0}, "CY2025Q2": {1: 70.0}, "CY2025Q1": {1: 60.0}},
    "net_income": {"CY2026Q3": {1: -180.0}, "CY2026Q2": {1: 50.0}, "CY2026Q1": {1: 40.0},
                   "CY2025Q3": {1: 60.0}, "CY2025Q2": {1: 55.0}, "CY2025Q1": {1: 45.0}},
}
RECENT = ["CY2026Q3", "CY2026Q2", "CY2026Q1"]


def test_latest_quarter_growth_and_ttm_labelled():
    latest = sc.latest_quarters(Q_FRAMES, RECENT, 2025)
    assert latest[1]["period"] == "CY2026Q3" and latest[3]["period"] == "CY2026Q2"  # 3 hasn't filed Q3 yet
    rows = sc.add_prices(sc.build_rows(TICKERS, ANNUAL, PRIOR, INSTANT, latest, 2025, {1: "2025-12-31"}),
                         {"AAA": {"market_cap": 4000.0, "quote_type": "EQUITY"}})
    a = next(r for r in rows if r["symbol"] == "AAA")
    assert (a["fiscal_year"], a["fiscal_year_end"], a["latest_quarter"], a["ttm_through"]) == (2025, "2025-12-31", "Q3 2026", "Q3 2026")
    assert a["revenue_growth_q_yoy_pct"] == pytest.approx(20)  # 300 vs 250
    # TTM = FY2025 + Q1-Q3 2026 - Q1-Q3 2025: revenue 1000 + 840 - 720, op income 250 - 90 - 200, net income 200 - 90 - 160
    assert a["revenue_ttm"] == pytest.approx(1120) and a["net_income_ttm"] == pytest.approx(-50)
    assert a["operating_margin_ttm_pct"] == pytest.approx(-40 / 1120 * 100)
    assert a["pe"] == pytest.approx(20) and a["pe_ttm"] is None and a["roe_ttm_pct"] == pytest.approx(-5)
    c = next(r for r in rows if r["symbol"] == "CCC")
    # Gamma's revenue is unreliable (no TTM), and it has no year-ago quarter; Beta had no Q3 2025
    assert c["latest_quarter"] == "Q2 2026" and c["revenue_growth_q_yoy_pct"] == pytest.approx(25) and c["revenue_ttm"] is None
    b = next(r for r in sc.build_rows(TICKERS, ANNUAL, PRIOR, INSTANT, latest, 2025) if r["symbol"] == "BBB")
    assert b["latest_quarter"] == "Q3 2026" and b["revenue_growth_q_yoy_pct"] is None and b["ttm_through"] is None
    # A filter on the latest quarter: the screen drops rows without one
    assert [r["symbol"] for r in sc.screen(rows, {"revenue_growth_q_yoy_pct": [None, 22]}, today=TODAY)["rows"]] == ["AAA"]


TODAY = date(2026, 11, 18)


def test_a_stale_latest_quarter_is_flagged_and_fails_quarter_filters():
    # D's case: SEC's frames still end at Q1 2026 in November, though its Q2 and Q3 10-Qs are filed.
    # EEE (cik 5) has AAA's Q1 figures only; AAA's Q3 is a fiscal quarter ending 27 Sep.
    frames = {k: {p: v | ({5: v[1]} if p in ("CY2026Q1", "CY2025Q1") else {}) for p, v in by_p.items()}
              for k, by_p in Q_FRAMES.items()}
    tickers = [TICKERS[0], {"cik": 5, "ticker": "EEE", "name": "Stale"}]
    annual = {k: v | {5: v[1]} for k, v in ANNUAL.items()}
    latest = sc.latest_quarters(frames, RECENT, 2025, ends={"CY2026Q3": {1: "2026-09-27"}})
    quotes = {s: {"market_cap": 4000.0, "quote_type": "EQUITY"} for s in ("AAA", "EEE")}
    rows = sc.add_prices(sc.build_rows(tickers, annual, PRIOR | {"revenue": PRIOR["revenue"] | {5: 800.0}},
                                       INSTANT, latest, 2025), quotes)
    assert [(r["symbol"], r["latest_quarter"], r["quarter_end"]) for r in rows] == [
        ("AAA", "Q3 2026", "2026-09-27"), ("EEE", "Q1 2026", "2026-03-31")]
    assert next(r for r in rows if r["symbol"] == "EEE")["revenue_growth_q_yoy_pct"] == pytest.approx(260 / 230 * 100 - 100)
    hits = sc.screen(rows, {"revenue_growth_q_yoy_pct": [10, None]}, today=TODAY)["rows"]
    assert [(r["symbol"], r["quarter_stale"]) for r in hits] == [("AAA", False)]  # 13% growth, 7 months old: out
    every = {r["symbol"]: r for r in sc.screen(rows, {}, today=TODAY)["rows"]}
    eee = every["EEE"]
    assert eee["quarter_stale"] and eee["latest_quarter"] == "Q1 2026" and eee["pe"] == pytest.approx(20)  # FY figures stay
    assert all(eee[f] is None for f in sc.QUARTER_FIGURES)
    assert (eee["revenue_q"], eee["revenue_q_prev"], eee["ttm_through"]) == (None, None, None)  # B-184
    assert eee["revenue"] is not None and eee["revenue_growth_pct"] is not None  # FY figures stay
    aaa = every["AAA"]
    assert aaa["revenue_q"] is not None and aaa["revenue_q_prev"] is not None and aaa["ttm_through"] == "Q3 2026"
    # A filter on the latest quarter's revenue passes the current row only
    assert [r["symbol"] for r in sc.screen(rows, {"revenue_q": [1, None]}, today=TODAY)["rows"]] == ["AAA"]
    assert [r["symbol"] for r in sc.screen(rows, {"revenue_q": [1, None]}, today=date(2026, 7, 31))["rows"]] == ["AAA", "EEE"]
    assert not sc.screen(rows, {"operating_margin_ttm_pct": [None, None]}, today=TODAY)["rows"][1:]  # only AAA has TTM
    # The same row with its quarter still current (four months after it ended) passes.
    assert [r["symbol"] for r in sc.screen(rows, {"revenue_growth_q_yoy_pct": [10, None]}, today=date(2026, 7, 31))["rows"]] == ["AAA", "EEE"]


def test_ttm_is_the_year_when_the_latest_quarter_closes_it():
    frames = {"revenue": {"CY2025Q4": {1: 300.0}, "CY2024Q4": {1: 200.0}}}
    latest = sc.latest_quarters(frames, ["CY2025Q4", "CY2025Q3", "CY2025Q2"], 2025)
    a = sc.build_rows(TICKERS[:1], ANNUAL, PRIOR, INSTANT, latest, 2025)[0]
    assert a["revenue_growth_q_yoy_pct"] == pytest.approx(50) and a["revenue_ttm"] == 1000.0 and a["net_income_ttm"] == 200.0
    # A laggard whose newest quarter is still in the fiscal year gets growth but no TTM
    stale = sc.latest_quarters({"revenue": {"CY2025Q2": {1: 300.0}}}, ["CY2026Q1", "CY2025Q4", "CY2025Q3", "CY2025Q2"], 2025)
    assert sc.build_rows(TICKERS[:1], ANNUAL, PRIOR, INSTANT, stale, 2025)[0]["revenue_ttm"] is None


def test_ttm_counts_quarters_since_a_non_december_fiscal_year_closed():
    assert sc._closing_quarter("2026-02-01", 2025) == (2025, 4) and sc._closing_quarter("2026-02-28", 2025) == (2026, 1)
    assert sc._closing_quarter("2026-06-27", 2025) == (2026, 2) and sc._closing_quarter(None, 2025) == (2025, 4)
    # A fiscal year to March 2026 already holds CY2026Q1: TTM to Q3 2026 adds only Q2 and Q3 (less 2025's)
    latest = sc.latest_quarters(Q_FRAMES, RECENT, 2025, {1: "2026-03-31"})
    a = sc.build_rows(TICKERS[:1], ANNUAL, PRIOR, INSTANT, latest, 2025)[0]
    assert a["revenue_ttm"] == pytest.approx(1000 + 580 - 490) and a["net_income_ttm"] == pytest.approx(200 - 130 - 115)
    # One to June 2026 adds Q3 alone; one to June 2025 would need five quarters, more than were fetched
    june = sc.latest_quarters(Q_FRAMES, RECENT, 2025, {1: "2026-06-27"})
    assert sc.build_rows(TICKERS[:1], ANNUAL, PRIOR, INSTANT, june, 2025)[0]["revenue_ttm"] == pytest.approx(1050)
    old = sc.latest_quarters(Q_FRAMES, RECENT, 2025, {1: "2025-06-30"})
    assert sc.build_rows(TICKERS[:1], ANNUAL, PRIOR, INSTANT, old, 2025)[0]["revenue_ttm"] is None


def test_a_year_smaller_than_its_quarters_is_dropped_with_its_ttm():
    # FIX: a Q1 2026 10-Q tagged Q1 2025's revenue (and operating income) as calendar 2025's, and SEC's
    # CY2025 frame serves it. FY revenue 230 < Q3 2025's 250: no FY revenue, margins, P/S or TTM.
    annual = {"revenue": {1: 230.0}, "net_income": {1: 200.0}, "operating_income": {1: 60.0}, "gross_profit": {1: 90.0}}
    latest = sc.latest_quarters(Q_FRAMES, RECENT, 2025)
    a = sc.add_prices(sc.build_rows(TICKERS[:1], annual, PRIOR, INSTANT, latest, 2025),
                      {"AAA": {"market_cap": 4000.0, "quote_type": "EQUITY"}})[0]
    assert a["revenue_unreliable"] and a["revenue"] is None and a["ps"] is None
    assert a["net_margin_pct"] is None and a["gross_margin_pct"] is None and a["revenue_ttm"] is None
    assert a["operating_margin_ttm_pct"] is None
    # TTM below its newest quarter (a year short of a quarter's worth, mixed tags): flagged, no TTM
    short = {"revenue": {1: 255.0}, "net_income": {1: 200.0}}
    frames = {"revenue": {"CY2026Q3": {1: 300.0}, "CY2026Q2": {1: 100.0}, "CY2026Q1": {1: 100.0},
                          "CY2025Q3": {1: 250.0}, "CY2025Q2": {1: 250.0}, "CY2025Q1": {1: 250.0}}}
    b = sc.build_rows(TICKERS[:1], short, PRIOR, INSTANT, sc.latest_quarters(frames, RECENT, 2025), 2025)[0]
    assert b["revenue"] == 255.0 and b["revenue_unreliable"] and b["revenue_ttm"] is None and b["net_income_ttm"] is None
    # The healthy case is untouched
    ok = sc.build_rows(TICKERS[:1], ANNUAL, PRIOR, INSTANT, latest, 2025)[0]
    assert not ok["revenue_unreliable"] and ok["revenue_ttm"] == pytest.approx(1120)


class _FakeSec:
    def __init__(self):
        self.periods = set()

    def company_tickers(self):
        return TICKERS[:1]

    def frame(self, concept, unit, period):
        self.periods.add(period)
        if period == "CY2025":
            vals = {"Revenues": 1000.0, "NetIncomeLoss": 200.0, "OperatingIncomeLoss": 250.0}
            return {1: {"val": vals[concept], "end": "2025-12-31"}} if concept in vals else {}
        concept_key = {"Revenues": "revenue", "OperatingIncomeLoss": "operating_income", "NetIncomeLoss": "net_income"}.get(concept)
        v = Q_FRAMES.get(concept_key, {}).get(period, {}).get(1)
        end = "2026-09-27" if (concept, period) == ("Revenues", "CY2026Q3") else None  # a fiscal quarter
        return {1: {"val": v, "end": end}} if v is not None else {}


class _FakeYahoo:
    def market_caps(self, symbols):
        return {"AAA": {"price": 10.0, "market_cap": 4000.0, "quote_type": "EQUITY"}}


def test_build_fetches_quarterly_frames(tmp_path):
    from datetime import date
    sec = _FakeSec()
    svc = sc.ScreenerService(tmp_path, sec, _FakeYahoo())
    svc.build(today=date(2026, 11, 17))
    assert {"CY2026Q3", "CY2025Q1", "CY2026Q3I"} <= sec.periods and "CY2025Q4" not in sec.periods
    row = svc.load()["rows"][0]
    assert (row["fiscal_year_end"], row["latest_quarter"], row["quarter_end"]) == ("2025-12-31", "Q3 2026", "2026-09-27")
    assert row["revenue_growth_q_yoy_pct"] == pytest.approx(20) and row["revenue_ttm"] == pytest.approx(1120)
    assert row["pe"] == pytest.approx(20) and row["pe_ttm"] is None
