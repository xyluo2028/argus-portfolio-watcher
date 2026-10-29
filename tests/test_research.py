from datetime import date

import pytest

from argus.services import research as r


def _st(**years):
    """Statements with two fiscal years: each kwarg row=(latest, prior)."""
    bs_rows = {"Total Assets", "Long Term Debt", "Current Assets", "Current Liabilities", "Ordinary Shares Number",
               "Working Capital", "Retained Earnings", "Total Liabilities Net Minority Interest"}
    cf_rows = {"Operating Cash Flow"}
    out = {"years": ["2026-01-31", "2025-01-31"], "balance": {}, "income": {}, "cashflow": {}}
    for k, v in years.items():
        name = k.replace("_", " ")
        part = "balance" if name in bs_rows else "cashflow" if name in cf_rows else "income"
        out[part][name] = list(v)
    return out


GOOD = _st(Net_Income=(120, 100), Total_Assets=(1000, 1000), Operating_Cash_Flow=(150, 110),
           Long_Term_Debt=(100, 200), Current_Assets=(500, 400), Current_Liabilities=(200, 200),
           Ordinary_Shares_Number=(100, 100), Total_Revenue=(800, 700), Gross_Profit=(400, 300))


def test_piotroski_all_pass_and_missing_lines_are_unknown():
    p = r.piotroski(GOOD)
    assert (p["score"], p["out_of"], p["label"]) == (9, 9, "strong")
    partial = {**GOOD, "balance": {k: v for k, v in GOOD["balance"].items() if k != "Current Assets"}}
    p2 = r.piotroski(partial)
    assert p2["out_of"] == 8 and next(t for t in p2["tests"] if "Current ratio" in t["test"])["pass"] is None
    assert r.piotroski({"years": ["2026"]})["available"] is False


def test_piotroski_counts_failures():
    bad = _st(Net_Income=(-50, 10), Total_Assets=(1000, 1000), Operating_Cash_Flow=(-20, 5),
              Long_Term_Debt=(300, 100), Current_Assets=(300, 400), Current_Liabilities=(300, 200),
              Ordinary_Shares_Number=(130, 100), Total_Revenue=(600, 700), Gross_Profit=(200, 300))
    p = r.piotroski(bad)
    passed = [t["test"] for t in p["tests"] if t["pass"]]
    # Losing less cash (-20) than accounting profit (-50) still passes the accrual test, as Piotroski defines it.
    assert passed == ["Cash flow exceeds net income (quality of earnings)"] and p["label"] == "weak"


def test_altman_z_zones():
    st = _st(Total_Assets=(1000, 1000), Working_Capital=(200, 0), Retained_Earnings=(300, 0), EBIT=(150, 0),
             Total_Liabilities_Net_Minority_Interest=(500, 0), Total_Revenue=(1000, 0))
    z = r.altman_z(st, market_cap=1500)
    expected = 1.2 * 0.2 + 1.4 * 0.3 + 3.3 * 0.15 + 0.6 * 3.0 + 1.0
    assert z["z"] == pytest.approx(expected) and z["zone"] == "safe"
    assert r.altman_z(st, market_cap=None)["available"] is False
    assert r.altman_z(st, 1500, sector="Financial Services")["caveat"]


def test_insider_summary_counts_only_open_market_trades():
    rows = [
        {"name": "A", "change": -1000, "transactionPrice": 50, "transactionCode": "S", "transactionDate": "2026-09-01"},
        {"name": "B", "change": 200, "transactionPrice": 40, "transactionCode": "P", "transactionDate": "2026-08-01"},
        {"name": "C", "change": 5000, "transactionPrice": 0, "transactionCode": "A", "transactionDate": "2026-07-01"},
        {"name": "D", "change": -999, "transactionPrice": 10, "transactionCode": "S", "transactionDate": "2025-01-01"},  # too old
    ]
    s = r.insider_summary(rows, today=date(2026, 10, 9))
    assert s["since"] == "2025-10-09"
    assert (s["buy_count"], s["buy_value"], s["sell_count"], s["sell_value"]) == (1, 8000, 1, 50000)
    assert [x["kind"] for x in s["recent"]] == ["Sale", "Buy", "Award"]


def test_valuation_bands_percentile_and_losses_left_out():
    hist = [{"period": f"{y}-{m:02d}-28", "v": v} for (y, m), v in zip(
        [(2022, 3), (2022, 6), (2022, 9), (2023, 3), (2024, 3), (2025, 3), (2026, 3)], [40, 30, -5, 20, 50, 60, 10])]
    b = r.valuation_bands({"peTTM": hist}, {"peTTM": 25.0}, today=date(2026, 10, 9))
    pe = b[0]
    assert pe["label"] == "P/E" and pe["min"] == 10 and pe["max"] == 60 and pe["points"] == 6  # -5 dropped
    assert pe["percentile"] == pytest.approx(2 / 6 * 100)  # 10 and 20 are at or below 25


def test_band_rerated_at_a_new_current_value():
    hist = [{"period": f"{y}-03-28", "v": v} for y, v in zip(range(2021, 2027), [40, 30, -5, 20, 50, 10])]
    pe = r.valuation_bands({"peTTM": hist}, {"peTTM": 25.0}, today=date(2026, 10, 9))[0]
    moved = r.with_current(pe, 45.0)
    assert moved["current"] == 45.0 and moved["percentile"] == pytest.approx(3 / 4 * 100)  # 2021 is outside 5 years
    assert r.with_current(pe, None)["percentile"] is None and moved["median"] == pe["median"]


def test_tone():
    assert r.tone("Nvidia beats estimates, shares surge on record growth")["label"] == "positive"
    assert r.tone("Shares plunge after guidance cut and SEC probe")["label"] == "negative"
    assert r.tone("Company to present at conference")["label"] == "neutral"


def test_growth_profile_history_and_forward():
    quarterly = [{"period_end": f"{y}-{m:02d}-28", "revenue": rev, "net_income": ni, "gross_margin_pct": 60.0}
                 for (y, m), rev, ni in zip([(2025, 3), (2025, 6), (2025, 9), (2025, 12), (2026, 3), (2026, 6)],
                                            [100, 110, 120, 130, 150, 165], [10, 11, 12, 13, 20, 22])]
    annual = [{"period_end": f"{y}-12-31", "revenue": rev, "net_income": rev / 10}
              for y, rev in [(2020, 100), (2021, 120), (2022, 150), (2023, 200), (2024, 260), (2025, 330)]]
    analyst = {"revenue_estimate": {"0y": {"avg": 700.0, "low": 650.0, "high": 750.0, "growth": 0.4, "numberOfAnalysts": 9}},
               "earnings_estimate": {"0y": {"avg": 2.0, "growth": 0.5, "numberOfAnalysts": 8, "yearAgoEps": 1.33}},
               "growth_estimates": {"0y": {"stockTrend": 0.5, "indexTrend": 0.12}, "LTG": {"stockTrend": None, "indexTrend": 0.1}}}
    g = r.growth_profile(quarterly, annual, {"eps_growth_5y_pct": 30.0, "peg": 0.8}, analyst)
    q = g["quarters"][0]  # newest first
    assert q["period_end"] == "2026-06-28" and q["revenue_yoy_pct"] == pytest.approx(50) and q["net_income_yoy_pct"] == pytest.approx(100)
    assert g["quarters"][-1]["revenue_yoy_pct"] is None  # nothing a year before the oldest quarter
    assert g["filed_cagr"]["revenue_5y"] == pytest.approx(((330 / 100) ** (1 / 5) - 1) * 100)
    assert g["filed_cagr"]["revenue_3y"] == pytest.approx(((330 / 150) ** (1 / 3) - 1) * 100)
    assert g["reported"]["eps_5y"] == 30.0 and g["peg"] == 0.8
    fy = next(f for f in g["forward"] if f["horizon"] == "0y")
    assert (fy["revenue_growth_pct"], fy["eps_growth_pct"], fy["index_eps_growth_pct"]) == pytest.approx((40, 50, 12))
    assert [f["horizon"] for f in g["forward"]] == ["0y"]  # LTG has only the index's figure: skipped


class _ColdFinnhub:
    """Fundamentals provider and ratio history in one, like Finnhub's /stock/metric."""
    name = "finnhub"

    def __init__(self):
        self.metric_calls, self.fail = 0, False
        self.series = {k: [{"period": f"{y}-{m:02d}-28", "v": v + y - 2021 + m / 10}
                           for y in range(2021, 2026) for m in (3, 6, 9, 12)]
                       for k, v in (("peTTM", 20.0), ("psTTM", 2.0), ("pb", 3.0), ("evEbitdaTTM", 12.0))}
        self._fetched = False

    def get_metrics(self, symbol):
        from argus.providers.base import ProviderError
        self.metric_calls += 1
        if self.fail:
            raise ProviderError("finnhub: 429 rate limited")
        self._fetched = True
        return {"pe_ttm": 22.0, "ps_ttm": 2.1204, "pb": 4.0, "ev_ebitda": 14.0,
                "revenue_growth_q_yoy_pct": 18.31, "revenue_growth_yoy_pct": 25.0}

    def ratio_series(self, symbol):
        if not self._fetched:
            self.get_metrics(symbol)
        return self.series

    def insider_transactions(self, symbol, since):
        return []


def test_research_cold_fundamentals_are_fetched_and_partial_results_not_kept(make_argus):
    fh = _ColdFinnhub()
    a = make_argus(fundamentals=[fh])
    a.market.directory = fh
    assert a.market.cached_fundamentals(["BCRX"]) == {}  # cold cache

    fh.fail = True  # the first build hits a rate limit: nothing to fill the bands with
    first = a.research("BCRX")
    assert first["partial"] and all(b["current"] is None for b in first["valuation"] or [{"current": None}])
    assert a.research("BCRX")["as_of"] == first["as_of"]  # kept briefly, not rebuilt on every call
    a._research["BCRX"] = (a._research["BCRX"][0] - a.RESEARCH_RETRY_S - 1, first)  # ...but not as final

    fh.fail = False
    fh.metric_calls = 0
    out = a.research("BCRX")
    bands = {b["key"]: b for b in out["valuation"]}
    assert bands["psTTM"]["current"] == 2.1204 and bands["psTTM"]["percentile"] is not None
    assert bands["peTTM"]["current"] == 22.0 and bands["evEbitdaTTM"]["current"] == 14.0
    assert out["growth"]["reported"]["revenue_q_yoy"] == 18.31
    assert fh.metric_calls == 1  # the ratio history came with the fundamentals call
    assert not out["partial"] and "fundamentals" not in out["errors"]
    assert a.market.cached_fundamentals(["BCRX"])["BCRX"]["metrics"]["ps_ttm"] == 2.1204  # stored

    # A complete result is cached for the hour; a warm build doesn't refetch fundamentals.
    assert a.research("BCRX")["as_of"] == out["as_of"]
    a.research("BCRX", refresh=True)
    assert fh.metric_calls == 1


def _month(period, sb=0, b=0, h=0, s=0, ss=0):
    return {"period": period, "strongBuy": sb, "buy": b, "hold": h, "sell": s, "strongSell": ss}


def test_analyst_consensus_all_buys_is_never_none():
    # INOD: Yahoo sends recommendationKey "none" and no mean while 4 analysts rate it a buy.
    info = {"recommendationKey": "none", "recommendationMean": None, "numberOfAnalystOpinions": 4}
    c = r.analyst_consensus(info, [_month("0m", sb=1, b=3)])
    assert c == {"count": 4, "rating": "buy", "rating_mean": 1.75, "rating_source": "counts", "target_count": 4}
    assert r.analyst_consensus(info, [_month("0m", sb=3, b=1)])["rating"] == "strong_buy"


def test_analyst_consensus_comes_from_the_counts_not_yahoo_headline():
    # KRYS: Yahoo says "strong buy", mean 1.25, 9 analysts; the counts beside it are 1 strong buy, 10 buy, 1 hold.
    info = {"recommendationKey": "strong_buy", "recommendationMean": 1.25, "numberOfAnalystOpinions": 9}
    trend = [_month("-1m", sb=5, b=1), _month("0m", sb=1, b=10, h=1)]
    c = r.analyst_consensus(info, trend)
    assert (c["count"], c["rating"], c["rating_mean"], c["rating_source"]) == (12, "buy", 2.0, "counts")
    assert c["target_count"] == 9  # Yahoo's count is the number of price targets
    assert r.analyst_consensus({}, [_month("0m", h=2, s=3, ss=1)])["rating"] == "sell"


def test_analyst_consensus_falls_back_to_yahoo_without_counts():
    info = {"recommendationKey": "hold", "recommendationMean": 2.8, "numberOfAnalystOpinions": 5}
    assert r.analyst_consensus(info, []) == {"count": 5, "rating": "hold", "rating_mean": 2.8,
                                             "rating_source": "yahoo", "target_count": 5}
    # "none" with a mean: label the mean rather than show "none"
    assert r.analyst_consensus(info | {"recommendationKey": "none", "recommendationMean": 1.9}, [])["rating"] == "buy"
    assert r.analyst_consensus({}, [_month("0m")])["rating"] is None  # no coverage at all
