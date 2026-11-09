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

# -- B-146: one holding (np.cov returns a scalar) and none -----------------------------------------

def test_single_holding_carries_all_the_risk():
    days, rm = _walk(1, 400, start=date(2025, 1, 1))
    _, ra = _walk(2, 400, beta_to=rm, beta=2.0)
    out = risk.analyze({"A": 100.0}, {"SPY": _closes(days, rm), "A": _closes(days, ra)})
    assert out["available"]
    [pos] = out["positions"]
    assert pos["symbol"] == "A" and pos["weight_pct"] == pytest.approx(100) and pos["risk_pct"] == pytest.approx(100)
    assert out["beta"] == pytest.approx(pos["beta"]) and pos["beta"] == pytest.approx(2.0, abs=0.15)
    assert out["volatility_pct"] == pytest.approx(pos["vol_pct"]) and pos["vol_pct"] > 0
    assert out["var"]["99"]["var_pct"] > out["var"]["95"]["var_pct"] > 0
    assert out["correlation"] == {"symbols": ["A"], "matrix": [[1.0]]}


def test_no_holdings_is_a_clear_empty_result():
    days, rm = _walk(1, 400, start=date(2025, 1, 1))
    for values in ({}, {"A": 0.0}):
        out = risk.analyze(values, {"SPY": _closes(days, rm)})
        assert out == {"available": False, "reason": "No holdings with a market value to analyze."}


def test_risk_endpoint_with_one_holding_and_with_none(make_argus, monkeypatch):
    from fastapi.testclient import TestClient

    from argus.api.server import create_app

    days = [date(2026, 6, 1) + timedelta(days=i) for i in range(120) if (date(2026, 6, 1) + timedelta(days=i)).weekday() < 5]
    from datetime import datetime, time

    from argus.market_calendar import NY
    from argus.providers.base import Quote

    closes = {s: _closes(days, _walk(seed, len(days))[1]) for seed, s in enumerate(("SPY", "X"))}
    at_close = datetime.combine(days[-1], time(16, 5), NY)
    quotes = {s: Quote(s, c[days[-1]], c[days[-2]], c[days[-2]], c[days[-1]], c[days[-2]], at_close, "fake")
              for s, c in closes.items()}
    a = _risk_argus(make_argus, monkeypatch, closes, days[-1], quotes, held=("X",))
    a.portfolios.create_portfolio("empty")
    with TestClient(create_app(a, start_hub=False), base_url="http://localhost") as c:
        r = c.get("/api/portfolios/p/risk")
        assert r.status_code == 200 and r.json()["available"], r.json()
        assert [(p["symbol"], round(p["risk_pct"], 6)) for p in r.json()["positions"]] == [("X", 100.0)]
        r = c.get("/api/portfolios/empty/risk")
        assert r.status_code == 200 and not r.json()["available"] and "No holdings" in r.json()["reason"]


# -- B-142: the last session's close from quotes while Yahoo lags its daily bar --------------------

def _risk_argus(make_argus, monkeypatch, closes, last, quotes, held=("X", "Y")):
    from datetime import datetime, time

    import argus.app as app_mod
    from argus.providers.base import ProviderError
    from argus.market_calendar import NY
    from argus.services.portfolio import TxnInput

    class Provider:
        name = "fake"

        def get_quotes(self, symbols):
            return {s: q for s, q in quotes.items() if s in symbols}

    a = make_argus([Provider()])
    a.portfolios.create_portfolio("p")
    t0 = datetime.combine(min(closes["X"]), time(16), NY)
    a.portfolios.add_transactions("p", [TxnInput("BUY", s, t0, 10, 100) for s in held])
    monkeypatch.setattr(app_mod, "market_status", lambda *_: {"last_session": last.isoformat(), "session": "closed",
                                                              "is_trading_day": False})
    monkeypatch.setattr(a.market, "daily_closes_many", lambda syms, start: {s: dict(closes.get(s, {})) for s in syms})
    monkeypatch.setattr(a.factors, "daily", lambda: (_ for _ in ()).throw(ProviderError("offline")))
    return a


def test_risk_values_the_last_session_from_quotes_until_its_bar_arrives(make_argus, monkeypatch):
    """Yahoo's bars end a session before the quotes': risk takes that session's close from the quotes,
    as performance does, says so, and flags a latest-day loss beyond the 99% VaR; once the real bar is
    stored it wins, and the filled close is never stored."""
    from datetime import datetime, time

    from argus.market_calendar import NY
    from argus.providers.base import Quote

    days = [date(2026, 6, 1) + timedelta(days=i) for i in range(120) if (date(2026, 6, 1) + timedelta(days=i)).weekday() < 5]
    walks = {s: _closes(days, _walk(seed, len(days))[1]) for seed, s in enumerate(("SPY", "X", "Y"))}
    last, hist = days[-1], days[:-1]
    stored = {s: {d: c[d] for d in hist} for s, c in walks.items()}
    prev = {s: c[hist[-1]] for s, c in stored.items()}
    at_close = datetime.combine(last, time(16, 5), NY)
    quotes = {s: Quote(s, prev[s] * k, prev[s], prev[s], prev[s] * k, prev[s], at_close, "fake")
              for s, k in (("X", 0.9), ("Y", 0.9), ("SPY", 0.95))}

    a = _risk_argus(make_argus, monkeypatch, stored, last, quotes)
    r = a.risk("p")
    assert r["as_of"] == last.isoformat()
    assert r["closes_from_quotes"] == {"date": last.isoformat(), "symbols": ["SPY", "X", "Y"]}
    ld = r["last_day"]
    assert ld["date"] == last.isoformat() and ld["return_pct"] == pytest.approx(-10.0)
    # In dollars of the value before the fall: today's value is 90% of it.
    assert ld["value"] == pytest.approx(-r["total_value"] / 9) and ld["exceeds_var_99"]
    assert all(last not in c for c in stored.values())  # computed from, never stored

    # The real bar arrives (a smaller fall than the quote said): it's what risk uses.
    for s, c in stored.items():
        c[last] = prev[s] * 0.99
    r = a.risk("p")
    assert r["closes_from_quotes"] is None and r["as_of"] == last.isoformat()
    assert r["last_day"]["return_pct"] == pytest.approx(-1.0) and not r["last_day"]["exceeds_var_99"]
