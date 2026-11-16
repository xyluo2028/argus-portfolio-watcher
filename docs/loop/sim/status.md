# Trader bot: paper account

Play money, started with $10,000.00. Orders fill at the middle of the last US session's range, (high + low) / 2; positions are valued at its close. No trades on days without a new session. Rewritten by `scripts/sim.py report` at the end of every round; the history is in `equity.csv`.

**As of the 2026-11-13 close**

| | |
|---|---|
| Account value | **$10,033.40** (+0.33% since the start) |
| SPY over the same sessions | +0.00% |
| Change since the previous session | first session |
| Cash | $2,100.10 |
| Invested (market value) | $7,933.30 |
| Realized P&L | +$0.00 |
| Dividends accrued, not yet recorded | $0.00 |
| Trades so far | 5 |

## Positions

| Symbol | Shares | Avg cost | Close | Value | Weight | Unrealized |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 4.6501 | 752.66 | 754.37 | $3,507.90 | 35.0% | +$7.95 (+0.23%) |
| ADBE | 4.9821 | 240.86 | 243.08 | $1,211.05 | 12.1% | +$11.06 (+0.92%) |
| XLV | 6.377 | 188.18 | 188.85 | $1,204.30 | 12.0% | +$4.30 (+0.36%) |
| META | 1.5764 | 634.35 | 641.69 | $1,011.56 | 10.1% | +$11.57 (+1.16%) |
| LNG | 3.234 | 309.21 | 308.75 | $998.50 | 10.0% | −$1.49 (-0.15%) |
| Cash | | | | $2,100.10 | 20.9% | |

## Trades for the 2026-11-13 session

| Side | Symbol | Shares | Mid price | Amount | Why |
|---|---|---:|---:|---:|---|
| BUY | SPY | 4.6501 | 752.66 | $3,499.94 | Core index position ~35%; buying the pullback (F&G 30). Thesis note #1. |
| BUY | ADBE | 4.9821 | 240.86 | $1,199.99 | Quality at P/E 13.6 (0th pct of 5y), FCF margin 41%, steady 12% growth. Thesis #2. |
| BUY | META | 1.5764 | 634.35 | $999.99 | Sold-off growth, P/E 22 (30th pct), rev +26%; smaller size for margin compression. Thesis #3. |
| BUY | LNG | 3.234 | 309.21 | $999.99 | Energy diversifier, estimates rising, negative 1y beta to SPY. Thesis #4. |
| BUY | XLV | 6.377 | 188.18 | $1,199.99 | Health care, strongest sector (1M +11%), low beta. Thesis #5. |

## Last 30 sessions

| Session | Account value | Return | SPY | Cash |
|---|---:|---:|---:|---:|
| 2026-11-13 | $10,033.40 | +0.33% | +0.00% | $2,100.10 |

To look at this account in your own Argus: sign in as the bot's account there, open **Data**, and restore `docs/loop/sim/bot0.json` (it replaces only that account's records).
