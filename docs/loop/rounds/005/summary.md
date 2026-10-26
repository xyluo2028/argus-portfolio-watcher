# Round 005 summary

Date: 2026-10-26, from about 02:12 UTC. That's Sun 10-25, about 22:12 ET. The market was closed for the weekend, so every value is at the Fri 10-23 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 10-23 close plus post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,747.15 | $98,761.42 | +$14.27 | $1,253.87 | +0.02% |
| loop-income | 17 | $98,347.12 | $99,161.09 | +$813.97 | $1,652.88 | +0.81% (+0.85% with the $33.76 PG dividend now accrued) |
| loop-growth | 11 | $95,500.05 | $93,347.20 | −$2,152.85 | $4,499.95 | −2.15% |

**Trades this round:** none.
- **loop-macro:** every position is within ±0.39 pp of target. With the FOMC, GDP and PCE all due this week, a GLD trim was simulated but parked. Note 42 on GLD has a review date of 10-29.
- **loop-income:** every position is within ±0.32 pp of target. KO, MSFT, ABBV and XOM all report this week. Added alert #7 (MSFT down 6% or more in a day). A `^TNX` yield alert was rejected (B-078).
- **loop-growth:** all theses hold. 10 of the 11 holdings report between 10-26 and 11-05. Note 43 is an RMBS pre-earnings note with exit rules, review date 10-27. The seven new names screened all failed the investor's bar.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 25 findings: macro 10, income 8, multibagger 7.
- **New items:** B-074 to B-084.
- **Found by two investors:** B-013 (macro and income), B-068 (macro and income) and B-025 (macro and multibagger).
- **Existing items with new evidence:** B-002, B-009, B-016, B-019, B-023, B-026, B-036, B-045, B-051, B-053, B-055, B-061, B-067 and B-069. Each is noted with an `r005` line.
- **B-045 lowered to low:** next earnings dates now agree between `/api/earnings` and `/api/events`. Only the missing report timing remains.
- **Confirmed fixed by investors:**
  - **B-066:** Markets 1D was checked over the weekend (macro, income). Bitcoin's 1D is the exception and is now B-075.
  - **B-056:** stale-SEC flag on KO, NEE and RMBS (income, multibagger). The banner wording is now B-080.
  - **B-048:** consensus labels agree with the counts on 12 names plus KO and NEE.
  - These three were moved to Done.

**Picks:**
- **B-074:** wrong numbers, high severity.
- **B-068:** wrong numbers, reported by two investors.
- **B-025:** wrong numbers, reported by two investors this round and by all three over five rounds.

## Shipped
- **B-074, ex-dividend days didn't reconcile (2ad121f).**
  - Dividends that a position held through its ex-date are now accrued from Argus's payment history and counted as income on the ex-date. That covers the performance series, TWR and gain, plus `totals.dividends`, with the estimated part in `dividends_accrued`.
  - A recorded `DIVIDEND` transaction replaces the accrual, so nothing is counted twice.
  - Live check on loop-income: the 10-23 series change went from −$627.50 to −$593.74, which now equals Day P&L. Gain went from $813.97 to $847.73, and TWR from +0.83% to +0.86%.
- **B-068, volatility and Sharpe from a handful of sessions (79aa805).**
  - Below 20 daily returns, `/performance` now returns null with a reason ("needs 20 sessions, has 4").
  - When shown, the label names the window, e.g. "Volatility (ann., N sessions)".
  - The Dashboard, CLI and MCP all show this. All three loop portfolios currently show the reason.
- **B-025, Day % vs Day P&L, and brief movers with the wrong sign (cb40ff3).**
  - The brief's `top_gainers` and `top_losers` now keep only positive and only negative movers.
  - A position bought in the current session now measures Day % from its fill price, the same base Day P&L uses.
  - Checked on all three briefs. A temporary scratch portfolio checked a same-session buy, then was deleted: its creation and deletion show in the snapshot's audit log.

Nothing was blocked. `uv run pytest -q` reports 245 passed, and `npm run build` passes.

## Re-check next round
- **Income:**
  - When PG's dividend is paid (mid-November), record it as a `DIVIDEND`. `dividends_accrued` should drop to 0 while `totals.dividends` stays at about $33.76.
  - Check the next ex-date (e.g. KO on 12-01) reconciles with Day P&L.
  - The Analysis → Dividends "so far" figure and the stress scenarios are still price-only.
- **All three:**
  - Volatility and Sharpe stay withheld until a range has 20 sessions; check the labeled figures when they appear.
  - Buy something during a session and confirm Day % and Day P&L agree.
  - On a one-sided day, confirm the brief's mover lists come back short rather than padded.
- **Macro:** bitcoin 1D (B-075), and B-013 for the SGOV and IEF ex-dates.
- **Multibagger:** RMBS reports 10-26 after the close. Check that statements pick up Q3 (watch B-056 and B-073), and look at B-082 (missing gross profit and operating income).

## For a human
- **Schedule timing:** this round fired at about 22:12 ET on a Sunday, the fifth round in a row outside market hours. Check the routine's timezone and days: the README asks for weekdays during market hours. Same-session behavior (B-025's fill-price base, B-046) can't be checked live at these hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Scratchpad:** each investor was told to use its own scratch subfolder. Proposed again: put this in the investor guide.
- **`scripts/cloud-session.sh` restart:** it exits early ("already running") if the old server still answers the health check while shutting down, so after a `pkill` it sometimes has to be run twice. Proposed: wait for the old process to exit before checking health.
- **Open high-severity items for the next picks:** B-009 (Finnhub vs SEC quarterly growth) and B-017 (asset-class view). B-013 (upcoming dividends disagree across pages) has now been reported in five rounds.
