# Round 002: multibagger (growth) investor

## What I did
- **Timing:** 2026-10-21 about 02:15 UTC, which is Tue 10-20 at 22:15 ET, after the post-market session. This is still the same trading day as round 001, so no holding has reported or moved its fundamentals since I bought. Small caps were still out of favour (IWM closed at 275.78: +11.1% over one year and −5.7% over 3 months, from `/api/returns/IWM` bases).
- **Holdings review** (`/api/research/<sym>`, `/api/fundamentals/<sym>`, about 0.3–3.3 s each). Every thesis is intact, so I made no trims and no exits.
  - LOAR: latest quarter +39.4%, operating margin 24.4%. P/S is at the 0th percentile of its 5-year band and EV/EBITDA at the 0th.
  - PODD: +23.5%. P/E, P/S and EV/EBITDA are all at the 0th percentile.
  - KRYS: +24.1%, operating margin 49%. Insiders sold $105M.
  - TOST: +23.1%, operating margin up to 8.0%.
  - TMDX: +20.7%, decelerating, so I'm watching it.
  - HRMY: +30.3%.
  - ESE: +14.4%, decelerating, and P/S is at the 95th percentile. This is the weakest thesis, and I'll review it at earnings.
  - BLLN: +64.4% (SEC).
  - RMBS: statements still have no revenue (B-008).
- **Earnings ahead:** RMBS on 10-26 is the first to report. The other dates depend on which Argus panel you read (finding 1).
- **Screens** (`POST /api/screener`). Opening the Screener status didn't start the universe build (B-027). My first POST started it, and it finished about 15 s later (5,358 companies, FY2025).
  - Screen A (my growth-quality screen from round 001) returned 19 names.
  - Screen B (compounder) returned 22.
  - The new Screen C covered market cap $0.3–8B, revenue growth ≥25%, operating margin ≥10%, FCF margin ≥10%, P/S ≤8 and revenue ≥$100M. It returned 31 names.
- **Researched** GRND, INOD and BCRX, and compared them with TMDX and HRMY (`/api/compare`, 0.05 s).
- **Trades** (two starter positions at the post-market quote, each with a thesis note and a review date of 2026-11-20):

  | Symbol | Shares | Price | Cost | Why |
  |---|---|---|---|---|
  | GRND | 487 | 14.35 | 6,988.45 | Revenue +29–38% y/y for 6 quarters, operating margin 23–39%, EV/EBITDA at the 8th percentile of its own band, insiders own about 83%. Risks: near-zero book equity, insiders are net sellers |
  | INOD | 107 | 56.00 | 5,992.00 | Revenue growth re-accelerating to +54% and +58%, no debt, ROE 38%, H1 operating cash flow of $164M (prepayment). Risks: customer concentration, $175M of insider selling, beta 3 |

- **Book now:** 11 positions. Invested at cost: **$95,500.05. Cash: $4,499.95.** No realized gains. The largest position at cost is LOAR at $10,953, which is 11.0% of capital.
- **Watchlist `growth-candidates`:** I added BCRX and PTCT. Both showed CY2025 revenue growth of 94% and 115%, and I need to check whether that's durable or one-off.

## Last round's changes
- **B-005 (screener net income 1000x too small): partly fixed.**
  - What works: LOAR no longer shows P/E 81,740, and ESTC no longer shows +99,900% earnings growth. ESTC's growth is now null, and its net income is $367.8M.
  - What doesn't: the guard only applies when a revenue figure exists, so banks and REITs still get absurd values (finding 3).
  - The cost of the fix (B-032) is real for me. LOAR, which I hold, has no screener P/E, ROE or earnings growth. Across the universe, 185 of the 2,726 companies with revenue over $100M (6.8%) have null net income, and 107 of them are $0.3–15B companies. In the top 500 by market cap, 38 are affected, including AVGO, ANET, SCHW, IBKR, MDT and BSX. A P/E or ROE filter silently drops all of them.
- **B-006 (calendar):** not part of my workflow.
- **B-007 (day-one performance): works.** `GET /api/portfolios/loop-growth/performance?range=all` gave `gain −193.21`, which equals unrealized P&L of −193.21, with `net_invested 82,519.60`. After my two buys it gave gain −436.09 against unrealized −436.62. The 0.53 gap is rounding of the quote values. TWR matches the chart's last point.
- **Still open from my round 001 list, re-confirmed:**
  - **B-015:** opening `/api/research/INOD` and `/api/research/BCRX` cold returned every band with `current: null`. A second, non-refresh call stayed null. Only `?refresh=true` filled them in.
  - **B-009:** BLLN still shows Finnhub's −12.82% for the latest quarter, against SEC's +64.4%.
  - **B-008 is broader than RMBS.** BCRX has `revenue: null` for every quarter in `/api/financials/BCRX`, while the screener has $874.8M. Its company facts carry revenue only under `RevenueFromContractWithCustomerIncludingAssessedTax`, through 2026-06-30. Among the 22 company-facts files cached under `data/cache/sec/`, 3 are affected: RMBS, BANR and BCRX.

## Findings

### 1. The same stock shows two different earnings dates on one page, and the dates drift day to day
- kind: bug
- severity: high
- evidence:
  - On `/t/TMDX`, the "Events" card says **Wed, Nov 4 Earnings**. The "Reported financials" card a few rows below says **Next report Thu, Oct 29, after close**.
  - The API agrees with this split:
    - `GET /api/events?days_ahead=45&portfolio=loop-growth` (Finnhub calendar only, `events.py::_earnings`) returns TMDX 11-04, KRYS 11-09, TOST 11-10 and HRMY 11-03.
    - `GET /api/earnings/<sym>` → `next` (Yahoo dates merged with Finnhub only within ±2 days, `earnings.py::build`) returns TMDX 10-29 amc, KRYS 11-02 bmo, TOST 11-03 and HRMY 11-04 bmo.
  - For HRMY, Argus's own news shows the company's release "Harmony Biosciences to Report Third Quarter 2026 Financial Results on November 4, 2026". So the events feed, which drives the dashboard's Coming up and the brief, is a day early.
  - In round 001 the same events feed gave TMDX 10-27, KRYS/TOST 11-02 and ESE 11-18. It now gives 11-04, 11-09/11-10 and 11-12.
  - I decide whether to add before a print, or to hold a full-size position through it, from this date. A week's error on TMDX (38% short interest) matters.
- suggestion:
  - Use one source of truth for "next earnings" in both places. Prefer a date the company has confirmed (Yahoo's date when it differs from Finnhub's projection), or show both and mark the date as "estimated" or "confirmed".
  - At minimum, the Events card and "Next report" on the same page should come from the same function.

### 2. After-hours P&L counts shares bought after hours as a gain (+$243 of the +$347 is not real)
- kind: bug
- severity: medium
- evidence:
  - I bought GRND 487 @ 14.35 and INOD 107 @ 56.00 at 22:18 ET, which is exactly their post-market quotes.
  - `GET /api/portfolios/loop-growth` then showed GRND `ext_pnl +141.23` and INOD `ext_pnl +102.19`. Those are (ext − regular close) × qty, measured from a close I never held through.
  - Totals `ext_pnl` rose from **+103.47** just before the buys to **+346.88**. The dashboard header now reads "After hours +$346.88 (+0.36%)", but my real after-hours change is +$103.47.
  - The same rows show `day_pnl −141.23` and `−102.19`, measured from the buy price. So the two figures double-count the same 29¢ in opposite directions. This is related to B-025 (Day % vs Day P&L), but it affects the extended-hours figures.
- suggestion: for lots opened after the regular close, measure `ext_pnl` from the lot's price, not from the close. That makes it zero at purchase.

### 3. Screener P/E is still 1000x too large for companies without a revenue figure (BANR P/E 12,784)
- kind: bug
- severity: medium
- evidence:
  - `POST /api/screener` returned BANR with `net_income: 195382`, `pe: 12784`, `roe_pct: 0.01` and `revenue: null`. `GET /api/financials/BANR?period=annual` gives FY2025 net income **$195.38M** (EPS 5.64), so the real P/E is about 12.8.
  - DX shows the same pattern: screener net income 319,065 and P/E 8,525, against $319.07M in its statements.
  - FRNM, BXBL, GTEN, TWLV and SPEG also have no revenue and a P/E of 476–54,197.
  - The B-005 guard compares net income with revenue, so it never fires when revenue is null. There are 834 rows with no revenue (banks, REITs, mREITs, shells).
- suggestion: when revenue is null, apply the same check against equity, assets or market cap (for example, net income under 0.1% of equity → null). Better still, read net income from company facts, which is B-032.

### 4. Analyst consensus shows "None" when every analyst rates the stock a buy
- kind: bug
- severity: medium
- evidence:
  - `/api/research/GRND` → `analysts.rating: "none"`, `rating_mean: null`, `count: 5`, but `trend[0]` = 3 strong buy, 2 buy, 0 hold.
  - INOD shows the same: `rating: "none"` with 1 strong buy and 3 buys.
  - On `/t/GRND` the Research > Analysts card shows **Consensus: None** and "mean –", directly above a bar of 5 buys.
  - For small caps with few analysts, which are the names I hunt, the provider's summary key is often missing. Argus already has the counts.
- suggestion: when the provider's rating or mean is missing, compute the mean from `trend[0]`. Use 1 for strong buy through 5 for strong sell (GRND gives 1.4) and map it to a label.

### 5. A trade entered in the evening is dated the next day (UTC) on the stock page, but booked to today in performance
- kind: bug
- severity: low
- evidence:
  - The GRND buy was made at 22:18 ET on Tue 10-20. `argus txn list` shows `ts 2026-10-21T02:18:34Z`.
  - `/api/portfolios/loop-growth` → GRND `first_opened: "2026-10-21"`. The "Your position" row on `/t/GRND` and the thesis note date also say 2026-10-21.
  - `/performance` books the flow on 2026-10-20, so the same trade appears on two different dates.
  - The cause is `portfolio.py:338`, `min(l.opened ...).date()`, which takes the UTC date. Holding-period dates (long-term vs short-term) would be off by a day for any evening trade.
- suggestion: convert to America/New_York before calling `.date()` in `first_opened`, the position transaction list and note dates.

### 6. The dashboard shows two different IWM returns for the same session
- kind: ux
- severity: low
- evidence:
  - The phone dashboard (`/`, 390 px) shows the "Portfolio vs IWM, last session" tile as **−0.46% / +1.66%**. The Performance card a few rows below says **IWM 0.00%**, with excess return −0.46%.
  - Both cover 2026-10-20. The portfolio's −0.46% is measured from my buy prices, while +1.66% is IWM's full day from the prior close.
  - Neither comparison is like-for-like on a day with buys, so I can't tell whether I beat the benchmark today.
- suggestion: on a day that includes buys, label the tile's portfolio figure "since buy" (or use the performance TWR in both places), so the tile and the card agree.

### 7. The price-target bar pins the price to the "low" end when the price is below every target
- kind: ux
- severity: low
- evidence:
  - On `/t/GRND`, Research > Analysts > "Price targets vs today" puts the price dot at the far left on top of "low 19.00", but the price is 14.06.
  - It reads as "price is at the low target", when the price is really 26% below the lowest target. That is a signal I care about.
- suggestion: widen the scale to include the price, or show the dot with an arrow outside the range and an "x% below the lowest target" label.

### 8. The screener can't screen on "cheap versus its own history", which is the check I run on every finalist
- kind: feature
- severity: low
- evidence:
  - For every finalist I open `/api/research/<sym>` to read the band percentiles. Today that showed LOAR P/S at the 0th percentile, PODD at the 0th, GRND's EV/EBITDA at the 8th, and ESE's P/S at the 95th.
  - That took 1.8–3.3 s per name, plus `?refresh=true` because of B-015.
  - The screener has P/E and P/S, but no "percentile in its own 5-year range". So "growth ≥25% and P/S in the bottom quartile of its own history" takes 30 manual research calls.
  - It would have put GRND and LOAR at the top of my list immediately, and flagged ESE as stretched before I bought it.
- suggestion: add a `ps_percentile_5y` (or EV/EBITDA percentile) field to screener rows, computed from the quarterly P/S history Argus already builds for the research bands. It could be computed only for the rows a screen returns, to stay inside provider limits.

Summary (3 lines):
1. Reviewed all 9 holdings (theses intact, no news since yesterday's buys). Added starters GRND 487 @ 14.35 and INOD 107 @ 56.00, for 11 positions, $95,500.05 at cost and $4,499.95 cash. Added BCRX and PTCT to the watchlist.
2. The worst issue: earnings dates disagree on the same stock page (TMDX: Events Nov 4 vs "Next report" Oct 29; HRMY Nov 3 vs the company's Nov 4) and drift day to day. After-hours P&L also counts after-hours purchases as gains (+$347 shown, +$103 real).
3. B-005 is only partly fixed (BANR P/E 12,784 when revenue is null), B-007 works, and B-015, B-009 and B-008 (now BCRX too) are still present. Consensus shows "None" when all analysts rate the stock a buy.
