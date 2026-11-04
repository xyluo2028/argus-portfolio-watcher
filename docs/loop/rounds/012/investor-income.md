# Round 012: income investor

## What I did
- **Market (Argus market context, Tue 11-03 close, reviewed about 21:15 ET):**
  - The S&P 500 rose 0.36% to 7568.92 and SPY 0.30%. Tech bounced (XLK +1.31%, XLC +1.18%) and defensives lagged. Breadth was weak: 214 advancers against 286 decliners. Fear & Greed is 27.5 ("Fear") and VIX is 20.8.
  - Rates edged up. On the curve the 10-year is 4.95% (4.91% on 11-02) and the 2-year 4.61%. JOLTS came in at 7.523M against 7.150M expected. ISM services is Wed 10:00 and claims Thu 08:30. Payrolls have dropped out of Argus's calendar (finding 3).
  - The brief has all four bond ETFs 1.9–2.2% above their 52-week lows (BND, VCIT, VGIT, SCHP), and SCHD, VIG and KO near their highs.
- **Portfolio `loop-income` (11-03 close):**
  - Value $101,126.84, cost $99,618.80, unrealized +$1,508.04 (+1.51%).
  - Day P&L is −$651.48 (−0.64%) against SPY +0.30%. This is the mirror of Monday's rotation: HD −2.20%, PEP −2.24%, JNJ −1.62% and SCHD −0.97% fell, and MSFT +2.74% was the only gainer.
  - Day P&L matches the value change exactly (101,778.32 → 101,126.84, no ex-dates today).
  - Drift: every position is within ±0.28 pp of target. HD is +0.28, ABBV −0.19 and XOM −0.14. The band is ±2 pp. Bond ETFs are 34.7% of the book.
  - Risk (as of 11-02, 252 days): beta 0.13, volatility 7.5%, 95% VaR $660, 1-year max drawdown −5.7%. I recomputed VIG, SCHD, KO and XOM betas from Argus's own `/api/history` (0.619, 0.184, −0.287, −0.691), and all four match the risk card.
- **Income:** forward income is $3,361.73, a 3.32% yield. 2026 so far is $53.07 (PG and O only), and expected is $521.14. The November bond-ETF payments that B-129 restored last round are gone again (finding 1).
- **Trades: none.** Drift is a tenth of the band. The bond sleeve is near its lows with yields of 4.3–5.2%, so I'm holding, not selling into weakness, and I have no cash to add ($381.20). I wrote note 67 on BND (review 11-10, after payrolls and CPI): add bonds only if the 10-year goes above 5.1% and drift calls for it.
- **Cash: $381.20.**
  - Invested at cost: $99,618.80. Realized gains: $0.
  - Return to date: (101,126.84 + 381.20 − 100,000) ÷ 100,000 = **+1.51%**.
  - Adding Argus's $53.07 of accrued dividends gives +1.56%. Adding the ~$132 of November bond-ETF dividends that Argus no longer shows (finding 1) gives about +1.69%.

## Last round's changes
- **B-128 (NaN bar no longer empties history): works.** `argus history SPY` now has the 11-02 bar (close 752.10, ts 05:00 UTC). Risk, performance, fundamentals, research, earnings and returns all return 200. `/risk` is 0.32 s and `/research/O` 1.1 s.
- **11-03 gap (Yahoo daily bars end at 11-02):**
  - **Risk handles it well.** The card says "to 2026-11-02", and its total value uses today's quotes ($101,126.84).
  - **Performance doesn't.** It carries 11-02's value forward as the 11-03 point (finding 2).
- **B-129 (passed estimated ex-dates count): undone by the data.** The code path is fine, but Yahoo's dividend list for the bond ETFs got *shorter* overnight, and Argus overwrote its cached copy (finding 1). Received is back to $53.07 and November to $105.86, the exact r011 "before" numbers.
- **B-130 (fail soft): works.** Nothing failed this round, so there was no error state to see. Every card I use loaded, with no page errors and no horizontal overflow on the dashboard or /analysis (desktop, and /analysis at 390 px).
- **Still open, re-seen:**
  - **B-131:** "O EPS 1.12 vs 0.43 (beat +162.2%)" is still on Coming up and in the brief's `earnings_recent`.
  - **B-132:** HD `last` still has `date null, period 2026-09-30, quarter 2, year 2027`.
  - **B-064:** XOM 11-16 is still ≈ $22.66 at $1.03, not $1.07.
  - **B-062/B-070:** `/api/fundamentals/O` still gives `payout_ratio_pct` 236.39.
  - **B-021:** beta vs SPY 0.13 sits next to a factor "Market" loading of 0.39 (t 11.1), with nothing explaining the difference.
  - **B-017:** look-through sectors still show "Unclassified 34.7%", the bond sleeve, with no duration and no +100 bp scenario. This hurts more this week, with all four bond ETFs near their 52-week lows.
  - **B-022:** Targets still opens "By sector" with "Targets sum to 0.0%".
  - **B-012:** the tile still reads "50% / 50%" Stock / ETF.
  - **B-118:** `/?portfolio=loop-income` still opened loop-growth.

## Findings

### 1. Yahoo's dividend list shrank overnight and Argus replaced its cache with it: the bond ETFs' 10-01 row is gone, November's ~$132 of bond income vanished again, and projections skip from 09-01 to 12-01
- kind: bug
- severity: high (bond ETFs are my main income source. The income tile and the November bar are wrong again, the same client-facing error B-129 fixed one day ago.)
- evidence:
  - **What `GET /api/portfolios/loop-income/dividends` (as_of 2026-11-03) shows now:**
    - VCIT, BND, VGIT and SCHP all have `last_ex_date 2026-09-01` and `next_ex_date_est 2026-12-01`.
    - Each has one event, 12-01, and `received_ytd 0`.
  - **What it showed in r011:** the same four had `last_ex_date 2026-10-01`, and after B-129 the 11-02 estimate counted as received.
  - Totals: received is **$53.07** (r011 after B-129: $185.00), November is projected at **$105.86** (was $237.79), and year_total is $521.14.
  - `data/argus.sqlite` `dividend_history` for BND, VCIT, VGIT and SCHP has `as_of 2026-11-04 02:13:15`, and the last row is 2026-09-01. Live `yfinance.Ticker('BND').dividends.tail()` also ends at 2026-09-01 0.253, so Yahoo itself dropped the 10-01 row it served yesterday.
  - **Cause in code:**
    - `app.dividend_histories` upserts whatever Yahoo returns, replacing the old list. Only a failed fetch keeps the old copy.
    - `services/dividends._passed` then estimates just one step after the last ex-date (10-01). That's now outside its half-period grace, so nothing counts.
    - The projection loop starts after `today`, so October and November are silently skipped for a monthly payer.
  - **Other effects:**
    - The dashboard's Coming up and the Dividends table show no bond-ETF payment in November.
    - `trailing_12m` has dropped below the forward rate (VCIT 3.316 against 4.08), because the year now holds 10 payments, not 12.
- suggestion:
  - **Merge the fetched history into the stored one instead of replacing it.** Keep any previously seen ex-date that the new answer lacks, at least within the last ~400 days. A new value for the same date can still overwrite.
  - **In `_passed`, walk every estimated step** from the last ex-date up to today. Count those the position held, still marked estimated, rather than only the first step. Also flag "history has a gap: N expected payments missing" rather than dropping them silently.
  - **Test:** monthly history whose last row disappears on a refresh, then today = ex-date + 2 → still counted once.

### 2. Performance carries 11-02's value into 11-03: the card says +2.24% and +$2,213 while the header says −0.64% today and $1,508 unrealized, and SPY and excess return show "–" for the whole range
- kind: bug
- severity: high (contradictory numbers on one screen. I can't hand a client "return +2.24%" next to a −$651 day.)
- evidence:
  - **`GET /api/portfolios/loop-income/performance`:**
    - The series ends `{'d': '2026-11-02', 'value': 101778.32}`, then `{'d': '2026-11-03', 'value': 101778.32, 'twr_pct': 2.2389, 'bench_pct': None}`.
    - `summary.end 2026-11-03, end_value 101778.32, gain 2212.59, benchmark_pct null, excess_pct null`, with `provisional_today false`.
  - **Same response time, the live numbers:** `/api/portfolios/loop-income` gives market_value **101,126.84** and day_pnl −651.48. The 11-03 point should be about 101,126.84, with TWR ≈ +1.6% and gain ≈ $1,561.
  - Dashboard (screenshot): the Performance card shows "Return +2.24%", "SPY –", "Excess return –" and "Gain +$2,213". The line is flat into Nov 3, and the SPY line stops at Nov 2. Right above it the header shows "−$651.48 (−0.64%) last session".
  - loop-growth's dashboard has the same flat 11-03 point: "Return −3.52%" next to a "+$1,509.93 (+1.57%) last session" header.
  - Cause: Yahoo's daily bars end at 11-02 (the 11-03 session isn't in yet). The series fills the missing bar with the last close, and the benchmark has no value, so the whole range's SPY comparison goes null.
- suggestion:
  - When the last session has no daily bar but quotes do, build that point from the quote closes, for the portfolio and for SPY (set `provisional_today: true` and label it "from quotes").
  - Failing that, end the series at the last date that has bars, and compute `benchmark_pct` to the last common date rather than nulling it.

### 3. Payrolls (Fri 11-06) disappeared from the calendar three days before the release
- kind: bug
- severity: medium (payrolls are the week's rate driver for my bond sleeve. Last round Argus showed it correctly.)
- evidence:
  - `GET /api/market-context` → `calendar.events` jumps from "Initial Jobless Claims 11-05" to "Core CPI 11-10".
  - `all_events` (153 rows) has 0 rows dated 11-06 and none for Mon 11-16 either. Per-date counts: 11-05: 15, then 11-09: 8.
  - Nasdaq's raw feed today: `?date=2026-11-07` (which answers for Fri 11-06) returns 1 row and 0 US rows, so the provider dropped Friday.
  - Argus keeps rows it has seen only from the last session to today (`_keep_releases`, B-034), so a future day that vanishes from the feed disappears from Argus too.
  - In r011 the round summary confirmed "NFP Fri 11-06 08:30".
- suggestion:
  - Keep previously seen future rows for a day that comes back empty, at least for anchor events (NFP, CPI, FOMC), and mark them "from earlier fetch".
  - Or flag "no data from provider for Fri 11-06" instead of showing nothing.

### 4. The Coming-up list and the brief disagree on upcoming dividends
- kind: ux
- severity: low
- evidence:
  - Dashboard Coming up (next 14 days) lists "Fri, Nov 13 O Dividend paid ≈ $19.31", "Mon, Nov 16 PG Dividend paid ≈ $33.76" and "Mon, Nov 16 XOM Ex-dividend ≈ $22.66".
  - `argus brief loop-income --json` gives `dividends_upcoming: []`.
  - If the brief's window is shorter, the JSON doesn't say so. Someone writing the client brief from it would report "no dividends coming".
- suggestion: include the window in the brief (`dividends_window_days`) or use the same 14 days as Coming up.

### 5. Feature: rate sensitivity for the bond sleeve, now that it's near 52-week lows (r012 evidence for B-017)
- kind: feature
- severity: medium
- evidence:
  - The brief flags BND, VCIT, VGIT and SCHP at 1.9–2.2% above their 52-week lows, with the 10-year at 4.95% (4.91% yesterday).
  - /analysis has no duration and no "+/−100 bp" scenario. The bonds sit in "Unclassified 34.7%". The only quick stress, "SPY falls 10% (via beta)", gives −1.3% because bond betas are 0.06–0.15.
  - My decision this round (hold or add bonds) rests on how much another 25–50 bp would cost. I can't get that from Argus.
- suggestion: weighted duration per bond ETF (from the N-PORT maturities Argus already loads), plus a "rates +50/+100 bp" row in Stress scenarios: −duration × Δy × value.

## Summary for the lead
- Held, no trades: drift ≤0.28 pp, bond sleeve near its 52-week lows. Note 67 on BND (review 11-10). Cash $381.20, return to date +1.51%.
- Top finding: Yahoo's dividend list for the bond ETFs lost its 10-01 row overnight and Argus overwrote its cache, so B-129's November bond income (~$132) is gone again and projections skip Oct/Nov. Merge histories, and walk every missed step.
- Second: performance carries 11-02's value into 11-03 (Yahoo bar gap), so "+2.24% / +$2,213" sits next to a −$651 day, and SPY comparison is null for the whole range. Third: NFP (11-06) vanished from the calendar when Nasdaq dropped that day. B-128 and B-130 verified working.
