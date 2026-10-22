# Round 003: income investor

## What I did
- **Market (Argus market context, as of the 10-21 close, reviewed at 22:15 ET):**
  - The 10-year is at 5.13% (5.12% on 10-20, 4.96% a month ago). The 2-year is at 4.81% and the 30-year at 5.42%.
  - Fear & Greed is 27 ("Fear"). The S&P 500 was +0.58% on the day, and SPY +0.525%.
  - FOMC is on 10-28.
  - Rates are about 17 bp higher than a month ago. The brief flags BND, VCIT, VGIT and SCHP as near their 52-week lows. I'm still happy to hold intermediate duration at a 4 to 5% yield.
- **Portfolio `loop-income` (day two):**
  - Value $98,084.89, cost $98,347.12, unrealized −$262.23 (−0.27%). Last session was −$290.36 (−0.30%) against SPY's +0.53%. Staples, O and ABBV fell 1.5 to 1.8%.
  - Risk: beta 0.14, volatility 7.2%, 1-year max drawdown −5.6%, 1-day 95% VaR $665. The 2022 rate-shock replay gives −14.0%.
  - Income: forward income is $3,332.38 a year (3.40% on value, 3.39% on cost).
  - Drift: every position is within ±0.22 pp of target, against a ±2 pp band.
  - The bond ETFs (BND, VCIT, VGIT, SCHP) make up 35.5%, above my 30% floor. Argus can't show that figure; see B-017.
- **Research:**
  - Payout safety: I checked Argus's dividend run rates against EPS and FCF, using fundamentals and the SEC statements (findings 1, 2 and 5).
  - Upcoming events: PG reports 10-22 before the open and goes ex-dividend on 10-23. NEE reported on 10-21: EPS 1.24 beat the 1.19 estimate, but revenue of $8.09B missed the $8.72B estimate. KO reports 10-27 and MSFT 10-28.
  - Realty Income (O) yields 5.90%, only about 0.8 pp over the 10-year, and Argus shows its payout as 236% of GAAP EPS. A REIT needs AFFO for that test, and Argus doesn't have it.
- **Swap I considered:** SCHP into VCIT. `POST /simulate` shows only weights, so I worked out the income by hand: +$11.8 a year (VCIT 63.3 sh × $4.08 = $258.40, against SCHP's $246.57). That isn't worth giving up inflation protection with the FOMC a week away. I kept SCHP.
- **Decision: no trades.** Nothing is outside its band, rates moved 1 bp on the day, and no dividend changed. I'm keeping the cash as a withdrawal buffer.
- **Housekeeping:**
  - Added alert #5: PG `day_loss_pct 4` ahead of its earnings.
  - Added note #39 on O (yield spread and the AFFO caveat), with a review date of 2026-11-03.
- **Cash:** $1,652.88, unchanged. Invested at cost: $98,347.12. Realized gains: $0.

## Last round's changes
- **B-033 (brief scoped to its portfolio): works.**
  - `GET /api/brief/loop-income` lists only my holdings.
  - Upcoming earnings are PG 10-22, KO 10-27 and MSFT 10-28. RMBS and the watchlist names are gone.
  - NEE, which reported on 10-21 and has actuals, sits under `earnings_recent`.
  - `top_losers` now contains only decliners.
  - This helps: I could hand this brief to a client.
- **B-010 (lumpy TIPS ETF run rate): works.**
  - SCHP shows `rate 1.258`, equal to `trailing_12m 1.258`, for income of $246.57 a year.
  - VCIT, BND and VGIT keep their last payment × 12, and their trailing 12 months stay close (4.08 vs 3.99, 2.988 vs 2.94, 2.268 vs 2.292).
  - Portfolio forward income is $3,332.38. The labels weren't updated to match (finding 3).
- **B-007, day-two performance check: works.**
  - `/performance` gives `gain −262.23`, which equals `totals.unrealized_pnl −262.23`, with `net_invested 98,347.12`.
  - The benchmark return is +0.525%. That matches SPY's own closes in Argus's history (769.05 → 773.09, +0.525%).
  - Max drawdown is −0.295%, from the +0.03% close on 10-20 down to −0.27%, which is right.
  - On the dashboard, Return −0.27%, SPY +0.53% and Gain −$262 all match.
- **B-008:** doesn't touch my work.
- **Still open, re-confirmed today:**
  - B-012: the tile still reads "Stocks / ETFs 51% / 49%", and its subtitle now reads "ETF / Stock", which contradicts the title.
  - B-022: Targets & drift still opens on "By sector", with empty target boxes and "Targets sum to 0.0%".
  - B-044: "Where the risk comes from" still shows 15 of 17 rows; SCHP and MSFT are missing.
  - B-041: look-through shows HD, O and NEE "via ETFs $0".
  - B-017: BND, VCIT, VGIT and SCHP are still in `funds_without_profile`, and look-through shows 35.5% as "Unclassified".
  - B-002: at 390 px, the Analysis stress, factor and dividends tables cut off after two or three columns.
  - B-023: simulate still has no income or drift (see above).
  - B-040, B-013 and B-026: see findings 4 to 6.

## Findings

### 1. SEC quarterly statements have no diluted EPS for fiscal Q4, for every company I hold
- kind: bug
- severity: medium
- evidence:
  - `GET /api/financials/KO` (quarterly) has `eps_diluted null` for 2025-12-31 and 2024-12-31. Net income is filled for those quarters ($2.27B and $2.19B).
  - The same happens for every fiscal year-end, not only December:
    - JNJ: 2025-12-28.
    - PG: 2026-06-30 and 2025-06-30.
    - MSFT: 2026-06-30 and 2025-06-30.
    - HD: 2026-02-01 and 2025-02-02.
  - The /t/KO "Reported financials" table shows "–" in EPS (dil.) on those rows.
  - Cause: `providers/sec_edgar.py:55` marks `eps_diluted` `additive=False`, so the fourth quarter isn't derived as the 10-K year less the nine-month figure, the way net income is.
  - Effect on my work: I can't build a trailing-12-month EPS from SEC data to check payout. Any TTM figure is either three quarters long or has to come from Yahoo.
- suggestion:
  - Derive Q4 EPS from the annual figure less the nine-month figure (or Q1 + Q2 + Q3). Alternatively, use Q4 net income ÷ Q4 diluted shares when the share count is available.
  - Mark the value as derived.

### 2. The dashboard Dividends "Payout" column contradicts the yield and EPS beside it (KO 77% vs 64%, JNJ 60% vs 82%)
- kind: bug
- severity: medium
- evidence:
  - The Dashboard's Dividends tab gives Payout as `payout_ratio_pct` from Finnhub (`/api/portfolios/loop-income/fundamentals`).
  - Argus's own figures give a different ratio. For KO, Annual/sh is $2.12 and EPS (TTM) on /t/KO is $3.33, a payout of **63.7%**, but the column shows **77.2%**. KO's SEC net income for the last four quarters is $13.7B, against about $8.9B of dividends, which is about 65%.
  - For JNJ, $5.36 ÷ EPS $6.55 is **81.8%**, but the column shows **60.0%**. JNJ's latest quarter (2026-09-27) EPS was $0.09 after a charge, and the Finnhub figure doesn't include it.
  - Others are close: PEP 74.1 vs 72.3, PG 66.8 vs 63.8, XOM 53.0 vs 52.6.
  - Payout ratio is the number I use to judge dividend safety, and the two KO figures put it on opposite sides of my 70% comfort line.
- suggestion:
  - Compute payout as Argus's annual dividend rate ÷ EPS TTM, from SEC data once finding 1 is fixed or from the same EPS the stock page shows.
  - Add an FCF payout (dividends ÷ SEC FCF TTM) next to it.
  - Keep Finnhub only as a labeled fallback. This goes with B-043, the two-yields problem.

### 3. The run-rate footnote is wrong since B-010, and nothing marks which payers use the trailing year
- kind: ux
- severity: low
- evidence:
  - The Dashboard Dividends tab (`HoldingsTabs.tsx:87`) and the Analysis Dividends card (`DividendsCard.tsx:113`) still say "Annual rate = latest payment × payments per year".
  - SCHP's last payment is $0.056 (× 12 = $0.67), but its Annual/sh shows $1.26, the trailing 12 months. VTIP's is similar.
  - `/dividends` still returns `irregular: false` for SCHP, so neither the API nor the page tells you which method was used.
  - SCHP's projected events are $0.1048 a month, which is neither its last payment nor any actual payment.
  - A client looking at SCHP's line can't reconcile $0.056 a month with $1.26 a year.
- suggestion:
  - Add a `basis: "last_payment" | "trailing_12m"` field.
  - On the page, show a marker such as "T12M" next to the rate.
  - Change the footnote to "latest payment × payments per year, or the trailing 12 months for payers whose payments vary".

### 4. The Dividends page still overrides announced dates with estimates, now for KO too (B-013)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/events?symbol=KO&days_ahead=70` returns KO `ex_dividend 2026-12-01` and `dividend_pay 2026-12-15` (Yahoo). /t/KO's Events card shows the same dates.
  - The Dividends tab and Analysis show KO's next ex-date as **~Dec 15**. That's last ex-date + 3 months, and it happens to equal the pay date.
  - PG still shows **~Oct 24** (a Saturday), while events have the announced **Fri 10-23**.
  - Coming up still lists "Sat, Oct 31 · JPM · Dividend paid", although I bought JPM after its 10-06 ex-date. The Dividends page correctly gives JPM no 2026 income.
  - The bond ETFs are still estimated for Sun 11-01.
- suggestion: same as round 002. Prefer an announced ex-date from events, roll estimates to a business day, and drop `dividend_pay` events for lots bought after the ex-date.

### 5. Fundamentals FCF is still Yahoo's levered figure (B-040), and NEE's is negative
- kind: bug
- severity: high (existing B-040)
- evidence:
  - /t/KO "Free cash flow (TTM)" shows **5.22B**. The SEC table on the same page has quarterly FCF of 1.76B + 2.87B + 4.56B + 3.37B = **12.56B**.
  - MSFT is unchanged at `fcf_ttm 16,545,500,160`.
  - NEE returns `fcf_ttm −17.77B`, which makes a utility's dividend look entirely debt-funded. That is normal for a capex-heavy utility, but it isn't the operating cash flow − capex figure the SEC table uses.
- suggestion: as in B-040, use the sum of the last four SEC quarters when they exist, and label the source.

### 6. Cold `/risk` now takes 33 s (it was 17.7 s); the brief takes 6 s
- kind: perf
- severity: medium (existing B-026, worse)
- evidence:
  - First call after the overnight restart: `curl /api/portfolios/loop-income/risk` took **33.4 s**, and `/api/brief/loop-income` took **6.1 s**.
  - Warm timings: `/dividends` 2.5 s, `/fundamentals` 1.6 s, `/exposure` 1.1 s, `/performance` 0.9 s.
  - Analysis waits on `/risk`, so the first daily look at risk takes half a minute.
  - The /t/KO price chart still read "Loading chart…" after 6 s and only appeared after about 15 s.
- suggestion: warm risk (history for held symbols) in the background at startup and after the close, or return the cached result while it recomputes.

### 7. Dividend growth from Argus's own payment history: last raise, 1-year growth, streak
- kind: feature
- severity: medium
- evidence:
  - The only growth figure is Finnhub's "Div CAGR 5Y". It's blank for all six ETFs and lags by up to a year.
  - Argus already holds each symbol's payment history (`trailing_12m`, `last_amount` and frequency come from it), but it doesn't show when a payer last raised or by how much.
  - The decision it would change: I'd see a freeze (a payer that skipped its usual raise quarter) early, before a cut. That is the main early warning for an income portfolio. Today I have to compare amounts across quarters by hand from the provider.
- suggestion:
  - Per holding, show last raise date, last raise %, growth over 1 year and 3 years from the history, and a "no raise in 12+ months" flag.
  - Add a portfolio line for income growth year on year at constant shares.

### 8. Simulate still can't tell me the income effect of a swap (B-023)
- kind: feature
- severity: medium (existing B-023)
- evidence:
  - The call: `POST /api/portfolios/loop-income/simulate` with `{"trades":[{"symbol":"SCHP","side":"sell","qty":196},{"symbol":"VCIT","side":"buy","amount":4990}]}`.
  - It returns weights, concentration and sector look-through, with no forward income, yield or drift against targets.
  - I computed the +$11.8 a year by hand from `/dividends`.
  - It also buys 63.3329 fractional shares from an `amount`, with no option to round to whole shares.
- suggestion:
  - Add `income_before` and `income_after` (from the dividend run rates already in `/dividends`) and `drift_after` against the saved targets.
  - Add an option for whole shares.

### 9. Three different market betas on one page, none labeled against the others (B-021)
- kind: ux
- severity: low (adds evidence to B-021)
- evidence:
  - The Analysis "Beta vs SPY" tile shows **0.14** (1 year). The factor table shows a Market loading of **0.36**, and the stock pages show Finnhub betas.
  - XOM shows a 1-year beta of **−0.67** in "Where the risk comes from", against a Finnhub beta of **0.17**. KO shows −0.26 against 0.29.
  - I re-computed the 1-year betas from Argus's own daily closes and got XOM −0.672, PEP −0.162 and KO −0.260, so the risk numbers are right.
  - The factor loading and the tile differ because they come from different models and windows. Nothing on the page says so.
  - A client sees three answers to "how much market risk do I have?".
- suggestion:
  - Add a one-line note under the factor table: "multi-factor loading; not comparable to the beta vs SPY tile".
  - Label stock-page betas "provider, 5-year monthly".

Other notes (not counted above):
- The XOM statements come from a new registrant, "ExxonMobil Holdings Corp". `/api/financials/XOM` has only two quarterly periods (2026-06-30 and 2025-06-30) and no annual figures. The 2026-06-30 figures look like a six-month total: net income $14.5B, revenue $116B. The predecessor registrant's history isn't stitched in. I can't confirm this from Argus alone, so I'm leaving it as a lead for the developers.
- Alerts and notes are still global (B-018). The new O note is dated `created_at 2026-10-22`, the UTC date, although I wrote it at 22:17 ET on 10-21 (B-049).
- No alerts fired. PG's after-hours move of +1.22% ahead of its earnings tomorrow is visible on the dashboard.

Summary for the round lead:
1. No trades (each position within ±0.22 pp, 10-year 5.13%, cash $1,652.88). B-033, B-010 and the day-two performance check (gain −$262.23 = unrealized P&L; SPY +0.525% matches its history) all work.
2. New: SEC quarterly statements have no fiscal Q4 diluted EPS for KO, JNJ, PG, MSFT and HD. The Dividends "Payout" column (Finnhub) contradicts Argus's own rate ÷ EPS (KO 77% vs 64%). The run-rate footnote is wrong for SCHP after B-010.
3. Still broken: B-013 (KO estimated ex-date ~12-15 vs announced 12-01, PG Sat 10-24, JPM pay), B-040 (KO FCF 5.2B vs 12.6B), B-026 (cold `/risk` 33 s), B-012, B-022, B-044, B-041, B-017, B-023.
