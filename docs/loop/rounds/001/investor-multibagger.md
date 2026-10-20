# Round 001: multibagger (growth) investor

## What I did
- **Market view** (`GET /api/market-context`, 1.2 s): S&P 500 +12.8% YTD, Nasdaq 100 +17.2%, Russell 2000 down 5.5% over 3 months
  and small caps behind large caps by 9.3 pp over 3 months. Fear & Greed 38 ("Fear"), 10-year yield 5.10%, WTI oil $96.
  Small and mid-cap growth is out of favour, which is the kind of setup I want to buy into.
- **Screener** (`POST /api/screener`): the universe was not built when I arrived (`built:false, building:false`, see finding 7).
  My first screen started the build, which took about 10 s (5,358 companies, FY2025).
  - Screen A: market cap $0.5–15B, revenue growth ≥20%, gross margin ≥40%, operating margin ≥5%, liabilities/equity ≤2, revenue ≥$100M, giving 19 matches.
  - Screen B: market cap $0.3–25B, revenue and earnings growth ≥15%, ROE ≥15%, FCF margin ≥10%, L/E ≤1.5, giving 23 matches.
- **Research:** I pulled fundamentals and the research bundle for 19 names (DUOL TMDX RMBS LQDT HRMY PODD VICR CELH NUTX KRYS ADEA LRN
  PEGA TOST USLM ESE XZO BLLN LOAR), plus `/api/financials`, `/api/compare`, `/api/peers` and `/api/events` for the finalists.
  Each research call took about 1–3.5 s. Fundamentals took about 1–1.9 s cold.
- **Portfolio `loop-growth`:** created with IWM as its benchmark. I made 9 buys on 2026-10-20 at the current quote, each with a thesis note (review 2026-11-20):

  | Symbol | Shares | Price | Cost | Why |
  |---|---|---|---|---|
  | LOAR | 174 | 62.95 | 10,953 | Revenue +36–39% y/y, op margin 18%→24%, insiders bought $14.3M |
  | PODD | 76 | 143.84 | 10,932 | Revenue +23–34%, every valuation band at its 5-year low |
  | KRYS | 33 | 327.35 | 10,803 | 95% gross margin, 45% op margin, revenue +24–32%, no debt |
  | TOST | 307 | 32.49 | 9,974 | Steady +22–25% growth, op margin 5%→8% |
  | RMBS | 96 | 93.68 | 8,993 | 80% gross margin, 35% op margin, consensus +18–20% |
  | TMDX | 124 | 72.23 | 8,957 | ROE 33%, P/E 16 near band low (short interest 38%, so sized smaller) |
  | HRMY | 205 | 38.93 | 7,981 | Revenue +24%, 5.6x forward P/E |
  | ESE | 32 | 249.59 | 7,987 | Revenue +14–35%, 20% insider ownership |
  | BLLN | 57 | 104.215 | 5,940 | Revenue +64% y/y and profitable; a starter position because of its multiple |

  Invested at cost: **$82,519.60. Cash: $17,480.40.** The largest position is 11% of starting capital (13.3% of invested).
- **Watchlist `growth-candidates`** (not bought): DUOL (growth slowing to +11% guide, $50M of insider selling), CELH (growth
  is acquisition-driven and the latest quarter was +10.6%), VICR (P/S at the 95th percentile, $390M of insider selling; reports today),
  XZO (growth stalled to +3%), USLM, PEGA, NUTX.
- **Earnings ahead:** RMBS 10-26, TMDX 10-27, KRYS/TOST/HRMY 11-02, PODD/BLLN 11-04, LOAR 11-05, ESE 11-18. Most of the book reports within 3 weeks.

## Last round's changes
None. This is round 001.

## Findings

### 1. The screener's annual figures can be 1000x too small, which gives P/E 81,740 and earnings growth of +99,900%
- kind: bug · severity: high
- evidence: `POST /api/screener` (screen A) returned LOAR with `net_income: 72146`, `pe: 81740`, `roe_pct: 0.006`, `net_margin_pct: 0.015`.
  Argus's own `GET /api/financials/LOAR` quarters for 2025 add up to 15.3+16.7+27.6+12.5 = **$72.1M**, and `/api/fundamentals/LOAR` shows
  `pe_ttm` 85.4. In screen B, ESTC had `net_income_prev: 367766` (exactly its FY2026 net income ÷ 1000), so
  `earnings_growth_pct` came out at 99,900%. `GET /api/financials/ESTC?period=annual` shows the prior year was a **loss** of
  −$108.1M, so growth should be null. Any screen with a P/E or ROE bound silently drops these companies, and sorting by earnings growth puts them at the top.
- suggestion: in `build_rows`, reject (null out) a frame value that is less than 1/500 of the same company's revenue, or one that differs
  by a factor of about 1000 from the company-facts value Argus already uses for `/api/financials`. Another option is to source the screener's
  net income from the same company-facts path as the stock page.

### 2. The stock page shows "Revenue growth, latest quarter −12.8%" above a financials table that says +64.4%
- kind: bug · severity: high
- evidence: on `/t/BLLN`, the "Valuation & fundamentals > Growth" box shows **−12.8%** (`/api/fundamentals/BLLN` →
  `revenue_growth_q_yoy_pct: -12.82`, source finnhub). The "Reported financials" table on the same page (SEC) shows Q2 2026 $109.45M vs
  Q2 2025 $66.57M = **+64.4%**, and `/api/research/BLLN` → `growth.quarters[0].revenue_yoy_pct` = 64.4. For a growth investor this is the single most
  important number, and the page contradicts itself. It would have kept me out of BLLN. (For LOAR and PODD the two sources agree.)
- suggestion: when SEC quarters exist, compute latest-quarter and TTM y/y revenue growth from them and use those values in fundamentals. Otherwise, show the source
  next to the figure and flag it when it disagrees with the statements by more than 10 pp.

### 3. Statements miss revenue tagged `RevenueFromContractWithCustomerIncludingAssessedTax` (RMBS has no revenue or margins)
- kind: bug · severity: high
- evidence: `GET /api/financials/RMBS` returns `revenue: null` for all 8 quarters, so `/api/research/RMBS` → `growth.quarters` has null revenue
  growth, gross margin and operating margin. The screener has RMBS revenue ($707.6M FY2025) because its `REVENUE` list includes that tag. SEC
  company facts for RMBS (CIK 917273) tag revenue only as `RevenueFromContractWithCustomerIncludingAssessedTax`. The concept list
  in `backend/argus/providers/sec_edgar.py:45` does not include it.
- suggestion: add `RevenueFromContractWithCustomerIncludingAssessedTax` (and ideally the screener's other revenue tags) to the statements'
  revenue concept so the two code paths share one list.

### 4. A quarter can take a mis-tagged 10-K fact, so VICR shows Q3 2025 revenue of $407.7M (+338% y/y)
- kind: bug · severity: medium
- evidence: `GET /api/financials/VICR`: 2025-09-30 revenue 407,701,000. The quarters around it are $94–113M, so the four 2025 quarters add up to $705M against a
  $407.7M year. SEC facts contain two values for 2025-07-01..09-30. The 10-Q says $110.4M. The 10-K's copy is $407.7M, which is really the
  full-year value, mis-dated by the filer. Argus picked the 10-K copy, and research `growth.quarters` reports +337.6% revenue growth for that quarter.
- suggestion: for a 3-month period, prefer the original 10-Q fact over a later 10-K copy. Also add a sanity check: if the derived quarters don't add up to the
  FY figure within 1%, mark the quarter unreliable.

### 5. Research valuation bands come back with `current: null` the first time a symbol is opened, and that result is cached
- kind: bug · severity: medium
- evidence: my first `GET /api/research/LOAR` (no fundamentals cached yet) returned P/E, P/S, P/B and EV/EBITDA bands with
  `current: null, percentile: null`. Calling `/api/fundamentals/LOAR` and then `/api/research/LOAR` again still returned null (served from the
  research cache). Only `?refresh=true` gave `peTTM current 85.4, percentile 17`. `app.research()` reads only `cached_fundamentals`.
  "Where is it in its own 5-year range" is exactly what I check on a new idea from the screener, and new ideas are always cold.
- suggestion: if no fundamentals are cached, fetch them inside `research()`, or don't cache a bundle whose bands have no current value.

### 6. The screener is stuck on the last calendar year and has no quarterly or TTM growth
- kind: feature · severity: medium
- evidence: the screener status says `fiscal_year: 2025` on 2026-10-20, so its figures are 10 months old. LOAR screens at +23% growth (CY2025), but its TTM growth is +29.8%
  and its last two quarters were +36% and +39% (`/api/research/LOAR` growth). DUOL screens at +38.7%, but its latest quarter is +18% and the guide is +11%.
  Acceleration and deceleration are what a growth screen exists to catch, and the screener can't see either.
- suggestion: add `revenue_growth_ttm_pct` and `revenue_growth_latest_q_pct` fields, built from the 10-Q frames (CY2026Q2 vs CY2025Q2,
  which the frames API already serves). Even the single latest-quarter y/y would change which names I research.

### 7. Rows missing gross margin silently drop out of a gross-margin filter (APP, KLAC, DAVE, TGTX)
- kind: ux · severity: medium
- evidence: the default Screener page shows APP (+70% revenue growth), KLAC, DAVE and TGTX with gross margin "–". These companies tag `CostOfRevenue` rather than
  `GrossProfit`. My screen A (gross margin ≥40%) excluded all of them without saying so. The only hint is the footnote "Rows missing a filtered field drop out" in the code.
- suggestion: derive gross profit as revenue − `CostOfRevenue` / `CostOfGoodsAndServicesSold` when `GrossProfit` is missing. On the page, show
  "N companies excluded because <field> is missing".

### 8. The screener universe wasn't built until a screen was run
- kind: ux · severity: low
- evidence: at 15:20:40 UTC (server started 15:19), `GET /api/screener` returned `built:false, building:false, progress:null`. The build
  only started when I sent `POST /api/screener` and finished about 10 s later. The status endpoint and the Screener page don't start it, so the
  first visitor sees an empty table and the market breadth stays unavailable until someone screens.
- suggestion: start the build when the server starts (or on the status GET) whenever the universe isn't built.

### 9. Dashboard "Day %" and "Day P&L" use different bases for a position bought today
- kind: bug · severity: low
- evidence: on the Dashboard Holdings tab, LOAR shows Day % **+1.70%** and Day P&L **+$18.27** on a $10,972 value. $18.27 is
  174 × (63.06 − 62.95 buy price), which is 0.17%, but +1.70% is against yesterday's close of 62.00. The header says the portfolio is −0.02% today while every row shows +1–3%.
- suggestion: for lots bought today, show Day % against the buy price (or label it "since buy") so the row reconciles.

### 10. `compare`/peers default PEG column is empty; Compare lacks the growth fields
- kind: ux · severity: low
- evidence: `GET /api/compare?symbols=LOAR,PODD,KRYS,TMDX,TOST,RMBS` returns `peg: null` for 5 of 6, but `/api/fundamentals/LOAR` has
  `peg_ttm: 1.71` in a separate field. The default fields also leave out operating margin, latest-quarter growth and forward growth, which are the columns I
  compare growth names on. Peers on `/t/BLLN` was still "Loading…" 5 s after render, and a cold `/api/peers/TMDX` took 4.0 s.
- suggestion: fall back to `peg_ttm` when `peg` is missing. Add `operating_margin_pct` and `revenue_growth_q_yoy_pct` to the compare defaults.

### Smaller notes
- Thesis notes are per symbol, not per portfolio (`NoteBody` has no portfolio). With three investors sharing one instance, two portfolios holding
  the same stock would mix their theses on the stock page.
- Screener on a phone (390 px): the results table is clipped after the Market cap column, so growth, margins and P/E can't be seen. The filter rows also wrap
  "to / max" onto separate lines. This is a concrete case of B-002.
- I couldn't confirm the cause, but it looks wrong: `/api/earnings/BLLN` has no Q1 2026 report, and its Q4 2025 "EPS actual 0.34 (beat +598%)" equals the SEC diluted EPS
  for **Q1 2026** (0.34) rather than Q4 (net income $5.98M). The quarter labels may be shifted.

Summary (3 lines):
1. I ran `loop-growth` with 9 growth buys (LOAR, PODD, KRYS, TOST, RMBS, TMDX, HRMY, ESE, BLLN), $82,519.60 at cost and $17,480.40 cash. Screener → research → buy took about 20 minutes, which is fast.
2. Wrong numbers found: screener figures 1000x too small (LOAR P/E 81,740, ESTC +99,900%); BLLN page shows −12.8% vs +64.4% quarterly growth; RMBS has no statement revenue (missing tag); VICR has a mis-tagged $407.7M quarter.
3. Biggest gaps: the screener has only CY2025 data (no TTM or latest quarter), and valuation bands come back empty on a symbol's first research call.
