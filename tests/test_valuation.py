"""DCF calculator inputs (services/valuation.py) and saved models."""

from datetime import date

import pytest

from argus.errors import ArgusError
from argus.services import valuation as v

QUARTER_ENDS = ["2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"]


def _quarters(**fields):
    return [{"period_end": d, **{k: vals[i] for k, vals in fields.items()}} for i, d in enumerate(QUARTER_ENDS)]


def test_ttm_series_sums_back_to_back_quarters_only():
    q = _quarters(revenue=[10, 11, 12, 13, 14, None])
    assert v.ttm_series(q, "revenue") == {date(2025, 12, 31): 46, date(2026, 3, 31): 50}
    gap = [p for p in _quarters(revenue=[1] * 6) if p["period_end"] != "2025-09-30"]
    assert v.ttm_series(gap, "revenue") == {}


def test_multiples_come_from_finnhub_or_from_p_s():
    q = _quarters(revenue=[10] * 6, operating_cash_flow=[5, 5, 5, 5, 5, -40])
    series = {"peTTM": [{"period": "2026-03-31", "v": 30.0}, {"period": "2025-12-31", "v": -5.0}],
              "psTTM": [{"period": "2026-03-29", "v": 4.0}, {"period": "2025-12-31", "v": 3.0}]}
    assert v.multiple_history("net_income", series, q) == [(date(2026, 3, 31), 30.0)]  # a loss has no multiple
    # P/OCF = P/S x revenue / OCF, matched to the filing's quarter end within a few days.
    assert v.multiple_history("operating_cash_flow", series, q) == [(date(2025, 12, 31), 6.0), (date(2026, 3, 31), 8.0)]


def test_analyst_growth_prefers_long_term_eps_growth():
    analyst = {"growth_estimates": {"LTG": {"stockTrend": 0.12}}, "earnings_estimate": {"+1y": {"growth": 0.3}},
               "revenue_estimate": {"+1y": {"growth": 0.08}}}
    assert v.analyst_growth("free_cash_flow", analyst) == pytest.approx((12.0, "analysts' long-term EPS growth, per year"))
    assert v.analyst_growth("net_income", {"earnings_estimate": {"+1y": {"growth": 0.3}}})[0] == pytest.approx(30.0)
    assert v.analyst_growth("revenue", analyst)[0] == pytest.approx(8.0)
    assert v.analyst_growth("revenue", {}) == (None, None)


def test_share_change_is_yearly_and_split_adjusted_input():
    st = {"years": ["2025-12-31", "2024-12-31", "2023-12-31"], "income": {"Diluted Average Shares": [81.0, 90.0, 100.0]}}
    change, years = v.share_change(st)
    assert years == 2 and change == pytest.approx(-10.0)
    assert v.share_change({}) == (None, None)


def test_build_leaves_a_metric_that_stopped_being_reported_without_a_value():
    q = _quarters(revenue=[100] * 6, free_cash_flow=[5, 5, 5, 5, None, None], operating_cash_flow=[9] * 6)
    years = {"company": "X", "periods": [{"period_end": f"{y}-12-31", "revenue": 300 + 20 * i, "free_cash_flow": 10}
                                         for i, y in enumerate(range(2019, 2026))], "units": {"revenue": "USD"}}
    out = v.build("X", 10.0, {"market_cap": 4000.0, "dividend_yield_pct": 2.0}, {"periods": q}, years, {}, {}, {}, {},
                  date(2026, 8, 1))
    assert out["shares"] == 400 and out["dps"] == pytest.approx(0.2)
    rev, ocf, fcf = (out["metrics"][k] for k in ("revenue", "operating_cash_flow", "free_cash_flow"))
    assert rev["base"] == 400 and rev["base_basis"] == "last four quarters" and rev["multiple"]["current"] == 10
    assert rev["growth"]["hist_5y"] == pytest.approx(((420 / 320) ** 0.2 - 1) * 100)
    assert ocf["base"] == 36
    # Its last full quarters and its last year both end over a quarter before the newest filing.
    assert fcf["base"] is None and fcf["annual"][-1]["value"] == 10


def test_build_uses_the_fiscal_year_for_annual_only_filers():
    years = {"periods": [{"period_end": "2025-12-31", "net_income": 50.0}], "units": {"net_income": "EUR"}}
    ni = v.build("X", 10.0, {}, {}, years, {}, {}, {}, {}, date(2026, 5, 1))["metrics"]["net_income"]
    assert (ni["base"], ni["base_basis"], ni["currency"]) == (50.0, "last fiscal year", "EUR")


def test_inputs_are_checked():
    good = {"metric": "revenue", "base": 1e9, "years": 5, "growth": 10, "decay": 0, "multiple": 3, "target_return": 10,
            "dps": 0, "dividend_growth": 0, "share_change": -1}
    assert v.clean_inputs(good)["years"] == 5
    for bad in ({**good, "metric": "ebitda"}, {**good, "growth": "fast"}, {**good, "years": 0}, {**good, "multiple": float("nan")}):
        with pytest.raises(ArgusError):
            v.clean_inputs(bad)


def test_saved_models_round_trip_and_travel_in_snapshots(make_argus, tmp_path):
    a = make_argus()
    inputs = {"metric": "operating_cash_flow", "base": 168.3e9, "years": 3, "growth": 20, "decay": 0, "multiple": 17,
              "target_return": 10, "dps": 0, "dividend_growth": 0, "share_change": 0}
    saved = a.save_valuation("amzn", inputs, "ui")
    assert saved["inputs"]["multiple"] == 17
    assert [m["symbol"] for m in a.valuation_models()] == ["AMZN"]
    a.snapshots.dump(tmp_path / "s.json")
    assert a.snapshots.load(tmp_path / "s.json")["counts"]["valuation_model"] == 1
    assert a.save_valuation("AMZN", None) is None and a.valuation_models() == []
