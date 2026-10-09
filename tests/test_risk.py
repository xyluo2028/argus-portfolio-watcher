from datetime import date, timedelta

import numpy as np
import pytest

from argus.providers.french import parse_csv
from argus.services import risk


def _walk(seed, n, start=date(2007, 9, 3), vol=0.01, beta_to=None, beta=1.0):
    rng = np.random.default_rng(seed)
    days = [start + timedelta(days=i) for i in range(n)]
    if beta_to is None:
        r = rng.normal(0.0003, vol, n)
    else:
        r = beta * beta_to + rng.normal(0, vol / 3, n)
    return days, r


def _closes(days, r, p0=100.0):
    p = p0 * np.cumprod(1 + r)
    return {d: float(x) for d, x in zip(days, p)}


def test_beta_vol_var_and_risk_shares():
    days, rm = _walk(1, 400, start=date(2025, 1, 1))
    _, ra = _walk(2, 400, beta_to=rm, beta=2.0)
    _, rb = _walk(3, 400, beta_to=rm, beta=0.5)
    closes = {"SPY": _closes(days, rm), "A": _closes(days, ra), "B": _closes(days, rb)}
    out = risk.analyze({"A": 50.0, "B": 50.0}, closes)
    pos = {p["symbol"]: p for p in out["positions"]}
    assert pos["A"]["beta"] == pytest.approx(2.0, abs=0.15) and pos["B"]["beta"] == pytest.approx(0.5, abs=0.15)
    assert out["beta"] == pytest.approx(1.25, abs=0.1)
    assert sum(p["risk_pct"] for p in out["positions"]) == pytest.approx(100)
    assert pos["A"]["risk_pct"] > 70  # same weight, far more risk
    assert out["var"]["99"]["var_pct"] > out["var"]["95"]["var_pct"] > 0
    assert out["var"]["95"]["cvar_pct"] >= out["var"]["95"]["var_pct"]
    assert out["correlation"]["symbols"] == ["A", "B"] and out["correlation"]["matrix"][0][0] == pytest.approx(1)


def test_stress_replays_history_and_proxies_late_listings():
    days = [date(2007, 9, 3) + timedelta(days=i) for i in range(7000)]
    noise = np.random.default_rng(9).normal(0, 0.01, len(days))
    spy = {d: 100.0 * (1 + n) for d, n in zip(days, noise)}
    spy[date(2007, 10, 9)], spy[date(2009, 3, 9)] = 100.0, 50.0  # SPY halves over the 2008 window
    old = {d: 100.0 if d <= date(2007, 10, 9) else 80.0 for d in days}           # listed before: actual -20%
    young = {d: 10.0 + 0.001 * i for i, d in enumerate(days) if d >= date(2015, 1, 1)}  # listed later: proxied
    out = risk.analyze({"OLD": 50.0, "NEW": 50.0}, {"SPY": spy, "OLD": old, "NEW": young})
    gfc = next(s for s in out["scenarios"] if s["key"] == "gfc")
    assert gfc["spy_pct"] == pytest.approx(-50)
    assert gfc["proxied"] == ["NEW"] and gfc["portfolio_pct"] > -100
    spy10 = next(s for s in out["scenarios"] if s["key"] == "spy_down_10")
    assert spy10["portfolio_pct"] < 0


def test_proxy_never_loses_more_than_everything():
    beta, spy = 4.2, -0.565
    assert (1 + spy) ** beta - 1 > -1


def test_factor_regression_recovers_loadings():
    days, mkt = _walk(5, 300, start=date(2025, 1, 1))
    rng = np.random.default_rng(6)
    smb, mom = rng.normal(0, 0.005, 300), rng.normal(0, 0.005, 300)
    rp = {d: 1.2 * m + 0.5 * s - 0.3 * mo + rng.normal(0, 0.0005) for d, m, s, mo in zip(days, mkt, smb, mom)}
    factors = {d: {"Mkt-RF": m, "SMB": s, "HML": 0.0 + rng.normal(0, 1e-4), "RMW": rng.normal(0, 1e-4),
                   "CMA": rng.normal(0, 1e-4), "Mom": mo, "RF": 0.0} for d, m, s, mo in zip(days, mkt, smb, mom)}
    f = risk._factor_exposures(rp, factors)
    load = {l["factor"]: l["beta"] for l in f["loadings"]}
    assert load["Mkt-RF"] == pytest.approx(1.2, abs=0.05) and load["SMB"] == pytest.approx(0.5, abs=0.08)
    assert load["Mom"] == pytest.approx(-0.3, abs=0.08) and f["r2"] > 0.9


def test_french_csv_parsing():
    text = "This file was created...\n\n,Mkt-RF,SMB,HML,RMW,CMA,RF\n20260828,  0.50, -0.10,  0.20, 0.00, 0.10, 0.01\n\nCopyright 2026\n"
    assert parse_csv(text) == {"2026-08-28": {"Mkt-RF": 0.005, "SMB": -0.001, "HML": 0.002, "RMW": 0.0, "CMA": 0.001, "RF": 0.0001}}
