# Trader bot: paper account

Play money, started with $10,000.00. Orders fill at the middle of the last US session's range, (high + low) / 2; positions are valued at its close. No trades on days without a new session. Rewritten by `scripts/sim.py report` at the end of every round; the history is in `equity.csv`.

**As of the 2026-11-19 close**

| | |
|---|---|
| Account value | **$9,459.17** (-5.41% since the start) |
| SPY over the same sessions | -5.10% |
| Change since the previous session | −$186.56 |
| Cash | $250.11 |
| Invested (market value) | $9,209.06 |
| Realized P&L | +$0.00 |
| Dividends accrued, not yet recorded | $0.00 |
| Trades so far | 7 |

## Positions

| Symbol | Shares | Avg cost | Close | Value | Weight | Unrealized |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 4.6501 | 752.66 | 715.87 | $3,328.87 | 35.2% | −$171.08 (-4.89%) |
| XLV | 6.377 | 188.18 | 177.46 | $1,131.66 | 12.0% | −$68.33 (-5.69%) |
| ADBE | 4.9821 | 240.86 | 221.68 | $1,104.43 | 11.7% | −$95.56 (-7.96%) |
| LNG | 3.234 | 309.21 | 295.37 | $955.23 | 10.1% | −$44.76 (-4.48%) |
| META | 1.5764 | 634.35 | 596.22 | $939.88 | 9.9% | −$60.11 (-6.01%) |
| NVDA | 6.127 | 155.05 | 145.98 | $894.42 | 9.5% | −$55.57 (-5.85%) |
| TMUS | 5.2579 | 171.17 | 162.53 | $854.57 | 9.0% | −$45.43 (-5.05%) |
| Cash | | | | $250.11 | 2.6% | |

## Trades for the 2026-11-19 session

None.

## Last 30 sessions

| Session | Account value | Return | SPY | Cash |
|---|---:|---:|---:|---:|
| 2026-11-19 | $9,459.17 | -5.41% | -5.10% | $250.11 |
| 2026-11-18 | $9,645.73 | -3.54% | -3.20% | $250.11 |
| 2026-11-17 | $9,795.79 | -2.04% | -2.91% | $1,200.11 |
| 2026-11-16 | $9,933.04 | -0.67% | -1.91% | $1,200.11 |
| 2026-11-13 | $10,033.40 | +0.33% | +0.00% | $2,100.10 |

To look at this account in your own Argus: sign in as the bot's account there, open **Data**, and restore `docs/loop/sim/bot0.json` (it replaces only that account's records).
