# Trader bot: paper account

Play money, started with $10,000.00. Orders fill at the middle of the last US session's range, (high + low) / 2; positions are valued at its close. No trades on days without a new session. Rewritten by `scripts/sim.py report` at the end of every round; the history is in `equity.csv`.

**As of the 2026-11-17 close**

| | |
|---|---|
| Account value | **$9,795.79** (-2.04% since the start) |
| SPY over the same sessions | -2.91% |
| Change since the previous session | −$137.25 |
| Cash | $1,200.11 |
| Invested (market value) | $8,595.69 |
| Realized P&L | +$0.00 |
| Dividends accrued, not yet recorded | $0.00 |
| Trades so far | 6 |

## Positions

| Symbol | Shares | Avg cost | Close | Value | Weight | Unrealized |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 4.6501 | 752.66 | 732.44 | $3,405.92 | 34.8% | −$94.03 (-2.69%) |
| XLV | 6.377 | 188.18 | 185.24 | $1,181.28 | 12.1% | −$18.72 (-1.56%) |
| ADBE | 4.9821 | 240.86 | 235.55 | $1,173.53 | 12.0% | −$26.45 (-2.20%) |
| LNG | 3.234 | 309.21 | 301.97 | $976.57 | 10.0% | −$23.41 (-2.34%) |
| META | 1.5764 | 634.35 | 618.87 | $975.59 | 10.0% | −$24.40 (-2.44%) |
| TMUS | 5.2579 | 171.17 | 167.90 | $882.80 | 9.0% | −$17.19 (-1.91%) |
| Cash | | | | $1,200.11 | 12.3% | |

## Trades for the 2026-11-17 session

None.

## Last 30 sessions

| Session | Account value | Return | SPY | Cash |
|---|---:|---:|---:|---:|
| 2026-11-17 | $9,795.79 | -2.04% | -2.91% | $1,200.11 |
| 2026-11-16 | $9,933.04 | -0.67% | -1.91% | $1,200.11 |
| 2026-11-13 | $10,033.40 | +0.33% | +0.00% | $2,100.10 |

To look at this account in your own Argus: sign in as the bot's account there, open **Data**, and restore `docs/loop/sim/bot0.json` (it replaces only that account's records).
