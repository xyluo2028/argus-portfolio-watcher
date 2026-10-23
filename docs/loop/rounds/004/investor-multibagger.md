# Round 004: multibagger (growth) investor

## What I did
- **Timing:** about 02:13–03:00 UTC Fri 2026-10-23 (22:13 ET Thu 10-22). The market was closed, so prices are the 10-22 close plus post-market quotes.
- **Market:** it was a risk-off tech day. SMH fell 6.0% (556.70 → 523.35), QQQ 2.9% and SPY 1.2%, while IWM rose 0.07%.
- **Book** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost **$95,500.05**, value **$94,644.67**, unrealized **−$855.38** (−0.90%).
  - Day P&L is −$502.73. I recomputed (price − prev_close) × qty for every row, and each row and the total match.
  - **Cash: $4,499.95.** No realized gains. Return to date is (94,644.67 + 4,499.95 − 100,000) ÷ 100,000 = **−0.86%**.
  - The largest position is LOAR at 11.9% of value. Nothing is above 15% at cost.
- **Holdings review:**
  - **RMBS −7.6%:** a semis sell-off. SMH was −6% and Argus's news has nothing company-specific. RMBS reports 10-26 (amc), and I'll decide on it then.
  - **ESE −5.9% and HRMY −6.0%:** I found no news on either in research. Both theses are unchanged.
  - **TMDX:** still decelerating. Revenue grew +20.7% in Q2, against +37% for FY2025. Q2 net income was 14.7M against 34.9M a year earlier, and adjusted EPS missed. The stock is −40% YTD and below both moving averages. I wrote a thesis note (id 41) with exit conditions to check on 11-06, after Q3.
  - The other seven are intact.
- **Hunt** (`POST /api/screener`):
  - **Screen C** (market cap $0.3–8B, revenue growth ≥25%, operating margin ≥10%, FCF margin ≥10%, P/S ≤8, revenue ≥$100M) returned the same 30 names as last round.
  - **Quality screen** (gross margin ≥55%, ROE ≥15%, growth ≥20%) returned 9 names. **Scale-up screen** (growth 30–300%, gross margin ≥50%, operating margin ≥0, FCF margin ≥5%) returned 11.
  - I researched XZO, COLL, GEN, NVMI, LIF and HIMS.
  - **XZO:** SEC revenue growth fell to +3% against the screener's +62% (FY2025).
  - **COLL:** the stock fell from 36 to 22 in August–September, and revenue grew +6% in the latest quarter.
  - **NVMI:** a foreign filer, so there are no SEC quarters.
  - **HIMS:** GAAP operating margin of −12.9%.
  - **LIF** was the only one that held up:
    - Revenue grew +37.8% and +38.1% in the last two quarters, with a 78% gross margin.
    - But GAAP operating margin is about 0. The 25.7% net margin and the P/E of 24.6 come from a $129.7M Q4-2025 tax item.
    - Insiders sold $77M over 12 months and bought nothing.
  - I added LIF to `growth-candidates` with a note.
- **Trades: none.**
  - No thesis broke. TMDX's deciding data point is Q3 (11-04/05), and RMBS reports in 3 days.
  - LIF isn't yet at the operating leverage I underwrite.
  - $4.5k only buys a token position.

## Last round's changes
- **B-015 (cold research bands): works and helps.**
  - These names were never researched before this round, and the first call filled the bands:
    - COLL: P/E 16.1 at the 43rd percentile.
    - GEN: P/E 14.1 at the 25th percentile.
    - LIF: all four bands, P/S 6.3 at the 33rd percentile.
    - HIMS: P/S 2.6 at the 32nd percentile.
  - Reported growth was filled on the first call for all six names, with `partial: false`. Each call took 1.5–2.2 s.
  - XZO (IPO, too few points) has an empty band list, and NVMI has only P/B. Both are expected for new or foreign listings.
- **B-058 (fiscal-Q4 EPS): works.**
  - All 11 holdings have a derived Q4 EPS (`annual_less_ytd`). Examples: LOAR 0.13, PODD 1.43, TOST 0.17, RMBS 0.58, INOD 0.25, ESE FY-Q4 8.44.
  - The large values agree with net income: TMDX 2.59 on $105.4M (a tax benefit), ESE 8.44 on $218.7M.
- **B-040 (FCF from SEC): works.**
  - TMDX `fcf_ttm` is 79.04M, sourced from `sec`.
  - LIF's card shows FCF (TTM) 103.24M, which equals the sum of its table's last four quarters (23.81 + 17.21 + 36.57 + 25.65).
  - The card's EPS TTM ($1.72) and revenue TTM ($572.56M) also tie to the table.
- **Still open** (findings 2–4 and the list below):
  - B-045 earnings dates.
  - B-056 (RMBS still ends at 2026-03-31 with no staleness flag in `/api/financials/RMBS`).
  - B-048 (INOD `rating: none` with 1 strong buy and 3 buys).
  - B-061 (the revenue-chart y-axis label is still clipped on /t/LIF).
  - B-002 (the /screener filter rows still wrap at 390 px, and the results table is cut off at the Market cap column).

## Findings

### 1. Consensus headline and mean come from Yahoo while the counts and bars come from Finnhub, and they contradict each other (KRYS "Strong Buy 1.25" with 1 strong buy out of 12)
- kind: bug
- severity: high
- evidence:
  - `GET /api/research/<sym>` returns `analysts.rating` and `rating_mean`, which come from Yahoo `recommendationMean` (`app.py:1158`). The `trend` field and the "Ratings by month" bars come from Finnhub.
  - The mean computed from the trend (1 = strong buy … 5 = strong sell), side by side:

    | Symbol | Argus rating | Argus mean | Argus count | Trend now | Computed mean | Analysts in trend |
    |---|---|---|---|---|---|---|
    | KRYS | strong_buy | 1.25 | 9 | 1 SB, 10 B, 1 H | 2.00 | 12 |
    | LIF | strong_buy | 1.50 | 9 | 1 SB, 7 B, 2 H | 2.10 | 10 |
    | COLL | strong_buy | 1.50 | 8 | 2 SB, 5 B, 1 H | 1.88 | 8 |
    | XZO | strong_buy | 1.33 | 2 | 1 SB, 2 B | 1.67 | 3 |
    | GEN | buy | 2.09 | 10 | 5 B, 6 H | 2.55 | 11 |
    | PODD | buy | 2.00 | 23 | 4 SB, 11 B, 11 H | 2.27 | 26 |

  - On /t/LIF, the Consensus tile reads "Strong Buy · 9 analysts · mean 1.50". The bars directly below read "8 buy · 2 hold", which is 10 analysts and mostly plain buys.
  - The headline overstates conviction on most names, and its analyst count disagrees with the bars on the same card.
- suggestion:
  - Compute the label and mean from the same Finnhub trend row that the bars show, and use that row's total as the count.
  - Keep Yahoo's figure only as a fallback when no trend exists. That also fixes B-048 (INOD "none" with 4 buys).

### 2. Earnings dates still disagree on one stock page and between endpoints, and KRYS drops out of the events list (B-045)
- kind: bug
- severity: high
- evidence:
  - On /t/LIF, the Events card says "Tue, Nov 10 Earnings", while Reported financials on the same page says "Next report Mon, Nov 9, during market".
  - `/api/earnings/KRYS` gives `next 2026-11-02 bmo, EPS est 1.92`. `/api/events?symbol=KRYS&days_ahead=30` gives `2026-11-09 bmo, est 1.8065`.
  - Because of that, KRYS (which reports 11-02 in the earnings data) is **missing** from the default 14-day `/api/events?portfolio=loop-growth`, even though 11-02 is inside the window.
  - TMDX is 11-05 in earnings and 11-04 in events.
  - Timing is null in events for HRMY and PODD, while earnings gives `bmo` for both.
  - I nearly missed that a 11%-weight holding may report in 10 days.
- suggestion: use one source of truth for the next earnings date (the `/api/earnings` `next` value) in events, the brief and the stock page's Events card. When the providers disagree, show both dates.

### 3. P/E, net margin and ROE count one-off tax benefits as earnings, with no warning (LIF P/E 24.6 on a ~0% operating margin)
- kind: feature
- severity: medium
- evidence:
  - The /t/LIF valuation card shows a net margin of 25.7% next to an operating margin of 1.1%, and P/E (TTM) 24.6.
  - The reported table on the same page shows Q4-2025 net income of **$129.69M** against operating margins of −5.6% to 6.1% in the surrounding quarters. That quarter is a tax-allowance release, and 1.52 of the $1.72 TTM EPS comes from it.
  - TMDX is the same: Q4-2025 net income is $105.4M (EPS 2.59). P/E is 16.4 from Finnhub, 18.8 from price ÷ Yahoo `eps_ttm`, and 13.1 from the screener.
  - That makes both names look like cheap compounders on P/E, while on operating income one is roughly break-even.
- suggestion: when TTM net income is more than about 2× TTM operating income (or a quarter's net margin is more than 3× its operating margin), mark P/E and net margin with "includes a one-off (tax or other)". Also show a P/E on pre-tax or operating income alongside.

### 4. The screener still uses FY2025 growth: this round's top hits had already slowed sharply (B-019, new evidence)
- kind: bug
- severity: medium
- evidence:
  - **XZO:** the screener says revenue growth is **+62.0%**, while Argus's own SEC quarters show **+3.0%** (Q2 2026) and +6.0% (Q1). Research's Finnhub "revenue_q_yoy" says **−46.7%**, so the page gives three growth numbers for one company (see also B-009).
  - **COLL:** +23.6% in the screener against +6.3% in the latest quarter, after a 40% fall in the stock.
  - **HIMS:** +59% in the screener against +3.8% in Q1 2026.
  - This is the third round in a row where the screen's leaders are shrinking stories.
- suggestion:
  - Add a TTM or latest-quarter y/y revenue growth column, computed from the SEC quarters that research already builds.
  - As a minimum step, add the latest-quarter growth to each result row, so I can sort it out of the list without opening each name.

### 5. Peers for LIF are bitcoin miners and B2B software
- kind: ux
- severity: medium
- evidence:
  - The `/api/peers/LIF` Peers card lists WK, QTWO, BILL, **CORZ**, FRSH, INTA, **CIFR**, AVPT and AGYS ("Suggested by Finnhub (same sub-industry)").
  - Life360 is a consumer family-location subscription app. CORZ and CIFR (net margins of −326% and −586%) are crypto miners.
  - The peer P/S and growth comparison, which I use to judge "cheap vs similar businesses", is meaningless here. I had to build my own set (`/api/compare?symbols=LIF,GRND,DUOL,HIMS`, which is fast at 0.01 s).
- suggestion:
  - Rank Finnhub's peers by closeness in gross margin and growth to the company, and drop any whose gross margin differs by more than 40 pp or whose net margin is below −100%.
  - Or offer the screener's similar-profile names (consumer subscription) as an alternative.

### 6. The screener universe still isn't built until the first screen runs (B-027, new evidence)
- kind: ux
- severity: low
- evidence:
  - At 02:15 UTC, about 3 minutes after preflight, `GET /api/screener` returned `built: false, building: false, progress: null`.
  - My first `POST /api/screener` returned `matches: 0, rows: []` with `building: true, progress: "SEC ticker map"`.
  - It was built about a minute later.
  - The first screen of the day silently returns zero matches rather than "building".
- suggestion: start the build at server start (or on the first `GET` of the status), and have the POST return a clear `building` message (and the UI a spinner) rather than 0 matches.

### 7. Research news has no usable date in the list, and it still counts other companies (B-059, new evidence)
- kind: bug
- severity: low
- evidence:
  - The `/api/research/RMBS` `news` list now includes 2 Rambus items. It also still has items on Netlist, Cadence, Qnity, KLA and "Silence Therapeutics, Disc Medicine…", and `news_tone` is `{positive: 6, neutral: 3}`.
  - On a −7.6% day, there was nothing explaining the move, and the sector context (SMH −6%) isn't linked anywhere.
- suggestion:
  - Filter the news to the company, as in B-059.
  - On a holding's large daily move, show the sector ETF's move for that day ("SMH −6.0% today").

## Summary
1. **No trades.** All 11 theses hold. TMDX is on watch with a written exit rule for 11-06, RMBS reports 10-26, and LIF went onto the watchlist. Cost $95,500.05, value $94,644.67, cash $4,499.95, return to date −0.86%.
2. **Last round's fixes work.** B-015 bands fill on first open, B-058 Q4 EPS is derived for all holdings, and B-040 FCF ties to the table. B-045, B-056, B-048, B-061 and B-002 are still open.
3. **New findings:**
   - The consensus headline comes from Yahoo and contradicts Finnhub's bars (KRYS "Strong Buy 1.25" with 1 strong buy out of 12).
   - KRYS is missing from events because of a date conflict.
   - P/E counts one-off tax benefits.
   - The screener's FY growth misled again (XZO 62% vs 3%).
   - LIF's peers are crypto miners.
