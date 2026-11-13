# Round 016: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:45 UTC on Fri 2026-11-13, which is Thu 11-12 evening ET with the market closed. Prices are the 11-12 close. **Yahoo's 11-12 daily bar was not yet published** (the last bar for RMBS, LOAR, RDDT, INOD and PAYS is 11-11), so tonight was the late-bar case for B-157.
- **Market:** a risk-off day for small caps. Russell 2000 −1.66%, S&P −0.35%, XBI −3.27%, ITA −2.06%, VIX 18.7 (+6.9%).
  - Fear & greed read 25.3 before the screener universe finished building and 40.9 after (see finding 8).
- **Book** (`GET /api/portfolios/loop-growth`, 1.4 s): 10 positions, value **$100,986.59**, cost $98,186.15, Day P&L **−$1,963.42 (−1.91%)** against IWM −1.64%.
  - Movers: LOAR −5.3% (−$815), RDDT −5.8% (−$440), INOD −4.9% (−$201).
  - LOAR has no company news in Argus. Its peers fell too: HEI −2.8%, TDG −3.4%, XAR −2.8% (`argus quotes`). That's sector beta, not a thesis event.
  - Post-market +$183.42.
  - TMDX is 17.2% by value but 14.0% at cost, so no adds.
- **Holdings review:** every thesis note (28–84) is intact, and nothing changed since the Q3 prints. ESE reports 11-19 amc (now in the brief).
- **Hunt:**
  - **Screens** (`POST /api/screener`, 10 ms):
    - Screen A: cap $1–25B, growth ≥25%, op margin ≥12%, ROE ≥12%, P/E 5–45, L/E ≤2 (19 matches).
    - Screen B: cap $0.5–15B, growth ≥30%, FCF ≥10%, GM ≥50%, P/S ≤12 (18 matches).
  - **Growth check:** I checked every screen-A hit's latest SEC quarter (`/api/financials/<sym>`). Only 8 of 19 still grow ≥25% y/y (finding 3).
  - **NUTX:** the screener says +82.4%. Q3 is **−18.7%** y/y, and Q2 was −13.6%. Pass.
  - **DUOL** (watchlist, −4.1% today): growth went from +26.5% to +18.3% to +13.7% over three quarters, op margin is 7.8%, and insiders made 84 sales vs 1 buy. Pass.
  - **TGTX:**
    - For: Q3 +60.7% y/y and 33% op margin. Forward P/E is 22 on FY27 EPS of 2.93.
    - Against: TTM P/E is 96. The screener's 21.8 P/E and 72.6% net margin come from a FY2025 tax benefit. Short interest is 28%, there were no insider buys, and healthcare is already 46% of my book.
    - Decision: added to `growth-candidates`, note 90, review 2027-02-26.
  - **ANIP:** +27.6% y/y and 18% op margin. P/E is 14.2, the 0th percentile of its own history. But growth is partly acquired (the $560M deal), insiders made 48 sales and no buys, and FY+1 EPS growth is only +7%. Pass.
- **Trades: none.** I have no cash, and no candidate beats my weakest holding on evidence that growth will last. I don't sell on price: INOD is −35% on cost but still +52.9% growth with a raised guide (note 73).
- **Cash:** (100,000 − 1,782.08 realized) − 98,186.15 cost = **$31.77**.
- **Return to date:** (100,986.59 + 31.77 − 100,000) ÷ 100,000 = **+1.02%**.
  - The Dashboard's time-weighted return is +0.45% vs IWM +0.96%. Its "Gain +$1,018" matches my figure.

## Last round's changes
- **B-157 (momentum when Yahoo's bar is late): works, verified live in the late-bar case.**
  - RMBS's cached bars end at 11-11, and the quote is 84.97 (11-12).
  - All three views show **1W +21.9%**: `/api/fundamentals/RMBS` gives `return_1w_pct 21.94`, `/api/portfolios/loop-growth/fundamentals` gives 21.94, and the `/t/RMBS` Momentum card at 390 px shows +21.9%.
  - Hand check: 84.97 ÷ 69.68 (the 11-05 close) − 1 = +21.94%.
  - LOAR (+2.81% = 75.04/72.99), RDDT (+6.12% = 99.55/93.81) and INOD (−6.03% = 36.29/38.62) also match.
  - This fixes my round-015 top finding.
- **B-152 (Risk's last session = Day P&L): works.**
  - `/api/portfolios/loop-growth/risk` gives `last_day.value −1963.42`, `basis session_holdings`. That equals the Dashboard's "−$1,963.42 (−1.91%) last session".
  - I made no evening trade, so the after-a-trade case wasn't exercised.
- **B-156 (calendar):** not my area, but it now has rows: 11-12 jobless claims actual 200K, and PPI on 11-13. `errors` no longer lists events.
- **B-160 (brief's 7-day window):** ESE 11-19 now appears in `earnings_upcoming`, but only because the window rolled forward a day (11-12 + 7). That isn't a fix.
- **Re-checks still open:**
  - **B-149 / PAYS timing: still open.** PAYS is `timing amc` with reaction base 11-09 → 11-10 −18.9%. The 11-09 bar (open 14.93, close 12.51, 2.66M shares) shows the release moved the stock intraday.
  - **B-120: still open, and it's RDDT-specific** (finding 4).
  - **B-106: still open.** `watchlist_movers: []`, while NUTX fell −9.4% and DUOL −4.1% on growth-candidates.
  - **B-109: still open.** Simulating a 10-share RDDT buy prices it at the 99.55 close, while post-market is 100.85. There's still no `price_source`.

## Findings

### 1. The Watchlist page never shows my watchlist: it reads only a list named "Watchlist", so the 14-name list built through MCP/API is invisible in the UI
- kind: bug
- severity: high (the UI says I have no candidates; I can't use the page my job revolves around)
- evidence:
  - `GET /api/watchlists` returns `[{"name": "growth-candidates", "count": 13}]` (14 after I added TGTX).
  - `/watchlist` at 390 px (8 s settle) shows: "Watchlist · Nothing yet. Add tickers above, or ask Claude: 'add TSLA to my Argus watchlist'".
  - The cause is in the frontend: `api.watchlist(name = "Watchlist")` in `frontend/src/api.ts`, and `Watchlist.tsx` loads only that name. There's no picker.
  - The Screener's "+ watch" buttons add to that hidden "Watchlist" list, a different one from the list MCP's `watchlist_add` uses. So agent and UI users keep two disjoint lists without knowing it.
  - B-106 is the brief side of the same gap.
- suggestion: list the names from `/api/watchlists` in a selector on the Watchlist page (remember the choice), and open the only or most recent list by default. Show which list "+ watch" will add to.

### 2. Stock page EPS growth rows are Finnhub's and contradict the SEC EPS on the same card (TGTX "EPS growth YoY +633.7%" while SEC TTM EPS fell 2.79 → 0.67)
- kind: bug
- severity: medium (wrong sign on a growth investor's core number)
- evidence: `/t/TGTX` Valuation & fundamentals card and `/api/fundamentals/TGTX`:
  - **EPS (TTM):** $0.67, labeled "SEC, 4Q to 2026-09-30".
  - **Rows beside it:** "EPS growth YoY **+633.7%**" and "EPS growth, latest quarter **−71.5%**", both `sources: finnhub` and unlabeled on the page.
  - **From Argus's own SEC quarters** (`/api/financials/TGTX`):
    - Prior TTM EPS: 0.16 + 0.03 + 0.17 + 2.43 = 2.79.
    - Current TTM EPS: 0.67. That's **−76%**, not +634%.
    - Latest quarter: 0.35 vs 2.43 = **−85.6%**. Research → Growth agrees: net income y/y −85.8%.
  - "Revenue growth, latest quarter" right above was moved to SEC by B-009 (+60.7%, labeled), so the card now mixes sources row by row.
- suggestion: as B-009 did for revenue, compute both EPS growth rows from the SEC quarters when they're present, label them, and fall back to Finnhub with a source label only when they aren't.

### 3. Screener growth is a year stale: 11 of 19 "≥25% growth" hits grow less than that now, and 5 are flat or shrinking (B-019)
- kind: feature
- severity: high (the screen's main filter mostly returns ex-growers; I had to make 19 extra calls to clean it)
- evidence:
  - Screen A (above) gave 19 rows. Then I made one `/api/financials/<sym>` call per row and compared the latest SEC quarter (Q3-26) with Q3-25:

    | Symbol | Screener growth | Latest quarter y/y |
    |---|---|---|
    | NUTX | +82.4% | **−18.7%** |
    | CRK | +77.0% | **−14.1%** |
    | GPOR | +48.5% | **−4.5%** |
    | JOE | +27.4% | **−3.0%** |
    | XZO | +62.0% | **+0.0%** |
    | PGY | +26.1% | +6.6% |
    | VCTR | +46.2% | +9.8% |
    | DUOL | +38.7% | +13.7% |
    | SSRM | +63.7% | +16.0% |
    | PODD | +30.7% | +19.2% |
    | RMBS | +27.1% | +22.3% |

  - Only TGTX, RDDT, LIFE, INOD, ANIP, TMDX, LPG and KRYS still grow ≥25%.
  - Argus already has these quarters: research and the stock page use them.
- suggestion: add a "Revenue growth, latest quarter y/y" field to the screener (from the cached SEC quarterlies) so it can be filtered and sorted. Label the existing columns "FY2025".

### 4. Forward P/E: RDDT is the only holding whose forward EPS doesn't match any Estimates row (B-120 narrowed)
- kind: bug
- severity: medium
- evidence:
  - For every other name I checked, `eps_forward` in `/api/fundamentals/<sym>` equals Research → Estimates `+1y` exactly:
    - KRYS 9.228 = 9.23
    - LOAR 1.671 = 1.67
    - TMDX 2.486 = 2.49
    - TGTX: 64.56 ÷ 22.06 = 2.93 = 2.93
    - ANIP: 71.06 ÷ 6.96 = 10.20 = 10.20
  - RDDT is the outlier: `eps_forward 9.286` (forward P/E 10.7), while Estimates show `0y 5.48`, `+1y 6.86`. On FY27 the forward P/E should be 99.55 ÷ 6.86 = **14.5**.
- suggestion: compute forward P/E from the Estimates `+1y` row Argus already shows, and label it "FY2027E". When the provider's forward EPS disagrees with that row by more than 10%, drop it.

### 5. The screener ranks one-off tax-benefit years as quality: TGTX shows P/E 21.8 and net margin 72.6% vs TTM P/E 96 (related to B-071)
- kind: ux
- severity: medium
- evidence:
  - `POST /api/screener` and the Screener page (default ROE sort) list TGTX second, with net margin 72.6%, ROE 78.2% and P/E 21.8.
  - These figures come from FY2025, which included Q3-25 net income of $390.9M on $161.7M revenue (a tax benefit; `/api/financials/TGTX`).
  - The stock page shows P/E (TTM) 96.4, SEC net margin 11.8%.
  - A ≤45 P/E filter therefore lets in a stock trading at 96× trailing GAAP.
- suggestion: when net income is more than operating income + 50% in the fiscal year, flag the row ("one-off gain, P/E n/m"), or use operating income for the P/E filter.

### 6. PAYS's report is still timed after close; the reaction still starts after a −14.8% report-day move (B-149)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/earnings/PAYS` gives `report_date 2026-11-09, timing amc`, with reaction base 11-09 close 12.51 → 11-10 close 10.14 (−18.9%).
  - `argus history PAYS` shows 11-09 open 14.93, close 12.51 on 2.66M shares (about 3× normal). The company's EPS headline was at 17:09Z (round 015).
  - From the last close before the report (11-06, 14.69), the move is −31%.
- suggestion: as filed in round 015. When the report-day bar moves >10% on >2× volume, measure from the prior close.

### 7. Cold loads are still slow: brief 7.7 s, watchlist 10.2 s, and stock-page chart and peers still "Loading…" at 3.5 s
- kind: perf
- severity: low (known area: B-026, B-097)
- evidence:
  - **Brief:** `GET /api/brief/loop-growth` took 7.71 s cold, then 0.10 s warm. It was 4.9 s last round and 1.35 s the round before.
  - **Watchlist:** `GET /api/watchlists/growth-candidates` took **10.2 s** cold, then 0.06 s warm.
  - **Stock page:** `/t/TGTX` with a 3 s settle shows "Loading chart…", the 5D–Max chips as "–" and Peers "Loading…".
  - Screener 10 ms, compare 0.16 s, research 1.4–1.9 s.
- suggestion: warm the brief and watchlist caches after the close, as already happens for screener prices.

### 8. Fear & greed jumped 25.3 → 40.9 in the same evening once breadth loaded (B-036)
- kind: bug
- severity: low (known)
- evidence:
  - `/api/market-context` at 02:13Z gave score 25.3 with 5 components and `errors.breadth` set.
  - A few minutes later, after the universe built, it gave 40.9, with no new market data in between.
  - The rating text didn't say a component was missing.
- suggestion: as filed. Show "5 of 7 components" while breadth is missing.

### 9. Simulate reports concentration by market value only, while my 15% cap and most sizing rules are at cost
- kind: feature
- severity: low
- evidence:
  - `POST /api/portfolios/loop-growth/simulate` (BUY 10 RDDT) returns `weight_before/after` and `top1_pct 17.2` by value only. That's TMDX at 17.2% of value, but 14.0% at cost.
  - To check my rule I have to divide `cost_basis` by capital myself.
- suggestion: add `cost_weight_before/after` (cost ÷ total cost) to `positions_changed`.

## Summary for the round lead
- **Trades:** none. Book $100,986.59 plus $31.77 cash (+1.02% to date). Day P&L −1.91% vs IWM −1.64% (LOAR and RDDT −5% on sector beta, no news). Theses intact. TGTX added to the watchlist (note 90); NUTX, DUOL and ANIP passed.
- **Last round's fixes:** B-157 verified live tonight with a late Yahoo bar (RMBS 1W +21.9% in the API, the Dashboard tab and the stock page). B-152 holds (Risk −1,963.42 = Day P&L).
- **Top findings:**
  - New: the Watchlist page shows only a list named "Watchlist", so the 14-name list built through MCP is invisible in the UI.
  - New: the stock page's EPS growth rows (Finnhub) contradict its SEC EPS (TGTX +634% vs −76%).
  - B-019: 11 of 19 screener "≥25% growth" hits are below that now, 5 flat or negative.
  - Still open: B-120 (RDDT only), B-149, B-106, B-109.
