# Trader bot: paper account

Play money, started with $10,000.00. Orders fill at the middle of the last US session's range, (high + low) / 2; positions are valued at its close. No trades on days without a new session. Rewritten by `scripts/sim.py report` at the end of every round; the history is in `equity.csv`.

**As of the 2026-11-18 close**

| | |
|---|---|
| Account value | **$9,645.73** (-3.54% since the start) |
| SPY over the same sessions | -3.20% |
| Change since the previous session | −$150.06 |
| Cash | $250.11 |
| Invested (market value) | $9,395.62 |
| Realized P&L | +$0.00 |
| Dividends accrued, not yet recorded | $0.00 |
| Trades so far | 7 |

## Positions

| Symbol | Shares | Avg cost | Close | Value | Weight | Unrealized |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 4.6501 | 752.66 | 730.20 | $3,395.50 | 35.2% | −$104.44 (-2.98%) |
| XLV | 6.377 | 188.18 | 181.17 | $1,155.32 | 12.0% | −$44.67 (-3.72%) |
| ADBE | 4.9821 | 240.86 | 226.20 | $1,126.95 | 11.7% | −$73.04 (-6.09%) |
| META | 1.5764 | 634.35 | 616.38 | $971.66 | 10.1% | −$28.33 (-2.83%) |
| LNG | 3.234 | 309.21 | 296.49 | $958.85 | 9.9% | −$41.14 (-4.11%) |
| NVDA | 6.127 | 155.05 | 150.96 | $924.93 | 9.6% | −$25.06 (-2.64%) |
| TMUS | 5.2579 | 171.17 | 164.02 | $862.40 | 8.9% | −$37.59 (-4.18%) |
| Cash | | | | $250.11 | 2.6% | |

## Trades for the 2026-11-18 session

| Side | Symbol | Shares | Mid price | Amount | Why |
|---|---|---:|---:|---:|---|
| BUY | NVDA | 6.127 | 155.05 | $949.99 | Post-report entry: Q3 beat and raised guide, P/E TTM 19 (0th pct of 5y), ~9.4x FY+1 EPS; sized ~10% for governance risk. Thesis note id 8. |

## Last 30 sessions

| Session | Account value | Return | SPY | Cash |
|---|---:|---:|---:|---:|
| 2026-11-18 | $9,645.73 | -3.54% | -3.20% | $250.11 |
| 2026-11-17 | $9,795.79 | -2.04% | -2.91% | $1,200.11 |
| 2026-11-16 | $9,933.04 | -0.67% | -1.91% | $1,200.11 |
| 2026-11-13 | $10,033.40 | +0.33% | +0.00% | $2,100.10 |

To look at this account in your own Argus: sign in as the bot's account there, open **Data**, and restore `docs/loop/sim/bot0.json` (it replaces only that account's records).
