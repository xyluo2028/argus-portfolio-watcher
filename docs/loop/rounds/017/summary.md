# Round 017 summary

This is the first round of the trader-bot format: one $10,000 paper account, `bot0-sim` of the account `bot0`. Rounds 001–016 ran the three investor agents instead.

**Trading day.** The session traded was Friday 2026-11-13. The round ran on Monday 11-16, before the US open, and `market_session` was `closed`.

## Data sources (preflight)

- **Quotes:** working, from Finnhub. The Finnhub key reaches Finnhub: `/quote?symbol=AAPL` returned 200 with a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth`, which needs the screener universe still building in the background (B-027).
- **Stream:** off on purpose.
- **Agents and tools:** the `trader` and `programmer` agent types and the `mcp__argus__*` tools weren't loaded in this session. I ran general-purpose agents that read their `.claude/agents/` files, and they used the CLI and the API.

## The account (at the 11-13 close)

| | |
|---|---|
| Account value | **$10,033.40**, +0.33% since the start |
| SPY over the same sessions (`sim.py`) | +0.00%, because this is the first session |
| SPY from the trader's fill (752.66) to the close (754.37) | +0.23% |
| Cash | $2,100.10 (20.9%) |
| Invested | $7,933.30, in 5 positions |

Trades, all filled at the 11-13 mid, each with a thesis note:

| Order | Fill | Reason |
|---|---|---|
| BUY 4.6501 SPY | 752.66 | Core index position at 35%; buying the pullback with fear & greed at 30 |
| BUY 4.9821 ADBE | 240.86 | P/E 13.6, the 0th percentile of its own 5 years; FCF margin 41%; revenue +12% |
| BUY 1.5764 META | 634.35 | Down 16% in a month, P/E 22, revenue +26%; sized smaller because the Q3 operating margin fell to 20% |
| BUY 3.234 LNG | 309.21 | Energy diversifier; estimates rising; 1y beta to SPY negative |
| BUY 6.377 XLV | 188.175 | Health care is the strongest sector and has low beta |

- **Cash:** the trader kept about 21% to act on NVDA's earnings on 11-17.
- **Alerts:** ADBE ≤ 215, META ≤ 560, LNG ≤ 261, and NVDA moving 8% or more in a day.
- **Watchlist:** `candidates`, with 8 names.

**Account check:**
- `sim.py status` answers `"ok": true`.
- All 5 transactions are at their session's mid price, so none were made outside `scripts/sim.py`.
- The trader confirmed that r016's B-163, B-164 and B-165 work.

## Shipped

- **B-053: the benchmark is measured from the first day's fills, like the portfolio (6f03b10).**
  - On a portfolio's first session, SPY used to start at that session's close, so it always read 0.00% and the whole first-day return counted as excess.
  - SPY now starts at the portfolio's own SPY fill price, or at the session mid when SPY isn't held.
  - For bot0-sim, excess return is now +0.20% (it was +0.42%). The Dashboard tile reads +0.42% against SPY +0.23%, labeled; it read −0.36% before.
- **B-106: the brief reads every named watchlist (222ba06).**
  - The brief has a new `watchlist_earnings` section (upcoming and recent), and `watchlist_movers` now covers every list of the account. Each row names its lists.
  - Live, bot0's brief now shows NVDA (11-17) and INTU (11-19).
  - Other accounts' lists stay invisible, and a test covers that.
- **B-021, labeling part: every beta states its source and window (cac6bf4).**
  - The stock page shows "Finnhub, 5y monthly vs S&P 500". The window is inferred: Finnhub's figures match a 5-year monthly regression, and Yahoo's fallback says the same.
  - The Risk card shows "vs SPY, 1y daily".
  - The factor Market loading and the SPY −10% scenario are labeled too, and the API and MCP return `beta_basis`.
  - No numbers changed. The scenario-vs-replay gap was split off as B-173.

Nothing was blocked. Tests: 431 pass, and `npm run build` passes.

**New items:**
- B-168: no cash balance (high)
- B-169: SPY quote low vs the bar
- B-170: alert on a moving-average break
- B-171: market-context date is Sunday
- B-172: CLI gaps
- B-173: split from B-021

## For the trader to re-check next round

- **bot0-sim performance:** excess return should be about +0.20%, and the chart's SPY line should start at +0.23%. On a session with no buys, the Dashboard tile should go back to SPY's plain day change.
- **NVDA:** after NVDA reports on 11-17, it should move to the brief's `watchlist_earnings.recent`. A `candidates` name moving 3% or more should show up in `watchlist_movers`.
- **Beta labels:** check them on ADBE and LNG (stock page vs the Risk card), on the SPY −10% scenario row, and on the factor Market row.

## For a human

- **B-168, cash balance (high):**
  - Argus has no cash, so every weight on the Dashboard and in Risk is a share of the invested $7,933, not of the $10,033 account. The trader can't check its house-rule caps in Argus.
  - A fix probably needs a starting-cash or deposit setting per portfolio. Applying it to bot0-sim would change the trader's account outside `scripts/sim.py`, so please decide how the loop should handle that (for example, `sim.py` setting it).
- **B-169, the fill price input:**
  - SPY's 11-13 quote low from Finnhub (745.20) disagrees with Yahoo's daily bar (747.88), and with the S&P 500, VOO and IVV.
  - `sim.py` fills at the quote's (high + low) / 2, so the SPY fill was 752.66 rather than about 754.00.
  - Any fix changes the referee's input. Consider whether `sim.py` should prefer the session's daily bar.
- **Two return-vs-SPY figures:**
  - `sim.py report` gives SPY +0.00% for the first session because it compares closes. Argus now gives +0.23%, from the fill.
  - The two will diverge only by the first day's gap. That's harmless, but worth knowing when reading `status.md`.
- **Process:** the `trader` and `programmer` agent types aren't registered in cloud sessions, maybe because the agent files load from `main`. The fallback worked.
