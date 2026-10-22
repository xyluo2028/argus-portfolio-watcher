# Round 003: multibagger (growth) investor

## What I did
- **Timing:** about 02:15 UTC Thu 2026-10-22 (22:15 ET Wed 10-21), with the market closed. Quotes are the 10-21 close plus post-market. This is the first full session for GRND and INOD.
- **Book** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost **$95,500.05**, value **$95,147.40**, unrealized **−$352.65**.
  - Day P&L is +$83.98. I checked every row as (price − prev_close) × qty, and all of them match.
  - **Cash: $4,499.95.** No realized gains. Return to date is −0.35%.
  - The largest position is LOAR at 11.5% of value.
- **Theses:**
  - **INOD:** +10.0% on the day (55.05 → 60.56). There was no company news, only "growth streak" pieces. Revenue +57.8% and +54.4% over the last two quarters. Intact.
  - **GRND:** −2.4% (13.73). Revenue +32.5% and +38.3%, EV/EBITDA at the 8th percentile of its own history. Intact.
  - **TMDX:** −3.1%, still decelerating (+20.7%). On watch.
  - **RMBS:** Argus's SEC table now shows decelerating growth (+22.7%, +18.1%, +8.1%), but that ends at Q1 2026. Finnhub shows +20.4% for the latest quarter. RMBS reports on 10-26, and I'll decide then (finding 2).
  - **ESE:** P/S still at the 95th percentile. It reports 11-12.
  - The others (LOAR, PODD, KRYS, TOST, HRMY, BLLN) are unchanged.
- **Hunt** (`POST /api/screener`, 0.01 s, universe already built, FY2025):
  - My screen C (market cap $0.3–8B, revenue growth ≥25%, operating margin ≥10%, FCF margin ≥10%, P/S ≤8, revenue ≥$100M) returned 30 names.
  - A compounder screen (adding gross margin ≥50%, ROE ≥15% and D/E ≤1.5) returned 4.
  - Most of the screen's top names fell apart once I checked recent quarters:
    - DUOL: +41% → +35% → +27% → +18%, with a +11% forecast.
    - ODD: this-year revenue estimate −19%.
    - HROW: −8% and +11%.
    - PTCT, NUTX and GPOR are lumpy or one-off.
  - BELFA held up: revenue +25.2% in Q2 2026 with an 18% operating margin. But its P/E is 57 and the forecast for next year is +8.5%. I added it to `growth-candidates` with a note.
- **Trades: none.**
  - No thesis broke. RMBS, the only open question, reports in 4 days.
  - Nothing from the hunt beat what I already hold, and $4.5k of cash would only buy a token position.

## Last round's changes
- **B-008 (statements revenue tagged including assessed tax): works and helps.**
  - RMBS and BCRX statements now have revenue for all 8 quarters.
  - Research growth and margins are filled in: RMBS gross margin 79.7%, operating margin 34.3%. BCRX has no gross margin, as expected.
  - Without this, I couldn't have seen RMBS's deceleration at all.
  - A related gap remains: Q4 revenue is still missing when the FY and 9-month figures use a different tag from the quarters (finding 3).
- **B-033 (brief scoped to its portfolio):** not re-checked in depth. `/api/events?portfolio=loop-growth` lists only my 11 holdings.
- **B-007 day two: works.**
  - `GET /api/portfolios/loop-growth/performance?range=all` gives `gain −352.65`, which equals unrealized P&L of −352.65.
  - `benchmark_pct` is 0.2538%, which matches IWM's own bars: 276.48 / 275.78 − 1.
  - TWR is −0.369%. That equals (1 − 0.4566%) × (95,147.40 / 95,063.96) − 1.
- **Still broken from my earlier reports:**
  - **B-045 (earnings dates):** `/api/events` gives TMDX 11-04 and KRYS 11-09, while `/api/earnings/<sym>` gives `next` TMDX 10-29 and KRYS 11-02. HRMY now agrees (11-04).
  - **B-015 (cold research bands):** this got worse; see finding 1.
  - **B-009:** BLLN still shows Finnhub's −12.82% for the latest quarter against SEC's +64.4%. BLLN's valuation bands are now an empty list.
  - **B-048 (consensus "None" when every analyst rates a buy):** INOD is still `rating: "none"`, `rating_mean: null` with 1 strong buy and 3 buys. GRND now shows "buy 1.6", but only because the provider started sending a rating.
  - **B-051 (price-target bar):** on /t/RMBS the price (92.80) sits on top of "low 100.00".
  - **B-019 (screener uses last calendar year):** it actively misled this round. Of my screen C's top hits, DUOL (38.7% in the screener against +18% in the latest quarter) and ODD (+25% against a −19% this-year estimate) are shrinking stories.
  - **B-002 (phone width):** on /screener at 390 px, every filter row wraps into two lines ("to" and max on a second line), and the results only start below the first screen.

## Findings

### 1. Valuation bands and "reported growth" are empty on the first open, and even the first `?refresh=true` doesn't fill them (B-015, worse than reported)
- kind: bug
- severity: high
- evidence:
  - Cold `GET /api/research/DUOL` (1.6 s) returned all four bands with `current: null` and `percentile: null`. `growth.reported` was null in every field.
  - A second, non-refresh call (0.004 s) returned the same nulls from cache.
  - `?refresh=true` then filled them in: P/E 15.6 at the 18th percentile, P/S 5.6 at the 12th, reported revenue q/y 18.31.
  - For **BELFA** and **BCRX**, the *first* `?refresh=true` call still returned nulls. BCRX gave `psTTM current: null` while `/api/fundamentals/BCRX` has `ps_ttm 2.1204`. Only a second `?refresh=true` filled them.
  - Seven of the eight names I researched cold this round hit this: DUOL, ODD, HROW, BELFA, BCRX, and BLLN, whose bands list was empty. So my main "cheap vs its own history" check shows nothing for every new idea.
- suggestion:
  - Research should wait for, or fetch, fundamentals before it builds the bands and `growth.reported`.
  - Don't cache a research result whose bands are all null because fundamentals were cold.

### 2. Statements silently stop at an old quarter when SEC company facts lag (RMBS shows Q1 2026 as "latest", while Q2 was filed 07-28)
- kind: bug
- severity: high
- evidence:
  - `/api/financials/RMBS` and the stock page's Reported financials end at **2026-03-31**. Research growth shows the latest quarter at +8.1% y/y.
  - SEC's submissions index for RMBS shows a **10-Q filed 2026-07-28 for the period 2026-06-30**. The companyfacts JSON, both Argus's fresh cache and a direct fetch, stops at the filing dated 2026-04-28.
  - So the gap is on the provider's side. But Argus doesn't say the data is six months old: the same page shows Finnhub "Revenue growth, latest quarter +20.4%" next to a table whose newest row is +8.1%.
  - I nearly cut RMBS for a "+22% → +8% deceleration" that may be one quarter out of date.
- suggestion: when the newest statement period is more than about 100 days older than the newest 10-Q/10-K in the filings index (or simply more than 135 days old), show "Latest SEC data: Q1 2026, a newer 10-Q filed 2026-07-28 isn't in SEC's XBRL feed yet" on the statements card and in research growth.

### 3. Q4 revenue is missing when FY and 9-month figures use a different tag from the quarters (CRMD Q4 2025)
- kind: bug
- severity: medium
- evidence:
  - `/api/financials/CRMD` returns 2025-12-31 (and 2024-12-31) with gross profit $107.3M and operating income $59.1M, but **no revenue**.
  - The company facts have `Revenues` FY2025 = 311,709,000 and 9-month = 183,093,736, so Q4 = **$128.6M** can be derived.
  - The quarters are picked from `RevenueFromContractWithCustomerExcludingAssessedTax` and `...IncludingAssessedTax`, which have no FY or 9-month value for 2025.
  - Q3 2025 also uses the including-tax value of 101.5M, while `Revenues` says 104.3M for the same 3 months.
  - Research's y/y growth and TTM revenue have a hole wherever this happens.
- suggestion: derive Q4 per tag. If the chosen quarter tag has no FY value, fall back to the tag that has both FY and 9-month values for that year. Add a test with CRMD-shaped facts.

### 4. Q4 diluted EPS is null for every company
- kind: bug
- severity: medium
- evidence:
  - In `/api/financials/<sym>` (quarterly), `eps_diluted` is null for 2025-12-31 and 2024-12-31 at LOAR, RMBS, GRND, TOST, PODD and KRYS (all 6 checked). It is also null at ESE's fiscal-year-end quarters (2025-09-30, 2024-09-30).
  - The RMBS stock page's table shows "–" in EPS (dil.) for those rows.
  - The EPS trend I read to judge earnings compounding has a gap every fourth quarter.
- suggestion: derive Q4 EPS as FY EPS minus the 9-month EPS (or Q4 net income ÷ diluted shares when the share count is tagged), and flag it as derived.

### 5. News tone counts articles about other companies (RMBS: 6 "positive", none about Rambus)
- kind: bug
- severity: medium
- evidence:
  - `/api/research/RMBS` `news` covers Netlist's DDR5 product, Cadence, Qnity Electronics, KLA on CNBC, and "Silence Therapeutics, Disc Medicine… moving higher".
  - `news_tone` = `{positive: 6, neutral: 4, negative: 0}` is computed from those articles.
  - GRND gets an empty list instead.
  - So a "positive" tone badge on a holding can mean nothing about the holding.
- suggestion: keep an item only when the symbol or company name appears in its headline or summary (or when the provider tags it as primary), and compute the tone only over the items kept.

### 6. Screener rows have no sector or industry
- kind: feature
- severity: medium
- evidence:
  - The `POST /api/screener` rows have no `sector` or `industry` key (see SEI and HIMS in a sample row), and there is no sector filter in `GET /api/screener` `fields`.
  - Screen C's 30 hits mix uranium royalties, E&Ps, LPG shipping, REITs and pharma with one-off licence revenue. I had to open each one to find the 5 or 6 businesses I can underwrite, and I can't see that 4 of my 11 holdings are in medtech/biotech.
  - Argus already has sectors, from the stock page header and the portfolio rows.
- suggestion: add `sector` (and `industry` if available) to each row, plus an include/exclude sector filter on the Screener page. That alone would have cut screen C from 30 to about 12 names.

### 7. The revenue chart's y-axis labels are cut off and a stray value label overlaps (stock page, Reported financials)
- kind: ux
- severity: low
- evidence: on /t/RMBS at 1400 px (full page), the left axis label for 190.24M is clipped to "90.24M", and a separate "180.19M" label floats over the last bar at the top right.
- suggestion: give the axis a left margin that fits the widest label (or use compact $190M labels), and drop or position the last-value label inside the plot area.

Summary (3 lines):
1. No trades. All 11 theses are intact, INOD is +10% on its first full day, RMBS reports 10-26, and I added BELFA to the watchlist. Cost $95,500.05, value $95,147.40, cash $4,499.95.
2. B-008 works (RMBS and BCRX have revenue) and B-007 day two checks out. B-015 is worse: even the first `?refresh=true` returns null bands. B-045, B-009, B-048, B-051 and B-019 are still present.
3. New: RMBS statements silently stop at Q1 2026 (a Q2 10-Q is missing from SEC's XBRL feed), CRMD Q4 revenue isn't derived, Q4 EPS is always null, news tone counts unrelated articles, and screener rows have no sector.
