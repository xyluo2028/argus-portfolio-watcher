# Round 016: macro investor

## What I did
- **When:** Thu 11-12 at about 21:15 ET (02:15 UTC Fri 11-13). The market was closed; the latest close is 11-12 (SPY 757.12).
- **Sources:**
  - `GET /api/market-context` (twice: before and after breadth loaded).
  - `argus quotes --json` for HYG, LQD, TLT, ^VIX3M, UUP, GLD, ES=F, NQ=F, ^IRX, TIP, RSP, HG=F, MTUM, SPLV, SMH, EEM, EFA, IWM, SGOV, ^FVX and ^TYX.
  - `/api/history/<sym>` for SPY, IEF, TLT, GLD, XLE and VTIP. I used them to work out 5/10/20/60-day correlations to SPY by hand.
  - The loop-macro endpoints: summary, performance, risk, exposure, drift, dividends, targets, transactions, simulate and `/api/brief/loop-macro`.
  - `/api/research/SPY` news and `/api/notes`.
  - Screenshots: Markets at 1400 px (whole page, in tiles) and 390 px, and Analysis at 1400 px. For Analysis, a Playwright script picks loop-macro in the header first.
- **Backdrop: the hot CPI from 11-10 is now driving a bear move in rates.**
  - **Curve:** the 10Y went from 4.98 (11-10) to **5.10** (11-12) and the 2Y from 4.73 to 4.86 (11-11 was a bond holiday). 2s10s is 24 bp and 10s3m is 78 bp. The 30Y auction stopped at 5.441%.
  - **Bonds:** TLT −1.48%, IEF −0.80%, LQD −0.88% and TIP −0.47%.
  - **Real assets:** gold fell too (GLD −2.82%), so this is a real-yield move, not an inflation-hedge bid.
  - **Equities:** they fell less, but breadth was poor. SPX −0.35%, NDX −0.30%, RUT −1.66% and RSP −0.87%, with 139 up and 359 down. The news was led by NVIDIA's leadership change.
  - **Volatility:** VIX 18.70 (+6.9%) and VIX3M 20.06, a ratio of 0.93 (still contango).
  - **Credit:** HYG −0.48%; the junk vs IG component reads "Fear" 44.
  - **Other markets:** UUP +0.24%, USD/JPY 159.87 and WTI 88.1 (back up from 85.7, still below my 90/95 triggers). Bitcoin is −1.2%.
  - **Data and futures:** initial claims were 200K vs 194K consensus. Fear & greed is 41 with all seven components. Futures are firm overnight (ES +0.39%, NQ +0.64%).
- **Regime:** sticky inflation with a hawkish repricing across the curve. Stocks and bonds fell together today, but over 20 days IEF's correlation to SPY is still **−0.24** (60-day +0.05; my calculation from Argus closes to 11-11). Next events: core PPI 11-13 08:30 (consensus 0.3% m/m, previous 0.7%), Warsh on 11-16 and the FOMC minutes on 11-18.
- **Decision: no trade.**
  - Note 68's IEF stop (10Y > 5.15% or IEF corr to SPY turning positive) isn't hit: 10Y 5.10 and 20d corr −0.24.
  - Note 85's legs aren't triggered either: no cooling plus 10Y < 4.8, WTI isn't below 80 and isn't above 95.
  - A 5.1% 10Y also pays for holding the hedge.
  - **Staged in note 89 (review 11-16):** if core PPI is ≥ 0.4% m/m **and** the 10Y closes above 5.15, SELL 44 IEF / BUY 39 SGOV. Simulated at the 11-12 close: net cash +48.57, FIFO realized −46.64 (= 44 × (90.21 − 91.27), the first lot), IEF 11.6 → 7.6% and SGOV 16.4 → 20.4%.
- **Book at the 11-12 close:**
  - value $97,988.11 and cost $98,149.18;
  - unrealized −$161.07 and realized −$483.04;
  - **Day P&L −$228.12 (−0.23%)** against SPY −0.35%. IEF −$92 and XLV −$75 were the drags; XLE +$94 offset them.
  - TWR since 10-20 is −0.60% against SPY −1.55% (+0.95 pp).
  - All ten positions are inside the ±2 pp band. The largest drift is IEF at −0.90 pp.
  - Beta 0.24, volatility 5.5% and VaR99 $739.
- **Cash: $1,367.79** (unchanged, no trades). Value plus cash is $99,355.90, a **return to date of −0.64%** (−0.58% with $63.40 of accrued dividends).

## Last round's changes
- **B-156 (calendar survives a failed day): partly verified. The calendar is back, and that helped.**
  - Nasdaq answers again: `errors.events` is gone, `calendar.events` has 40 rows and `all_events` has 154 (181 raw).
  - `data/cache/econ_releases.json` now exists with 33 rows for 11-11 and 11-12, so the kept store is filling.
  - I couldn't observe the "k of 24 days unavailable" note because no day failed tonight.
  - CPI (11-10) is still not visible anywhere (finding 2).
- **B-152 (Risk "Last session" = Day P&L): works.**
  - Analysis → Risk shows "Last session (11-12) −$228, −0.23%, held that session".
  - `last_day.value` −228.12 = `totals.day_pnl` −228.12 = brief totals, and `basis` is `session_holdings`.
  - I didn't re-test the evening-trade case because I made no trade, and I couldn't test the pre-open label at this hour.
- **B-157 (momentum from a stale bar):** not in my workflow. Note that tonight Yahoo's 11-12 bar is also late: `/api/history/SPY` ends 11-11. Market-context and risk both say "last close from quotes" (`closes_from_quotes` date 11-12), and their figures tie to the quotes.

## Findings

### 1. "FOMC Meeting Minutes" (11-18) is dropped from the key calendar by its own filter
- kind: bug
- severity: medium (the minutes are one of the three events in my next week, and the default Markets view hides them)
- evidence:
  - `/api/market-context` `calendar.all_events` has `{"date":"2026-11-18","time_et":"14:00","event":"FOMC Meeting Minutes"}`, but `calendar.events` (the 40 "key" rows shown by default on Markets) does not.
  - The Markets page lists Housing Starts on Wed 11-18, then jumps to Initial Jobless Claims on Thu 11-19.
  - **Cause:** `MAJOR` in `services/market_context.py` matches `FOMC (Statement|Minutes|Economic Projections)` as whole words. Nasdaq names the release "FOMC **Meeting** Minutes", so it never matches.
- suggestion: match `FOMC( Meeting)? Minutes` (or `\bMinutes\b` together with `FOMC`), and add a test with Nasdaq's exact name.

### 2. The calendar is back, but its window starts yesterday: this week's CPI actual is gone after two days
- kind: feature (re-sighting of B-035, made worse by the B-156 outage)
- severity: medium (core CPI is the event behind both my plan notes; I still read it from the tape)
- evidence:
  - `all_events` dates run from 2026-11-11 to 12-03. The earliest row is 11-11 05:00 (OPEC), so Tuesday 11-10's CPI isn't there.
  - `econ_releases.json` only has rows for 11-11 and 11-12, because the server got 403s on the days CPI printed.
  - Markets' key table starts at Thu 11-12 (claims 200K vs 194K).
  - A macro desk reviews the week's prints against consensus every evening: CPI on Tuesday, PPI on Friday.
- suggestion: show the last 5 sessions of key releases (with actual, consensus and the surprise) above "upcoming", served from the kept store. Seeding the store from a second source for CPI/PPI/NFP actuals (BLS) would cover outage days like 11-10.

### 3. Performance's last step disagrees with Day P&L after last night's evening trade (−$221.12 vs −$228.12)
- kind: bug (a new consequence of B-049)
- severity: medium (B-134's acceptance says the final step should equal Day P&L; two numbers for one session)
- evidence:
  - **Performance:** `/performance` books txns 58/59 (made at 21:17 ET on 11-11, stamped `2026-11-12T02:17Z`) as 11-12 flows: `flow_in` 3116.12 and `flow_out` 3175.50 on the 11-12 row.
  - **The arithmetic:** the 11-12 step is 97,988.11 − 98,268.61 − 3,116.12 + 3,175.50 = **−221.12**. Summary and risk both say **−228.12**.
  - **The $7.00 gap** is 50 × (63.51 fill − 63.37 11-11 close): the XLE sale's after-hours fill is credited to 11-12.
  - **The TWR step** is −0.218% vs Day P&L −0.232%.
  - **The 11-11 end value** in performance (98,268.61) still includes the 50 XLE shares sold that evening. Last night's Dashboard showed $98,216.23.
- suggestion: date a trade by its New York session (the session it was made in, or after), not by its UTC timestamp. That is B-049's fix, and then performance, Day P&L and risk agree.

### 4. Fear & greed reads 25.3 from 5 of 7 components, then 40.9 once breadth loads
- kind: bug (re-sighting of B-036)
- severity: medium
- evidence:
  - **First call (02:13 UTC):** `fear_greed.score` was 25.3 "Fear" with 5 components (no price strength, no breadth) and `errors.breadth` "needs the screener's universe".
  - **Minutes later:** 40.9 with 7 components. The Markets gauge shows 41.
  - Neither the API nor the gauge said "5 of 7" on the first call.
  - Price strength scores 92 "Extreme greed" (24 highs vs 2 lows) on a day with 28% advancers.
- suggestion: return `components_used`/`components_total` and show "partial (5/7)". Rank new-highs share against its own history like the other components.

### 5. First loads are slow: performance 12.1 s, risk 15.4 s
- kind: perf (re-sighting of B-026)
- severity: medium
- evidence: the first `curl -w %{time_total}` on loop-macro gave:
  - `/performance` 12.09 s;
  - `/risk` 15.42 s;
  - the summary 1.77 s.

  Warm, the same calls take 0.06 s, 0.42 s and 0.09 s.
- suggestion: warm held symbols' history and risk at startup or on a timer after the close.

### 6. The brief still has no macro events though the calendar now has them (PPI tomorrow 08:30, minutes 11-18)
- kind: feature (re-sighting of B-038)
- severity: medium
- evidence:
  - `/api/brief/loop-macro` has no events or calendar key; `earnings_upcoming` and `dividends_upcoming` are `[]`.
  - Meanwhile `calendar.events` has Core PPI and PPI for 11-13 08:30, and the next FOMC (12-09) is in `calendar.fomc`.
  - For a macro book the brief's "what's coming" is empty every night.
- suggestion: add `macro_upcoming` (key releases in the next 2 sessions, plus the next FOMC date) and `macro_recent` (yesterday's actuals vs consensus) to the brief.

### 7. Calendar twins still unlabeled; next week's claims row has no "previous" though it printed today
- kind: ux (re-sighting of B-091)
- severity: low
- evidence:
  - Markets lists "PPI 6.6% / 6.3%" and "PPI 0.4% / 1.3%", "Core PPI 5.0%" and "Core PPI 0.3%", "Retail Sales 0.8%" and "Retail Sales 6.29%", "Industrial Production 0.7%" and "2.25%", and "Housing Starts 1.221M" and "−5.2%". None is labelled m/m or y/y.
  - Thu 11-19 "Initial Jobless Claims" shows Previous "–", though the 11-12 row has actual 200K.
- suggestion: label pairs by magnitude or Nasdaq's period field (m/m, y/y). Fill "previous" from the kept store's last actual for the same release.

### 8. "all 181 US releases" shows 154 rows
- kind: ux
- severity: low
- evidence: on Markets, ticking the checkbox labelled "all 181 US releases" grows the table from 40 to **154** rows (counted with Playwright). In the API, `all_count` is 181 and `all_events` has 154; the noise filter removed 27.
- suggestion: label it "all 154 US releases (27 duplicates/levels hidden)", or use `len(all_events)`.

### 9. No short-window stock–bond correlation or rate sensitivity on the day both legs fell
- kind: feature (re-sighting of B-067 and B-017)
- severity: medium (this is the number my IEF stop depends on, and I computed it by hand again)
- evidence:
  - **Today's move:** IEF −0.80% and TLT −1.48% while SPY fell 0.35%.
  - **Argus's figure:** Risk's correlation matrix is 1-year only.
  - **My calculation** from `/api/history`: IEF corr to SPY was −0.35 over 5 days, −0.21 over 10, −0.24 over 20 and +0.05 over 60.
  - **What's missing:** the stress table has a "2022 rate shock" replay (−8.8%) but no "+25/+50 bp parallel" line on the book, and 41.8% of the book is still "Unclassified" with no duration.
- suggestion: add a 20/60-day column to the correlation and beta table, and a "+50 bp" scenario using N-PORT or regression duration for bond ETFs.

### 10. Re-sightings (short)
- **B-159:** the 10-year card says "+10 bp" (^TNX 5.103 vs the 11-11 holiday tick 4.998). The cash curve moved +12 bp from the last bond session (4.98 on 11-10 to 5.10).
- **B-044:** "Where the risk comes from" lists 9 of 10 holdings (SGOV missing) with no note.
- **B-022:** Targets & drift opens on "By sector … Targets sum to 0.0%" though 10 position targets summing to 100% are saved.
- **B-118:** the header opens on loop-growth, so every Analysis visit needs a manual switch.
- **B-127:** the brief's `theses_due` still lists superseded notes (21, 57, …).
- **Phone (B-002):** at 390 px, Markets stacks nine gauge cards one per row, about 1,300 px of scrolling before fear & greed. A 2-column compact grid would fit them in one screen.
- **Minor:** `/api/history/SPY?range=3mo` ignores `range` and returns 1y of bars, with no error.

## Consistency checks that passed
- **Day P&L:** the sum of position day P&L = −228.12 = `totals.day_pnl` = risk `last_day.value` = brief totals. XLE 98 × (64.33 − 63.37) = 94.08.
- **Benchmark:** SPY's 11-12 step in performance, (1 − 1.5513%) ÷ (1 − 1.2015%) − 1 = −0.354%, matches 757.12 ÷ 759.81 − 1.
- **Curve:** 2s10s 24 bp = 5.10 − 4.86 and 10s3m 78 bp = 5.10 − 4.32. The card's 1M −14 bp matches the curve's 10-09 point of 5.24.
- **Volatility:** VIX/VIX3M 18.70 ÷ 20.06 = 0.93 = the term component.
- **Simulate:**
  - net cash 44 × 90.21 − 39 × 100.53 = 48.57;
  - realized −46.64 is FIFO on the 55 @ 91.27 lot (10-23), consistent with past realized figures;
  - the SGOV FIFO average (129 × 100.6095 + 31 × 100.52) ÷ 160 = 100.592 matches the summary.
- **Drift:** weights sum to 100% and `trade_to_target` = (target − weight) × value for each row.
- **Pages:** Markets rendered in 0.24 s (1400 px) and 0.25 s (390 px), with no overflow or page errors. The B-158 banner overflow is gone tonight because there is no error. Analysis rendered with no errors or overflow.

## Summary for the round lead
1. **Trades:** none. Hot CPI is now a bear move: 10Y 5.10 (+12 bp), 2Y 4.86, GLD −2.8%, IEF −0.8% with SPX −0.35%. Note 68's IEF stop (10Y > 5.15 or 20d corr > 0) isn't hit (corr −0.24). Staged in note 89: on core PPI ≥ 0.4% and 10Y > 5.15, SELL 44 IEF / BUY 39 SGOV. loop-macro is $97,988.11, cash $1,367.79, return to date −0.64%.
2. **Verified:** B-152 works (−228.12 everywhere, "held that session"). B-156 is partly verified: the calendar is back and `econ_releases.json` is filling, but no partial failure happened to test.
3. **Top findings:**
   - **new bug:** the "FOMC Meeting Minutes" 11-18 row is filtered out of the key calendar, because the regex expects "FOMC Minutes";
   - **B-035:** the calendar window starts yesterday, so this week's CPI is invisible;
   - **B-049:** performance's last step is −221.12 vs Day P&L −228.12 after the evening trade;
   - **B-036:** fear & greed 25.3 → 40.9;
   - **B-026:** cold risk 15 s;
   - **B-038:** the brief still has no macro events.
