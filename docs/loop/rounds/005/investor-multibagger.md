# Round 005: multibagger (growth) investor

## What I did
- **Timing:** about 02:15–03:00 UTC Mon 2026-10-26 (Sun 10-25, 22:15 ET). The market was closed, so prices are the 10-23 close plus post-market quotes.
- **Book** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost **$95,500.05**, value **$93,347.20**, unrealized **−$2,152.85** (−2.25%).
  - Day P&L on 10-23 was −$1,297.47. I recomputed (price − prev_close) × qty for every row, and each row and the total match. The dashboard's "vs IWM" tile (−0.33%) matches IWM's history (276.67 → 275.75).
  - **Cash: $4,499.95.** No realized gains. Return to date is (93,347.20 + 4,499.95 − 100,000) ÷ 100,000 = **−2.15%**.
  - The largest position is PODD at 12.1% of value. Nothing is above 15% at cost.
- **Holdings review:**
  - **LOAR −5.0% on 10-23:** research news has only a Morgan Stanley target cut to $72 (Equal-Weight). Q2 revenue grew +39.4% and the thesis is intact. It reports 11-05.
  - **RMBS reports Monday 10-26 after the close.** Consensus is EPS 0.80 and revenue $217.4M, which is about +22% on Q3-25's $178.5M. I'm holding through it. I wrote a note (id 43) with exit rules for 10-27: revenue growth under 12%, or a falling product line with a guide below consensus.
  - **TMDX:** still on watch, with exit rules due 11-06 (note 41).
  - **The rest are intact.** Latest-quarter SEC revenue growth: INOD +57.8%, BLLN +64.4%, GRND +32.5%, HRMY +30.3%, PODD +23.5%, TOST +23.1%, KRYS +24% (Finnhub), ESE +14.4%.
  - Ten of 11 holdings report between 11-02 and 11-05.
- **Hunt** (`POST /api/screener`):
  - **Screen C** (market cap $0.3–8B, revenue growth ≥25%, operating margin ≥10%, FCF margin ≥10%, P/S ≤8) returned the same 30 names.
  - **New quality screen** (market cap $1–15B, growth 15–100%, operating margin ≥18%, ROE ≥18%, P/E 5–30, liabilities/equity ≤2) returned 8 names.
  - I researched DUOL, BELFA, BCRX, PTCT, TGTX, ADMA and NXT:
    - **DUOL:** growth slowing every quarter (+41 → +35 → +26.5 → +18.3%), consensus Hold, mean target 5% below the price, $47M of insider selling.
    - **TGTX:** +70% growth, but operating margin has fallen to 9%. The P/E of 18.5 is flattered by a $391M tax quarter (B-071). P/S is about 10 on TTM revenue.
    - **ADMA:** growth has stalled (+2.0% and −0.3% in the last two quarters).
    - **NXT:** +8% growth.
    - **PTCT and BCRX:** lumpy royalty and one-off revenue.
    - **BELFA:** P/E at the 95th percentile of its own history.
  - None of them clears my bar. The watchlist is unchanged.
- **Trades: none.**
  - No thesis broke.
  - Ten holdings report within 10 days, and I'd rather add after the prints (INOD is the candidate if Q3 confirms) than put the last $4.5k in beforehand.

## Last round's changes
- **B-048 (consensus from its counts): works and helps.**
  - For all 11 holdings plus LIF, the label, mean and count in `/api/research/<sym>` equal what I compute from the trend row.
  - Examples: KRYS Buy 2.00 with 12 analysts (was "Strong Buy 1.25"), INOD Buy 1.75 with 4 (was "none"), LIF Buy 2.10 with 10, GRND Strong Buy 1.40 with 5. Each shows `rating_source: counts`.
  - /t/RMBS reads "Buy · 8 analysts · mean 2.25", directly above bars of "6 buy · 2 hold". The price-target count (7) is shown separately.
  - It's now trustworthy at a glance.
- **B-056 (stale SEC flag): works.**
  - /t/RMBS shows "SEC's data ends at the quarter ended 2026-03-31 (209 days ago)…" in two places: the valuation card and Reported financials.
  - FCF TTM reads "SEC, 4Q to 2026-03-31". The API gives `latest_period_age_days: 209, stale: true`.
  - It explains why the card's "Revenue growth, latest quarter" (+20.4%, Finnhub, Q2) differs from the table's last row (+8.1%, Q1).
- **B-066 (Markets 1D):** not directly in my workflow. The IWM figures I use agree with history (above).
- **B-045 (earnings dates): the dates now agree.** All 11 holdings have the same next date in `/api/earnings/<sym>` and `/api/events`, KRYS is back in the 14-day list, and TMDX is 11-05 on both. Timing still disagrees (finding 4).
- **Still open:**
  - B-009: BLLN shows −12.8% against SEC's +64.4%.
  - B-061: the RMBS revenue chart's top label reads "|90.24M".
  - B-051: the RMBS price of 85.65 is below every target, and the dot sits on "low 100.00".
  - B-025: the brief's `top_gainers` includes RMBS −0.09% and ESE −0.38%.
  - B-002: at 390 px, the /t/KRYS peers table and Events row are cut off at the right.

## Findings

### 1. FCF silently falls back to Yahoo for 4 of my 11 holdings because SEC capex isn't read (LOAR, TOST, ESE, HRMY)
- kind: bug
- severity: medium
- evidence:
  - In `GET /api/financials/<sym>?period=quarterly`, `capex` is null in every quarter for LOAR, TOST and ESE, and in the last two quarters for HRMY. `free_cash_flow` is null to match.
  - `operating_cash_flow` is present for all of them (LOAR about $30M per quarter, TOST $132–194M).
  - Because of that, `argus fundamentals <sym> --json` gives `fcf_ttm` with source **yahoo** and `sec.fcf_ttm_quarters: null`:

    | Symbol | `fcf_ttm` (Yahoo) | Sum of SEC operating cash flow, last 4 quarters |
    |---|---|---|
    | LOAR | 82.8M | 121.3M |
    | TOST | 474.2M | 635M |
    | ESE | 233.9M | |
    | HRMY | 182.8M | |

  - INOD, RMBS, KRYS, PODD and TMDX do come from SEC.
  - That leaves two FCF definitions across one portfolio (levered from Yahoo, OCF − capex from SEC), so the FCF margins I compare across holdings aren't like for like. This is the same mechanism as B-069 (capex not read for HD, NEE, PEP, O), widened to growth names.
- suggestion:
  - Read the other capex tags these filers use (for example `PaymentsToAcquireProductiveAssets`, or capitalized software plus PP&E, as TOST reports).
  - When capex is still missing, label the card "FCF (Yahoo, levered)" so the switch is visible.

### 2. Statements drop gross profit and operating income on the newest quarters (INOD Q1/Q2 2026), and never derive gross profit (KRYS, GRND, TGTX)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/financials/INOD?period=quarterly`:
    - Q4-2025 has `gross_profit` 27.7M and `operating_income` 10.9M, an operating margin of 15.1%.
    - **Q1 and Q2 2026 have neither**: only revenue, net income, EPS and cash flow.
    - Finnhub on the same page says operating margin is 18.4%. The two quarters I most need to judge operating leverage on a +58% grower are blank in the SEC table.
  - KRYS, GRND and TGTX have `gross_profit` null in all six quarters, so the table's Gross % column is "–", while the card shows Finnhub's 94.6% (KRYS).
  - ESE has no `operating_income` in five of six quarters.
  - BELFA has `eps_diluted` null in every quarter (dual-class EPS), and `net_income` null for Q3 and Q4 2025.
- suggestion:
  - Derive gross profit as revenue − `CostOfRevenue` / `CostOfGoodsAndServicesSold` when there's no `GrossProfit` tag.
  - Fall back to the other operating-income tags, or revenue − costs and expenses.
  - At minimum, mark a quarter where a field present in earlier quarters disappears.

### 3. Momentum "1 week" contradicts the chart's 5D on the same page (RMBS −7.6% vs −1.8%)
- kind: bug
- severity: low
- evidence:
  - /t/RMBS (and `argus fundamentals RMBS --json`) gives `return_1w_pct` −7.57 (Finnhub). The chart's 5D button above it says −1.8%.
  - From Argus's own history: the 10-16 close of 87.25 to the 10-23 close of 85.65 is **−1.83%** (5 sessions). Finnhub's figure equals the 10-19 close of 92.66 to 85.65, which is **−7.57%**, only 4 sessions.
  - The same pattern holds elsewhere:

    | Symbol | Finnhub "1 week" | 5D from history |
    |---|---|---|
    | KRYS | −2.73% | −1.60% |
    | PODD | +4.97% | +5.61% |
    | TOST | +4.01% | +3.45% |

  - Over a weekend, "1 week" is really 4 sessions, measured back from today's date.
- suggestion: compute the short momentum rows (1 week, 1 month) from Argus's own daily bars, anchored on the last session, so they match the chart buttons. Or label the row with its start date.

### 4. Events and the dashboard drop the report timing that `/api/earnings` has (HRMY, PODD, LOAR show no "before open")
- kind: bug
- severity: low (the remaining part of B-045; the dates now agree)
- evidence:
  - `/api/earnings/<sym>` gives `next.timing` **bmo** for HRMY, PODD and LOAR (and `dmh` for BLLN, GRND, INOD, TMDX).
  - `/api/events?portfolio=loop-growth` gives `hour: null` for all seven. The dashboard's "Coming up" card shows a plain "Earnings" for them, against "Earnings · before open" for KRYS.
  - Whether a report is before the open or after the close decides whether I can act the same day.
- suggestion:
  - Fill `hour` in events from the earnings record when Finnhub's calendar leaves it null.
  - Map `dmh` to "time not announced" rather than hiding it.

### 5. The screener's FY2025 growth misled again: ADMA +20% vs +2.0% / −0.3% in the last two quarters (B-019, new evidence)
- kind: feature
- severity: medium
- evidence:
  - My new quality screen (`POST /api/screener` with `revenue_growth_pct` [15,100], `operating_margin_pct` ≥18, `roe_pct` ≥18, `pe` 5–30) returned 8 names:
    - **ADMA** at +20%: SEC quarters show **+2.0%** (Q2-26) and **−0.3%** (Q1-26).
    - **XZO** at +62%: SEC shows +3%, as reported in r004.
    - **NXT** at +20%: SEC shows +8.2%.
  - Three of the eight hits are no longer growing at the rate I filtered for. That's the fourth round running, and each one costs 2–3 research calls to rule out.
- suggestion: add a "Revenue growth, latest quarter (SEC)" column and filter. Research's `growth.quarters[0].revenue_yoy_pct` already computes it per name.

### 6. Sector view puts ESE and GRND in Technology, so the portfolio reads 41.5% tech, with no warning that healthcare is 47%
- kind: ux
- severity: low
- evidence:
  - The `/api/portfolios/loop-growth` positions give `sector: "Technology"` for ESE (Esco Technologies, an industrial maker of test, filtration and aerospace products) and GRND (a consumer dating app).
  - The dashboard's "By sector" card shows Healthcare 47.1%, Technology 41.5% and Industrials 11.5%. On a GICS-style basis, Technology would be about 26%, with Industrials about 19.5% and Communication about 7%.
  - Nothing flags that nearly half the book is one sector (PODD, KRYS, TMDX, HRMY, BLLN), all of which report in the same week.
- suggestion:
  - Prefer the provider's industry (Yahoo/Finnhub `finnhubIndustry`) mapped to GICS-like sectors over the word "Technology" taken from a company name.
  - Optionally, add a sector-concentration line ("Healthcare 47% of value") to the brief.

### 7. The stock page's revenue chart label is still clipped and oversized (B-061, still present)
- kind: ux
- severity: low
- evidence:
  - On /t/RMBS (desktop, 1400 px), the top y-axis label reads "|90.24M" for 190.24M.
  - The bar value label "180.19M" and the axis labels are drawn at roughly twice the table's font size.
  - On the phone (/t/KRYS, 390 px), the same chart's labels are tiny by comparison.
- suggestion: give the y-axis a fixed left padding and scale the label font with the chart width.

## Summary
1. **No trades.** All 11 theses hold, and 10 of the 11 report between 10-26 (RMBS) and 11-05. I wrote an RMBS pre-earnings note (id 43). Cost $95,500.05, value $93,347.20, cash $4,499.95, return to date −2.15%.
2. **Last round's fixes work.** B-048 consensus agrees with the counts for all 12 names I checked. B-056 flags RMBS as stale in both places, with FCF coverage shown. B-045 dates now agree between earnings and events, but timing doesn't.
3. **New findings:**
   - SEC capex is missing, so FCF falls back to Yahoo for LOAR, TOST, ESE and HRMY.
   - INOD's newest quarters lose gross profit and operating income.
   - Finnhub's "1 week" is 4 sessions and contradicts the chart's 5D.
   - Event timing is dropped.
   - Screener FY growth again misled (ADMA).
   - ESE and GRND are mis-sectored.
