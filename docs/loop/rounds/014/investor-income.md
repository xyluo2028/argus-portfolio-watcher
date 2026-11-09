# Round 014: income investor

## What I did
- **Market (Argus market context, reviewed Sun 11-08 ~21:15 ET, latest close Fri 11-06):**
  - A quiet Friday after Thursday's selloff. The S&P 500 rose 0.31% to 7376.86 and the Nasdaq 100 1.35%, but the week was still −2.7% (NDX −4.9%, XLK −8.2%). VIX fell from 28.2 to 25.6.
  - Payrolls were hot: 165K against 65K expected, average hourly earnings +0.4% (0.3% expected), unemployment 4.1%. ^TNX closed at 4.859. On the curve the 10-year is 4.86%, against 5.27% a month ago. The 2-year is 4.51%.
  - Fear & Greed reads 16.8, "Extreme fear". Breadth is now built (59% of the 500 above their 50-day average), so this round the gauge has all its components (B-036 still explains the jump from last round's 1.2).
  - Next up: CPI on Tue 11-10, PPI 11-13, HD earnings 11-17 and the FOMC on 12-09.
- **Portfolio `loop-income` (11-06 close, `argus portfolio show --json`):**
  - **Value and P&L:** value $102,195.90, cost $99,950.30, unrealized +$2,245.60 (+2.25%). Day P&L −$375.21 (−0.37%) against SPY +0.31%. Staples, utilities and HD fell on the rotation back into tech, and JNJ and ABBV rose.
  - **Performance:** TWR +2.46% since 10-20, SPY −4.39%, excess +6.85%. Gain $2,429.09 equals unrealized plus accrued dividends ($2,245.60 + $183.50), to the cent.
  - **Last step:** 102,195.90 − 102,239.61 − 331.50 (Thursday's after-close XOM buy, booked on 11-06 per B-046) = −375.21, which equals Day P&L.
- **Risk, cross-checked by hand:** I rebuilt the risk card from `/api/history` closes for all 17 holdings and SPY, using today's weights over 252 sessions.
  - Volatility 7.89%, beta 0.157 and max drawdown −5.70% match Argus exactly.
  - Historical VaR came out at 95% 0.67% / 99% 1.04%, against Argus's 0.65% / 1.02% ($668 / $1,039). The small gap is interpolation.
  - I also checked down-day beta (SPY down days only): 0.157, the same as the full beta. Thursday's 0.23 ratio was one day, not a pattern, so I'm withdrawing last round's B-021 "beta understates" evidence for this book.
- **Income:** forward income $3,344.27 (3.27% yield, 3.35% on cost). The 2026 expected total is now **$781.91**, up from $653.71 last round, and December is $490.49. Received so far is $183.50 (est.).
- **Drift:** every position is within ±0.38 pp of target, against a ±2 pp band. The largest drifts are HD +0.38, NEE +0.25 and VIG −0.24.
- **Bond duration (by hand, since Argus doesn't have it):** I regressed 1-year daily price returns on ^TNX changes. Effective duration comes out at about 5.4 for BND, 5.7 for VCIT, 4.8 for VGIT and 4.0 for SCHP. For the $35.3k bond sleeve that is about −$900 per +50 bp.
- **Decision: no trade.**
  - Drift is a fifth of the band.
  - The 10-year at 4.86% is well below my 5.1% add trigger (note 67).
  - CPI on Tuesday is the next rate catalyst after a hot payrolls print, and I'm not adding duration or equities ahead of it.
  - Wrote note 81 (BND, review 11-13) with the reasoning and the duration estimate.
- **Cash: $49.70** (invested at cost $99,950.30; realized gains $0; no trades this round).
  - Return to date: (102,195.90 + 49.70 − 100,000) ÷ 100,000 = **+2.25%**.
  - Adding Argus's $183.50 of accrued dividends gives +2.43%. Argus doesn't book dividends as cash, so I don't count them as spendable.

## Last round's changes
- **B-141 (dividend projections follow the payer's own calendar): works, and it fixes my top finding from last round.**
  - BND, VCIT, VGIT and SCHP now project 12-01 and 12-18. There is no January payment. The next bond ex-dates are 2027-02-01 and 03-01 (`/api/events?days_ahead=120`).
  - SCHD moved to 12-09, matching its 12-10/12-11 history. VIG is 12-21. NEE now shows the announced 11-27 (not estimated).
  - SCHP correctly skips January and February 2027, as its own history did in early 2026.
  - The 2026 total rose to $781.91, not the developer's $788.33. The −$6.42 difference is real data: Yahoo has now published the 10-01 bond rows, and those lowered the latest per-share amounts (VGIT 0.206 → 0.189, BND 0.253 → 0.249), which the estimates use.
  - Side effect of the same new data: "received" fell from $185.64 to $183.50 because the 11-02 estimates re-priced. That is expected while Yahoo still lacks the 11-02 rows, a week after the ex-date.
- **B-142 (risk uses the quote-filled last session and flags a VaR breach): works, but I couldn't test the late-Yahoo case.**
  - Yahoo's 11-06 bars were in, so `closes_from_quotes` is null and risk `as_of` is 11-06, the same as performance's end.
  - The new "Last session (11-06)" tile shows −$374 (−0.36%) with `exceeds_var_99: false`, which is right. Header Day P&L is −$375.21. The $0.90 gap is exactly the 2 XOM shares bought after Thursday's close at 165.75 against the 165.30 close (2 × 0.45).
  - I'll re-check the "from quotes" note on the next evening Yahoo is late.
- **B-140 (splits):** no false split flags on my book (`split_warnings: []`). The `stock_split` rows for my holdings are real splits (SCHD 3:1 and SCHP 2:1 in 2024, NEE 4:1 in 2020, KO 2:1 in 2012), and their dividend history is per-share adjusted (SCHD rate 1.068).
- **Re-seen, still open:**
  - **B-131 looks resolved by data:** O's Q3 now reads "EPS 0.43 vs 0.43 (beat +0.7%)" on Coming up (estimate 0.4271), not "+162%". I didn't check whether a code path changed.
  - **B-136 (partly):** the brief's `dividends_upcoming` now lists O paying 11-13. PG's payment and XOM's ex-date on Mon 11-16 are still missing, while Coming up shows them. The brief's 7-day window ends Sunday.
  - **B-132:** HD's 11-17 earnings row is still "quarter 3, year 2027".
  - **B-022:** Targets still opens on "By sector" with "Targets sum to 0.0%" (desktop and 390 px).
  - **B-044:** "Where the risk comes from" lists 15 of 17 holdings. SCHP and XOM are missing, without a note.
  - **B-063:** the footnote "Annual rate = latest payment × payments per year" is wrong for SCHP. Its rate is $1.17, the trailing 12 months, not 0.056 × 12.
  - **B-026:** the first `/risk` took 25.6 s and the second 0.68 s.
  - **B-127:** note 67 (BND, review 11-10) stays in `theses_due` after my newer BND note 81.
  - **B-002 / last round's finding 6:** at 390 px, Analysis's factor table still shows only the names and the Dividends table cuts off after Yield.

## Findings

### 1. Next-12-month dividend events don't add up to forward annual income: SCHP's per-payment amount assumes 12 payments while its calendar projects 11
- kind: bug
- severity: low (a $19 gap, but it's the reconciliation a client report needs: the income calendar total should equal forward income)
- evidence:
  - `/api/portfolios/loop-income/dividends`: SCHP `rate` 1.166, `annual_income` $228.54, every projected event `per_share` 0.09717 (= 1.166 ÷ 12).
  - `/api/events?portfolio=loop-income&days_ahead=365`: SCHP has **11** ex-dates through 2027-11-08. B-141 correctly skips Jan and Feb but adds a second December payment, and the 11 payments total $209.49. Every other holding sums exactly to its `annual_income`.
  - Book total over the next 12 months: $3,325.23 in events against $3,344.27 forward income.
  - SCHP's trailing 12 months were 10 payments (12-01, 12-19, 04-01 … 10-01) summing to 1.166, so the right per-payment figure is about rate ÷ payments in its calendar.
- suggestion: when a payer's calendar has N payments in a year, project each at rate ÷ N (or project the same month's prior-year amount). Test: the sum of next-12-month events = `annual_income` for every holding.

### 2. Bond sleeve rate sensitivity is still missing; a 25-line regression on Argus's own data gives it (B-017)
- kind: feature
- severity: medium (34.5% of the book, and my main decision this week is about rates and CPI)
- evidence:
  - `/exposure` still lists the four bond ETFs as "Unclassified 34.5%" with no duration.
  - From `/api/history/{BND,VCIT,VGIT,SCHP}` and `/api/history/^TNX` (1y, 250 bars), the slope of daily returns on 10-year yield changes gives effective duration of about 5.4 / 5.7 / 4.8 / 4.0. That is about −$900 on the sleeve per +50 bp.
  - The brief flags all four as "near 52w low" (gap 2.4–2.8%) with no context about yields.
- suggestion: until N-PORT duration is wired in, show an "empirical rate sensitivity (1y)" column per bond fund, plus a "10y +50 / +100 bp" row in Stress scenarios, from this regression. Label it as estimated.

### 3. Bond-ETF ex-dates a week old still come only from estimates; "received" moves when Yahoo backfills
- kind: ux
- severity: low
- evidence:
  - The stored dividend history for BND, VCIT, VGIT and SCHP ends at 10-01 (as of 2026-11-09). The 11-02 rows are still absent, and Yahoo took about five weeks to publish the 10-01 rows.
  - The "2026 so far (est.)" tile went from $185.64 to $183.50 between rounds without any trade. Nothing on the page says which part is estimated: $130.43 of $183.50 comes from estimated 11-02 rows (`estimated: true` in the API only).
- suggestion: split the tile into "confirmed $53.07 + estimated $130.43", or give estimated rows a marker in the Dividends table's "2026 received" column.

### 4. Brief misses Monday's events on a Sunday-evening run (B-136, narrowed)
- kind: bug
- severity: low
- evidence:
  - `/api/brief/loop-income` at 11-08 21:15 ET: `dividends_upcoming` = [O pay 11-13].
  - `/api/events` and Coming up both list PG's payment ($33.76) and XOM's ex-date ($24.72) on Mon 11-16. That is the next week's first session, and a client call on Monday morning would want both.
- suggestion: when markets are closed, count the window in sessions (the next 5 sessions plus 1) instead of 7 calendar days from today.

### 5. Analysis at 390 px still hides the income numbers (B-002)
- kind: ux
- severity: low
- evidence: screenshot of `/analysis` at width 390 (no page overflow, no errors). The Dividends table shows Symbol, Pays, Annual/share and Yield. Yield on cost, Annual income, 2026 received, Rest of 2026 and Next ex-date are off the right edge, with no scroll hint. The factor table shows names only.
- suggestion: on phones, show Symbol, Annual income and Next ex-date first, and put the rest behind a row tap.

### 6. "Last session" tile on Analysis and the header's day P&L differ after an after-close trade, with no explanation
- kind: ux
- severity: low
- evidence: header −$375.21 against risk tile −$374 (`last_day.value` −374.31). The difference is the 2 XOM shares filled after Thursday's close above the close price. Risk uses a constant-weight return × value. Both are defensible, but a client sees two numbers.
- suggestion: use the same Day P&L figure in the tile, with the percentage from risk, or add a tooltip: "weights at the prior close; excludes fills at off-close prices".

### 7. First risk load is 25.6 s (B-026)
- kind: perf
- severity: low (known)
- evidence: the first `GET /api/portfolios/loop-income/risk` of the evening took 25.60 s, the second 0.68 s. The other portfolio endpoints took 0.07–1.05 s and the brief 3.6 s.
- suggestion: as in B-026, warm risk in the background after startup.

## Summary for the lead
- No trade. Drift is within ±0.38 pp, the 10-year at 4.86% is below my 5.1% add trigger, and CPI is on 11-10. Note 81 added. Cash $49.70, value $102,195.90, return to date +2.25% (+2.43% with accrued dividends).
- Confirmed: B-141 fixed last round's top bug (bond ETFs 12-01 + 12-18, no January; 2026 income $781.91). B-142's Last session tile works (−$374, within $0.90 of Day P&L, explained by the after-close XOM fill). No false split flags. I matched risk's volatility, beta and drawdown exactly, and VaR within interpolation, from Argus's own price history.
- New findings, all low: SCHP's 11 projected payments sum $19 short of its annual income; the brief misses Monday's PG payment and XOM ex-date on a Sunday run. Still open: B-017 rate sensitivity (medium; I estimated duration about 5 by hand), B-026 (25.6 s), B-022, B-044, B-063, B-127 and B-002.
