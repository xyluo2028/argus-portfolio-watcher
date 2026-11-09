# Round 014: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:45 UTC on Mon 2026-11-09, which is Sunday evening ET with markets closed. Prices are the Fri 11-06 close plus Friday post-market quotes.
- **Market:** a rebound day on Friday. SPY +0.31%, IWM +0.99%. Fear & greed is 16.8 ("Extreme fear", VIX 25.6). Breadth now loads: 59% of the top 500 are above their 50-day average (`/api/market-context`, 1.4 s, no errors).
- **Book before trades** (`GET /api/portfolios/loop-growth`, 0.8 s): 10 positions, value $98,541.23, Day P&L **+$3,335.00 (+3.50%)** against IWM's +0.99%.
  - TMDX made +27.9% on Friday after its Q3 report, adding +$3,118.84. It is now 16.9% of value (14.0% at cost, so no adds).
  - **Check on performance:** the last step is 98,541.23 − 95,417.18 = 3,124.05. Adding back the 11-06 net flow of −210.95 gives 3,335.00, which equals Day P&L to the cent.
- **GRND, the one open item from last week:** its 10-Q is now in Argus (`/api/financials/GRND?period=quarterly`).
  - **Growth:** Q3 revenue was $141.4M, **+22.1%** y/y, after Q2 +32.5% and Q1 +38.3%.
  - **Margins:** operating margin was **2.9%**, against 39.1% a year ago and 23.5% in Q2. Net income was −$6.6M, GAAP EPS −0.04.
  - **Research tab:** FY26 EPS consensus fell from 0.53 to 0.32 in 7 days, and FY27 from 0.69 to 0.60.
  - **Insiders and dilution:** chairman Zage sold about 1.0M shares ($13.5M) between 10-16 and 11-03. A shelf prospectus was filed on 11-06 (News).
  - **Verdict:** my written break is margin under 20% for *two* quarters, so this is one quarter early. But the margin and alignment pillars weakened together while growth is falling fast. A compounder doesn't do that.
- **Hunt:** I ran three screens (`POST /api/screener`, 5–6 ms each; still FY2025 only, B-019). Screen: cap $1.5–30B, growth ≥20%, op margin ≥15%, FCF ≥12%, ROE ≥12%, P/E ≤45, L/E ≤2.5. It surfaced **RDDT**.
  - **SEC quarterlies:** revenue +69%, +61% and **+53%** y/y in Q1–Q3'26 (Q3 $895.0M). Op margin was 29.2% in Q3, up from 23.7% a year ago. Q3 FCF was $362.6M (TTM $1.20B), with no debt.
  - **Price and valuation:** −58.6% YTD, and **−29.2%** on its Q3 report (10-29 amc, 129.60 → 91.73) despite a beat. P/E 19.4 and P/S 5.9 are both at the 0th percentile of its own history.
  - **Compare:** META trades at P/E 20.8 and P/S 6.5 on 27.5% growth (`/api/compare`).
  - **Passed:** DUOL (Q3 only +13.7% y/y, op margin falling to 7.8%), HIMS (operating losses, reports tonight) and NVMI (no SEC quarterlies).
- **Trades** (both via `argus txn add`, at the latest prints, which are Friday post-market):
  - SELL 487 GRND @ 13.41 (txn 56). Realized **−$457.78**. Note 83 holds the reasoning.
  - BUY 72 RDDT @ 95.65 (txn 57), a 6.9% starter. Thesis note 84: break if growth < 30% or op margin < 20%; review 2027-02-04.
- **After trades:** 10 positions, cost $98,186.15, value **$98,794.45**, realized −$1,782.08, cash **$31.77**.
  - Cash check: (100,000 − 1,782.08) − 98,186.15 = 31.77.
  - Return to date = (98,794.45 + 31.77 − 100,000) ÷ 100,000 = **−1.17%**.
  - The largest position at cost is TMDX at 14.0%. By value, healthcare is 46.9%.
- **Other holdings:** no changes. ESE reports 11-19. Everything else reported last week, and each thesis was checked in round 013.

## Last round's changes
- **B-140 (splits): works for me, with no false flags.**
  - `split_warnings` is `[]` for loop-growth, loop-income and loop-macro.
  - The `stock_split` table holds only real splits: QUAL 4:1 on 11-05, plus historical O, SCHD, SCHP, XLE, KO and NEE.
  - None of my holdings got a spurious "possible split".
- **B-142 (risk uses the quote-filled last session): works, but the tile disagrees with Day P&L** (finding 6).
  - `/risk` gives `as_of` 2026-11-06, with `closes_from_quotes` null because Yahoo's 11-06 bars are in.
  - Its "Last session (11-06)" is **+$3,978 (+4.20%)**, while the Dashboard says **+$3,335.00 (+3.50%) last session**.
- **B-141 (dividend calendars):** not relevant to me; I hold no payers.
- **B-143 (a company that reported after the close but has no actuals yet): partly resolved by data, with a new bug.**
  - GRND's Q3 row now exists, but it's dated the wrong day and has a fake reaction (finding 2).
  - Last week's brief and Coming up already disagreed: the brief listed GRND under recent earnings (11-05) while Coming up left it out.
- **Still open (multibagger re-check list):**
  - B-119 (EPS basis): still broken (finding 3).
  - B-106 (brief watchlist movers): still empty (finding 7).
  - B-109 (simulate at the close after hours): untestable tonight because the market is closed. Simulate still priced at the 4 pm close (GRND 13.54, RDDT 95.10) even though the latest prints were Friday post-market (13.41 / 95.65), and it doesn't say which price it used.

## Findings

### 1. Simulate silently turns a SELL into a BUY when the trade uses `type` (the ledger's field name)
- kind: bug
- severity: high (the what-if is silently inverted: I'd have sized my RDDT buy off a book that *doubled* GRND)
- evidence:
  - `POST /api/portfolios/loop-growth/simulate` with `{"trades":[{"type":"SELL","symbol":"GRND","qty":487},{"type":"BUY","symbol":"RDDT","qty":72}]}` returned `trades[0].side: "BUY"`, `qty_after: 974` for GRND, `net_cash −13,441.18` and `value_after 111,982.41`. There was no error or warning.
  - Transactions use `type` (`POST /api/portfolios/{ref}/transactions`, `argus txn add ... SELL`). Simulate reads `t.get("side", "BUY")` (`app.py` `simulate_trades`), so the unknown key is ignored and the default applies.
  - With `"side":"SELL"`, the result was right: net cash −356.13, realized −457.78.
  - Minor: the same response classed RDDT as "Unclassified" in `sector_lookthrough_after`, while the Dashboard's By sector card shows it as "Communication…" 6.9% right after the buy.
- suggestion:
  - Make `side` required, with no default.
  - Accept `type` as an alias, or reject unknown keys.
  - Use the same field name as transactions everywhere: API, MCP and UI.

### 2. GRND's Q3 report is dated a day late, so its reaction is a fake "after hours −1.0%" instead of Friday's real move
- kind: bug
- severity: medium (the reaction to the print is the first thing I check; this one is invented)
- evidence:
  - **The release:** Research → News has "Grindr Inc. Reports Third Quarter 2026 Revenue Growth of 22%…" at **2026-11-05T21:05Z** (4:05 pm ET Thursday).
  - **`/api/earnings/GRND`** gives `report_date: 2026-11-06, timing amc`.
    - Its reaction has `base_date 2026-11-06, base_close 13.54, close_pct −0.96, provisional, label "after hours"`. That is Friday's post-market 13.41 against Friday's close.
    - The real reaction is 11-05 close 13.64 → 11-06 close 13.54 = **−0.73%**, with the open at −2.1%.
  - **The stock page's Reported financials** reads "2026-09-30 · reported Nov 6, after close … −1.0% after hours".
  - **The brief's `earnings_recent`** says GRND `date: 2026-11-05`, with Finnhub `epsEstimate 0.0408` and no actual. The stock page shows est **0.15** and actual **0.12** (Yahoo). So there are two dates and two estimates for one report.
  - INOD, TMDX and LOAR (same night) are dated correctly, so it looks like the Yahoo date wins the merge when Finnhub has no actual (`earnings.build`, `abs(k − d) <= 2` keeps the first key).
- suggestion:
  - When Finnhub's calendar and Yahoo disagree by a day, keep the earlier date, or the date of a matching press-release headline.
  - Never label a reaction "after hours" when the market is closed for the weekend and the next session hasn't opened.

### 3. Yahoo "reported" EPS is adjusted, not GAAP, and the stock page claims +19% EPS growth on a quarter that lost money (B-119)
- kind: bug
- severity: medium (the surprise and growth figures say the opposite of the 10-Q)
- evidence: GRND, all values from Argus.
  - Reported financials shows Q3 `EPS (dil.) −0.04` (SEC) next to `EPS actual 0.12†`, and "Miss −20.0%" against est 0.15.
  - The footnote says † is "Yahoo's reported EPS, which can be GAAP". Here it is clearly adjusted.
  - The Valuation & fundamentals card says **"EPS growth, latest quarter +19.0%"**. Research → Growth for the same quarter shows net income **−121.4%** y/y, and SEC EPS went from 0.16 to −0.04.
- suggestion:
  - Label the basis by comparing with SEC diluted EPS for the same period, as proposed in round 013.
  - Take "EPS growth, latest quarter" from the SEC table it sits beside, or tag its source.

### 4. A margin collapse is invisible on the stock page: TTM figures hide a quarter that went from 39% to 3% operating margin
- kind: feature
- severity: medium (this was the decisive fact for my GRND exit, and I only found it in the table at the bottom)
- evidence:
  - **The card:** `/t/GRND` Valuation & fundamentals shows Operating margin **20.7%** and Net margin **10.9%** (both "SEC, 4Q to 2026-09-30"). The Peers row shows Rev growth +32.4% and Net margin 10.9%.
  - **The quarter:** Q3 operating margin was 2.9%, against 39.1% a year ago and 23.5% in Q2 (Reported financials, and Research → Growth). Net income was negative.
  - **Mislabeled growth:** the card's "Revenue growth YoY +32.4%" is the prior quarter's figure, shown above the correct "latest quarter +22.1%" (related to B-009/B-102).
  - Nothing on the page explains the drop. News has no summary (B-121), and there is no expense breakdown.
- suggestion:
  - Add "latest quarter" rows for operating and net margin, with the y/y change in points, beside the TTM ones.
  - Flag a drop of more than 10 points, e.g. "Op margin 2.9% in Q3, −36 pts y/y", on the card and in the brief for holdings.
  - This is the margin twin of B-144's cash-flow flag.

### 5. Forward P/E 10.2 for RDDT matches no estimate on its own Estimates tab (B-120)
- kind: bug
- severity: medium (a growth buy looks 30–40% cheaper than consensus supports)
- evidence:
  - `GET /api/fundamentals/RDDT` (also `/api/compare`) gives `pe_forward 10.24` on `eps_forward 9.29`, which is Yahoo's `forwardEps`.
  - `GET /api/research/RDDT` gives estimates of 0y (FY26) **5.48** and +1y (FY27) **6.86**.
  - At 95.10 those mean forward P/Es of 17.4 and 13.9. No figure in Argus gives 9.29.
  - The PEGs also disagree: `peg 0.46` vs `peg_ttm 0.11` (B-123).
- suggestion: compute forward P/E as price ÷ next fiscal year's consensus from the Estimates tab, and label the year (e.g. "P/E FY27e 13.9"). Drop Yahoo's `forwardPE` or show it only with its own label.

### 6. Two "last session" numbers $643 apart, and Day % disagrees with Day P&L for lots bought after a close
- kind: ux
- severity: medium (the same label shows different numbers in different places)
- evidence:
  - **Two "last session" figures:**
    - The Dashboard header says "+$3,335.00 (+3.50%) last session". The Risk card's "Last session (11-06)" is **+$3,978 (+4.20%)** (`/risk` `last_day`).
    - The Risk figure is today's holdings over Friday: 189 TMDX × 19.26, 194 LOAR × 2.31, RDDT included and GRND excluded. I recomputed it to the cent. Only the hover tooltip says "Today's holdings".
  - **Day % vs Day P&L:**
    - The Holdings table shows TMDX **Day % +23.00%**, while the stock moved +27.92% (`argus quotes`, and the stock page's 1D). That is the position return on the 65 shares bought at 77 after Thursday's close.
    - RDDT, bought after Friday's close, shows **Day % +1.38% with Day P&L $0.00**.
    - So one column follows two rules, and the brief's `top_gainers` reports TMDX at +23.0%.
- suggestion:
  - Rename the risk tile "Today's holdings over 11-06", or show actual Day P&L beside it.
  - In Holdings, always show the stock's Day %, and put the position's own % in a tooltip or in the Day P&L cell.

### 7. The brief's `watchlist_movers` is still empty while six watchlist names moved 5–13% (B-106)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/brief/loop-growth` returns `watchlist_movers: []`.
  - `GET /api/watchlists/growth-candidates` shows MNTN +13.4%, VICR +8.7%, CELH +7.1%, NUTX −6.75%, BELFA +6.1% and XZO −5.5%. The brief code reads the default watchlist, not the named ones.
- suggestion: as filed.

### 8. Argus can't tell me why RDDT fell 29% on a beat, and its News tab is mostly unrelated personal-finance stories
- kind: feature
- severity: low (known B-096 and B-059; RDDT is the worst case I've seen)
- evidence:
  - `/api/research/RDDT` news returns 12 items. Five of them are unrelated: "Wife Fears Becoming Mother-in-Law's 'Retirement Plan'…", "I Thought I Needed $1M To Retire…", "Average Social Security Check…" and others. These are stories quoting Reddit posts.
  - Nothing explains the −29.2% on 10-30. Revenue was in line ($895.0M vs $896.0M est) and EPS beat (1.40 vs 1.38), so the cause must be guidance or user metrics. Argus has neither (B-090).
- suggestion:
  - Drop headlines that don't name the company or its ticker in the title, for platform names like Reddit.
  - On a reaction beyond ±15%, surface the headlines from the report day.

### 9. Watchlist cold load is still 9.7 s
- kind: perf
- severity: low
- evidence:
  - First `GET /api/watchlists/growth-candidates` took 9.73 s; it was 8.78 s last round.
  - Other timings: portfolio 0.81 s, performance 0.03 s, brief 1.35 s, research 1.4–1.8 s, risk 1.5 s, compare 2.7 s, screener 5–6 ms.
- suggestion: as filed (B-026/B-097). Warm the named watchlists with the screener.

### 10. Earnings rows for a company without SEC quarterlies get invented period ends (NVMI 2026-10-06, 2026-07-07)
- kind: bug
- severity: low
- evidence: `/api/earnings/NVMI` gives `reports[0].period_end 2026-10-06` (reported 11-05) and `reports[1] 2026-07-07`. Nova's quarters end on 09-30 and 06-30. `/api/financials/NVMI` has no periods, because it is a 20-F/6-K filer.
- suggestion: when there are no SEC periods, label the row by report date or calendar quarter (Q3 2026) instead of stepping 13 weeks from an arbitrary anchor.

## Summary
1. **Trades:**
   - Sold all 487 GRND @ 13.41, realized −$457.78. Q3 op margin was 2.9% (39% a year ago), FY26 EPS consensus was cut 40%, a shelf was filed and the chairman is selling.
   - Bought a 72-share RDDT starter @ 95.65: Q3 +53% y/y, op margin 29%, P/E 19 at the bottom of its range.
   - Cash is $31.77 and value $98,794.45, so return to date is **−1.17%**. Friday was +3.50% vs IWM +0.99%.
2. **Top findings:**
   - Simulate silently turns `type: SELL` into a BUY (high).
   - GRND's report is dated 11-06 with a fake "after hours −1.0%" reaction, and the brief and stock page show two dates and two estimates (medium).
   - Yahoo EPS is labeled possibly-GAAP but is adjusted, and "EPS growth +19%" sits on a loss quarter (B-119, medium).
   - The TTM margins hide a 39% → 3% collapse (medium).
   - RDDT's forward P/E of 10.2 matches no estimate in Argus (B-120, medium).
3. **Re-checks:**
   - Confirmed: B-140 raises no false split flags, and performance's last step equals Day P&L. B-142 works, but its tile reads +$3,978 vs Day P&L +$3,335.
   - Still broken: B-106 (watchlist movers empty), B-119, B-143 (now a wrong-date variant). B-109 couldn't be tested with the market closed.
