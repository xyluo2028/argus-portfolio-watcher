# Round 005: macro investor

## What I did
- **Backdrop.** I read the backdrop at about 22:15 ET on Sun 10-25. The market was closed and the last session was Fri 10-23. Sources: `GET /api/market-context`, `argus quotes ... --json`, and the Markets page at desktop and 390 px.
  - **Indices:** S&P 7,623.68 (−0.52% 1D, −1.1% 1M). NDX was flat on the day (−0.004%; QQQ −0.01% agrees) and −5.0% over 1M. Russell −0.29%.
  - **Volatility:** VIX 19.45 (+2.2% 1D, +28% 1M).
  - **Rates:** ^TNX 4.99% (+3.5 bp). On the curve the 10Y is 5.00, 2s10s is +31 bp and 10s3m is +78 bp. The Fed is at 4.00% and is expected to hold on Wed 10-28.
  - **Oil and the sectors:** WTI settled at 103.27 on Friday (+3.8%), and Sunday night Globex trades at 101.28. On Friday XLE was +2.6% and DBC +1.6%, while staples (XLP −1.9%), health care (XLV −1.1%) and discretionary (XLY −1.7%) sold off.
  - **Gold:** 4,008, down 7.3% over 1M.
  - **Fear & greed:** 7.9 "Extreme fear" with 5 readings. Once breadth loaded it was 25.3 "Fear" with 7 readings.
  - **Breadth:** 147 advancers vs 351 decliners, and 57% of stocks are above their 50-day average.
- **Correlations.** I computed these myself from `/api/history` 1y daily closes. Each cell is the correlation with SPY.

  | Asset | 20 days | 60 days | 1 year |
  |---|---|---|---|
  | IEF | −0.29 | +0.27 | +0.30 |
  | TLT | −0.24 | | +0.28 |
  | GLD | +0.54 | | +0.38 |
  | XLE | −0.22 | | −0.24 |
  | DBC | −0.20 | | −0.24 |

  - Over the last 20 days, Treasuries are hedging equities and gold isn't.
  - Argus's safe-haven reading (SPY vs TLT −4.0 pp over 20 days) and junk reading (HYG vs LQD −1.7 pp) both match my own computation exactly.
- **Regime:** unchanged. It is still stagflation-lite: oil above $100, the 10-year at 5%, core PCE at 3.3% and a Fed on hold, with a narrowing, defensive-led equity tape. The energy and commodity sleeve (XLE plus DBC, 16.6%) is doing its job.
- **Decision: no trades.**
  - Every position is within ±0.39 pp of target (`/drift`), and the regime hasn't changed.
  - The week is full of event risk: FOMC Wed, GDP and PCE Thu, then Chicago PMI and the ECI on Fri. I won't re-hedge into a binary event on noise.
  - I ran `POST /simulate` on a GLD trim (SELL 6 GLD, BUY 22 SGOV) and parked it. GLD isn't acting as a hedge, but its thesis review is due 10-29, after the event.
  - I added note 42 on GLD with that reasoning, review date 10-29.
- **Portfolio:** 11 positions, value $98,761.42, cost $98,747.15, unrealized +$14.27, realized +$1.03. Day P&L on 10-23 was −$170.19 (−0.17%) against SPY −0.52%.
  - Risk: beta 0.245, volatility 6.12% and 1-day 95% VaR $564.
- **Cash balance: $1,253.87**, unchanged (100,000 + 1.03 realized − 98,747.15 cost). The return to date is +0.02% ($100,015.29 in all). No dividends yet.

## Last round's changes
- **B-066, Markets 1D for indices, futures, FX and crypto: works over a weekend, with one exception.**
  - **Indices:** every gauge's 1D equals its quote's `change_pct`. ^GSPC −0.519, ^NDX −0.004, ^RUT −0.292, VIX +2.207, ^TNX +0.707.
  - **Futures and FX:** WTI −1.93% is Sunday night's 101.28 against Friday's 103.27 settle, and gold and USD/JPY are also measured from the quote's `prev_close`.
  - **Sectors:** the sector 1D and 1W values recompute exactly from the history (XLE 1W +1.6%).
  - This fixes my r004 finding #1. The exception is bitcoin's 1D (finding 1).
- **B-056 and B-048:** single-stock items that don't touch an ETF book.
- **Futures showing the next session's date:** it is only in the API (`as_of 2026-10-26` on CL=F, GC=F, JPY=X and BTC-USD). The cards don't show it (finding 2).

## Findings

### 1. Bitcoin "1D" covers only the 2 hours since midnight UTC (−0.43%), not a day
- kind: bug
- severity: medium
- evidence:
  - At 02:16 UTC on 10-26, the BTC-USD gauge shows 1D −0.43%, with `change −341` against `prev_close 80,039.69`.
  - `argus quotes BTC-USD` shows `open 80,039.69 = prev_close`. That is Yahoo's 00:00 UTC open, so the "1D" window is only 2 h 16 min long.
  - `/api/history/BTC-USD` has no 10-25 bar: it goes from 10-24 (80,790.84) straight to 10-26 (79,733.95). In r004 the 10-22 bar was missing in the same way.
  - A real 24-hour move would be measured from the price around 80,7xx. This meets B-066's acceptance text ("the quote's previous close for crypto"), but for a 24/7 asset the quote's previous close is midnight UTC.
- suggestion:
  - For `-USD` symbols, measure 1D from the price 24 hours earlier: the last hourly bar at or before now − 24 h. Alternatively, label it "since 00:00 UTC".
  - Fill the missing daily bar from the quote's `prev_close`, as is already done for the spark.
- backlog: follow-up to B-066 (done)

### 2. On a weekend, Markets is stamped "as of Fri, Oct 23, 4:00 PM ET", but four cards show Sunday-night prices
- kind: ux
- severity: medium
- evidence:
  - The page header reads "Market closed · as of Fri, Oct 23, 4:00 PM ET".
  - The WTI ($101.28, −1.93%), gold, USD/JPY and bitcoin cards show 22:00 ET Sunday Globex or 24/7 prices. The API knows this (`as_of 2026-10-26`), but no card says so.
  - So the oil −1.93% reads as a Friday move, when oil actually rose 3.8% on Friday.
  - The gold card shows 4,007.8 while `argus quotes GC=F` returns 4,004.5 at the same minute (as_of 02:03 UTC). Neither shows a time.
- suggestion: put a small "Mon session · 22:05 ET" (or "overnight") tag on any card whose `as_of` is later than the header's date. This is part of B-055 and B-016.
- backlog: B-055 / B-016

### 3. Dividends projects SGOV and IEF ex-dates on Sun 11-01, while Coming up, the brief and events show nothing for 14 days
- kind: bug
- severity: medium
- evidence:
  - `/api/portfolios/loop-macro/dividends` gives SGOV and IEF `next_ex_date_est 2026-11-01` (a Sunday). Together they make up November's projected $55.71.
  - In the same session these all come back empty:
    - The Dashboard "Coming up · next 14 days" card says "Nothing scheduled."
    - `argus brief loop-macro --json` gives `dividends_upcoming []`.
    - `argus events --json` doesn't mention SGOV, IEF or VTIP at all.
  - The estimated date should also roll forward to the next business day (Mon 11-02).
- suggestion: use one source for upcoming ex-dates (the dividends projection) in Coming up, the brief and events, and roll weekend estimates forward to the next business day.
- backlog: B-013 (new evidence)

### 4. Fear & greed jumps from 7.9 "Extreme fear" to 25.3 "Fear" when breadth loads (fourth sighting)
- kind: ux
- severity: medium
- evidence:
  - The first `/api/market-context` returned `score 7.9`, 5 components, and `errors.breadth` set.
  - A few minutes later it returned `score 25.3` with 7 components. The two added readings are "Price strength" at 80.6 "Extreme greed" (25 highs vs 6 lows, on a 147/351 down day) and "Price breadth" at 57.2.
  - All five history-ranked readings are between 0.6 and 12.9.
- suggestion: as in B-036. Rank the breadth readings against their own history, and show "5 of 7 readings" while breadth loads.
- backlog: B-036

### 5. Risk and the correlation matrix still use only 1 year, so the bond-hedge flip is invisible
- kind: feature
- severity: medium
- evidence:
  - Analysis → Correlations shows SPY/IEF +0.30 and SPY/GLD +0.36, and `/risk` gives `lookback_days 252` with IEF beta 0.12.
  - Over 20 days the correlations are IEF −0.29, TLT −0.24 and GLD **+0.54**.
  - This week the real question is "add duration, cut gold?". The only window Argus offers gives the opposite answer for both.
- suggestion: as in B-067, add a lookback choice (20, 60 or 252 days) to `/risk` and the matrix.
- backlog: B-067

### 6. Simulate still returns no risk change
- kind: feature
- severity: medium
- evidence:
  - `POST /simulate` with SELL 6 GLD and BUY 22 SGOV returned weights, concentration and look-through sectors only.
  - It didn't return beta, volatility or VaR, so I can't see that the trim cuts about 18% of the book's risk contribution (GLD's `risk_pct` is 17.9% at 6.7% weight).
  - Also, `value_after` is $98,776.28 against `value_before` $98,761.42. The $14.86 of net cash spent shows up as a value *gain*.
- suggestion: as in B-023, add `risk_before` / `risk_after`. Show `net_cash` next to `value_after`, or count cash in the value (B-024).
- backlog: B-023 (and B-024 for the value line)

### 7. The brief's "top_gainers" includes IEF at −0.16%
- kind: bug
- severity: low
- evidence:
  - `argus brief loop-macro --json` gives `top_gainers [XLE +2.60, DBC +1.58, SGOV +0.04, VTIP +0.02, IEF −0.16]`.
  - Last round the same bug showed in losers (SGOV 0.00).
- suggestion: as in B-025, filter gainers on `change_pct > 0` and losers on `change_pct < 0`.
- backlog: B-025

### 8. The brief's "near_52w_extremes" lists all 11 holdings
- kind: ux
- severity: low
- evidence:
  - `near_52w_extremes` has 11 rows for 11 positions:
    - SGOV is 0.07% from its high, which is always true for a T-bill fund.
    - SPY is 2.8% from its high and IEF 2.7% from its low.
  - A list that names everything tells me nothing.
- suggestion: scale the threshold by volatility (for example within 0.5 × the 1-month σ), or skip cash-like ETFs whose 1-year range is under 2%.
- backlog: new

### 9. Sharpe 0.38 from 4 sessions (it was 18.3 last round), and a 10-20 TWR offset against SPY
- kind: bug
- severity: low
- evidence:
  - `/performance` gives `sessions 4, sharpe 0.379, volatility_pct 1.98`, while `/risk` gives `volatility_pct 6.12`. That's two volatilities for one book.
  - The Dashboard chart starts loop-macro at +0.11% and SPY at 0.00% on 10-20.
  - Excess shows +1.19%. Measured from my 10-20 SPY fill (769.47 → 759.97, −1.23%), it would be about +1.25%.
- suggestion: as in B-068 and B-053.
- backlog: B-068, B-053

### 10. The quote for BTC-USD comes back as symbol "BTC.USD"
- kind: bug
- severity: low
- evidence:
  - `argus quotes BTC-USD --json` and `/api/history/BTC-USD` both return `"symbol": "BTC.USD"`. The Markets gauge uses "BTC-USD".
  - Share-class normalization (BRK-B → BRK.B) seems to be applied to crypto pairs too. A client matching on symbol would miss the row.
- suggestion: skip the dash-to-dot rewrite for `-USD` (and other crypto or FX) suffixes.
- backlog: new

## Still-open items I re-checked
- **B-054:** VTIP is still `next_ex_date_est null` with `projected_rest_of_year 0`.
- **B-022/B-024:** the Analysis Targets & drift card opens "By sector" and shows ETF 100% with "Targets sum to 0.0%". `/drift` still warns "targets sum to 99.0%" because there is no cash line.
- **B-017:** the look-through is still 39.2% "Unclassified", and Dashboard "By sector" is ETF 100%.
- **B-039:** on Markets, the 10-year "+4 bp" and VIX "+2.21%" are both green.
- **B-029:** the API reports ^TNX 1D as 0.707 (percent of the yield), while the card shows +4 bp.
- **B-035:** over the weekend the calendar starts on Mon 10-26 and shows none of last week's actuals.
- **B-002:** on a phone, Markets is 5,774 px tall with one gauge per row.
- **B-026:** not seen this round. `/risk` returned in 0.73 s (warm, with no trade since).

## Summary for the round lead
1. No trades. Every position is within ±0.39 pp of target, and the regime is unchanged (stagflation-lite: oil about $103, 10Y at 5%, Fed on hold), with FOMC, GDP and PCE this week. I added note 42 on GLD for its 10-29 review. loop-macro is $98,761.42, unrealized +$14.27, and cash is $1,253.87.
2. B-066 checked over a weekend: it works for indices, futures, FX and sectors. One new bug: bitcoin 1D covers only the 2 h since midnight UTC, and its history skips 10-25. Also new: the weekend Markets cards show Sunday-night prices under a "Fri 4:00 PM" header (B-055/B-016), and dividends projects SGOV and IEF on Sun 11-01 while Coming up, the brief and events are empty (B-013).
3. Still open: B-036 (fear & greed 7.9 → 25.3), B-067 (20d SPY correlations: IEF −0.29 and GLD +0.54, against +0.30 and +0.36 over 1y), B-023, B-025, B-068 and B-053. New and low: near-52w lists every holding, and BTC-USD comes back as "BTC.USD".
