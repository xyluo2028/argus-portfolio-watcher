# Round 010: multibagger (growth) investor

## What I did
- **Timing:** about 02:14 to 02:45 UTC on Mon 2026-11-02, which is Sun 11-01 at about 21:15 ET. The market was closed, so prices are the 10-30 close and post-market quotes.
- **Book** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost $97,758.05, value **$94,159.22**, unrealized −$3,598.83.
  - Day P&L on 10-30 was **−$1,936.84 (−2.02%)**. IWM fell 1.65% and QQQ 3.47%.
  - The AI-semis group fell again: SMH −6.98%, ALAB −10.9%, CRDO −8.7%, MU −5.3%. RMBS fell 6.97% (−$767), in line with SMH, and has no company news in Argus. INOD fell 5.1% and LOAR 4.2%.
- **Performance reconciles:**
  - Day P&L: 94,159.22 − 96,096.06 (10-29 step) = −1,936.84, which equals Day P&L.
  - TWR: (1 − 0.017627) × (1 − 1,936.84 ÷ 96,096.06) − 1 = **−3.743%**, which equals `twr_pct`.
  - IWM leg: 1.029843 × (1 − 0.016478) − 1 = 1.287%, which equals `benchmark_pct`.
- **Earnings week.** 9 of my 11 holdings report by 11-05: KRYS 11-02 before the open, TOST 11-03 after the close, HRMY, PODD and BLLN 11-04, then LOAR, GRND, INOD and TMDX 11-05. Each has a written exit line (notes 31, 41, 49, 55). No thesis broke on Friday: RMBS's drop is the group's, and its last quarter was +22.3% with a 38% operating margin.
  - TOST's consensus Q3 revenue is $2.012B, +23.2% on Q3-25's $1.633B (SEC). Note 55's exit line is growth under 18%.
  - KRYS: consensus is drifting down. Yahoo's 0q estimate went from 2.16 to 1.92 over 90 days, with 1 down revision and 0 up in 30 days. Its revenue growth was 24% in Q2. I hold through the report.
- **Hunt** (`POST /api/screener`, 5,343 companies, FY2025, each call 0.02 s):
  - **Screen A:** market cap $0.5–15B, growth ≥25%, gross margin ≥40%, operating margin ≥8%, FCF margin ≥5%, P/S ≤12, liabilities/equity ≤2. It returned 8 names, and 3 of them I already hold or watch.
  - **Screen B:** market cap $0.3–20B, growth ≥20%, gross margin ≥45%, operating margin ≥5%, P/S ≤15, ROE ≥10%. It returned 17 names.
  - **IA:** pass. The screener shows FY growth of +78.6%, but the last two quarters ran +2.0% and +10.7%.
  - **COLL:** pass. The screener shows +23.6%, but the quarters have slowed to +12.9%, +8.9% and +6.3%.
  - **PAYS (Paysign): candidate.**
    - SEC quarters ran +45.8%, +50.8% and +48.1% y/y. Operating margin went from 8.1% to 23.8% to 24.8%.
    - No debt. Insiders own about 21%. Yahoo's 0q EPS consensus went from 0.073 to 0.13 in 60 days.
    - The negatives: 19 insider sales ($7.5M) and no buys in 12 months; the stock is up 168% in a year; and its 73% FCF margin is customer-fund float (finding 4).
    - I added it to `growth-candidates` and wrote **note 58** (review 11-10). I buy after its 11-09 report if Q3 growth is ≥35% and operating margin ≥20%, funded from any holding that breaks this week.
- **Trades: none.** Nothing broke. With $2.2k of cash I can't fund a real position. Swapping a holding for PAYS the day before nine reports would mean selling on price, not on a broken thesis.

  | Cost | Value | Unrealized | Cash | Return to date |
  |---|---|---|---|---|
  | $97,758.05 | $94,159.22 | −$3,598.83 | **$2,241.95** | (94,159.22 + 2,241.95 − 100,000) ÷ 100,000 = **−3.60%** |

## Last round's changes
- **B-117 (Day P&L after an after-close sale):** I made no sales, so I couldn't test the case itself. Day P&L (−$1,936.84) still equals the Performance step for 10-30.
- **B-034 and B-116 (calendar):** not part of my workflow, so I didn't check them.
- **"Re-check next round" dates are right:** the brief lists TOST 11-03 amc and INOD 11-05 amc. MNTN (watchlist) is 11-04. KRYS 11-02 bmo is also listed.

## Findings

### 1. A past earnings report vanished minutes after I added the symbol to a watchlist (PAYS Q2 2026; B-088 reproduced)
- kind: bug
- severity: high (the stock page's beat/miss history is wrong for the quarter I'm sizing, and the deletion is silent)
- evidence:
  - I called `GET /api/earnings/PAYS` at about 02:20 UTC. The first report was `period_end 2026-06-30, report_date 2026-08-05, eps_estimate 0.0612, eps_actual 0.11, reaction close +29.3%`.
  - Then `POST /api/watchlists/growth-candidates {"symbols":["PAYS"]}`.
  - A few minutes later, the same call (twice) starts at `2025-12-31 / 2026-03-24`. The 2026-06-30 report is gone.
  - The Q1-26 report (filed around May 2026) was never there.
  - /t/PAYS → Reported financials shows "–" for EPS est., EPS actual, Result and Reaction on both 2026-06-30 and 2026-03-31. The rows from 2025 back are complete.
  - The cause is the one in B-088: `EventsService.refresh` runs `delete(Event).where(symbol, d between start and end)` and re-inserts only what Finnhub's earnings calendar returns now. Here that no longer included the 08-05 row.
- suggestion: in `refresh`, delete only future rows (d ≥ today) in the window, and keep past rows that have an `epsActual`. Or merge past rows the way B-034 merges calendar rows.

### 2. On a weekend the brief's 2-day news window covers no trading session, and it empties Research → News for the movers (RMBS −7%, no headline anywhere; B-105, B-110)
- kind: bug
- severity: high (my biggest loser of the week had no news on any page)
- evidence:
  - On Sunday, `GET /api/brief/loop-growth` → `headlines` has only TOST. That's one Yahoo opinion piece.
  - RMBS (−6.97%, −$767), INOD (−5.1%) and LOAR (−4.2%) get nothing. `events.news(sym, days=2)` asks Finnhub for Sat–Sun only.
  - After the brief ran, `GET /api/research/RMBS`, `/INOD` and `/KRYS` → `news` came back **empty (0 items)** and `news_tone` was all zeros. ESE, which isn't a mover, still had its 7-day item from 10-26.
  - This is the 1-hour per-symbol cache from B-105. On a weekend it hides everything, not just older items.
- suggestion: key the news cache by (symbol, days). Count the brief's window back from `last_session` (or 2 sessions), not from today's calendar date.

### 3. The screener reports "not built, not building" while the startup warm-up is building it, and a screen in that window starts a second build (B-027)
- kind: bug
- severity: low
- evidence:
  - About 3 minutes after the restart, `GET /api/screener` returned `built: false, building: false, progress: null`. A minute later it returned `built: true, fundamentals_at 02:16:21`.
  - In `app.py`, `_warm_screener` calls `self.screener.build()` directly, outside the `run_background("screener")` job, so `job_running("screener")` is false.
  - In that window the Screener page shows no "Building…" message, because it checks `!built && building`. A screen call runs `_screener_job()`, which starts a second, concurrent build.
- suggestion: run the warm-up build through `_screener_job()` (or set the same flag) so the status reads `building` with progress, and a screen doesn't start another build.

### 4. PAYS shows a "FCF margin 73.0%" that is customer-fund float, beside a 15.7% net margin (B-111)
- kind: bug
- severity: medium (a growth screen on FCF margin ranks PAYS as a cash machine)
- evidence:
  - `GET /api/fundamentals/PAYS`: `fcf_margin_pct` 73.04 (`sec`), `fcf_ttm` $73.5M against `revenue_ttm` $100.6M, and `net_margin_pct` 15.7.
  - The quarterly FCF column on /t/PAYS is 1.19M, 18.52M, **47.5M** (Q4-25, on revenue of 22.76M), 6.3M, then −6.11M and −20.28M earlier.
  - Paysign holds prepaid card funds, so operating cash flow swings with customer balances.
  - The screener also lists PAYS at FCF margin 62.5% (FY2025). Its ROA is 5.7% against ROE 30.1%, which points the same way.
- suggestion: when TTM FCF is more than 2× net income, or one quarter's FCF exceeds its revenue × 1.5, add a "lumpy, check working capital or customer funds" flag. Or show the quarterly FCF range next to the TTM margin.

### 5. Two EPS consensus figures for one quarter again: PAYS 0.09 vs 0.13, KRYS 1.81 vs 1.92 (B-119)
- kind: bug
- severity: medium
- evidence:
  - /t/PAYS Events card and Reported financials header: "EPS est. 0.09". That's Finnhub's 0.0918 from `/api/earnings/PAYS` `next`.
  - `GET /api/research/PAYS` → `estimates.trend.0q.current` is **0.13** (Yahoo, Estimates tab). That's 42% higher, on the same page.
  - KRYS reports tomorrow: the brief has 1.8065 and Yahoo 0q has 1.918.
- suggestion: as filed. Label the source and basis, or show one consensus.

### 6. The screener's FY growth surfaced two more companies that have stopped growing (IA, COLL; B-019)
- kind: feature
- severity: medium
- evidence:
  - From Screen B (`POST /api/screener`, growth ≥20%):

    | Name | Screener FY2025 | Latest quarters (`research.growth.quarters`) |
    |---|---|---|
    | IA | +78.6% | +2.0%, +10.7% |
    | COLL | +23.6% | +12.9%, +8.9%, +6.3% |

  - That's five rounds running. `revenue_growth_q_yoy_pct` (SEC) is already in `/api/fundamentals`.
- suggestion: add a latest-quarter growth column and filter, even if it's computed only for the returned rows.

### 7. The brief still ignores my named watchlist: six names moved 3% or more and `watchlist_movers` is empty (B-106)
- kind: bug
- severity: medium (new evidence)
- evidence:
  - `GET /api/brief/loop-growth` → `watchlist_movers: []`.
  - `GET /api/watchlists/growth-candidates` shows VICR −7.52%, PTCT −6.97%, MNTN −4.98%, NUTX −4.74%, DUOL −3.52% and CELH +3.41%.
  - MNTN also reports 11-04 and isn't in `earnings_upcoming`.
- suggestion: as filed.

### 8. Cold watchlist 6.2 s, cold brief 3.9 s (B-026)
- kind: perf
- severity: low
- evidence: the first `GET /api/watchlists/growth-candidates` (13 symbols) took 6.21 s and the first `GET /api/brief/loop-growth` took 3.91 s. The portfolio took 0.23 s and the screener 0.02 s. Stock pages render in 0.2–0.4 s with no errors or overflow at 1400 and 390 px.
- suggestion: as filed. Warm the watchlist quotes and fundamentals with the other startup caches.

## Summary
1. **No trades.** Nine holdings report 11-02 to 11-05 under written exit lines. RMBS's −7% on 10-30 matches SMH's. PAYS is a new candidate (note 58, buy case after its 11-09 report). IA and COLL failed research. Value $94,159.22, **cash $2,241.95**, return to date −3.60%.
2. **Last round's items:** Day P&L reconciles to the Performance step and TWR (−3.743%). The re-check dates (TOST 11-03, MNTN 11-04, INOD 11-05) are correct.
3. **Top findings:**
   - PAYS's Q2 earnings report vanished from `/api/earnings` after a watchlist add (B-088 reproduced).
   - The weekend brief's 2-day news window left RMBS, INOD and KRYS with zero headlines on every page (B-105).
   - The screener reports "not building" during the startup build.
   - PAYS's 73% FCF margin is customer float.
