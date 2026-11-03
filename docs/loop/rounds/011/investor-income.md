# Round 011: income investor

## What I did
- **Market (Argus market context, Mon 11-02 close, reviewed about 21:15 ET):**
  - Rotation day. The S&P 500 fell 0.51% to 7541.40, the Nasdaq 100 fell 1.39% and XLK fell 2.95%, while XLY rose 2.41% and XLF 1.86%. SPY fell 0.48%. VIX is 21.15 (+8.9%) and Fear & Greed is 25.6 ("Fear"). Breadth has loaded: 317 advancers against 183 decliners, and 64% of stocks are above their 50-day average.
  - Rates eased a little. The 10-year is 4.91% on the curve (4.894% on the gauge) and the 2-year 4.59%. A month ago they were 5.28% and 4.83%. WTI is about $96, down from $101.6 on Friday after the Iran headlines, which pulled energy down.
  - Macro: ISM manufacturing came in at 55.5 against 54.5 expected, with prices paid 75.2. JOLTS is Tue 10:00, ISM services Wed 10:00, claims Thu 08:30, and payrolls plus unemployment Fri 11-06 08:30.
- **Portfolio `loop-income` (11-02 close):**
  - Value $101,778.32, cost $99,618.80, unrealized +$2,159.52 (+2.17%).
  - Day P&L is +$200.16 (+0.20%) against SPY −0.48%. HD +3.63% (+$191), PEP +2.24% and KO +1.86% led. XOM −4.05% (−$167), MSFT −2.83% and ABBV −2.05% lagged.
  - Day P&L doesn't match the value change. Value rose $69.13 from Friday's $101,709.19, with no trades. The ~$131 gap is the bond ETFs' 11-02 ex-dividend, which the prices dropped by but Argus never credited (finding 1).
  - Drift: every position is within ±0.36 pp of target. The largest gaps are HD +0.36 pp, VCIT −0.19 and ABBV −0.18. The band is ±2 pp.
  - Bond ETFs are 34.5% of the book (BND 11.8%, VCIT 9.8%, VGIT 7.9%, SCHP 4.9%), above my 30% floor.
  - I couldn't review risk, performance or fundamentals because history is broken (finding 4).
- **Income:** forward income is $3,354.06, a 3.30% yield (3.37% on cost). Both check: 3,354.06 ÷ 101,778.32 and ÷ 99,618.80. The 17 "Rest of 2026" cells sum to the tile's $467.43, and November's $105.86 is O + NEE + JNJ + XOM + MSFT. But 2026 expected fell from $652.43 to $520.50 overnight, because the November bond-ETF payments are missing (finding 1).
- **Post-earnings review:**
  - **O (reported 11-02 after the close):** revenue was $1.62B against $1.55B expected (+4.6%). Argus's "EPS 1.12 vs 0.43, beat +162%" compares an AFFO-type figure with a GAAP estimate (finding 2), so I ignored it. The monthly dividend is unchanged at $0.272, a 5.67% yield against the 10-year's 4.89%: the spread is still a thin ~0.8 pp. Hold at the 4% target. I archived note 39 (due 11-03) and wrote note 64 (review 11-17).
  - **XOM:** fell 4.05%, and day-loss alert #4 fired. The cause is oil, not the company: Q3 beat (4.23 vs 4.12) and the news reports the dividend raised to $1.07. Weight is 3.88% against a 4% target. Hold. Note 65 (review 11-16, its ex-date).
- **Trades: none.** Every gap is under a fifth of the band. I also can't see risk or performance this round, and I won't trade on numbers I can't check.
- **Cash: $381.20.**
  - Invested at cost: $99,618.80. Realized gains: $0.
  - Return to date: (101,778.32 + 381.20 − 100,000) ÷ 100,000 = **+2.16%**.
  - Adding the $53.07 of accrued dividends Argus shows gives +2.21%, and adding the ~$131 of uncredited bond-ETF dividends gives about +2.34%.

## Last round's changes
- **B-006 (calendar after DST): works.**
  - Payrolls are on Fri 11-06 at 08:30, claims Thu 11-05 at 08:30, JOLTS Tue 11-03 at 10:00 and ISM services Wed 11-04 at 10:00.
  - ISM manufacturing is Mon 11-02 at 10:00 with its actual (55.5).
  - Nothing is dated on a weekend except Sunday's "OPEC Meeting" row in `all_events`. It isn't in the curated list, so it does no harm.
- **B-126 (window starts on the last session): works.** On Monday evening the window starts on Fri 10-30. The curated list shows ECI 0.8%, and `all_events` also has Chicago PMI 55.3. GDPNow is now on Mon 11-02 at 12:00, not Saturday.
- **B-088 (past reports survive refreshes): partly checked.**
  - `/api/portfolios/loop-income/earnings`, the brief and Coming up still have ABBV's and XOM's 10-30 rows. O's 11-02 row appeared the same evening.
  - `/api/earnings/<sym>` and the stock page's Events table return 500 (history), so I couldn't check there.
- **B-116:** still not checkable, because no PCE row is in the window.
- **Still open, re-confirmed on /analysis:**
  - B-063: the footnote still says "Annual rate = latest payment × payments per year".
  - B-022: Targets opens on "By sector" with "Targets sum to 0.0%".
  - B-012: the tile reads "50% / 50%" under "Stock / ETF".
  - B-087/B-125: Coming up says "Mon, Nov 16 PG Dividend paid ≈ $33.76", using the past tense for a future payment.

## Findings

### 1. A passed ex-date that the payment history doesn't have yet disappears: November's bond-ETF income ($131.93) is neither received nor projected, and Day P&L no longer matches the value change
- kind: bug
- severity: high (my income tile dropped 20% overnight with no trade, and a client report would be wrong. Bond ETFs are my main income source.)
- evidence:
  - `GET /api/portfolios/loop-income/dividends`, compared with r010:
    - 2026 expected fell from $652.43 to **$520.50**, and November from $238 to **$105.86**.
    - `received` is still $53.07.
    - VCIT, BND, VGIT and SCHP each show `last_ex_date 2026-10-01` and next `~12-01`. Nothing for November.
  - The missing amount is exactly the four November estimates from r010: VCIT 126×0.34 = 42.84, BND 169×0.249 = 42.08, VGIT 140×0.189 = 26.46, SCHP 20.55. Total **$131.93**.
  - The ex-date did happen. Yahoo's `prev_close` is dividend-adjusted, for example BND 71.3032 and VCIT 79.3399 in `argus quotes BND VCIT --json`.
  - **Day P&L doesn't reconcile.** It's +$200.16, but value moved only +$69.13 (101,778.32 − 101,709.19, no trades). The gap of $131.03 is the dividend: the price drop was excluded from Day P&L, but the dividend wasn't added anywhere.
  - Cause:
    - `dividend_histories` was fetched at 02:13 UTC, and Yahoo's `get_dividends("BND")` still ends at 2026-10-01.
    - In `services/dividends.analyze_holding`, an *estimated* ex-date is only projected while `today < nxt`.
    - Only an *announced* one that has passed "counts as received" (the comment near line 84).
    - So the 11-02 estimate drops out of both lists until Yahoo catches up.
  - The dashboard's Coming up and the brief show no bond-ETF payment at all this month.
- suggestion:
  - Treat an estimated ex-date the same as an announced one. Once the date passes and qty > 0, count it as received (marked "est.") until the history confirms or replaces it, within half a period.
  - Add a test: monthly payer, today = ex-date + 1, history not yet updated.

### 2. O's "beat +162.2%" compares AFFO (1.12) with a GAAP EPS estimate (0.43)
- kind: bug
- severity: medium (this goes straight into a client note. For REITs, half my real-estate exposure, every report will look like a blowout.)
- evidence:
  - Dashboard Coming up and /t/O Events: "Mon, Nov 2 O Reported EPS 1.12 vs 0.43 (beat +162.2%)".
  - `/api/portfolios/loop-income/earnings` returns `epsActual 1.12, epsEstimate 0.4271, epsSurprisePct 162.23` (Finnhub).
  - Argus's own SEC table on /t/O shows diluted EPS of 0.33–0.37 a quarter (2025-09 to 2026-06), so 1.12 can't be GAAP EPS. It matches O's AFFO run rate.
  - Revenue (1.62B against 1.55B, +4.6%) is the meaningful surprise, but the line doesn't show it.
- suggestion:
  - When actual ÷ estimate is above 2× or below 0.5×, or the company is a REIT, don't print a surprise %. Print "basis differs (likely FFO vs GAAP)" and show the revenue surprise instead.
  - Longer term, use FFO/AFFO consensus for REITs.

### 3. XOM's declared $1.07 dividend (ex 11-16) is still projected at $1.03 (new evidence for B-064, r010 finding 2)
- kind: bug
- severity: low
- evidence:
  - Brief headline (11-02 22:10 UTC): "...alongside a higher quarterly dividend of US$1.07".
  - `/dividends`: XOM `rate 4.12`, event 2026-11-16 `per_share 1.03`, `amount 22.66`.
  - Dashboard Coming up: "Mon, Nov 16 XOM Ex-dividend ≈ $22.66". It should be 22 × 1.07 = $23.54.
  - ABBV is the same: 1.73, against the 5.2% raise to about $1.82.
- suggestion: as B-064. Take the declared amount for announced events where a provider gives it, and show "raised x%" in the Dividends table and the brief.

### 4. The broken price history (known, being fixed) takes out most of my risk job; the UI shows only raw "Internal Server Error" or a permanent "Loading…"
- kind: ux (the evidence is for the lead's history fix. The ux part is how a failure shows.)
- severity: medium
- evidence (all at 21:15 ET, with the `price_bar.c` NOT NULL error in `data/server.log`):
  - **Broken for me:**
    - `GET /api/portfolios/loop-income/risk` → 500 in 4.4 s. That's volatility, beta, VaR, drawdown, the stress table, correlations and "where the risk comes from".
    - `/performance` → 500 in 0.7 s: TWR, vs SPY and the dashboard chart.
    - `/fundamentals` → 500 in 1.4 s: the holdings tabs Financials, Growth, Profitability and Momentum.
    - Per stock: `/api/fundamentals/XOM`, `/api/research/O`, `/api/earnings/O` and `/api/returns/BND` → 500. So there was no payout-ratio check after O's report, no news and no earnings history.
  - **Still working:** dividends (0.04 s), drift (0.03 s), exposure, simulate, the brief (1.1 s) and market context (including its sparklines and returns).
  - **The UI:**
    - The /analysis Risk card and the dashboard Performance card show only the text "Internal Server Error".
    - On /t/O, "Valuation & fundamentals" and "Peers" still read "Loading…" after 6 s, the chart is "Internal Server Error", and 5D through Max read "–".
    - No page names the cause ("price history unavailable") or says what still works.
  - One NaN bar on one symbol (PAYS, in another portfolio's watchlist, shows in the log too) fails whole endpoints that mostly don't need that bar, such as earnings and fundamentals.
- suggestion:
  - Besides the NaN fix, have the history cache skip or drop a bad bar and log it rather than raise.
  - Have cards show "Couldn't load price history (provider data error). Showing other data", and turn "Loading…" into an error after a timeout.

### 5. HD's last earnings row has no date and mixes calendar and fiscal labels
- kind: bug
- severity: low (unconfirmed which source is wrong)
- evidence:
  - `/api/portfolios/loop-income/earnings` HD `last`: `date null, period 2026-09-30, quarter 2, year 2027, epsActual 4.92`.
  - `next`: `2026-11-17, quarter 3, year 2027`.
  - HD's fiscal year ends around late January, and its quarter to early August was reported mid-August. A "period 2026-09-30" with no date doesn't match any HD report, and fiscal Q2 2027 would be about a year away.
- suggestion: drop or relabel a Finnhub row with no date, and take the fiscal quarter from SEC (`fy`/`fp`) when they disagree.

### 6. Curated calendar keeps three ISM sub-indices but drops Monday's big miss (construction spending −1.9% vs +0.4%) and Chicago PMI
- kind: ux (new evidence for B-094)
- severity: low
- evidence:
  - `market-context.calendar.events` on 11-02 lists ISM Manufacturing PMI, Employment and Prices.
  - `all_events` also has "Construction Spending −1.9% (cons. 0.4%)" at 10:00 and "Chicago PMI 55.3 (55.8)" on 10-30. The curated list has neither.
  - "Core CPI" and "CPI" each appear twice with no m/m or y/y label (B-091).
- suggestion: add construction spending and Chicago PMI to the curated list, and label the m/m and y/y rows.

## Summary for the lead
- Held, no trades. Drift ≤0.36 pp. Notes 64 (O post-Q3, ignore Finnhub's +162% "beat") and 65 (XOM −4% on oil, alert #4 fired); archived note 39. Cash $381.20, return to date +2.16%.
- Top finding: passed *estimated* ex-dates vanish until Yahoo's history catches up, so November's $131.93 of bond-ETF income is neither received nor projected, and Day P&L (+$200.16) no longer matches the value change (+$69.13). Second: O's "beat +162%" compares AFFO with a GAAP estimate.
- B-006 and B-126 verified working. History breakage blocks risk, performance, fundamentals and per-stock earnings/research for me, and the UI shows a raw "Internal Server Error" or a permanent "Loading…".
