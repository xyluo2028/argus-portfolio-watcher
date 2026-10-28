# Round 007: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:40 UTC Wed 2026-10-28 (Tue 10-27, about 22:15 ET). The market was closed, so prices are the 10-27 close plus post-market quotes.
- **Book** (`GET /api/portfolios/loop-growth`, matches the dashboard):
  - 11 positions, cost $97,758.05, value **$94,801.90**, unrealized −$2,956.15.
  - Day P&L on 10-27 was **−$1,659.27 (−1.72%)**, while IWM was **+1.15%**. Almost all of the loss is INOD.
- **INOD fell 25.3% (59.91 → 44.74).** It's −20.1% on my cost and now 5.0% of the book.
  - Why: the brief's `headlines` and Research → News carry reports that the company abruptly laid off about 550 people in India, with more cuts in the Philippines. The termination notices cite a "ramp-down of the business assignment".
  - What it means for the thesis: note 38's break condition is "growth under 25% or loss of a top customer". A large customer program shrinking is exactly that risk. The company hasn't confirmed anything, though, and Q3 is due 11-05 (`argus events`).
  - **Decision: hold, no add.** I won't sell a 5% position on a press report 8 days before the print that will confirm or refute it.
  - Note 49 sets the rule: exit the whole position on 11-05 if the company confirms a top-customer ramp-down, if Q3 growth comes in under 25%, or if the Q4 outlook implies under 25%.
- **Hunt** (`POST /api/screener`, universe built, 5,351 companies, FY2025):
  - Filters: market cap $0.3–10B, growth ≥20%, gross margin ≥40%, operating margin ≥5%, ROE ≥12%, P/E ≤50, liabilities/equity ≤2. It returned 12 names, three of which I already own (TMDX, RMBS, HRMY).
  - **DUOL** (already on my watchlist, reports 11-03) looked best on the screener: growth +38.7% at a P/E of 15.9. Research (`/api/research/DUOL`, 1.4 s) told a different story:
    - Quarterly growth is **decelerating**: +41.5%, +41.1%, +35.0%, +26.5%, then **+18.3%** in Q2-26.
    - The P/E is flattered by Q3-25 net income of $292M on $272M of revenue (a tax item).
    - Insiders sold $47.5M against $0.5M bought. Short interest is 20% of the float.
    - **Pass:** growth is below my 20% floor and still slowing.
  - The other hits are a gold miner, a silver miner, a land developer and names I've already ruled out. Nothing to buy with $2.2k of cash.
- **MNTN** (watchlist, note 47): closed 9.44, +0.4%. It reports 11-04, and the plan in note 47 stands.
- **Rest of the book:** no thesis news. Upcoming reports:
  - KRYS 11-02 (before open), TOST 11-03 (after close).
  - BLLN, HRMY and PODD 11-04.
  - GRND, INOD, LOAR and TMDX 11-05.
  - ESE 11-19.
- **Trades: none.**

  | Cost | Value | Unrealized | Cash | Return to date |
  |---|---|---|---|---|
  | $97,758.05 | $94,801.90 | −$2,956.15 | **$2,241.95** | (94,801.90 + 2,241.95 − 100,000) ÷ 100,000 = **−2.96%** |

## Last round's changes
- **B-046 (trades after the close count from the next session): works.**
  - The 10-27 series point has `flow_in` 2,258.00, the RMBS buy from 10-26 at 22:17 ET.
  - Value change minus the flow: 94,801.90 − 2,258.00 − 94,203.17 = **−1,659.27**. That's exactly Day P&L.
  - TWR checks out: (1 − 0.013894) × (1 − 1,659.27 ÷ 96,461.17) − 1 = **−3.086%**, which matches `twr_pct` and the dashboard's −3.09%.
  - Header Day % is −1.72%, on the same base.
  - The overnight gap from last round is closed: `/performance` `end_value` is $94,801.90, which equals the dashboard value.
  - RMBS Day P&L of −$170.61 is 121 × (88.91 − 90.32). The lot was filled at the prior close, so this can't tell "from the fill" apart from "from the prior close".
  - The INOD and GRND lots are dated 10-21 on /t/INOD, consistent with the series.
- **B-085 (500s on first open): works.** /t/IA and /t/IDR, never opened before, loaded with no 4xx/5xx responses and no page errors.
- **Holding sectors (instrument refresh restructure): fine.** All 11 holdings still carry their sector.
- **B-088 (MNTN Q2 report vanished): not reproduced.** `/api/earnings/MNTN` again lists the 2026-06-30 report (0.10 vs 0.1931, miss). I'll keep watching it through the 11-04 refresh.
- **B-009 / B-079 (valuation card lags the SEC table): still open, and worse.** See finding 2.

## Findings

### 1. On a −25% day the Momentum column still reports the previous session: INOD "Year to date +17.6%" while the stock is −12.2% YTD (B-083)
- kind: bug
- severity: high (new evidence for B-083: the column misses the crash entirely, under a header that says it's current)
- evidence:
  - The /t/INOD Momentum column (Finnhub, `GET /api/fundamentals/INOD`) against the chart buttons (`/api/returns/INOD`, anchored on the 10-27 close of 44.74):

    | Period | Momentum column | Chart button | Column ÷ prior close? |
    |---|---|---|---|
    | 1 week | **+8.8%** | 5D **−18.7%** (55.05 → 44.74) | 59.91 ÷ 55.05 = +8.8% ✓ |
    | 3 months | **+0.8%** | **−24.7%** (59.41 → 44.74) | 59.91 ÷ 59.41 = +0.8% ✓ |
    | 6 months | +26.6% | +7.0% | |
    | Year to date | **+17.6%** | **−12.2%** (50.95 → 44.74) | 59.91 ÷ 50.95 = +17.6% ✓ |
    | 1 year | −21.8% | −43.6% | |

  - The card header reads "as of Tue, Oct 27, 10:13 PM ET · same figures as the dashboard tabs". The rows Argus computes itself are current: 1 month is −35.4%, and the 52-week-high, 50-day and 200-day rows are right.
  - The same pattern shows on /t/IA: "1 week +1.9%" against the 5D button's +4.8%.
  - A holder looking at this card on the evening of a crash sees a stock up 17.6% this year.
- suggestion: compute every momentum row from the `/api/returns` bases, as 1 month already is, and drop the Finnhub `return_*` fields.

### 2. Two days after RMBS's print, its valuation card mixes Q3 EPS with Q2 revenue and Q2 growth (B-009, B-079)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/fundamentals/RMBS`. The SEC block has `latest_period` 2026-09-30 and `fcf_ttm_through` 2026-09-30.
  - Yahoo's `eps_ttm` has moved to **2.42**, which is Q3: SEC diluted EPS sums to 2.43.
  - `revenue_ttm` is still **$756.33M**, through Q2. SEC through Q3 gives $796.11M.
  - `revenue_growth_q_yoy_pct` is still **20.43** (Q2). The table shows +22.3% for Q3.
  - `fcf_margin_pct` is still **41.4%**: SEC FCF through Q3 divided by Yahoo revenue through Q2. On one window it's 312.93 ÷ 796.11 = 39.3%.
  - Last round only the provider lagged. Now fields on the same card come from different quarters, with nothing marked.
- suggestion: when `sec.latest_period` is newer than the provider's window, take TTM revenue, latest-quarter growth and the FCF margin's denominator from the SEC quarters. At minimum, label each provider field with its period.

### 3. P/E on the stock card isn't price ÷ the EPS shown right above it (INOD 32.7 vs 34.7; RMBS 39.6 vs 36.7)
- kind: bug
- severity: medium
- evidence:
  - On the /t/INOD card, EPS (TTM) is **$1.29** (Yahoo) and P/E (TTM) is **32.7** (Finnhub). 44.74 ÷ 1.29 = **34.7**.
    - The P/E implies EPS of 1.368. SEC's diluted EPS over 4 quarters is 0.41 + 0.42 + 0.25 + 0.24 = 1.32, which gives 33.9.
  - On /t/RMBS (via `/api/fundamentals`), EPS TTM is **2.42** and `pe_ttm` is **39.64**. 88.91 ÷ 2.42 = **36.7**. The P/E still sits on the pre-print EPS of about 2.24.
  - The research valuation band uses the same Finnhub P/E (INOD current 32.72, 30th percentile). So "cheap against its own history" is judged on an EPS the card doesn't show.
  - Three P/Es are available (32.7, 33.9, 34.7) and the page shows one with no source to reconcile it.
- suggestion: compute P/E as the live price ÷ the EPS shown on the card (or ÷ SEC diluted TTM), and use that in the valuation band's `current`. Fall back to the provider's P/E only when EPS is missing.

### 4. A holding crashes 25% and neither the dashboard nor the stock page says why
- kind: feature
- severity: medium
- evidence:
  - The dashboard shows INOD at −25.32% / −$1,623.19 with no hint of the cause. On /t/INOD the price header, chart and card show nothing either.
  - The reason sits at the very bottom, in Research → News, and in `GET /api/brief/loop-growth` → `headlines.INOD`. The brief even carries the useful summary: "notices reportedly pointed to a 'ramp-down of the business assignment'".
  - My whole decision (thesis broken or not?) depended on that one line. In the UI it's about six screens below the price.
- suggestion: when a holding moves more than ±8% in a session (or over 3× its typical move), show the top headline for that symbol and day under its row in Holdings, and under the price on the stock page. The brief already picks it.

### 5. The screener's FY2025 figures sent me to DUOL: "growth 38.7%, P/E 15.9" is a stock growing 18% on a one-off tax gain (B-019, B-071)
- kind: feature
- severity: medium
- evidence:
  - The screen in "What I did" ranked DUOL near the top: growth 38.7%, operating margin 13.1%, P/E 15.9.
  - Research `growth.quarters` gives the latest-quarter growth as **+18.3%**, down from +41.5% over five quarters. Q3-25 net income was **$292.2M** on $271.7M of revenue.
  - The screener has the same fiscal-year-only fields as last round. Again it costs one research call per hit to rule out the obvious.
- suggestion: add the "latest-quarter revenue growth" and "TTM operating margin" that research already computes as screener fields. Mark P/E when one quarter's net income is above that quarter's revenue.

### 6. Peers card takes about 6.4 s on a cold symbol and still reads "Loading…" after 8–10 s on the page
- kind: perf
- severity: low
- evidence:
  - Cold `GET /api/peers/CRMD` took 6.40 s and `/api/peers/XZO` 6.31 s. Warm calls take 0.01 s.
  - Playwright screenshots of /t/IA (8 s settle) and /t/INOD (10 s settle) both show Peers "Loading…". Every other card had rendered.
  - Comparing against peers is my second step after the card, and it's the slowest thing on the page.
- suggestion: return the peer list immediately and fill the metric rows as they arrive, or prefetch peer metrics when the stock page opens.

### 7. Same page, two next-report dates: IA Events says "Wed, Dec 16", Reported financials says "Thu, Dec 17, before open" (B-045)
- kind: bug
- severity: low
- evidence: /t/IA, first open. The Events card shows "Wed, Dec 16 · Earnings · EPS est. 0.27". The Reported financials header, a few lines below, shows "Next report Thu, Dec 17, before open · EPS est. 0.27".
- suggestion: drive both from one earnings-date resolver, as already proposed in B-045.

### 8. MNTN quote has its open above its high (open 9.56, high 9.521)
- kind: bug
- severity: low
- evidence: `argus quotes MNTN --json` returns `open` 9.56, `high` 9.521, `low` 9.23 and `price` 9.44 for session 2026-10-27. The day range bar would place the open outside the range.
- suggestion: when a quote's OHLC is inconsistent, widen high and low to include the open and price, or take OHLC from the daily bar.

### 9. Ownership "Value" is priced at today's close but labeled with the 6-30 filing date
- kind: ux
- severity: low
- evidence:
  - `GET /api/research/INOD` → `ownership.top[0]`: BlackRock, Date Reported 2026-06-30, 2,717,666 shares, Value **$121,588,381**. That equals 2,717,666 × **44.74**, today's price after the crash.
  - The value BlackRock reported at 6-30 was different. Next to a date, it reads as a reported figure.
- suggestion: label the column "Value at today's price", or show the value as reported.

## Summary
1. **No trades.** INOD fell 25% on reports of layoffs from a customer "ramp-down", which hits the thesis-break risk. I'm holding to the 11-05 print with explicit exit rules (note 49). The screener's top new idea, DUOL, failed on decelerating growth. Cost $97,758.05, value $94,801.90, **cash $2,241.95**, return to date −2.96%.
2. **Last round's fixes:** B-046 works. Day P&L equals the series change minus the flow, TWR and the header agree, and `/performance` now matches the dashboard overnight. B-085 works: no 500s on first opens. B-088 wasn't reproduced.
3. **Top findings:**
   - The Momentum column is a session stale and missed INOD's crash: YTD shows +17.6% against −12.2% (B-083, raised to high).
   - RMBS's card mixes Q3 EPS with Q2 revenue and growth (B-009, B-079).
   - P/E ≠ price ÷ the EPS shown above it.
   - Nothing in the UI says why a holding fell 25%.
