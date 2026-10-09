"""Portfolio risk from daily price history: beta, volatility, VaR/CVaR, drawdown, each position's
share of risk, correlations, historical stress scenarios and factor exposures.

Method: today's weights applied to each holding's daily returns over the last year (a
"holdings-based" view of the current portfolio, not of its past trades). A holding with a shorter
history is filled with beta x SPY on the days it didn't trade, and flagged.
"""

from __future__ import annotations

from datetime import date

import numpy as np

TRADING_DAYS = 252
MIN_OBS = 40  # fewer daily returns than this: beta is assumed 1 and the history marked thin
CORR_TOP = 12
SCENARIOS = [
    # (key, label, start, end): peak-to-trough windows of the S&P 500
    ("gfc", "2008 financial crisis", date(2007, 10, 9), date(2009, 3, 9)),
    ("covid", "COVID crash 2020", date(2020, 2, 19), date(2020, 3, 23)),
    ("rates", "2022 rate shock", date(2022, 1, 3), date(2022, 10, 12)),
    ("q4_2018", "Q4 2018 selloff", date(2018, 9, 20), date(2018, 12, 24)),
]
FACTOR_LABELS = {
    "Mkt-RF": "Market", "SMB": "Size (small minus big)", "HML": "Value (high minus low book/price)",
    "RMW": "Profitability (robust minus weak)", "CMA": "Investment (conservative minus aggressive)",
    "Mom": "Momentum",
}


def _close_on_or_before(closes: dict[date, float], d: date) -> tuple[date, float] | None:
    best = None
    for day in closes:
        if day <= d and (best is None or day > best):
            best = day
    return (best, closes[best]) if best else None


def analyze(values: dict[str, float], closes: dict[str, dict[date, float]], bench: str = "SPY",
            factors: dict[date, dict[str, float]] | None = None) -> dict:
    """`values`: market value per holding. `closes`: daily closes per symbol, the benchmark included
    (with enough history for the stress windows)."""
    total = sum(v for v in values.values() if v and v > 0)
    syms = [s for s, v in values.items() if v and v > 0]
    if total <= 0 or bench not in closes or len(closes[bench]) < MIN_OBS + 1:
        return {"available": False, "reason": "Not enough price history yet."}
    w = np.array([values[s] / total for s in syms])

    # -- one year of daily returns on the benchmark's trading days ---------------------------------
    days = sorted(closes[bench])[-(TRADING_DAYS + 1):]
    def series(sym):
        c = closes.get(sym, {})
        return np.array([c.get(d, np.nan) for d in days], dtype=float)
    def rets(p):
        with np.errstate(invalid="ignore", divide="ignore"):
            return p[1:] / p[:-1] - 1
    rm = rets(series(bench))
    raw = np.column_stack([rets(series(s)) for s in syms])  # T x N, NaN where a symbol didn't trade
    obs = np.sum(~np.isnan(raw), axis=0)
    betas = np.ones(len(syms))
    for i in range(len(syms)):
        ok = ~np.isnan(raw[:, i])
        if obs[i] >= MIN_OBS and np.var(rm[ok], ddof=1) > 0:
            betas[i] = np.cov(raw[ok, i], rm[ok])[0, 1] / np.var(rm[ok], ddof=1)
    filled = np.where(np.isnan(raw), betas * rm[:, None], raw)
    rp = filled @ w

    vol = float(np.std(rp, ddof=1) * np.sqrt(TRADING_DAYS))
    beta = float(np.cov(rp, rm)[0, 1] / np.var(rm, ddof=1)) if np.var(rm, ddof=1) > 0 else float(w @ betas)
    cov = np.cov(filled, rowvar=False) * TRADING_DAYS
    port_var = float(w @ cov @ w)
    risk_share = (w * (cov @ w)) / port_var if port_var > 0 else np.zeros(len(syms))
    asset_vol = np.sqrt(np.diag(cov))

    def var_cvar(level):
        cut = np.quantile(rp, 1 - level)
        tail = rp[rp <= cut]
        return {"var_pct": float(-cut * 100), "cvar_pct": float(-tail.mean() * 100),
                "var_value": float(-cut * total), "cvar_value": float(-tail.mean() * total)}

    growth = np.cumprod(1 + rp)
    drawdown = float((growth / np.maximum.accumulate(growth) - 1).min() * 100)

    positions = sorted(({
        "symbol": s, "weight_pct": float(w[i] * 100), "risk_pct": float(risk_share[i] * 100),
        "beta": float(betas[i]), "vol_pct": float(asset_vol[i] * 100), "history_days": int(obs[i]),
        "proxied": bool(obs[i] < len(rm) * 0.9),
    } for i, s in enumerate(syms)), key=lambda p: -p["risk_pct"])

    # -- correlations among the largest positions -------------------------------------------------
    top = [syms.index(s) for s in sorted(syms, key=lambda s: -values[s])[:CORR_TOP]]
    with np.errstate(invalid="ignore", divide="ignore"):  # a price that never moved has no correlation
        corr = np.corrcoef(filled[:, top], rowvar=False) if len(top) > 1 else np.ones((1, 1))

    # -- stress: replay history, or beta x SPY where a holding didn't exist ------------------------
    scenarios = []
    for key, label, start, end in SCENARIOS:
        b0, b1 = _close_on_or_before(closes[bench], start), _close_on_or_before(closes[bench], end)
        if not b0 or not b1 or (start - b0[0]).days > 7:
            continue  # the benchmark's cached history doesn't reach back that far
        spy_ret = b1[1] / b0[1] - 1
        impact, proxied = 0.0, []
        for i, s in enumerate(syms):
            c = closes.get(s, {})
            p0, p1 = _close_on_or_before(c, start), _close_on_or_before(c, end)
            if p0 and p1 and (start - p0[0]).days <= 7:
                r = p1[1] / p0[1] - 1
            else:  # listed after the window started: scale SPY's move by beta in log space, so a
                # high-beta proxy for a deep crash stays above -100% ((1 + r)^beta - 1)
                r = (1 + spy_ret) ** max(betas[i], 0.0) - 1
                proxied.append(s)
            impact += w[i] * r
        scenarios.append({"key": key, "label": label, "start": start.isoformat(), "end": end.isoformat(),
                          "spy_pct": spy_ret * 100, "portfolio_pct": impact * 100, "value": impact * total,
                          "proxied": proxied})
    scenarios.append({"key": "spy_down_10", "label": "SPY falls 10% (via beta)", "start": None, "end": None,
                      "spy_pct": -10.0, "portfolio_pct": float(w @ betas) * -10, "value": float(w @ betas) * -0.10 * total,
                      "proxied": []})

    return {
        "available": True,
        "as_of": days[-1].isoformat(),
        "lookback_days": int(len(rp)),
        "benchmark": bench,
        "total_value": total,
        "beta": beta,
        "volatility_pct": vol * 100,
        "benchmark_volatility_pct": float(np.std(rm, ddof=1) * np.sqrt(TRADING_DAYS) * 100),
        "max_drawdown_pct": drawdown,
        "var": {"95": var_cvar(0.95), "99": var_cvar(0.99)},
        "positions": positions,
        "correlation": {"symbols": [syms[i] for i in top],
                        "matrix": [[None if np.isnan(x) else float(x) for x in row] for row in np.atleast_2d(corr)]},
        "scenarios": scenarios,
        "factors": _factor_exposures(dict(zip(days[1:], rp)), factors) if factors else None,
    }


def _factor_exposures(rp_by_day: dict[date, float], factors: dict[date, dict[str, float]]) -> dict | None:
    """OLS of the portfolio's excess daily return on the five Fama-French factors plus momentum."""
    days = [d for d in rp_by_day if d in factors]
    if len(days) < 60:
        return None
    names = list(FACTOR_LABELS)
    X = np.column_stack([np.ones(len(days))] + [[factors[d][f] for d in days] for f in names])
    y = np.array([rp_by_day[d] - factors[d]["RF"] for d in days])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    dof = len(days) - X.shape[1]
    sigma2 = float(resid @ resid / dof)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
    r2 = 1 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return {
        "from": min(days).isoformat(), "to": max(days).isoformat(), "days": len(days), "r2": r2,
        "alpha_annual_pct": float(coef[0] * TRADING_DAYS * 100),
        "loadings": [{"factor": f, "label": FACTOR_LABELS[f], "beta": float(coef[i + 1]), "t": float(coef[i + 1] / se[i + 1])}
                     for i, f in enumerate(names)],
    }
