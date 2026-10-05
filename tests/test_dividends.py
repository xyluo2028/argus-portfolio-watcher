from datetime import date

import pytest

from argus.services.dividends import add_months, analyze, analyze_holding, frequency

TODAY = date(2026, 10, 5)


def test_frequency_from_gaps():
    monthly = [date(2026, m, 1) for m in range(4, 11)]
    quarterly = [date(2025, 12, 4), date(2026, 3, 11), date(2026, 6, 4), date(2026, 9, 10)]
    assert (frequency(monthly), frequency(quarterly), frequency([date(2026, 5, 1)])) == (12, 4, 1)
    # a missing quarter in the data (BNS-style) doesn't turn it semiannual
    assert frequency([date(2025, 4, 1), date(2025, 7, 2), date(2026, 4, 7), date(2026, 7, 7)]) == 4


def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 30), 2) == date(2027, 1, 30)


def test_forward_rate_uses_latest_payment_so_raises_show_up():
    hist = [("2025-12-04", 0.01), ("2026-03-11", 0.01), ("2026-06-04", 0.25), ("2026-09-10", 0.25)]
    h = analyze_holding(hist, 50, lambda d: 50 if d >= date(2026, 8, 25) else 0, TODAY)
    assert h["frequency"] == "quarterly" and h["rate"] == pytest.approx(1.0)
    assert [x["ex_date"] for x in h["received"]] == ["2026-09-10"]          # held only from Aug 25
    assert [x["ex_date"] for x in h["projected"]] == ["2026-12-10"]
    assert h["received"][0]["amount"] == pytest.approx(12.5)


def test_shares_bought_on_the_ex_date_miss_that_payment():
    hist = [(f"2026-{m:02d}-01", 0.27) for m in range(1, 11)]
    h = analyze_holding(hist, 20, lambda d: 0, TODAY)  # bought on/after Oct 1
    assert h["received"] == [] and [x["ex_date"] for x in h["projected"]] == ["2026-11-01", "2026-12-01"]


def test_stale_payer_is_not_extrapolated_and_non_payers_are_zero():
    stale = analyze_holding([("2025-11-01", 1.0), ("2026-02-01", 1.0)], 10, lambda d: 10, TODAY)
    assert stale["irregular"] and stale["projected"] == [] and stale["rate"] == pytest.approx(2.0)
    none = analyze_holding([], 10, lambda d: 10, TODAY)
    assert (none["pays"], none["rate"]) == (False, 0.0)


def test_portfolio_totals_and_months():
    rows = [{"symbol": "BND", "qty": 10, "avg_cost": 72, "cost_basis": 720, "price": 70, "market_value": 700},
            {"symbol": "TSLA", "qty": 1, "avg_cost": 300, "cost_basis": 300, "price": 300, "market_value": 300}]
    hist = {"BND": [(f"2026-{m:02d}-01", 0.25) for m in range(1, 11)]}
    out = analyze(rows, hist, lambda s, d: 10 if s == "BND" else 1, TODAY)
    t = out["totals"]
    assert t["annual_income"] == pytest.approx(30) and t["yield_pct"] == pytest.approx(3.0)
    assert t["received"] == pytest.approx(25) and t["projected"] == pytest.approx(5) and t["year_total"] == pytest.approx(30)
    assert (t["payers"], t["positions"]) == (1, 2)
    assert [round(m["received"] + m["projected"], 2) for m in out["by_month"]] == [2.5] * 12
