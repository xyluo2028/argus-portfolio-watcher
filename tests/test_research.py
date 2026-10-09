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


def test_tone():
    assert r.tone("Nvidia beats estimates, shares surge on record growth")["label"] == "positive"
    assert r.tone("Shares plunge after guidance cut and SEC probe")["label"] == "negative"
    assert r.tone("Company to present at conference")["label"] == "neutral"
