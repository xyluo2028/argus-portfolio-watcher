from datetime import UTC, date, datetime

import pytest

from argus.services.dividends import accrue, add_months, analyze, analyze_holding, frequency
from argus.services.portfolio import TxnInput

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


def test_lumpy_monthly_payer_uses_trailing_year():
    # SCHP-style TIPS ETF: monthly payments that swing with inflation accruals
    amounts = [0.092, 0.093, 0.177, 0.027, 0.096, 0.203, 0.221, 0.216, 0.077, 0.056]
    dates = ["2025-11-03", "2025-12-01", "2025-12-19", "2026-04-01", "2026-05-01", "2026-06-01",
             "2026-07-01", "2026-08-03", "2026-09-01", "2026-10-01"]
    h = analyze_holding(list(zip(dates, amounts)), 100, lambda d: 100, date(2026, 10, 21))
    assert h["frequency"] == "monthly" and not h["irregular"]
    assert h["trailing_12m"] == pytest.approx(1.258) and h["rate"] == pytest.approx(1.258)
    assert [x["per_share"] for x in h["projected"]] == pytest.approx([1.258 / 12] * 2)


def test_steady_and_one_way_monthly_payers_keep_last_payment_rate():
    # BND-style: small wobble around a level
    bnd = [0.237, 0.244, 0.239, 0.247, 0.245, 0.228, 0.25, 0.242, 0.247, 0.244, 0.252, 0.253, 0.249]
    h = analyze_holding([(f"{2025 + (m > 12)}-{(m - 1) % 12 + 1:02d}-01", a) for m, a in zip(range(10, 23), bnd)],
                        10, lambda d: 10, TODAY)
    assert h["rate"] == pytest.approx(0.249 * 12)
    # a big raise is a new rate, not lumpiness
    raised = [(f"2026-{m:02d}-01", 0.10 if m < 6 else 0.20) for m in range(1, 11)]
    assert analyze_holding(raised, 10, lambda d: 10, TODAY)["rate"] == pytest.approx(2.4)


def test_shares_bought_on_the_ex_date_miss_that_payment():
    hist = [(f"2026-{m:02d}-01", 0.27) for m in range(1, 11)]
    h = analyze_holding(hist, 20, lambda d: 0, TODAY)  # bought on/after Oct 1
    # Sun Nov 1 moves to Mon Nov 2
    assert h["received"] == [] and [x["ex_date"] for x in h["projected"]] == ["2026-11-02", "2026-12-01"]


def test_estimated_ex_dates_move_off_weekends_and_holidays():
    # quarterly on the 28th: Aug 28 -> Sat Nov 28 -> Mon Nov 30; monthly on the 26th: Thanksgiving -> Fri Nov 27
    h = analyze_holding([("2026-05-28", 0.5), ("2026-08-28", 0.5)], 1, lambda d: 1, TODAY)
    assert [x["ex_date"] for x in h["projected"]] == ["2026-11-30"]
    m = analyze_holding([(f"2026-{k:02d}-26", 0.1) for k in range(4, 10)], 1, lambda d: 1, TODAY)
    assert [x["ex_date"] for x in m["projected"]] == ["2026-10-26", "2026-11-27", "2026-12-28"]


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


# -- accrual from ex-dates held through ----------------------------------------
PG = {"PG": [("2026-07-24", 1.0568), ("2026-10-23", 1.089)]}


def _t(kind, d, qty=0.0, price=0.0, amount=0.0, sym="PG", hour=20):  # 16:00 ET
    return TxnInput(kind, sym, datetime(d.year, d.month, d.day, hour, tzinfo=UTC), qty, price, amount=amount)


def test_accrues_ex_dates_held_through():
    txns = [_t("BUY", date(2026, 10, 19), 31, 165)]
    out = accrue(txns, PG, date(2026, 10, 25))
    assert out == [{"symbol": "PG", "ex_date": "2026-10-23", "per_share": 1.089, "shares": 31,
                    "amount": pytest.approx(33.759)}]
    assert accrue(txns, PG, date(2026, 10, 22)) == []  # not ex yet


def test_no_accrual_for_shares_bought_on_or_after_the_ex_date_or_sold_before():
    assert accrue([_t("BUY", date(2026, 10, 23), 31, 162)], PG, date(2026, 10, 25)) == []
    sold = [_t("BUY", date(2026, 10, 1), 31, 160), _t("SELL", date(2026, 10, 22), 10, 165)]
    assert accrue(sold, PG, date(2026, 10, 25))[0]["shares"] == 21


def test_recorded_dividend_replaces_the_accrual():
    txns = [_t("BUY", date(2026, 7, 1), 31, 150),
            _t("DIVIDEND", date(2026, 8, 15), amount=32.76)]  # pays the 07-24 ex-date
    out = accrue(txns, PG, date(2026, 10, 25))
    assert [x["ex_date"] for x in out] == ["2026-10-23"]
    txns.append(_t("DIVIDEND", date(2026, 11, 16), amount=33.76))  # pay date for 10-23
    assert accrue(txns, PG, date(2026, 11, 20)) == []


def test_accrual_uses_split_adjusted_shares():
    hist = {"X": [("2026-09-01", 0.5)]}  # per share after the later 2:1 split
    txns = [_t("BUY", date(2026, 8, 1), 10, 100, sym="X"), _t("SPLIT", date(2026, 9, 15), 2, sym="X")]
    assert accrue(txns, hist, date(2026, 10, 1))[0]["amount"] == pytest.approx(10.0)
