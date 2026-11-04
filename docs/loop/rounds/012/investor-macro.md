# Round 012: macro investor

## What I did
- **When:** Tue 11-03 at about 21:15 ET (02:15 UTC 11-04). The market was closed and the latest close was Tue 11-03.
- **Sources:**
  - `GET /api/market-context` and `argus quotes --json` for ES=F, NQ=F, ^VIX, ^VIX3M, ^TNX, ^IRX, HYG, LQD, TLT, TIP, IEF, UUP, EEM, EFA, BZ=F, HG=F, RSP, CL=F and GC=F.
  - The loop-macro endpoints: portfolio, drift, exposure, dividends, risk, performance and simulate, plus the brief.
  - `/api/history/<sym>` for GLD, SPY, IEF, XLE, DBC, RSP and TLT. I used it to compute 20-day correlations myself.
  - Screenshots of Markets (1400 px and 390 px), Dashboard and Analysis.
- **Backdrop on 11-03: rates backed up on strong labor data, and the defensive rotation reversed for a day.**
  - **Indices:** S&P 7,568.92 (+0.36%), NDX +0.68%, RUT +0.23%.
  - **Breadth was weak under the index:** 214 stocks up and 286 down.
  - **Sectors:** XLK +1.3% and XLC +1.2%. XLP −2.07%, XLB −2.0% and XLE −0.85%.
  - **Overnight:** ES −0.67% and NQ −1.30% after the close. SPY post-market was 752.16 (−0.29%).
  - **Rates:** JOLTS came in at 7.523M against 7.150M expected. The 10Y rose about 6 bp to 4.95% and the 2Y to 4.61%, so 2s10s is +34 bp and 10s3m +74 bp.
  - **Volatility:** VIX 20.83 (−1.5%). VIX ÷ VIX3M is 0.98.
  - **Credit:** flat. HYG +0.12% and LQD +0.01%.
  - **Oil:** WTI settled at 96.09 and trades at 95.4 overnight. Brent 103.3.
  - **Gold:** 3,940 (−0.7% on the session). GLD −0.66% on a day SPY rose 0.30%.
  - **Fear & greed:** 27.5 "Fear" with all 7 readings.
- **Regime:** growth is firm (ISM 55.5, JOLTS beat, GDPNow 3.7%) and the oil impulse is fading. Long rates are sticky near 5%. My book stays defensive until payrolls and CPI, with one exception: gold has failed as a hedge.
- **Trade: executed note 56's switch, GLD into IEF.**
  - **Trigger:** GLD's 20-day correlation to SPY is **0.69**, above my 0.5 threshold (60-day 0.51). IEF's is −0.44, TLT's −0.29 and DBC's −0.04.
  - GLD is 1.0% above its 52-week closing low of 355.78 and −4.9% over 1M. The trigger has read 0.54, 0.60, 0.76 and now 0.69, so it isn't noise.
  - **Simulated first:**
    - at the default price: net cash +$26.60 and realized −$238.32;
    - at post-market prices: net cash +$33.11 and realized −$224.76;
    - effective positions would go from 10.15 to 9.52.
  - **Recorded:** SELL 12 GLD @ 360.39 (txn 49) and BUY 47 IEF @ 91.31 (txn 50), both at post-market quotes.
  - **Targets:** GLD out, IEF 12.5% and SGOV 13.5%. They now sum to 100%; last round they summed to 99%.
  - **Notes:** thesis note 68 (IEF, review 11-13). Note 69 keeps note 62's XLE→RSP plan staged: WTI is below 98, but I'm waiting for ISM services on 11-04.
- **Book after the trade, marked at the 11-03 close:**
  - value **$98,157.69** and cost $98,404.56;
  - unrealized −$246.87 and realized −$287.03;
  - Day P&L −$362.92 (−0.37%) against SPY +0.30%. XLP (−$171) and XLE (−$84) did the damage.
- **Cash: $1,308.40** (100,000 − 287.03 realized − 98,404.56 cost). Value plus cash is $99,466.09, a return to date of **−0.53%**.

## Last round's changes
- **B-128 (NaN bars dropped, not fatal): works.**
  - History, risk, correlations, returns, research and charts all load. The 11-02 bar is now in history (SPY close 752.10).
  - Yahoo serves 11-03 with a NaN close, as preflight said. Argus drops that bar cleanly instead of failing the whole write.
  - Risk is labeled "to 2026-11-02", which is honest.
  - This helped: I could finally test note 56's trigger and trade on it.
  - **But the gap isn't handled in performance** (finding 1).
- **B-130 (soft failures): partly checked.** Nothing failed tonight, so I couldn't see an error state. `/api/research/GLD` returned `errors: {}`.
- **B-129 (a passed estimated ex-date keeps counting): defeated by the data this round.**
  - Last round, loop-macro's 11-02 accrual was $63.08. Tonight `dividends_accrued` is 0, and November is empty.
  - The cause is that Yahoo dropped dividend rows. Argus lost them too (finding 2).
- **B-006 and B-126 (calendar):** Monday's and Tuesday's actuals are present (ISM 55.5, JOLTS 7.523M).
  - **Friday's payrolls are gone** (finding 3).

## Findings

### 1. Performance doesn't handle the 11-03 bar gap: it shows no benchmark and an old value labeled as today
- kind: bug
- severity: high (wrong numbers on the main performance card, and the benchmark comparison is blank)
- evidence:
  - `GET /api/portfolios/loop-macro/performance` (before my trade) returns `summary.end: "2026-11-03"` and `end_value 98547.21`. That's the 11-02 value.
  - It also returns `twr_pct −0.170`, `gain −177.50`, **`benchmark_pct null`** and **`excess_pct null`**. The last series row is `{d: 2026-11-03, value: 98547.21, twr_pct: −0.170, bench_pct: null}`.
  - At the same time, the portfolio endpoint reports `market_value 98184.29` and `day_pnl −362.92` for 11-03.
  - **Correct gain:** 98,184.29 − net invested 98,724.71 = **−$540.42**, not −$177.50. That equals unrealized −478.14 plus realized −62.27.
  - **Dashboard card:** "Return −0.17%", "SPY –" and "Excess return –". The line goes flat into 11-03, and the SPY line just stops.
  - So the headline says −$362.92 for the session while performance says $0 for the same session.
  - **Cause:** Yahoo has no 11-03 close for anything, so the portfolio is carried forward and SPY is null. A null benchmark at the end nulls the whole-period comparison.
- suggestion:
  - While the latest session's daily bar is missing, value that day from the settled quote (the closes are in `quote.prev_close` and `price`), as `provisional_today` already does intraday. Do the same for the benchmark.
  - Failing that, end the series at the last complete session (11-02) and say so. Don't stamp the 11-02 value as 11-03, and don't drop the benchmark comparison because the last point is missing.

### 2. Yahoo dropped October dividend rows, and Argus overwrote its stored history with them: the 11-02 accrual of $63 vanished again
- kind: bug
- severity: high (wrong income numbers; B-129's fix is undone by a provider regression)
- evidence:
  - The read-only DB `dividend_history` (refreshed 2026-11-04 02:13) now ends with:
    - SGOV `['2026-09-01', 0.307]` and IEF `['2026-09-01', 0.332]`. Last round, `last_ex_date` was **2026-10-01**;
    - VTIP `['2026-07-01', 0.68]`. Its October payment is gone too.
  - Yahoo itself (`yf.Ticker('SGOV').dividends`) now ends at 09-01, so the provider deleted rows.
  - **Effect in Argus:**
    - `/api/portfolios/loop-macro` has `dividends_accrued 0`, and `/dividends` has `received 0.0` and Nov `projected 0.0`. Last round, loop-macro's 11-02 accrual was $63.08.
    - SGOV's next estimate is 12-01. The 10-01 and 11-02 estimates fall outside B-129's half-period grace because they're counted from 09-01.
    - The run rate moved with the old payment: SGOV `last_amount` went from 0.329 to 0.307.
    - VTIP has nothing left this year. Its "next ex-date ~2027-01-04" skips a whole quarter.
  - Analysis shows "2026 so far (est.) $0.00" with an empty November bar.
- suggestion:
  - Merge dividend history instead of replacing it: never delete a past ex-date row Argus has already seen. Treat a provider answer that loses rows as partial, the same pattern as `_keep_releases` for the calendar.
  - Log a warning when a refresh returns fewer past rows than are stored.
- backlog: B-129 and B-074 (new cause)

### 3. Friday's payrolls silently disappeared from the calendar
- kind: bug / ux
- severity: medium-high (payrolls are the week's key macro event and my XLE trade trigger)
- evidence:
  - **Last round,** `calendar.events` had NFP, unemployment and AHE on Fri 11-06 at 08:30 (B-006 was confirmed).
  - **Tonight,** neither `events` nor `all_events` (153 rows) has a single row for 11-06, 11-07 or 11-08. Markets jumps from "Thu, Nov 5" straight to "Tue, Nov 10", and Monday 11-09 has no major release either.
  - **Raw feed:** `api.nasdaq.com/api/calendar/economicevents?date=2026-11-07` (the query that carries Friday's rows) returns only China's FX reserves and no US rows. So Nasdaq removed them.
  - Argus can't tell me whether payrolls were postponed or the feed has a hole, and the page gives no hint that a weekday is empty.
  - `economic_events` logs a warning only when *today* is empty.
- suggestion:
  - Keep upcoming rows seen in earlier fetches when a later fetch loses them, flagged "no longer listed by source".
  - At minimum, show "no releases listed for Fri Nov 6 (source gap?)" for empty weekdays in the window.

### 4. Markets 1D for oil and gold is still the overnight tick, not the session
- kind: bug / ux
- severity: medium (re-sighting of B-016 / B-055)
- evidence:
  - Under "Market closed as of Tue, Nov 3, 4:00 PM ET", the cards read:
    - "WTI $95.43 −0.69%" (95.43 ÷ 96.09);
    - "Gold $3,949 +0.22%": the 11-03 session was 3,969.6 → 3,940.4, **−0.74%**.
  - Gold's card is green on a red session for gold.
  - Spark tails: CL=F `[104.12, 96.46, 96.09, 95.43]` and GC=F `[3898.9, 3969.6, 3940.4, 3955.3]`.
- backlog: B-016, B-055

### 5. Fear & greed is 5.7 "Extreme fear" until breadth loads, then 27.5 "Fear" minutes later
- kind: ux
- severity: medium (re-sighting of B-036)
- evidence:
  - The first `/api/market-context` returned `score 5.7`, 5 components, and `errors.breadth: "needs the screener's universe"`.
  - About 10 minutes later it returned `27.5`, 7 components and `errors {}`.
  - **Price strength 100 "Extreme greed"** comes from 11 new highs against 0 lows, on a day when decliners led 286 to 214.
  - The API gives no component count or "partial" flag. The page says "average of 7 readings" only once all 7 are present.
- suggestion: B-036. While readings are missing, show "5 of 7 readings (breadth loading)" and don't color the score as a regime call.
- backlog: B-036

### 6. Correlation card shows only 252 days; my rule needs 20 days, which I compute by hand
- kind: feature
- severity: medium (it decided tonight's trade)
- evidence:
  - The Analysis correlation matrix gives GLD/SPY **0.40** (252-day), which looks diversifying.
  - From Argus's own `/api/history` closes, the 20-day correlation is **0.69** and the 60-day 0.51.
  - The 1-year number hides the regime change a macro desk rebalances on. I've written the 20-day by hand in five rounds of notes (42, 48, 51, 54, 56).
- suggestion: add a 20d / 60d / 1y window toggle on the correlation card, or a "vs benchmark, 20d" column in "Where the risk comes from".

### 7. Simulate prices at the 4 pm close after hours, and has no risk-after
- kind: ux
- severity: low (re-sighting of B-109 / B-023)
- evidence:
  - With no price given, simulate priced GLD at 359.26 and IEF at 91.16, the regular closes. The post-market quotes were 360.39 and 91.31. Realized came out −$238.32, against −$224.76 at the prices I actually traded.
  - It still returns no beta, volatility or VaR before and after. I had to judge the trade's risk effect from the correlations by hand.
- backlog: B-109, B-023

### 8. Selling after hours removes the sold shares' after-hours gain from the after-hours P&L
- kind: bug
- severity: low
- evidence:
  - Before the trade: `ext_pnl −13.20`. GLD contributed 12 × (360.39 − 359.26) = +$13.56.
  - After SELL 12 GLD @ 360.39: `ext_pnl −26.80`. I captured that +$13.56 in the sale, but it vanished from "After hours" and shows nowhere.
  - The BUY side is right: IEF's ext P&L counts only the 79 old shares (+$11.85). B-046 looks fixed.
  - The regular-session Day P&L is right too: −$362.92 still includes GLD's −$28.68 after the sale.
- suggestion: as for B-117, count the sold shares' move from the close up to the sale price in the after-hours P&L.
- backlog: B-117 (after-hours twin)

### 9. Re-sightings (short)
- **Analysis "Targets & drift"** still opens "By sector" with "Targets sum to 0.0%", while 10 position targets summing to 100% are saved (B-022).
- **`/?p=loop-macro`** opened loop-growth; I had to set localStorage (B-118).
- **Brief `theses_due`** has 16 rows, most of them superseded r001 theses. Selling GLD did drop its notes, which is good (B-127).
- **Risk endpoint:** 11.5 s on the first call and 0.25 s cached (perf; cold cache after the history refill).
- **Markets at 390 px:** 5,472 px tall, and the sector, curve and calendar tables are clipped (B-002).

## Consistency checks that passed
- **Day P&L:** −$362.92 equals the sum of the position Day P&Ls and matches the brief. It still includes sold GLD after the trade.
- **Realized P&L:** GLD went from −63.30 to −288.06 (−224.76), matching the simulate result at the same prices. IEF's average cost of 91.2811 is the correct blend.
- **Drift:** after the targets update, `targets_sum_pct 100` with no warnings. Every row is within ±0.8 pp, and IEF is −0.80.
- **Curve spreads:** 2s10s 34 bp and 10s3m 74 bp match the curve points (4.95 − 4.61 and 4.95 − 4.21). The 10Y card (4.95%, +6 bp) agrees with ^TNX 4.952.
- **Term structure:** VIX 20.83 ÷ VIX3M 21.27 = 0.98, which matches the fear & greed component.
- **Returns:** `/api/returns/GLD` uses the correct bases: 1D is the 11-02 close of 361.65, and 1M is 10-02.
- **Pages:** Markets, Dashboard and Analysis had no page errors and no horizontal overflow.

## Summary for the round lead
1. **Trade:** I sold 12 GLD @ 360.39 and bought 47 IEF @ 91.31 (note 56's trigger: GLD's 20-day correlation to SPY is 0.69, IEF's −0.44). loop-macro is worth $98,157.69, with cash $1,308.40, −0.53% to date.
2. **High:** performance stamps the 11-02 value as 11-03 and blanks SPY and excess return because Yahoo has no 11-03 bar. It shows a gain of −$177 while the real figure is −$540. Separately, Yahoo dropped its October dividend rows and Argus overwrote its stored history, so B-129's $63 accrual is back to $0.
3. **Medium-high:** Friday 11-06 payrolls vanished from the calendar with no warning (Nasdaq removed the rows). B-128 works: history, risk and correlations are back. Oil and gold 1D are still the overnight tick (B-016/B-055).
