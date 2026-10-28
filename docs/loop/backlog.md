# Backlog

Every finding from the investor reviews, deduplicated. The round lead keeps this file; see
`README.md` for how items are picked.

Format, one item per heading, newest IDs at the bottom of their section:

```markdown
### B-001 Short title
- kind: bug | ux | perf | feature | removal · severity: high | medium | low
- reported by: macro r001, income r002
- evidence: one or two lines, or a link to the round report
- acceptance: what "done" means (written when the item is picked)
- status: open | in progress rNNN | done (rNNN, <commit>) | blocked: <reason> | won't do: <reason>
```

## Open

### B-001 Run tests and the frontend build on every push (CI)
- kind: ux · severity: medium
- reported by: seed (docs/deployment.md, "Should do" #9)
- evidence: nothing checks the loop's pushes besides the loop itself
- note: pushing a new `.github/workflows/` file can be refused for the loop's GitHub access; if so, mark it blocked and leave the workflow file for a human to add
- status: open

### B-002 Check every page at phone width
- kind: ux · severity: medium
- reported by: seed (docs/deployment.md, "Should do" #12), macro r001, income r001, multibagger r001, macro r003, income r003, multibagger r003, macro r005, multibagger r005, income r006, macro r006
- evidence: pages were mostly designed and checked at desktop width. r001 at 390 px: Markets is 5,418 px tall
  with one gauge per row and clips the sector and calendar tables; Analysis tables (stress, dividends) and the
  Screener results table clip after the first columns; yield-curve end labels overlap on desktop
  (rounds/001/investor-macro.md, investor-income.md, investor-multibagger.md). r002: at 390 px duplicate calendar
  names (CPI / CPI, Core CPI / Core CPI) can't be told apart because Previous is cut off; name them MoM/YoY
  server-side (rounds/002/investor-macro.md #7)
- r003: phone-width Dashboard holdings table shows only symbol and name (macro r003 #8); Screener filter rows wrap onto two lines (multibagger r003); Dividends/Analysis tables still cut off (income r003)
- r004: Markets at 390 px shows nine full-width gauge cards before fear & greed; Markets tab off-screen in the nav (macro r004 #9)
- r005: stock page peers table and Events row cut off at phone width (multibagger r005)
- r006: Analysis at 390 px: stress scenarios show name and window but not the loss or $ change; factor table shows labels only; correlations clipped (income r006 #5); Markets 5,756 px tall (macro r006)
- r007: Analysis at 390 px still hides the dividend income column and stress losses (income r007 #8); Markets and Dashboard no horizontal overflow (macro r007)
- r007: stock-page Events table at 390 px squeezes the amount column ("≈ $22.79" only visible by scrolling) and clips long EPS text (developer r007)
- status: open

### B-003 Header badge says "no Finnhub key" when the stream is only switched off
- kind: bug · severity: low
- reported by: cloud smoke test (2026-10-21)
- evidence: with `ARGUS_STREAM=off` and a working key (quotes come from Finnhub), the badge reads
  "polling each minute (no Finnhub key)"; `frontend/src/components/LiveBadge.tsx` shows that text
  for every `stream.state === "disabled"`, and `backend/argus/live.py` doesn't say why it's disabled
- status: open

### B-004 Markets, Screener and Watchlist are hidden until a portfolio exists
- kind: ux · severity: medium
- reported by: cloud smoke test (2026-10-21)
- evidence: on a fresh instance `/markets` shows only "No portfolios yet" (`frontend/src/App.tsx`
  routes every page except `/data` to that card); market data and the screener don't need a portfolio
- status: open

### B-009 Stock page "Revenue growth, latest quarter" (Finnhub) contradicts the SEC table on the same page
- kind: bug · severity: high
- reported by: multibagger r001, still present r002, multibagger r003, multibagger r005, multibagger r006, multibagger r007
- evidence: /t/BLLN shows −12.8% (Finnhub `revenue_growth_q_yoy_pct`) above SEC quarters giving +64.4%
- r003: still present (BLLN −12.8% vs SEC +64.4%; multibagger r003)
- r005: still present (BLLN −12.8% vs SEC +64.4%; multibagger r005)
- r006: after RMBS's Q3 print the valuation card stays a quarter behind the SEC table on the same page: TTM revenue $756M (Yahoo, through Q2) vs $796M, latest-quarter growth +20.4% (Finnhub Q2) vs +22.3% (SEC Q3), EPS TTM $2.18 vs $2.43 (multibagger r006 #1; see B-079)
- r007: two days after its print RMBS card mixes Q3 EPS (2.42) with Q2 revenue $756M, Q2 growth +20.4% and FCF margin 41.4% (39.3% on one window) (multibagger r007 #2)
- acceptance: when SEC quarters are newer than the provider figures, the stock-page valuation card takes TTM revenue, latest-quarter revenue growth, EPS TTM and FCF margin from the SEC quarters (one consistent window), with the source/period shown; the card and the SEC table agree on RMBS and BLLN; FCF margin = SEC FCF ÷ SEC revenue over the same quarters (closes B-079); tests cover a provider-lagging case
- status: done (r007, ce9d74f)

### B-011 VICR Q3 2025 revenue $407.7M: a mis-dated 10-K fact beats the 10-Q's $110.4M
- kind: bug · severity: medium
- reported by: multibagger r001
- evidence: `/api/financials/VICR` 2025-09-30 revenue 407,701,000; research shows +338% y/y
- status: open

### B-012 Analysis "Stocks / ETFs" tile prints the values in weight order under a fixed label
- kind: bug · severity: medium
- reported by: income r001, still present r002, income r003
- evidence: shows 51% / 49% while stocks are 49.4%, ETFs 50.6%; `frontend/src/pages/Analysis.tsx:23-25`
- r003: still present; subtitle now reads "ETF / Stock" (income r003)
- r004: still present (income r004)
- status: open

### B-016 Market context figures frozen up to 15 min with no fetched-at time (XLI 1D 0.00%)
- kind: bug · severity: medium
- reported by: macro r001, macro r005, macro r006
- evidence: XLI `1D: 0.0` while its quote is +0.05%; `as_of` is a date only (rounds/001/investor-macro.md)
- r003: didn't reproduce (sector 1D matched quotes; macro r003)
- r005: weekend Markets header says "as of Fri 4:00 PM ET" while oil, gold, USD/JPY and BTC show Sunday-night prices with no time tag (macro r005 #2; see B-055)
- r006: Markets reads "as of Mon, Oct 26, 4:00 PM ET" while WTI, gold, USD/JPY and BTC are 10-27 overnight prices with no tag (macro r006)
- r007: oil and gold "1D" show the overnight move under "as of 4:00 PM": oil +1.37% / gold −0.33% while on 10-27 oil fell 1.8% and gold rose 0.9%; CL=F/GC=F history has no 10-27 settle, the 10-27 bar holds the overnight price (macro r007 #1)
- status: open

### B-017 Asset-class view: bonds, TIPS, gold, commodities and cash show as "Unclassified"; no asset-class targets or duration
- kind: feature · severity: high
- reported by: macro r001, income r001, income r002 (see B-041: SEC N-PORT data has asset classes), macro r003, income r003, macro r006
- evidence: look-through "Unclassified" 39.3% (loop-macro) and 35.5% (loop-income); `funds_without_profile`
  lists BND/VCIT/VGIT/SCHP; can't check a bond floor or set drift targets by asset class; no rate-shock scenario
- r003: still 39.3% (loop-macro) / 35.5% (loop-income) Unclassified (macro r003, income r003)
- r004: still present (income r004)
- r005: still open (macro r005, income r005)
- r006: /t/IEF has the N-PORT holdings (maturities, coupons) but shows no weighted maturity or duration; Peers lists TLT, EDV, ZROZ (17–27y duration) next to IEF (~7y); 39.1% Unclassified (macro r006 #3)
- r007: still no duration on bond ETF pages; UUP (long dollar futures) shows asset mix "Cash 100%" (macro r007 #9)
- status: open

### B-018 Notes (and cost alerts) aren't tied to a portfolio
- kind: feature · severity: medium
- reported by: macro r001, income r001, multibagger r001, income r003
- evidence: `note add` has no portfolio; theses for the same symbol mix across portfolios; no portfolio-level
  thesis; `below_cost_pct` uses cost averaged across portfolios
- r003: still present; new notes are dated with the UTC date (income r003, see B-049)
- status: open

### B-019 Screener has only the last calendar year: no TTM or latest-quarter growth
- kind: feature · severity: medium
- reported by: multibagger r001, multibagger r003, multibagger r005, multibagger r006
- evidence: `fiscal_year: 2025` on 2026-10-20; LOAR +23% CY vs +36–39% latest quarters
- r003: misled a screen — DUOL and ODD topped it on last year's growth but are now decelerating or shrinking (multibagger r003)
- r004: XZO +62% in the screener vs +3% latest SEC quarter; COLL and HIMS likewise (multibagger r004 #4)
- r005: ADMA FY2025 +20% vs +2.0% / −0.3% in the last two quarters; NXT, XZO (multibagger r005 #5)
- r006: fifth round: LQDT FY growth +31.2% vs +8.1/+3.7/−0.9% latest quarters; HROW op. margin +11.2% vs −15.6%/−50.0%; HIMS +4.5% vs −12.9% (3 of 8 hits; multibagger r006 #8)
- r007: DUOL tops the screen on FY growth 38.7% / P/E 15.9; latest quarter +18.3% and the P/E rests on a tax gain (multibagger r007 #5, see B-071)
- status: open

### B-020 Rows missing gross margin silently drop out of a gross-margin filter
- kind: ux · severity: medium
- reported by: multibagger r001
- evidence: APP, KLAC, DAVE, TGTX tag CostOfRevenue, not GrossProfit; no "N excluded" note
- status: open

### B-021 Two unlabeled betas; "SPY falls 10%" scenario understates risk next to the historical replays
- kind: ux · severity: medium
- reported by: income r001, income r003, macro r003, macro r006
- evidence: SCHD 0.71 (fundamentals) vs 0.22 (1y risk); scenario −1.5% vs replays −14% to −25%
- r003: three unlabeled betas (SPY tile 0.14, factor loading 0.36, stock pages use Finnhub's: XOM −0.67 vs 0.17); "SPY falls 10%" −2.5% vs replays −5.7% to −26.5% (income r003 #9, macro r003)
- r006: beta 0.25 (vs SPY, 1y) next to a factor "Market" loading 0.36, neither labeled (macro r006)
- status: open

### B-022 Targets & drift card opens on "By sector" when targets are saved by position
- kind: ux · severity: medium
- reported by: income r001, still present r002, macro r003, income r003, macro r006
- r003: still present (macro r003 #7, income r003)
- r004: still present (income r004)
- r005: still opens on "By sector"; "Targets sum to 0.0%" (income r005)
- r006: still opens "By sector", "Targets sum to 0.0%" (macro r006)
- status: open

### B-023 Simulate and alerts can't answer income or drift questions
- kind: feature · severity: medium
- reported by: income r001, income r003, macro r003, macro r005, macro r006
- evidence: simulate has no income/drift after; no dividend or drift alert kinds
- r003: simulate still shows no income or drift after, buys fractional shares from a dollar amount (income r003 #8); also no beta, volatility or VaR after the trade (macro r003 #6)
- r004: macro learned only after trading that beta went 0.240 → 0.246 (macro r004 #6)
- r005: simulate has no before/after risk; `value_after` counts net cash spent as a value gain (macro r005 #6)
- r006: simulate SELL 6 GLD / BUY 24 IEF returns no risk before/after (computed by hand: vol 6.09→5.67, beta 0.255→0.236, VaR $575→$543); `value_after` drops by the $20.04 cash released (macro r006 #5)
- r007: still no before/after risk; `value_after` drops by exactly the $47.28 the trade frees (macro r007 #8)
- status: open

### B-024 No cash line: targets under 100% produce phantom sells in drift
- kind: feature · severity: medium
- reported by: macro r001, macro r003, macro r006
- r003: 1% held as cash shows as a "targets sum to 99%" warning (macro r003 #7)
- r004: still present (macro r004)
- r005: still open (macro r005, income r005)
- r006: `/drift` warns "targets sum to 99.0%" for a 1% cash target (macro r006)
- status: open

### B-026 Risk, events and the brief take 11–15 s on first load after a trade
- kind: perf · severity: medium
- reported by: income r001, still present r002 (cold `/risk` 17.7 s), income r003, macro r003, income r005, macro r006
- r003: worse — cold `/risk` 33.4 s (income), 18.6 s (macro); brief 6.1 s
- r004: cold `/risk` 24.1 s (macro), 21.5 s (income); cold portfolio fundamentals 26.8 s then all 17 "pending" (income r004 #7)
- r005: cold `/risk` 15.5 s; portfolio fundamentals now 2.2 s (was 26.8 s) (income r005 #8)
- r006: first `/risk` after start 8.26 s (warm 0.64 s) (macro r006)
- r007: first /risk of the session 15.7 s (macro r007 #7) and 24.5 s (income r007 #4); later calls 0.8–3.4 s
- status: open

### B-027 Screener universe isn't built until someone runs a screen (breadth unavailable meanwhile)
- kind: ux · severity: low
- reported by: multibagger r001, multibagger r002 (opening the status didn't start the build)
- r004: still unbuilt ~3 min after start; first screen returned 0 matches without a "building" message (multibagger r004 #6)
- status: open

### B-028 Compare: PEG mostly empty (no fallback to peg_ttm); no growth/margin defaults
- kind: ux · severity: low
- reported by: multibagger r001
- status: open

### B-029 Yield gauge API returns percent-of-yield changes while the page shows bp
- kind: ux · severity: low
- reported by: macro r001, macro r006
- r004: still present (macro r004)
- r005: still open (macro r005)
- r006: 10y 1D still `−0.04` (percent of yield) in the API; card shows "−0 bp" (macro r006 #8)
- status: open

### B-030 Look-through "top stock exposure" lists a money-market fund held by DBC
- kind: ux · severity: low
- reported by: macro r001, macro r003
- r003: AGPXX still #2 single-stock exposure (macro r003)
- status: open

### B-031 Possible quarter shift in BLLN earnings rows (unconfirmed)
- kind: bug · severity: low
- reported by: multibagger r001
- evidence: Q4 2025 EPS actual 0.34 equals SEC Q1 2026 diluted EPS; no Q1 2026 report
- status: open

### B-032 Screener net income is null (not correct) for ~90 companies whose SEC frame value is a proxy-table figure
- kind: bug · severity: medium
- reported by: developer r001 (follow-up to B-005)
- evidence: the frames API serves the latest-filed fact, often the proxy's pay-vs-performance table tagged in
  thousands/millions; after B-005 LOAR, ANET, MDT, FDX, SCHW have no screener P/E, ROE or earnings growth.
  A correct value needs company facts (10-K/10-Q form) or another tag. r002: 185 of 2,726 companies with revenue
  >$100M have null net income, incl. AVGO, ANET, SCHW, IBKR, MDT, BSX (multibagger r002)
- status: open

### B-034 Economic calendar starts on the UTC date: after 8 pm ET that day's releases and actuals disappear
- kind: bug · severity: medium
- reported by: macro r002, macro r003, macro r006
- evidence: at 22:15 ET 10-20, `calendar.all_events` starts 10-21 and the 10-20 housing prints are missing;
  `providers/macro.py::economic_events` uses `date.today()` on a UTC server (rounds/002/investor-macro.md #2)
- r003: still present at 22:13 ET 10-21 (EIA crude draw, 20y auction missing; macro r003 #4)
- r004: third round; 10-22 claims (194K vs 200K) and LEI missing at 22:12 ET; next week's claims row lost "previous" (macro r004 #2)
- r006: at 22:14 ET 10-26 the calendar starts on 10-27 (macro r006)
- status: open

### B-035 Calendar shows no recent actuals or surprise vs consensus; 6 h cache leaves 08:30 actuals blank
- kind: feature · severity: medium
- reported by: macro r002
- r005: still open (macro r005)
- status: open

### B-036 Fear & greed jumps (24.6 → 38.3) when breadth loads; no component count; new-highs scored differently
- kind: ux · severity: medium
- reported by: macro r002, macro r003, macro r005, macro r006
- evidence: 22 highs vs 2 lows reads "Extreme greed" (rounds/002/investor-macro.md #4)
- r003: 27.0 with 5 readings → 39.8 with 7 within minutes; Price strength 86.7 on 26 highs vs 4 lows (macro r003 #5)
- r004: 9.5 → 27.8 when breadth loaded (macro r004 #3)
- r005: fear & greed 7.9 → 25.3 when breadth loads (macro r005 #4)
- r006: 11.7 "Extreme fear" (5 readings) → 25.4 "Fear" (7) when breadth loads (macro r006 #7)
- r007: 16.7 "Extreme fear" with 5 readings, then 29.9 "Fear" with 7 once breadth loads (macro r007 #3)
- status: open

### B-037 Markets has no 10y real yield, breakeven, dollar index or credit spreads
- kind: feature · severity: medium
- reported by: macro r002
- note: only if a free source (e.g. Treasury real yield curve, FRED-free alternatives) is reachable without a key
- status: open

### B-038 The brief has no macro events (next FOMC, major releases this week)
- kind: feature · severity: low
- reported by: macro r002, macro r006
- r006: still no FOMC (10-28) or this week's releases in the brief (macro r006)
- r007: no FOMC in the brief the night before the decision (macro r007 #6)
- status: open

### B-039 VIX and yield cards color a falling VIX/yield red and a yield rise green
- kind: ux · severity: low
- reported by: macro r002, macro r006
- r004: still present (macro r004)
- r005: still open (macro r005)
- r006: 10y card shows "−0 bp" in red for a −0.2 bp move (macro r006 #8)
- status: open

### B-041 Look-through uses Yahoo's top-10 holdings though Argus has full SEC N-PORT holdings
- kind: bug · severity: medium
- reported by: income r002, income r003
- evidence: HD via ETFs shows $0 though SCHD holds 3.36%, VIG 1.43%; N-PORT also has asset classes (B-017)
- r003: HD, O and NEE via ETFs still $0 (income r003)
- status: open

### B-042 Income calendar: next 12 months by pay date
- kind: feature · severity: medium
- reported by: income r002
- evidence: O's 12-30 ex-date counts in 2026 but pays in January; view stops at year-end
- status: open

### B-043 Two dividend yields for one stock (KO 2.74% Finnhub vs 2.27% Argus)
- kind: ux · severity: low
- reported by: income r002, income r003, macro r006
- r003: KO 2.76% vs 2.29% (income r003); see B-063 (payout column)
- r006: IEF 4.14% (/t/IEF, Peers) vs 4.04% (Analysis → Dividends) (macro r006 #6)
- status: open

### B-044 "Where the risk comes from" card drops holdings without saying so (15 of 17)
- kind: ux · severity: low
- reported by: income r002, income r003
- r003: still 15 of 17 (income r003)
- r005: still lists 15 of 17 (income r005)
- status: open

### B-045 Earnings dates disagree on one stock page and drift day to day
- kind: bug · severity: low
- reported by: multibagger r002, multibagger r003, multibagger r005
- evidence: /t/TMDX Events card Nov 4 vs "Next report" Oct 29; `/api/events` (Finnhub) vs `/api/earnings` next
  (Yahoo+Finnhub) differ for KRYS, TOST, HRMY; HRMY announced Nov 4, events say Nov 3
  (rounds/002/investor-multibagger.md #1)
- r003: TMDX events 11-04 vs earnings 10-29; KRYS 11-09 vs 11-02; HRMY now agrees (multibagger r003)
- r004: KRYS 11-02 (earnings) vs 11-09 (events) so it drops out of the 14-day events list; /t/LIF Nov 10 vs Nov 9; TMDX 11-04 vs 11-05 (multibagger r004 #2)
- r005: next dates now agree between `/api/earnings` and `/api/events`; remaining: events and the dashboard show no report timing for HRMY, PODD, LOAR while `/api/earnings` says before the open (multibagger r005 #4)
- r007: /t/IA Events says next report Dec 16, Reported financials says Dec 17 before open (multibagger r007 #7)
- status: open

### B-047 Screener P/E still 1000x when the company has no revenue figure (BANR 12,784)
- kind: bug · severity: medium
- reported by: multibagger r002 (follow-up to B-005)
- evidence: BANR, DX and five others; the B-005 guard needs revenue, so banks/REITs slip through. BANR statements
  also have no revenue (bank: the screener sums net interest + non-interest income, statements don't; developer r002)
- status: open

### B-049 Evening trades are dated the next (UTC) day in positions/transactions/notes but today in performance
- kind: bug · severity: low
- reported by: multibagger r002, income r003, income r006
- evidence: `portfolio.py:338`; same UTC-vs-New-York root as B-034
- r003: new note dated with UTC date (income r003)
- r004: after-close transaction dated 10-23 while performance puts it on 10-22 (macro r004 #5)
- r006: /t/JPM lists a 22:15 ET 10-26 buy as 2026-10-27 while performance puts it on 10-26 (income r006 #4)
- r006 (developer): B-046 (0cdd051) now books after-close trades on the next New York session in Day P&L and performance; `first_opened`, lot and transaction display dates still use the UTC date
- r007: KO bought 22:20 ET 10-27 is dated 2026-10-28 on the stock page and in its note (income r007 #5)
- status: open

### B-050 Dashboard "vs IWM last session" tile disagrees with Performance's IWM 0.00%
- kind: ux · severity: low
- reported by: multibagger r002
- status: open

### B-051 Price-target bar puts the price at "low" when it's below every target
- kind: ux · severity: low
- reported by: multibagger r002, multibagger r003, multibagger r005
- r003: RMBS price still at "low" (multibagger r003)
- r004: still present (multibagger r004)
- r005: still present (multibagger r005)
- status: open

### B-052 Screener filter on valuation percentile vs the company's own 5-year history
- kind: feature · severity: low
- reported by: multibagger r002
- status: open

### B-053 Excess return vs SPY starts the benchmark at the prior close, the portfolio at its fills
- kind: bug · severity: medium
- reported by: macro r003, macro r005, macro r006
- evidence: loop-macro shows −0.42% excess; over the same window (from the buy fills) SPY rose +0.47%, not +0.53%, so the
  true figure is about −0.36% (rounds/003/investor-macro.md #1)
- r004: still present (macro r004)
- r005: still present (macro r005 #9)
- r006: chart starts loop-macro +0.11% vs SPY 0.00% on 10-20; from the SPY fill excess would be +0.67% not +0.62% (macro r006)
- status: open

### B-054 VTIP's December dividend isn't projected (next ex-date blank, rest of 2026 $0)
- kind: bug · severity: medium
- reported by: macro r003, macro r006
- evidence: VTIP paid in December 2024 and 2025; the projection steps 3 months from the last ex-date (10-01) into
  January, missing ~$96–117 from 2026 (rounds/003/investor-macro.md #2; related to B-013)
- r004: still present (macro r004)
- r005: still open (macro r005)
- r006: VTIP still quarterly with no next ex-date, $0 rest of 2026 (macro r006 #6)
- status: open

### B-055 Markets shows nothing about the overnight session after hours (futures, post-market)
- kind: feature · severity: medium
- reported by: macro r003, macro r005, macro r006
- evidence: ES=F −0.46% and SPY −0.47% post-market while Markets shows only the close (rounds/003/investor-macro.md #3)
- r005: see B-016: Sunday-night futures/FX prices shown without a time tag (macro r005 #2)
- r006: see B-016 (macro r006)
- status: open

### B-057 Q4 revenue isn't derived when quarters and the full year use different revenue tags (CRMD)
- kind: bug · severity: medium
- reported by: multibagger r003
- evidence: CRMD Q4 2025 revenue null; should be $128.6M (rounds/003/investor-multibagger.md #3)
- status: open

### B-059 News tone counts articles about other companies (RMBS 6 positive, none about Rambus)
- kind: bug · severity: medium
- reported by: multibagger r003, multibagger r006
- evidence: rounds/003/investor-multibagger.md #5
- r004: still present; RMBS −7.6% day has no sector context (multibagger r004 #7)
- r006: RMBS earnings night scored 10 positive / 0 negative; "…as Shares Slip" scored positive, "Rambus falls…" neutral; five "positive" articles about other companies (multibagger r006 #6)
- r007: brief headlines for XOM are Chevron and Texas Pacific Land stories, KO gets a WPP story (income r007 #6)
- status: open

### B-060 Screener rows have no sector or industry; no sector filter
- kind: feature · severity: medium
- reported by: multibagger r003
- status: open

### B-061 Stock page revenue chart clips its y-axis label (190.24M shows as "90.24M"); stray value label overlaps bars
- kind: ux · severity: low
- reported by: multibagger r003, multibagger r005
- r004: still present (multibagger r004)
- r005: RMBS revenue chart top label still clipped ("|90.24M") (multibagger r005 #7)
- status: open

### B-062 Dashboard Dividends "Payout" (Finnhub) contradicts Argus's own rate ÷ EPS (KO 77.2% vs 63.7%)
- kind: bug · severity: medium
- reported by: income r003
- evidence: JNJ 60.0% vs 81.8% (rounds/003/investor-income.md #2; related to B-043)
- r004: see B-070 (FCF payout ratio)
- r005: still present (Payout O 236.4%, ABBV 189.8%; income r005)
- status: open

### B-063 Dividends footnote "Annual rate = latest payment × payments per year" is wrong since B-010
- kind: ux · severity: low
- reported by: income r003
- evidence: SCHP shows $1.26 (trailing 12 months), not $0.056 × 12; nothing marks which payers use the trailing year
  (rounds/003/investor-income.md #3)
- r004: still present (income r004)
- r005: still present (income r005)
- status: open

### B-064 Dividend growth from Argus's payment history: last raise, 1-year growth, "no raise in 12+ months"
- kind: feature · severity: medium
- reported by: income r003
- status: open

### B-065 XOM statements come from a new filer with two quarters; earlier filer's history isn't joined (unconfirmed)
- kind: bug · severity: low
- reported by: income r003 (lead)
- evidence: "ExxonMobil Holdings Corp", no annual figures, the 2026-06-30 quarter looks like a six-month total
- status: open

### B-067 Risk only uses a 1-year window; no 20/60-day correlation or beta
- kind: feature · severity: medium
- reported by: macro r004, macro r005, macro r006
- evidence: SPY/IEF correlation −0.28 over 20 days vs +0.30 over 1 year (rounds/004/investor-macro.md #4)
- r005: 20-day SPY correlation −0.29 for IEF and +0.54 for GLD vs 1-year +0.30 / +0.36 shown (macro r005 #5)
- r006: book beta 0.25 (1y) vs 0.06 (20d); IEF −0.42, GLD +0.51 over 20 days; window changes the trade size (macro r006 #4)
- r007: `/risk?lookback_days=20` silently ignored; book beta 0.02 (20d), 0.19 (60d), 0.25 (1y) (macro r007 #4)
- status: open

### B-069 PEP has no fiscal-Q4 rows (16-week quarter not derived); capex not read for HD, NEE, PEP, O
- kind: bug · severity: medium
- reported by: income r004, multibagger r005
- evidence: PEP Q4 2025 should be revenue 29.34B, EPS 1.85; HD/NEE/PEP/O FCF still Yahoo (NEE −17.8B) (rounds/004/investor-income.md #3, #6)
- r005: FCF silently falls back to Yahoo for LOAR, TOST, ESE and HRMY because SEC capex is null (multibagger r005 #1)
- status: open

### B-070 Payout ratio on free cash flow
- kind: feature · severity: medium
- reported by: income r004
- evidence: ABBV 190% on earnings vs ~67% on SEC FCF (rounds/004/investor-income.md #5; related to B-062)
- status: open

### B-071 P/E, net margin and ROE include one-off tax benefits with no warning
- kind: feature · severity: medium
- reported by: multibagger r004
- evidence: LIF P/E 24.6 and net margin 25.7% on ~0% operating margin; TMDX shows P/E 13.1, 16.4 and 18.8 in different places (rounds/004/investor-multibagger.md #3)
- r007: DUOL low P/E from a one-off tax gain (multibagger r007 #5)
- status: open

### B-072 Suggested peers are irrelevant (LIF lists bitcoin miners CORZ, CIFR)
- kind: ux · severity: medium
- reported by: multibagger r004
- status: open

### B-073 Fill quarters missing from SEC companyfacts from the filing's own XBRL
- kind: feature · severity: medium
- reported by: developer r004 (follow-up to B-056)
- evidence: KO's 10-Q for 2026-07-03 (filed 07-29, inline XBRL) isn't in companyfacts; NEE and RMBS likewise; parsing each filing's XBRL instance would fill them
- status: open
### B-075 Bitcoin 1D covers only the hours since midnight UTC; its history skips the 10-25 bar
- kind: bug · severity: medium
- reported by: macro r005 (follow-up to B-066), macro r006
- evidence: BTC quote `prev_close` is the 00:00 UTC open, so 1D at 22:15 ET Sunday covers ~2 h (rounds/005/investor-macro.md #1)
- r006: wrong sign: card −0.09% / −0.14% vs about +0.6% over a real 24 h; daily history now skips the 10-26 bar; quote `session_date` 10-26 for a 10-27 02:15 price (macro r006 #1)
- r007: BTC 1D +0.14% vs real 24h +1.6%; daily history skips the 10-27 bar (macro r007 #5)
- status: open

### B-076 Brief "near_52w_extremes" lists every holding
- kind: ux · severity: low
- reported by: macro r005, macro r006, income r006
- evidence: 11 rows for 11 positions (SGOV 0.07% from its high, SPY 2.8% from its high) (rounds/005/investor-macro.md #8)
- r006: loop-macro still lists all 11 holdings; loop-income lists 9 of 17, the two checked are right (macro r006, income r006)
- status: open

### B-077 Asking for BTC-USD returns symbol "BTC.USD"
- kind: bug · severity: low
- reported by: macro r005, macro r006
- evidence: rounds/005/investor-macro.md #10
- r006: still `BTC.USD` (macro r006)
- r007: still `BTC.USD` (macro r007 #5)
- status: open

### B-078 Alerts can't watch an index or yield (^TNX rejected as "not a US ticker")
- kind: feature · severity: medium
- reported by: income r005
- evidence: `argus alert add ^TNX price_above 5.25` → INVALID_SYMBOL while `argus quotes ^TNX` works (rounds/005/investor-income.md #2)
- status: open

### B-079 FCF margin divides SEC FCF by Yahoo revenue from a later window
- kind: bug · severity: low
- reported by: income r005 (related to B-056), multibagger r006
- evidence: KO 25.06% vs 25.49% over the same SEC quarters (rounds/005/investor-income.md #4)
- r006: RMBS FCF margin 41.4% = SEC FCF through Q3 ÷ Yahoo revenue through Q2; 39.3% on one window (multibagger r006 #1)
- r007: RMBS still 41.4% vs 39.3% (multibagger r007 #2); picked together with B-009
- status: done (r007, ce9d74f)

### B-080 Stale-SEC banner says a 10-Q "is due" when it was filed months ago; NEE's fundamentals card has no banner
- kind: ux · severity: low
- reported by: income r005 (follow-up to B-056)
- evidence: KO and NEE filed their 10-Qs; NEE's Yahoo FCF also has no source label (rounds/005/investor-income.md #5)
- status: open

### B-081 Stock page says "Not held in <portfolio>" when another portfolio holds it
- kind: ux · severity: low
- reported by: income r005, multibagger r006
- evidence: /t/KO defaulted to loop-growth, "Not held in loop-growth", while showing the loop-income alert and thesis (rounds/005/investor-income.md #7)
- r006: also shows "Not held in loop-growth" while the position loads, above that position's own buys (multibagger r006 #9)
- status: open

### B-082 Statements lose gross profit / operating income on some quarters (INOD Q1–Q2 2026; KRYS, GRND, TGTX gross profit; ESE op. income; BELFA EPS)
- kind: bug · severity: medium
- reported by: multibagger r005
- evidence: rounds/005/investor-multibagger.md #2
- status: open

### B-083 Momentum periods (Finnhub) contradict the chart's returns on the same page
- kind: bug · severity: high
- reported by: multibagger r005, income r006, multibagger r006, multibagger r007
- evidence: RMBS −7.6% vs −1.8% (rounds/005/investor-multibagger.md #3)
- r006: every Finnhub momentum period disagrees with the chart: JPM 6M +5.9% vs +8.4%, 1Y +12.6% vs +11.2%; RMBS 6M −34.3% vs −43.0%, YTD at the 10-23 close (a session stale); only Argus's own 1 month agrees (income r006 #6, multibagger r006 #7)
- r007: one session stale and missed INOD's −25.3% day: 1 week +8.8% vs −18.7% on the chart, YTD +17.6% vs −12.2% (multibagger r007 #1); severity raised to high
- acceptance: the stock page momentum periods (1W, 1M, 3M, 6M, YTD, 1Y) are computed from Argus's own daily closes including the latest session (or the live price), so they match the chart's returns for the same windows; INOD and RMBS agree with the chart; tests cover period boundaries and YTD
- status: done (r007, 96f181a)

### B-084 ESE and GRND classed as Technology; no warning that healthcare is 47% of the book
- kind: ux · severity: low
- reported by: multibagger r005
- evidence: rounds/005/investor-multibagger.md #6
- status: open

### B-086 Banks: revenue growth +109% and gross margin 0.0% (Finnhub/Yahoo); SEC statements have no bank revenue
- kind: bug · severity: medium
- reported by: income r006
- evidence: /t/JPM revenue growth YoY +109.0%, latest quarter +74.0%, gross margin 0.0%; BAC, C, USB, WFC, PNC similar; JPM tags `RevenuesNetOfInterestExpense`, so statements show "–" for Revenue (rounds/006/investor-income.md #2; related to B-047)
- status: open

### B-087 Accrued dividend labeled "received"; no dividend figure on the Dashboard tiles
- kind: ux · severity: low
- reported by: income r006 (follow-up to B-074)
- evidence: `/dividends` `totals.received 33.759` for PG's unpaid dividend; Analysis legend "Received (est.)"; Dashboard tiles show Realized P&L $0 and no dividends (rounds/006/investor-income.md #7)
- status: open

### B-088 A past earnings report vanishes after an events refresh (MNTN Q2 2026)
- kind: bug · severity: medium
- reported by: multibagger r006
- evidence: `/api/earnings/MNTN` returned the 2026-06-30 report (EPS 0.10 vs 0.1931) and minutes later didn't; `EventsService.refresh` deletes the ±100-day window before re-inserting (rounds/006/investor-multibagger.md #2)
- r007: didn't reproduce: MNTN's Q2 report is back in /api/earnings (multibagger r007)
- status: open

### B-089 Valuation bands include pre-listing or garbage points (MNTN P/S 0.019, P/B 0.020)
- kind: bug · severity: medium
- reported by: multibagger r006
- evidence: MNTN listed 2025-05-22; `psTTM` band has 0.019, 0.032; `pb` has 19 points back to 2021; P/S percentile 80 vs ~67 without them (rounds/006/investor-multibagger.md #4)
- status: open

### B-090 No revenue guidance or segment revenue
- kind: feature · severity: medium
- reported by: multibagger r006
- evidence: RMBS exit rule needs product revenue and guide vs consensus; Argus has total revenue only (rounds/006/investor-multibagger.md #5)
- status: open

### B-091 Economic calendar figures have no unit or period (PCE QoQ annualized read as monthly)
- kind: ux · severity: medium
- reported by: macro r006
- evidence: "Core PCE Prices · Previous 3.30%" on GDP day is QoQ SAAR; same-named Core CPI and Core PPI pairs; footnote says MoM/YoY (rounds/006/investor-macro.md #2; related to the B-002 r002 note)
- status: open

### B-092 ETF pages request SEC financials (502) and show an empty ownership card
- kind: removal · severity: low
- reported by: macro r006
- evidence: /t/IEF: `GET /api/financials/IEF` 502, "Reported financials" card says ETFs have none; Ownership & short all dashes (rounds/006/investor-macro.md #9)
- r007: SCHP page still fires a 502 SEC financials call (macro r007 #9)
- status: open

### B-093 Dividends page ignores announced ex-dates; projections stop at Dec 31
- kind: bug · severity: medium
- reported by: developer r006 (follow-up to B-013), income r005, income r006, income r007
- evidence: Dividends still shows its own estimate when an ex-date is announced: KO ~12-15 vs announced 12-01, NEE ~11-30 vs announced Fri 11-27; projections stop at year end so a window crossing Dec 31 gets no January estimates (JPM/ABBV next ex-date null in 2027); on a stock page "not owed" and the estimate amount are across all portfolios
- r007: /t/KO lists the December dividend twice: announced ex-date 12-01 and an estimated 12-15 for ≈$22.79 (merge only drops estimates within a few days of an announced date); announced ex-dates for O, KO, NEE and the PG 11-16 pay event have no amount (income r007 #1, #3)
- acceptance: an announced ex-date replaces the estimate for the same payment period (no duplicate KO December row on /t/KO, Coming up, brief or Dividends); the Dividends page uses the announced ex-date (KO 12-01, NEE 11-27); announced ex-dates and pay events carry the expected amount; projections continue past Dec 31 for windows that cross the year end; tests cover KO-like 14-day offset
- status: done (r007, 8e14633)

### B-094 Curated economic calendar drops the FOMC press conference, personal income/spending, ECI and Chicago PMI
- kind: bug · severity: medium
- reported by: macro r007
- evidence: the `MAJOR` regex in `backend/argus/services/market_context.py` leaves out the 10-28 14:30 press conference, personal income and spending, ECI and Chicago PMI, yet lets in "Dallas Fed PCE" and "GDP Sales" (rounds/007/investor-macro.md #2; related to B-091)
- status: open

### B-095 P/E isn't price ÷ the EPS shown on the same card (INOD 32.7 vs 34.7, RMBS 39.6 vs 36.7)
- kind: bug · severity: medium
- reported by: multibagger r007
- evidence: valuation bands use the same P/E (rounds/007/investor-multibagger.md #3; related to B-009)
- status: open

### B-096 Nothing on the dashboard or stock page says why a holding fell 25%
- kind: feature · severity: medium
- reported by: multibagger r007
- evidence: INOD −25.3% on 10-27 on layoff reports; the headline is only in the brief API and Research → News at the bottom of the page (rounds/007/investor-multibagger.md #4)
- status: open

### B-097 Peers card takes ~6.4 s on an uncached symbol and still reads "Loading…" after 8–10 s
- kind: perf · severity: low
- reported by: multibagger r007
- status: open

### B-098 Quote open above its high (MNTN open 9.56, high 9.521)
- kind: bug · severity: low
- reported by: multibagger r007
- status: open

### B-099 Ownership "Value" priced at today's close next to the 6-30 filing date
- kind: ux · severity: low
- reported by: multibagger r007
- status: open

### B-100 Returns, volatility, drawdown and beta are price-only and not labeled as such
- kind: feature · severity: medium
- reported by: income r007
- evidence: /t/BND 1Y −5.0%, 5Y −16.6%, Max −5.2% since 2007; with Argus's own trailing dividends 1Y ≈ −1.0% (rounds/007/investor-income.md #2)
- status: open

### B-101 Earnings line "EPS 0.91 vs 0.91 (beat +0.3%)" reads as a contradiction
- kind: ux · severity: low
- reported by: income r007
- evidence: the 0.9071 estimate is rounded to 0.91 (rounds/007/investor-income.md #7)
- status: open

### B-102 "Revenue growth YoY" labeled TTM shows Yahoo's latest-quarter growth when Finnhub has none (BLLN +64.4%)
- kind: bug · severity: low
- reported by: developer r007
- evidence: Yahoo's revenueGrowth is latest-quarter growth; the card labels it trailing 12 months
- status: open

### B-103 TSM revenue in TWD shown as dollars ($4.94T); derived FCF margin suspect
- kind: bug · severity: low
- reported by: developer r007
- status: open

## Done

### B-013 Upcoming dividends disagree across Dividends, Coming up, the brief and events
- kind: bug · severity: medium
- reported by: income r001, income r003, macro r005, income r005, macro r006, income r006
- evidence: Dividends projects ex-dates in the next 14 days but Coming up and `/api/brief` show none; events
  lists an ABBV pay the position isn't entitled to; estimated ex-dates on weekends; JPM/ABBV next ex-date null
  because it falls in 2027 (rounds/001/investor-income.md #4). r002: Dividends estimates PG ex-date Sat 10-24
  while events have the announced Fri 10-23; Coming up shows a JPM pay (Sat 10-31) for a position bought after
  the ex-date (rounds/002/investor-income.md #4)
- reported by (again): income r002
- r003: KO estimated ex-date ~12-15 though the announced ex-date is 12-01 (12-15 is the pay date); PG still Sat 10-24 vs announced 10-23; Coming up still lists the unentitled JPM pay (rounds/003/investor-income.md #4). See also B-054 (VTIP December not projected)
- r004: PG "~Oct 24" (Dividends) vs "Fri Oct 23" (Coming up) on the same page; events still lists the unentitled ABBV 11-16 pay (income r004 #8)
- r005: SGOV/IEF estimated ex-dates Sun 11-01, NEE ~Nov 28 (Sat) vs Fri 11-27 on /t/NEE, KO ~Dec 15 vs Dec 1; Coming up and the brief still list the unentitled JPM 10-31 pay as held (macro r005 #3, income r005 #3)
- r006: sixth sighting. Coming up, `/api/brief` and now /t/JPM list the JPM 10-31 pay as held though every share was bought after the 10-06 ex-date; Coming up and the brief omit the Dividends page's estimated 11-01 ex-dates for BND, VCIT, VGIT, SCHP (loop-income, $131.93) and SGOV, IEF (loop-macro); 11-01 is a Sunday; NEE ~11-28 (Sat) (income r006 #3, macro r006 #6)
- acceptance: this round's slice: (1) a dividend pay event counts as held for a portfolio (Coming up, the brief's `dividends_upcoming`, the stock page's Events card) only if the portfolio held shares on that dividend's ex-date; (2) Coming up and the brief include the estimated ex-dates the Dividends projection puts inside their window, marked as estimates, from the same projection code; (3) an estimated ex-date that falls on a weekend or US market holiday moves to the next business day, the same on Dividends, Coming up and the brief; tests cover each. KO's ex-vs-pay estimate and VTIP (B-054) stay open if not fixed by this
- status: done (r006, f76fbf4); remaining facets moved to B-093

### B-046 After-hours P&L counts shares bought after the close as a gain
- kind: bug · severity: high
- reported by: multibagger r002, income r006, multibagger r006
- evidence: header +$346.88 vs a real after-hours change of +$103.47
- r004: IEF bought after the close shows day P&L −$3.85 and after-hours +$3.85; brief lists it as a top gainer; 10-22 TWR moved 0.191% → 0.184% (macro r004 #5)
- r006: post-close buys at 22:15 ET: HD bought at 317.00 and marked at the 319.38 close adds +$2.38 to "last session" Day P&L and moves gain/TWR (income r006 #4); 25 RMBS bought at the close price changed the header Day % +0.92% → +0.90%, TWR −1.358% → −1.379%, and the brief's RMBS move +5.45% → +4.28% (multibagger r006 #3)
- acceptance: a transaction timestamped after the regular-session close of its New York trading day is next-session money: it doesn't change that session's Day P&L or Day % (header, dashboard, holdings, brief), nor that session's performance-series return or TWR (the flow counts at the start of the next session); its change from fill price to the last price shows only in after-hours P&L; the brief's movers report the stock's own session change for a position not bought during that session; tests cover an after-close buy at the close price and at a different post-market price
- status: done (r006, 0cdd051)

### B-085 Stock page returns 500s on first open: /api/profile and /api/holdings race to insert the same company_profile row
- kind: bug · severity: medium
- reported by: income r006
- evidence: /t/JPM first load: `GET /api/profile/JPM 500` and `GET /api/holdings/JPM 500` with `sqlite3.IntegrityError: UNIQUE constraint failed: company_profile.symbol`; both call `company_profile()` concurrently; works on reload (rounds/006/investor-income.md #1)
- acceptance: opening a stock page whose company profile is missing or stale never returns a 500: concurrent first requests to `/api/profile/<sym>` and `/api/holdings/<sym>` both succeed and leave one `company_profile` row (write it as an upsert or serialize the fetch per symbol); other cache tables written on a read path the same way get the same treatment; a test reproduces the race (two writers for a missing row) and passes
- status: done (r006, 7a9d693)

### B-074 Ex-dividend days don't reconcile: dividends are counted nowhere unless entered by hand
- kind: bug · severity: high
- reported by: income r005
- evidence: PG ex 10-23 ($1.089 × 31 = $33.76): Day P&L −$593.74 (adjusted prev close 164.501) but the performance series fell $627.50 (unadjusted 165.59); `totals.dividends` 0, TWR, drawdown and excess vs SPY treat every ex-date as a loss; only manual `DIVIDEND` transactions count (rounds/005/investor-income.md #1)
- acceptance: dividends a position held through its ex-date (from Argus's own payment history) are accrued automatically, unless a `DIVIDEND` transaction already records that payment (no double counting); they count as income in the performance series (so the ex-date day's change equals Day P&L), in TWR/gain and in `totals.dividends`, labeled as accrued/estimated where shown; tests cover accrual, a position bought after the ex-date (no accrual) and a manual DIVIDEND overriding the accrual
- r006: confirmed: loop-income's 10-26 value change equals Day P&L (income r006)
- status: done (r005, 2ad121f)

### B-068 Sharpe ratio reported from 3 sessions (18.3, 7.13); two volatility figures for one portfolio
- kind: bug · severity: medium
- reported by: macro r004, income r004, income r005, macro r005
- evidence: `/performance` Sharpe 18.3 (loop-macro) and 7.13 (loop-income) while CAGR is hidden for short histories; Dashboard volatility 17.3% vs Analysis 7.5% (rounds/004/investor-income.md #4, investor-macro.md #8)
- r005: Dashboard volatility 16.7% / Sharpe 3.17 from 4 sessions next to Analysis 7.5%; macro Sharpe 0.38 from 4 sessions, vol 1.98% vs 6.12% (income r005 #6, macro r005 #9)
- acceptance: volatility and Sharpe in `/performance` (and the Dashboard card) are null with a reason (e.g. "needs 20 sessions") when the series is shorter than 20 sessions; when shown, the label says what window they cover so they can't be mistaken for Analysis's 1-year risk figure; tests cover the short-series case
- r006: confirmed working (macro, income, multibagger r006)
- status: done (r005, 79aa805)

### B-025 Day % and Day P&L use different bases for positions bought today; brief "losers" include gainers
- kind: bug · severity: low
- reported by: multibagger r001, income r001, macro r003, macro r005, multibagger r005
- evidence: LOAR Day % +1.70% vs Day P&L +$18.27 (0.17% since buy); brief `top_losers` lists VGIT +0.11%
- r003: brief top losers include VTIP 0.00% and SGOV +0.01% (macro r003 #9)
- r004: brief losers list SGOV 0.00% (macro r004 #7)
- r005: brief top_gainers includes IEF −0.16% (macro r005 #7); also seen by multibagger r005
- acceptance: the brief's top_gainers contain only positions with change_pct > 0 and top_losers only < 0 (empty lists allowed); Day % and Day P&L for a position bought today use the same base (the fill price, not the prior close) so they agree in sign; tests cover both
- r006: mover lists confirmed (macro, income, multibagger r006); same-session Day % not checkable with the market closed
- status: done (r005, cb40ff3)

### B-066 Markets "1D" for indexes, futures, FX and crypto uses the wrong prior close
- kind: bug · severity: high
- reported by: income r004, macro r004
- evidence: S&P 500 gauge −0.64% vs real −1.21% (7757.17 → 7663.43 per `/api/history/^GSPC`); Nasdaq 100 −1.80% vs −2.90%; XLU +2.36% vs +2.07% (income r004 #1, suspects `providers/macro.py::closes()` bulk download/`dropna`). After the close WTI +3.72% vs +1.30% quote, gold −3.55% vs −1.27%, USD/JPY −0.78% vs +0.06%, bitcoin −3.18% vs −0.04%: Yahoo's "today" daily bar already holds the overnight price and the settle is gone; bitcoin has no 10-22 bar (macro r004 #1)
- acceptance: every Markets gauge and sector 1D equals (last price − previous session close) ÷ previous session close, matching `/api/history` daily closes for indexes/ETFs and the quote's previous close for futures, FX and crypto, including after the close; no gauge silently skips a session; a unit test with a ragged multi-ticker frame (one ticker missing a day, a 24/7 ticker) covers it
- note: Yahoo daily bars randomly null past closes and hold overnight prices after 6 pm for futures/FX/crypto; 1D now anchors each series on the batch quote's previous close (developer r004)
- status: done (r004, 0f70d37)

### B-056 Statements silently stop when SEC's XBRL feed lacks the latest 10-Q (RMBS ends at Q1 2026)
- kind: bug · severity: high
- reported by: multibagger r003, income r004
- evidence: RMBS Q2 10-Q filed 07-28 isn't in company facts; no gap flag, while Finnhub's +20.4% sits next to SEC's
  +8.1% on the same page (rounds/003/investor-multibagger.md #2)
- r004: KO and NEE statements also stop at Q1 2026 although SEC has KO's Q2 10-Q (filed 07-29) and NEE's Q2/Q3; KO's "SEC" FCF TTM 12.56B is a quarter stale with no period shown (rounds/004/investor-income.md #2)
- acceptance: first find why KO/NEE/RMBS stop at Q1 2026 (missing from company facts, a tag or dedup/form filter in Argus, a stale cache); if Argus drops quarters that SEC serves, fix it so KO and NEE show their Q2 2026 (and NEE Q3) rows; whatever the cause, statements/fundamentals expose the latest period end, and when the latest quarter is more than ~135 days old the API flags it (e.g. `stale_since`/`latest_period`) and the stock page says so next to the SEC figures and FCF TTM states the quarters it covers; tests cover the fix and the flag
- note: SEC's companyfacts feed itself ends at Q1 2026 for KO/NEE/RMBS though the 10-Qs (with XBRL) are filed; Argus drops nothing. Now flagged: `latest_period`, `stale` (>135 days), FCF TTM quarters shown; filling the rows is B-073 (developer r004)
- status: done (r004, eba0140)

### B-048 Analyst consensus "None" when every analyst rates buy; headline rating contradicts the counts beside it
- kind: bug · severity: high
- reported by: multibagger r002, multibagger r003, multibagger r004
- r003: INOD still "none" with 4 buys; GRND now "buy" only because the provider sends a rating (multibagger r003)
- r004: raised to high. The headline rating/mean come from Yahoo while counts and "Ratings by month" bars come from Finnhub: KRYS "Strong Buy 1.25" with 1 strong buy of 12; /t/LIF "Strong Buy · 9 analysts" above bars of 8 buy · 2 hold (rounds/004/investor-multibagger.md #1)
- acceptance: a stock page's analyst consensus label, mean and analyst count come from one source and agree with the buy/hold/sell counts shown beside them (when counts exist, the label and count are derived from them, or the label/mean are shown with their own source and count); a name whose analysts are all buys (INOD 4 buys) shows "Buy"/"Strong buy", never "None"; unit tests cover all-buy counts and a Yahoo-vs-Finnhub mismatch
- note: both feeds were Yahoo (headline key/mean vs monthly counts); label, mean and count now come from the counts, Yahoo headline only as a labeled fallback; target count shown separately (developer r004)
- status: done (r004, 5ec782e)

### B-015 Research valuation bands come back with current: null on first open, and that result is cached
- kind: bug · severity: high
- reported by: multibagger r001, still present r002 (INOD, BCRX), multibagger r003
- evidence: first `/api/research/LOAR` with cold fundamentals → bands `current: null`; stays until `?refresh=true`
- r003: worse — 7 of 8 names researched cold had empty bands and reported growth; for BELFA and BCRX even the first `?refresh=true` returned nulls (BCRX `psTTM current: null` while `/api/fundamentals/BCRX` has `ps_ttm 2.1204`); only a second refresh filled them (rounds/003/investor-multibagger.md #1)
- acceptance: the first `/api/research/<sym>` call (cold caches) returns valuation bands with `current` filled and reported growth filled whenever fundamentals and statements are available (e.g. by awaiting/fetching the fundamentals the bands need instead of using a cold cache), and a result with missing inputs isn't cached as final; a test simulating a cold fundamentals cache covers it
- note: BLLN's empty bands are a separate cause (too few Finnhub ratio-history points; developer r003)
- status: done (r003, 18613fa)

### B-058 Fiscal-Q4 diluted EPS is null in quarterly statements
- kind: bug · severity: medium
- reported by: multibagger r003, income r003
- evidence: `eps_diluted` null for the fiscal-year-end quarter at LOAR, RMBS, GRND, TOST, PODD, KRYS, ESE, KO, JNJ, PG,
  MSFT, HD while net income is filled; `sec_edgar.py:55` marks EPS `additive=False` so Q4 isn't derived
  (rounds/003/investor-multibagger.md #4, investor-income.md #1)
- acceptance: quarterly statements derive fiscal-Q4 diluted EPS when it isn't reported (full-year EPS − the three reported quarters' EPS, or Q4 net income ÷ Q4 diluted shares when the share count is tagged) and mark it derived, so KO, MSFT, LOAR and RMBS have no null EPS in their fiscal-Q4 rows; reported values are unchanged; a unit test with a company-facts fixture covers it
- note: derived values carry `eps_diluted_derived`; can be a cent off when shares move in-year (developer r003)
- status: done (r003, 10a3bb7)

### B-040 Fundamentals `fcf_ttm` is Yahoo's levered FCF: MSFT $16.5B vs $67.0B from SEC quarters
- kind: bug · severity: high
- reported by: income r002, income r003
- evidence: KO $5.2B vs $12.6B; dividends look unfunded (rounds/002/investor-income.md #1)
- r003: still present — KO 5.22B vs 12.56B SEC; MSFT unchanged; NEE −17.77B (income r003 #5)
- acceptance: `fcf_ttm` (fundamentals, stock page "Free cash flow (TTM)" and anything that uses it) is operating cash flow − capex over the last four SEC quarters when Argus has them (falling back to the provider's figure only when SEC data is missing, labeled by source), so MSFT and KO match the sums of the SEC table on the same page; a unit test covers the SEC path and the fallback
- note: NEE still falls back to Yahoo (its capex uses custom tags, so the SEC table has no FCF; developer r003)
- status: done (r003, 8eb7b29)

### B-033 A portfolio's brief lists other portfolios' (and watchlists') earnings, dividends, alerts and theses
- kind: bug · severity: medium
- reported by: macro r002, income r002
- evidence: `argus brief loop-macro --json` (10 ETFs) has earnings for PEGA, VICR, NEE/PG/RMBS (`held: true`), KO,
  USLM and a PG ex-dividend, while `/api/events?portfolio=loop-macro` is empty; the loop-income brief marks RMBS
  (a loop-growth holding) `held: true` and lists already-reported PEGA/VICR as upcoming. `app.py::daily_brief`
  calls `upcoming_events(days_ahead=7, days_back=3)` without the portfolio; alerts and theses aren't scoped
  (rounds/002/investor-macro.md #1, investor-income.md #2)
- acceptance: the brief for portfolio P lists earnings and dividends only for P's holdings (plus, if kept, watchlist
  names marked `held: false`), `held` means held in P, and alerts/theses are limited to P's symbols; events that
  have already happened aren't listed as upcoming; a test with two portfolios covers it
- status: done (r002, 8bb750b)

### B-008 Statements miss revenue tagged RevenueFromContractWithCustomerIncludingAssessedTax (RMBS)
- kind: bug · severity: high
- reported by: multibagger r001, multibagger r002
- evidence: `/api/financials/RMBS` revenue null for all 8 quarters, so research growth and margins are null;
  the screener's REVENUE list includes the tag, `backend/argus/providers/sec_edgar.py:45` doesn't. r002: BCRX and
  BANR too (BCRX statements have no revenue while the screener shows $874.8M)
- acceptance: statements (`/api/financials`) read revenue from `RevenueFromContractWithCustomerIncludingAssessedTax`
  when the other revenue tags have no value for a period, so RMBS and BCRX quarters have revenue and research
  growth/margins are filled; the statement and screener revenue tag lists can't drift apart (shared list or a test
  that checks they match); a unit test with a company-facts fixture using only that tag covers it
- status: done (r002, 1d4ad3f)

### B-010 TIPS ETF income understated: run rate uses one lumpy monthly payment × 12
- kind: bug · severity: high
- reported by: income r001, income r002
- evidence: SCHP `rate 0.672` vs `trailing_12m 1.258`, `irregular: false`; forward income ~$115/yr too low
  (rounds/001/investor-income.md #1); unchanged r002
- acceptance: a monthly payer whose payments vary a lot over the last 12 months (like a TIPS ETF) gets a run
  rate based on the trailing 12 months (or is flagged irregular and uses trailing), so SCHP's annual rate is close
  to its `trailing_12m`; steady payers (e.g. BND, O) keep their current run rate; unit tests cover a lumpy monthly
  payer and a steady one
- status: done (r002, bd921a1)

### B-005 Screener annual figures can be 1000x too small (LOAR P/E 81,740, ESTC earnings growth +99,900%)
- kind: bug · severity: high
- reported by: multibagger r001
- evidence: `POST /api/screener` gives LOAR `net_income: 72146` (company facts: $72.1M), `pe: 81740`; ESTC
  `net_income_prev: 367766` (its FY2026 income ÷ 1000; the prior year was really a loss) → +99,900%. Screens with
  P/E or ROE bounds silently drop these names (rounds/001/investor-multibagger.md #1)
- acceptance: a frame value implausibly small for the company (scaled ~1000x vs revenue / other values) is
  rejected (null) or corrected in the screener's row build, so LOAR's P/E and ESTC's earnings growth aren't
  absurd; a unit test with a ÷1000 frame value covers it; no change to correct rows
- status: done (r001, f459917)

### B-006 Economic calendar dates are one day late and times one hour late after DST ends
- kind: bug · severity: high
- reported by: macro r001
- evidence: `/api/market-context` calendar puts NFP and Michigan on Saturdays, the Fed decision on Oct 29 (FOMC
  ends Oct 28) and Housing Starts on Oct 21 with actuals already in on Oct 20; Nasdaq's date bucket is a day
  ahead and `providers/macro.py::economic_events` stamps the query date. After Nov 1, ISM shows 11:00 and NFP
  09:30 ET (a fixed EDT offset) (rounds/001/investor-macro.md #1, #2)
- acceptance: event dates and `time_et` come from the row's GMT time converted to America/New_York for that
  date (or an equivalent shift), so NFP lands on Fri Nov 6 08:30, ISM 10:00 after DST ends, and the Fed
  decision on the FOMC end date; unit tests cover a pre-DST and a post-DST date and a no-weekend check
- status: done (r001, fcb780c)

### B-007 Performance summary says gain 0 / net invested 0 on a portfolio's first day
- kind: bug · severity: medium
- reported by: macro r001, income r001
- evidence: `/api/portfolios/loop-macro/performance` → `net_invested: 0, gain: 0.0` with `flow_in: 98757.78`
  in the series, while the portfolio shows unrealized −$15.19; dashboard shows "Unrealized P&L −$75" over
  "Gain $0" for loop-income (rounds/001/investor-macro.md, investor-income.md #10)
- acceptance: when the range starts on (or before) the first flow, the start value is taken before that day's
  flows, so day-one `net_invested` equals the cost, `gain` equals value − net invested (matching unrealized P&L)
  and TWR is consistent; a unit test covers a one-day-old portfolio
- status: done (r001, 5ff1aad)


## Won't do

### B-014 XOM earnings listed twice (Oct 23 and Oct 30)
- kind: bug · severity: medium
- reported by: income r001
- evidence: `/api/events` and Coming up show both dates; `/api/earnings/XOM` says Oct 23
- status: won't do: no longer reproduces (r002: provider data changed; events and `/api/earnings/XOM` both say 10-30)

