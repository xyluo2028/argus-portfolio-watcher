# Round 011: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:45 UTC on Tue 2026-11-03, which is Mon 11-02 at about 21:15 ET. The market was closed, so prices are the 11-02 close plus post-market quotes.
- **Book before trading** (`GET /api/portfolios/loop-growth`, 0.05 s):
  - 11 positions, cost $97,758.05, value **$94,366.38**, unrealized −$3,391.67.
  - Day P&L for 11-02 was **+$207.16 (+0.22%)**, against IWM's −0.07%.
  - **Gains:** LOAR +9.34% (+$1,009), TOST +5.49% (+$534) and PODD +2.63%.
  - **Losses:** KRYS −10.95% (−$1,201) on its Q3 report, INOD −5.68%, BLLN −2.57% and HRMY −2.19%.
  - The brief's totals match the portfolio's.
- **KRYS reported Q3 before the open.** The 10-Q was already in Argus's SEC statements the same evening, which was useful.
  - **Revenue:** $127.34M, **+30.2% y/y** against Q3-25's $97.8M. Q2 was +24.1%, so growth is speeding up. Sequential growth was +6.8%.
  - **Operating margin:** 55.9%, up from 42.3% a year ago.
  - **EPS:** 2.05 against 1.81 (Finnhub) or 1.92 (Yahoo).
  - **Revenue against consensus:** a small miss, $127.3M against $128.6M.
  - **Headlines** (brief): a $400M buyback and a lower full-year expense guide.
  - **Price:** the stock fell 10.95% while XBI fell 2.5%. Argus gives no reason beyond the small revenue miss.
  - **Thesis (note 30): stronger.** The break line is growth under 15%.
  - **Valuation, computed by hand from SEC data** because `/api/fundamentals` and `/api/research` return 500 this round: TTM EPS 7.37 gives a P/E of 40. TTM revenue of $470M gives a P/S of 18.6.
- **Trade: BUY 7 KRYS at $295.00** (post-market quote; transaction 48). The position is now 40 shares at $321.69, with a cost of $12,867.55. That's 12.9% of capital, under my 15% cap, so there will be no more adds. Thesis update is **note 61** (review 2027-02-20). I added on the drop because the thesis got stronger. Price fell, and nothing in the business broke.
- **Everything else: hold.** TOST reports 11-03 after the close. HRMY, PODD and BLLN report 11-04, and LOAR, GRND, INOD and TMDX on 11-05. Each has a written exit line (notes 31/55, 41, 49). LOAR's +9.3% has no headline anywhere in Argus.
- **Hunt:** I re-ran Screen A (`POST /api/screener`, 0.008 s): market cap $0.5–15B, growth ≥25%, gross margin ≥40%, operating margin ≥8%, FCF margin ≥5%, P/S ≤12, liabilities/equity ≤2. It returned the same 8 names as last round (FY2025 data, unchanged), so there's nothing new. PAYS (note 58) still waits for its 11-09 report.
  - PTCT, on my watchlist, missed badly on 10-29 (EPS −0.62 against +0.35) and stays a pass.
- **After the trade:**

  | Cost | Value | Unrealized | Cash | Return to date |
  |---|---|---|---|---|
  | $99,823.05 | $96,437.68 | −$3,385.37 | **$176.95** | (96,437.68 + 176.95 − 100,000) ÷ 100,000 = **−3.39%** |

  Unrealized moved by +$6.30, which is 7 × (295.90 − 295.00). Day P&L stayed at $207.16. KRYS's after-hours P&L of −$29.70 is 33 × (−0.90), so it leaves out the 7 shares bought after the close (B-046 still holds).
- **Concentration:** healthcare is now 47.5% of value: KRYS, PODD, TMDX, HRMY and BLLN.

## What the broken history (NaN close for 11-02) did to my workflow
This is already known to the lead and isn't filed as a finding. `data/server.log` shows every one of the failures below raising the same `IntegrityError` from `market._store_bars`. The `price_bar` table has no rows at all, so every call re-downloads and fails again.

- **Broke:**
  - Stock page price chart: "Internal Server Error".
  - Dashboard "Performance vs benchmark" card: "Internal Server Error". Last round I reconciled the time-weighted return and benchmark with this card, and this round I couldn't.
  - `/api/portfolios/loop-growth/performance` and `/risk`: 500. No TWR, no beta, no correlation.
  - `/api/research/<sym>`: 500. That covers analysts, insiders, ownership, valuation bands, estimates and news. It's my main conviction tool, and Research → News was the only place to look for why KRYS fell 11% or LOAR rose 9%.
  - `/api/fundamentals/<sym>`: 500. The stock page's "Valuation & fundamentals" card stays on "Loading…" (finding 1). Portfolio and watchlist `/fundamentals` also return 500.
  - `/api/earnings/<sym>`: 500. No beat/miss history or reaction column on the stock page.
  - `/api/returns/<sym>`: 500.
- **Still worked:**
  - Quotes, the portfolio, the brief (with headlines) and events.
  - SEC financials.
  - The screener and Compare.
  - The watchlist with metrics, Peers, and portfolio and watchlist earnings summaries.
  - Market context, with breadth built by about 02:14.
  - The CLI `argus fundamentals`.
- **How I stayed within the rule:** I traded only on SEC statements and quotes, which both worked, and computed valuation by hand.

## Last round's changes
- **B-088 (past earnings reports survive refreshes): works, as far as I can check.**
  - In the `event` table (read-only query), KRYS keeps every past `eps_report` and `eps_result` row back to 2025-05. The 11-02 Q3 rows (Yahoo `eps_report` and Finnhub `eps_result` 2026-09-30) were added the same evening.
  - PAYS's Q2 `eps_result` (0.11 against 0.0612) is back in `/api/watchlists/growth-candidates/earnings`.
  - **Not verified:** PAYS still has **no `eps_report` rows** (Yahoo report dates and reaction) at 02:18 UTC, four hours after the expected cache expiry. `/api/earnings/PAYS` returns 500 (history), so I can't tell whether that's the history crash stopping the fill or a remaining gap. Re-check after the history fix.
- **B-006 and B-126 (calendar):** not part of my workflow.

## Findings

### 1. One failed history fetch takes down whole endpoints whose main content doesn't need history; the stock page's Valuation card then hangs on "Loading…"
- kind: bug
- severity: high (it blanked fundamentals, research and earnings history on every stock page, though the data was available)
- evidence:
  - `uv run argus fundamentals KRYS --json` returns all 40+ metrics: P/E 40.1, `revenue_growth_q_yoy_pct` 30.2, FCF margin 66.0, and others. `GET /api/compare?symbols=KRYS,PODD` returns the same metrics with a 200.
  - `GET /api/fundamentals/KRYS` returns **500**. The traceback is `app.py:752 fundamentals → self.price_stats([sym]) → market.daily_closes_many → _store_bars`. The optional price-stats block raises, and the whole response is lost.
  - Same pattern:
    - `/api/research/<sym>`: news, analysts and insiders don't need bars.
    - `/api/earnings/<sym>`: only the reaction column needs bars.
    - Portfolio and watchlist `/fundamentals`.
  - **UI at 1400 and 390 px (`/t/KRYS`, `--settle 8`):**
    - The chart card shows a raw "Internal Server Error".
    - The "Valuation & fundamentals" card still says **"Loading…"** after 8 s and never shows an error.
    - The Research tabs don't appear.
    - The Dashboard's Performance card shows the raw "Internal Server Error".
- suggestion:
  - Wrap the history-derived parts (`price_stats`, earnings reaction closes, research returns) in try/except, return them as null with an `errors: {"price_history": "..."}` note, and keep the rest of the response.
  - In the UI, show the card's error state instead of leaving "Loading…".

### 2. Two EPS consensus figures for the same quarter, now 44% apart for TOST tomorrow; KRYS's surprise is +13.5% or +6.9% (B-119)
- kind: bug
- severity: medium (I judge a report by beat or miss, and the size of the beat depends on which page I read)
- evidence:
  - TOST reports 11-03 after the close. The brief's `earnings_upcoming` has `epsEstimate 0.2564` (Finnhub). The Yahoo `eps_report` row for 2026-11-03 in the `event` table has `eps_estimate 0.37`.
  - KRYS's 11-02 report has `epsEstimate 1.8065, epsSurprisePct 13.48` (Finnhub; brief and stock page Events: "EPS 2.05 vs 1.81"). The Yahoo row has `eps_estimate 1.92, surprise_pct 6.88`.
  - The gap is probably GAAP against adjusted, but neither figure is labeled.
- suggestion: as filed. Label each figure's source and basis (GAAP or adjusted), or pick one consensus per page.

### 3. The brief's `watchlist_movers` is empty again while three names moved more than 6% (B-106)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/brief/loop-growth` returns `watchlist_movers: []`.
  - `GET /api/watchlists/growth-candidates` shows VICR −8.44%, NUTX −7.27% and USLM +6.61%.
  - DUOL (11-03), MNTN and XZO (11-04), and NUTX and CELH (11-05) all report this week, and none is in `earnings_upcoming`.
- suggestion: as filed. Include named watchlists, or a `watchlist=` parameter, in the brief's movers and earnings.

### 4. The "last report" row has a report date for one holding and only a period end for the other ten
- kind: ux
- severity: low
- evidence:
  - In `GET /api/portfolios/loop-growth/earnings`, KRYS's `last` is `{"date": "2026-11-02", "hour": "bmo", ...}` with no `period`.
  - For the other ten, `last` is `{"date": null, "period": "2026-06-30", ...}`. The same mix shows in `/api/watchlists/growth-candidates/earnings`: VICR, USLM, PEGA, PTCT and BELFA have a date, and eight others have only a period.
  - So for most holdings Argus can't say when the last report came out. That matters for knowing how stale a beat is, or whether the 10-Q should be in yet. The Yahoo `eps_report` rows in the database do carry those dates (e.g. TOST 2026-08-04).
- suggestion: fill `last.date` from the matching `eps_report` row, so every `last` has both the period and the report date.

### 5. Compare and the stock page show KRYS revenue growth of 22.6% the day its quarter printed +30.2% (B-009, B-102)
- kind: bug
- severity: low (new evidence for a known item)
- evidence:
  - `GET /api/compare?symbols=KRYS,PODD` gives KRYS `revenue_growth_yoy_pct 22.63` (Finnhub).
  - The SEC figures disagree. The latest quarter (`revenue_growth_q_yoy_pct`, also in `argus fundamentals`) is **30.2%**. TTM from the SEC quarters is 470.0 ÷ 373.2 = **+25.9%**.
  - `ps_ttm` is 19.44 (Finnhub), against market cap ÷ SEC TTM revenue = 8,758 ÷ 470.0 = **18.6**.
  - Compare is where I put candidates side by side, and it understates the holding that just accelerated.
- suggestion: in Compare, use SEC TTM growth and SEC P/S when SEC data is newer, or add the latest-quarter growth column.

### 6. The loop-growth Dashboard shows another portfolio's alert (B-018)
- kind: ux
- severity: low
- evidence:
  - `/` with loop-growth selected shows the "Alerts this session" card: "XOM: −4.05% on the day · loop-income r001".
  - I don't hold XOM. The brief filters it out correctly (`alerts_fired: []`).
  - The Dashboard and the header ("Alerts · 1") don't filter it, so the two views disagree.
- suggestion: filter the Dashboard card and the header count to the selected portfolio's symbols, as the brief does.

### 7. The biggest dollar gainer of the day has no headline anywhere (LOAR +9.3%; B-110, B-105)
- kind: feature
- severity: low
- evidence:
  - The brief's `headlines` covers KRYS, INOD and TOST.
  - LOAR (+9.34%, +$1,009, my largest position) is among the six movers it checks, but `events.news("LOAR", days=2)` returned nothing. Research → News was down (finding 1).
  - With no explanation, I can't tell whether this was an upgrade, a deal or a sector move two days before its report.
- suggestion: when a mover has no news, widen the window to 7 days. Show the sector ETF's move next to the mover (e.g. ITA for LOAR, XBI for KRYS), so "it moved with its group" is visible.

### 8. Cold watchlist 6.4 s, cold Peers 6.5 s (B-026, B-097)
- kind: perf
- severity: low
- evidence:
  - The first `GET /api/watchlists/growth-candidates` (13 symbols) took 6.39 s; the second took 0.41 s.
  - `GET /api/peers/KRYS` took 6.51 s.
  - The portfolio took 0.05 s, the screener 0.008 s and financials 0.03 s.
  - Stock pages render in 0.2 s with no horizontal overflow at 1400 or 390 px.
- suggestion: as filed.

## Summary
1. **Bought 7 KRYS at $295.00** after a strong Q3 (+30.2% revenue, 55.9% operating margin, $400M buyback) and an 11% drop. Note 61 is the thesis update. KRYS is now 12.9% at cost. Everything else holds into this week's reports. Value $96,437.68, **cash $176.95**, return to date −3.39%.
2. **History crash impact:** research, fundamentals, earnings history, performance, risk, returns and the stock chart all return 500. Only quotes, SEC statements, the screener, Compare and the brief worked.
3. **Top findings:**
   - Endpoints fail whole on one optional history block, and the Valuation card hangs on "Loading…". The CLI fundamentals still work.
   - TOST's consensus is 0.256 or 0.37 (B-119).
   - Watchlist movers are still ignored (B-106).
   - B-088 works for KRYS, but PAYS's report dates are unverified.
