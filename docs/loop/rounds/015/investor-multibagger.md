# Round 015: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:50 UTC on Thu 2026-11-12, which is Wed 11-11 evening ET with the market closed. Prices are the 11-11 close; post-market prints are noted where I used them. Yahoo's 11-11 daily bar was not yet published.
- **Market:** a strong day. SPY +1.32%, IWM +0.89%. Fear & greed is 38.3 ("Fear"), up from 16.8 last round (`/api/market-context`, 0.6 s; the only error was the Nasdaq calendar 403, a known issue).
- **Book** (`GET /api/portfolios/loop-growth`, 0.72 s): 10 positions, value **$102,950.01**, cost $98,186.15, Day P&L **+$1,568.16 (+1.55%)** against IWM +0.89%.
  - Movers: RMBS +5.7% (+$557), RDDT +7.1% (+$503; it is on the S&P after-hours gainers list), INOD +8.9%.
  - Post-market drift is −$386.52 (−0.38%).
  - TMDX is 16.9% by value but 14.0% at cost, so no adds; my rule is 15% at cost.
- **Holdings review:** every thesis is intact, and there were no earnings in the window.
  - ESE reports 11-19 (`argus events`). It isn't in the brief yet because the brief only looks 7 days ahead.
  - TOST was downgraded by Bernstein to Market Perform. That's an opinion change, not a thesis break: my break is growth < 18%, and Q3 was +21.3%.
  - BLLN: Piper cut its price target to $130 but kept Overweight.
- **Hunt:**
  - **Screens** (`POST /api/screener`, 5–8 ms, FY2025 data):
    - Screen A: cap $1–25B, growth ≥25%, op margin ≥12%, ROE ≥12%, P/E 5–45, L/E ≤2 (19 matches).
    - Screen B: cap $0.5–15B, growth ≥30%, FCF ≥10%, gross margin ≥50%, P/S ≤12 (17 matches).
  - **PAYS** (on my watchlist, reported 11-09): my r010 buy test was growth ≥35% and op margin ≥20%. Q3 passed it: SEC revenue 30.8M, **+42.6%** y/y, op margin **23.8%** vs 7.4%.
    - But the affirmed FY26 sales guide of $114–117M implies **Q4 $26.9–29.9M**, which is down q/q and only +18–31% y/y. That fits the "plasma customer exit" headline.
    - Insiders made 19 sales ($7.5M) and no buys. The stock fell from 14.69 to 9.48 (−35%) in two sessions.
    - Decision: **no buy**. Growth durability is the thesis, and the guidance breaks it. Note 86, review 2027-03-24.
  - **LIF** (watchlist, reported this week): Q3 revenue +39.8%, but op margin is 4.6%, flat y/y, so the inflection I was waiting for hasn't come. Insiders are heavy net sellers. Pass.
  - **XZO:** the screener's +62% growth is FY2025. SEC quarters are now **+0% / +3% / +6%** y/y. Pass.
  - **LIFE (Ethos):** +151% growth, but op margin is 1.6% and insiders sold $99.6M. Pass.
- **Trades: none.** Nothing new beat my weakest holding. INOD still passes its exit tests (note 73), and the PAYS case broke on guidance.
- **Cash:** (100,000 − 1,782.08 realized) − 98,186.15 cost = **$31.77**.
- **Return to date:** (102,950.01 + 31.77 − 100,000) ÷ 100,000 = **+2.98%**.

## Last round's changes
- **B-147 (simulate requires a side): works, and it fixes my round-014 finding.**
  - `{"type":"SELL","symbol":"INOD","qty":107}` now simulates as a SELL with `net_cash +4,084.19`.
  - Each bad trade gets a clear 400:
    - no side: "give side (or type) BUY or SELL"
    - side `sell` with type `BUY`: "side and type disagree (BUY vs SELL)"
    - `HOLD`: "side must be BUY or SELL, not 'HOLD'"
    - no symbol: "give a symbol"
  - Minor nit: the disagree message sorts the two values (`sorted(given)`), so it doesn't say which field held which.
- **B-139 (date-bomb tests) and B-146 (one-holding risk):** don't touch my workflow; I didn't re-test them.
- **On my re-check list, still open:**
  - **B-149 (GRND's report date): still wrong, and the reaction changed but is still wrong.**
    - `/api/earnings/GRND` still gives `report_date 2026-11-06`.
    - The reaction is now `base_date 11-06 → 11-09, close_pct −1.18%`. The real move was 11-05 → 11-06, −0.73%.
    - The new PAYS case (finding 2) looks like the same merge problem.
  - **B-120 (forward P/E): still open.** RDDT shows `pe_forward 11.38` on `eps_forward 9.29`, while Estimates show FY26 5.48 and FY27 6.86.
  - **B-106 (watchlist movers): still open.** `watchlist_movers: []`, while LIF (+6.4%) moved on growth-candidates.
  - **B-109 (simulate's price after hours): still open.** Simulate prices INOD at the 38.17 close and RDDT at 105.66. The post-market prints are 37.80 and 104.40. The response has no `price_source`.

## Findings

### 1. Momentum returns from the API, MCP and Dashboard tabs differ from the stock page on any evening Yahoo's bar is late; RMBS's 1-week return flips sign
- kind: bug
- severity: high (wrong numbers; the stock page says the two views show "same figures as the dashboard tabs")
- evidence:
  - **RMBS:** `GET /api/fundamentals/RMBS` and `GET /api/portfolios/loop-growth/fundamentals` both give 1W **−2.58%**, 1M −24.85% and YTD −12.11%. The `/t/RMBS` Momentum card (phone width) shows 1 week **+3.0%**, 1 month −20.6% and YTD −7.1%.
  - **The cause:** RMBS's cached bars end at 11-10 (80.76), because Yahoo hasn't published 11-11.
    - `price_stats` (`app.py`) takes `last = series[-1]` (the 11-10 close). But it computes the bases from the anchor, which is the last session (11-11), so the 5D base is the 11-04 close of 82.90.
    - 80.76 / 82.90 − 1 = −2.58%. The live figure is 85.36 / 82.90 − 1 = **+2.97%**, which is what the stock page shows (`Ticker.tsx rangeReturn` uses the quote).
  - **PAYS:** the API gives 1W −33.7% and YTD +96.9%; the page shows −38.0% and +84.1%.
  - **Effect:** every agent and MCP user, and the Dashboard's fundamentals tabs, get a 1W window that ends a session early and leaves out today's move.
- suggestion: in `price_stats`, use the quote price, as the stock page does, when the latest bar is older than the anchor session. This is the B-134 fill. Or, at minimum, measure from the last bar's own bases. One code path would make both views agree.

### 2. PAYS's report is labeled after the close, but Argus's own headlines and bars say it came out during the session; the reaction misses the first −14.8%
- kind: bug
- severity: medium (the reaction to the print is the first thing I check)
- evidence:
  - **The label:** `GET /api/earnings/PAYS` gives `report_date 2026-11-09, timing amc` and reaction `base_date 11-09 (12.51) → 11-10, close_pct −18.9%`.
  - **The headlines:** Research → News has Benzinga "PaySign Q3 EPS $0.11 Beats…" at **2026-11-09T17:09Z** (12:09 ET) and "Raises FY2026 GAAP EPS Guidance…" at 17:43Z. A Benzinga call transcript follows at 18:37Z.
  - **The bars:** `argus history PAYS` shows 11-09 open 14.93, low 12.32, close 12.51 on 2.66M shares, 3–4× normal volume. That is **−14.8%** from the 11-06 close of 14.69.
  - **Result:** the stock page's Reported financials shows "reported Nov 9, after close … −18.9%" when the real move from the last pre-report close is about **−31%**.
  - A Yahoo copy of the press release is stamped 21:05Z, which is probably where "amc" comes from. Either the timing or the timestamps are wrong, and Argus doesn't notice they conflict.
- suggestion:
  - When the report day's own bar moves more than ±10% on more than 2× average volume, measure the reaction from the prior close.
  - Or take timing from the earliest company headline matching "Q\d … EPS" when it is before 16:00 ET.
  - Show the two-day move when it's unclear. This is the same merge area as B-149.

### 3. The brief misses an announced earnings date eight days out; there is no per-holding "next report" in the brief
- kind: ux
- severity: low
- evidence:
  - `GET /api/brief/loop-growth` returns `earnings_upcoming: []`.
  - `argus events --json` lists ESE earnings on **2026-11-19** (held, est EPS 2.62). The brief uses `upcoming_events(days_ahead=7)` from the NY date 11-11, so the window ends 11-18.
  - On a Wednesday evening, next Thursday's report is what I need to plan around.
- suggestion: use a 10-business-day window for earnings in the brief, or always include each holding's next report date.

### 4. Guidance isn't structured, so the decisive number (the implied next quarter) has to be worked out by hand from a headline
- kind: feature
- severity: medium (it changed my PAYS decision from buy to pass)
- evidence:
  - PAYS passed every number Argus shows: growth +42.6%, op margin 23.8%, a beat, guidance "raised" in the headline title. The momentum card shows only −38%.
  - The break was only visible by taking the headline "Affirms FY2026 Sales Guidance of $114.000M-$117.000M" and subtracting the three SEC quarters (28.0 + 28.3 + 30.8 = 87.1). That leaves Q4 at $26.9–29.9M, below Q3 and +18–31% y/y.
  - The Estimates tab has EPS for `+1q` but no revenue for next quarter.
- suggestion:
  - Show the revenue consensus for next quarter and the implied y/y growth on the Estimates tab. Finnhub and Yahoo both have it.
  - Better: parse "FY… guidance of $X–$Y" headlines and show "implied Q4: $26.9–29.9M (+18–31% y/y)" under Reported financials.

### 5. Screener rows still show FY2025 growth for companies whose growth has gone to zero (XZO +62% vs +0% in Q3)
- kind: ux
- severity: medium (known B-019; this is a sharper example)
- evidence:
  - **XZO:** `POST /api/screener` (growth ≥25%) returns it with `revenue_growth_pct 62.0`. `/api/research/XZO` growth quarters are **+0.0% / +3.0% / +6.0% / +19.7%**.
  - **RDDT:** the screener's P/E is 38.5 (FY2025 earnings) while the stock page shows 21.6 TTM.
  - The fiscal year appears only in `screener_status().fiscal_year`, not beside each column.
- suggestion: label the columns "FY2025". Add a "latest-quarter growth y/y" field from the SEC quarterlies already cached for the research tab, so the screen can filter on it.

### 6. Forward P/E still uses Yahoo's unexplained forward EPS (RDDT 11.4 vs 13.9–17.4 from consensus) (B-120)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/fundamentals/RDDT` gives `pe_forward 11.38` on `eps_forward 9.29`.
  - `/api/research/RDDT` gives FY26 5.48 and FY27 6.86. At 105.66 those mean forward P/Es of 19.3 and 15.4.
  - PAYS is consistent (forward 15.4 = 9.48 / 0.615, the FY27 estimate), so the error depends on the symbol.
- suggestion: as filed. Compute it from the Estimates tab and label the year.

### 7. Stock page chart is still "Loading chart…" 2.7 s after render
- kind: perf
- severity: low
- evidence:
  - `scripts/screenshot.py /t/PAYS` with the default 2 s settle (rendered at 0.65 s) captured "Loading chart…" and "Company Loading…".
  - With an 8 s settle, everything was there.
  - Other timings:
    - API: portfolio 0.72 s, brief **4.9 s** (1.35 s last round), research 1.9 s, market-context 0.6 s, screener 5–8 ms.
    - Watchlist cold load: **7.2 s** (9.7 s last round, B-026).
- suggestion: show the chart before the Company card. Look into the brief's jump to 4.9 s; it may be the news fetch (B-105).

## Summary for the round lead
- I made no trades. The book is $102,950.01 plus $31.77 cash (+2.98% to date), and Day P&L was +1.55% vs IWM +0.89%. PAYS passed my buy test but failed on guidance (note 86). LIF, XZO and LIFE were passes.
- Top bug: momentum in `/api/fundamentals`, MCP and the Dashboard tabs uses a stale last bar against the current session's bases. RMBS shows 1W −2.6% there and +3.0% on the stock page.
- PAYS's report is timed "amc", but Argus's own headlines and bars show an intraday release, so the reaction misses the first −14.8% (related to B-149). B-147 works; B-149, B-120, B-106 and B-109 are still open.
