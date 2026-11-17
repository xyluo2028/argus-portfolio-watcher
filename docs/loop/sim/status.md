# Trader bot: paper account

Play money, started with $10,000.00. Orders fill at the middle of the last US session's range, (high + low) / 2; positions are valued at its close. No trades on days without a new session. Rewritten by `scripts/sim.py report` at the end of every round; the history is in `equity.csv`.

**As of the 2026-11-16 close**

| | |
|---|---|
| Account value | **$9,933.04** (-0.67% since the start) |
| SPY over the same sessions | -1.91% |
| Change since the previous session | −$100.36 |
| Cash | $1,200.11 |
| Invested (market value) | $8,732.93 |
| Realized P&L | +$0.00 |
| Dividends accrued, not yet recorded | $0.00 |
| Trades so far | 6 |

## Positions

| Symbol | Shares | Avg cost | Close | Value | Weight | Unrealized |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 4.6501 | 752.66 | 739.95 | $3,440.84 | 34.6% | −$59.10 (-1.69%) |
| ADBE | 4.9821 | 240.86 | 246.00 | $1,225.60 | 12.3% | +$25.61 (+2.13%) |
| XLV | 6.377 | 188.18 | 187.88 | $1,198.11 | 12.1% | −$1.88 (-0.16%) |
| META | 1.5764 | 634.35 | 626.41 | $987.47 | 9.9% | −$12.52 (-1.25%) |
| LNG | 3.234 | 309.21 | 305.20 | $987.02 | 9.9% | −$12.97 (-1.30%) |
| TMUS | 5.2579 | 171.17 | 170.01 | $893.90 | 9.0% | −$6.10 (-0.68%) |
| Cash | | | | $1,200.11 | 12.1% | |

## Trades for the 2026-11-16 session

| Side | Symbol | Shares | Mid price | Amount | Why |
|---|---|---:|---:|---:|---|
| BUY | TMUS | 5.2579 | 171.17 | $900.00 | Defensive value: P/E 16.4 at 5th pct of 5y range, FCF yield ~10%, div 2.4%, low beta; thesis note filed |

## Last 30 sessions

| Session | Account value | Return | SPY | Cash |
|---|---:|---:|---:|---:|
| 2026-11-16 | $9,933.04 | -0.67% | -1.91% | $1,200.11 |
| 2026-11-13 | $10,033.40 | +0.33% | +0.00% | $2,100.10 |

To look at this account in your own Argus: sign in as the bot's account there, open **Data**, and restore `docs/loop/sim/bot0.json` (it replaces only that account's records).
