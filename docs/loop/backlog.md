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
- reported by: seed (docs/deployment.md, "Should do" #12), macro r001, income r001, multibagger r001, macro r003, income r003, multibagger r003, macro r005, multibagger r005
- evidence: pages were mostly designed and checked at desktop width. r001 at 390 px: Markets is 5,418 px tall
  with one gauge per row and clips the sector and calendar tables; Analysis tables (stress, dividends) and the
  Screener results table clip after the first columns; yield-curve end labels overlap on desktop
  (rounds/001/investor-macro.md, investor-income.md, investor-multibagger.md). r002: at 390 px duplicate calendar
  names (CPI / CPI, Core CPI / Core CPI) can't be told apart because Previous is cut off; name them MoM/YoY
  server-side (rounds/002/investor-macro.md #7)
- r003: phone-width Dashboard holdings table shows only symbol and name (macro r003 #8); Screener filter rows wrap onto two lines (multibagger r003); Dividends/Analysis tables still cut off (income r003)
- r004: Markets at 390 px shows nine full-width gauge cards before fear & greed; Markets tab off-screen in the nav (macro r004 #9)
- r005: stock page peers table and Events row cut off at phone width (multibagger r005)
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
- reported by: multibagger r001, still present r002, multibagger r003, multibagger r005
- evidence: /t/BLLN shows −12.8% (Finnhub `revenue_growth_q_yoy_pct`) above SEC quarters giving +64.4%
- r003: still present (BLLN −12.8% vs SEC +64.4%; multibagger r003)
- r005: still present (BLLN −12.8% vs SEC +64.4%; multibagger r005)
- status: open

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

### B-013 Upcoming dividends disagree across Dividends, Coming up, the brief and events
- kind: bug · severity: medium
- reported by: income r001, income r003, macro r005, income r005
- evidence: Dividends projects ex-dates in the next 14 days but Coming up and `/api/brief` show none; events
  lists an ABBV pay the position isn't entitled to; estimated ex-dates on weekends; JPM/ABBV next ex-date null
  because it falls in 2027 (rounds/001/investor-income.md #4). r002: Dividends estimates PG ex-date Sat 10-24
  while events have the announced Fri 10-23; Coming up shows a JPM pay (Sat 10-31) for a position bought after
  the ex-date (rounds/002/investor-income.md #4)
- reported by (again): income r002
- r003: KO estimated ex-date ~12-15 though the announced ex-date is 12-01 (12-15 is the pay date); PG still Sat 10-24 vs announced 10-23; Coming up still lists the unentitled JPM pay (rounds/003/investor-income.md #4). See also B-054 (VTIP December not projected)
- r004: PG "~Oct 24" (Dividends) vs "Fri Oct 23" (Coming up) on the same page; events still lists the unentitled ABBV 11-16 pay (income r004 #8)
- r005: SGOV/IEF estimated ex-dates Sun 11-01, NEE ~Nov 28 (Sat) vs Fri 11-27 on /t/NEE, KO ~Dec 15 vs Dec 1; Coming up and the brief still list the unentitled JPM 10-31 pay as held (macro r005 #3, income r005 #3)
- status: open

### B-016 Market context figures frozen up to 15 min with no fetched-at time (XLI 1D 0.00%)
- kind: bug · severity: medium
- reported by: macro r001, macro r005
- evidence: XLI `1D: 0.0` while its quote is +0.05%; `as_of` is a date only (rounds/001/investor-macro.md)
- r003: didn't reproduce (sector 1D matched quotes; macro r003)
- r005: weekend Markets header says "as of Fri 4:00 PM ET" while oil, gold, USD/JPY and BTC show Sunday-night prices with no time tag (macro r005 #2; see B-055)
- status: open

### B-017 Asset-class view: bonds, TIPS, gold, commodities and cash show as "Unclassified"; no asset-class targets or duration
- kind: feature · severity: high
- reported by: macro r001, income r001, income r002 (see B-041: SEC N-PORT data has asset classes), macro r003, income r003
- evidence: look-through "Unclassified" 39.3% (loop-macro) and 35.5% (loop-income); `funds_without_profile`
  lists BND/VCIT/VGIT/SCHP; can't check a bond floor or set drift targets by asset class; no rate-shock scenario
- r003: still 39.3% (loop-macro) / 35.5% (loop-income) Unclassified (macro r003, income r003)
- r004: still present (income r004)
- r005: still open (macro r005, income r005)
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
- reported by: multibagger r001, multibagger r003, multibagger r005
- evidence: `fiscal_year: 2025` on 2026-10-20; LOAR +23% CY vs +36–39% latest quarters
- r003: misled a screen — DUOL and ODD topped it on last year's growth but are now decelerating or shrinking (multibagger r003)
- r004: XZO +62% in the screener vs +3% latest SEC quarter; COLL and HIMS likewise (multibagger r004 #4)
- r005: ADMA FY2025 +20% vs +2.0% / −0.3% in the last two quarters; NXT, XZO (multibagger r005 #5)
- status: open

### B-020 Rows missing gross margin silently drop out of a gross-margin filter
- kind: ux · severity: medium
- reported by: multibagger r001
- evidence: APP, KLAC, DAVE, TGTX tag CostOfRevenue, not GrossProfit; no "N excluded" note
- status: open

### B-021 Two unlabeled betas; "SPY falls 10%" scenario understates risk next to the historical replays
- kind: ux · severity: medium
- reported by: income r001, income r003, macro r003
- evidence: SCHD 0.71 (fundamentals) vs 0.22 (1y risk); scenario −1.5% vs replays −14% to −25%
- r003: three unlabeled betas (SPY tile 0.14, factor loading 0.36, stock pages use Finnhub's: XOM −0.67 vs 0.17); "SPY falls 10%" −2.5% vs replays −5.7% to −26.5% (income r003 #9, macro r003)
- status: open

### B-022 Targets & drift card opens on "By sector" when targets are saved by position
- kind: ux · severity: medium
- reported by: income r001, still present r002, macro r003, income r003
- r003: still present (macro r003 #7, income r003)
- r004: still present (income r004)
- r005: still opens on "By sector"; "Targets sum to 0.0%" (income r005)
- status: open

### B-023 Simulate and alerts can't answer income or drift questions
- kind: feature · severity: medium
- reported by: income r001, income r003, macro r003, macro r005
- evidence: simulate has no income/drift after; no dividend or drift alert kinds
- r003: simulate still shows no income or drift after, buys fractional shares from a dollar amount (income r003 #8); also no beta, volatility or VaR after the trade (macro r003 #6)
- r004: macro learned only after trading that beta went 0.240 → 0.246 (macro r004 #6)
- r005: simulate has no before/after risk; `value_after` counts net cash spent as a value gain (macro r005 #6)
- status: open

### B-024 No cash line: targets under 100% produce phantom sells in drift
- kind: feature · severity: medium
- reported by: macro r001, macro r003
- r003: 1% held as cash shows as a "targets sum to 99%" warning (macro r003 #7)
- r004: still present (macro r004)
- r005: still open (macro r005, income r005)
- status: open

### B-025 Day % and Day P&L use different bases for positions bought today; brief "losers" include gainers
- kind: bug · severity: low
- reported by: multibagger r001, income r001, macro r003, macro r005, multibagger r005
- evidence: LOAR Day % +1.70% vs Day P&L +$18.27 (0.17% since buy); brief `top_losers` lists VGIT +0.11%
- r003: brief top losers include VTIP 0.00% and SGOV +0.01% (macro r003 #9)
- r004: brief losers list SGOV 0.00% (macro r004 #7)
- r005: brief top_gainers includes IEF −0.16% (macro r005 #7); also seen by multibagger r005
- acceptance: the brief's top_gainers contain only positions with change_pct > 0 and top_losers only < 0 (empty lists allowed); Day % and Day P&L for a position bought today use the same base (the fill price, not the prior close) so they agree in sign; tests cover both
- status: done (r005, cb40ff3)

### B-026 Risk, events and the brief take 11–15 s on first load after a trade
- kind: perf · severity: medium
- reported by: income r001, still present r002 (cold `/risk` 17.7 s), income r003, macro r003, income r005
- r003: worse — cold `/risk` 33.4 s (income), 18.6 s (macro); brief 6.1 s
- r004: cold `/risk` 24.1 s (macro), 21.5 s (income); cold portfolio fundamentals 26.8 s then all 17 "pending" (income r004 #7)
- r005: cold `/risk` 15.5 s; portfolio fundamentals now 2.2 s (was 26.8 s) (income r005 #8)
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
- reported by: macro r001
- r004: still present (macro r004)
- r005: still open (macro r005)
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
- reported by: macro r002, macro r003
- evidence: at 22:15 ET 10-20, `calendar.all_events` starts 10-21 and the 10-20 housing prints are missing;
  `providers/macro.py::economic_events` uses `date.today()` on a UTC server (rounds/002/investor-macro.md #2)
- r003: still present at 22:13 ET 10-21 (EIA crude draw, 20y auction missing; macro r003 #4)
- r004: third round; 10-22 claims (194K vs 200K) and LEI missing at 22:12 ET; next week's claims row lost "previous" (macro r004 #2)
- status: open

### B-035 Calendar shows no recent actuals or surprise vs consensus; 6 h cache leaves 08:30 actuals blank
- kind: feature · severity: medium
- reported by: macro r002
- r005: still open (macro r005)
- status: open

### B-036 Fear & greed jumps (24.6 → 38.3) when breadth loads; no component count; new-highs scored differently
- kind: ux · severity: medium
- reported by: macro r002, macro r003, macro r005
- evidence: 22 highs vs 2 lows reads "Extreme greed" (rounds/002/investor-macro.md #4)
- r003: 27.0 with 5 readings → 39.8 with 7 within minutes; Price strength 86.7 on 26 highs vs 4 lows (macro r003 #5)
- r004: 9.5 → 27.8 when breadth loaded (macro r004 #3)
- r005: fear & greed 7.9 → 25.3 when breadth loads (macro r005 #4)
- status: open

### B-037 Markets has no 10y real yield, breakeven, dollar index or credit spreads
- kind: feature · severity: medium
- reported by: macro r002
- note: only if a free source (e.g. Treasury real yield curve, FRED-free alternatives) is reachable without a key
- status: open

### B-038 The brief has no macro events (next FOMC, major releases this week)
- kind: feature · severity: low
- reported by: macro r002
- status: open

### B-039 VIX and yield cards color a falling VIX/yield red and a yield rise green
- kind: ux · severity: low
- reported by: macro r002
- r004: still present (macro r004)
- r005: still open (macro r005)
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
- reported by: income r002, income r003
- r003: KO 2.76% vs 2.29% (income r003); see B-063 (payout column)
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
- status: open

### B-046 After-hours P&L counts shares bought after the close as a gain
- kind: bug · severity: medium
- reported by: multibagger r002
- evidence: header +$346.88 vs a real after-hours change of +$103.47
- r004: IEF bought after the close shows day P&L −$3.85 and after-hours +$3.85; brief lists it as a top gainer; 10-22 TWR moved 0.191% → 0.184% (macro r004 #5)
- status: open

### B-047 Screener P/E still 1000x when the company has no revenue figure (BANR 12,784)
- kind: bug · severity: medium
- reported by: multibagger r002 (follow-up to B-005)
- evidence: BANR, DX and five others; the B-005 guard needs revenue, so banks/REITs slip through. BANR statements
  also have no revenue (bank: the screener sums net interest + non-interest income, statements don't; developer r002)
- status: open

### B-049 Evening trades are dated the next (UTC) day in positions/transactions/notes but today in performance
- kind: bug · severity: low
- reported by: multibagger r002, income r003
- evidence: `portfolio.py:338`; same UTC-vs-New-York root as B-034
- r003: new note dated with UTC date (income r003)
- r004: after-close transaction dated 10-23 while performance puts it on 10-22 (macro r004 #5)
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
- reported by: macro r003, macro r005
- evidence: loop-macro shows −0.42% excess; over the same window (from the buy fills) SPY rose +0.47%, not +0.53%, so the
  true figure is about −0.36% (rounds/003/investor-macro.md #1)
- r004: still present (macro r004)
- r005: still present (macro r005 #9)
- status: open

### B-054 VTIP's December dividend isn't projected (next ex-date blank, rest of 2026 $0)
- kind: bug · severity: medium
- reported by: macro r003
- evidence: VTIP paid in December 2024 and 2025; the projection steps 3 months from the last ex-date (10-01) into
  January, missing ~$96–117 from 2026 (rounds/003/investor-macro.md #2; related to B-013)
- r004: still present (macro r004)
- r005: still open (macro r005)
- status: open

### B-055 Markets shows nothing about the overnight session after hours (futures, post-market)
- kind: feature · severity: medium
- reported by: macro r003, macro r005
- evidence: ES=F −0.46% and SPY −0.47% post-market while Markets shows only the close (rounds/003/investor-macro.md #3)
- r005: see B-016: Sunday-night futures/FX prices shown without a time tag (macro r005 #2)
- status: open

### B-057 Q4 revenue isn't derived when quarters and the full year use different revenue tags (CRMD)
- kind: bug · severity: medium
- reported by: multibagger r003
- evidence: CRMD Q4 2025 revenue null; should be $128.6M (rounds/003/investor-multibagger.md #3)
- status: open

### B-059 News tone counts articles about other companies (RMBS 6 positive, none about Rambus)
- kind: bug · severity: medium
- reported by: multibagger r003
- evidence: rounds/003/investor-multibagger.md #5
- r004: still present; RMBS −7.6% day has no sector context (multibagger r004 #7)
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
- reported by: macro r004, macro r005
- evidence: SPY/IEF correlation −0.28 over 20 days vs +0.30 over 1 year (rounds/004/investor-macro.md #4)
- r005: 20-day SPY correlation −0.29 for IEF and +0.54 for GLD vs 1-year +0.30 / +0.36 shown (macro r005 #5)
- status: open

### B-068 Sharpe ratio reported from 3 sessions (18.3, 7.13); two volatility figures for one portfolio
- kind: bug · severity: medium
- reported by: macro r004, income r004, income r005, macro r005
- evidence: `/performance` Sharpe 18.3 (loop-macro) and 7.13 (loop-income) while CAGR is hidden for short histories; Dashboard volatility 17.3% vs Analysis 7.5% (rounds/004/investor-income.md #4, investor-macro.md #8)
- r005: Dashboard volatility 16.7% / Sharpe 3.17 from 4 sessions next to Analysis 7.5%; macro Sharpe 0.38 from 4 sessions, vol 1.98% vs 6.12% (income r005 #6, macro r005 #9)
- acceptance: volatility and Sharpe in `/performance` (and the Dashboard card) are null with a reason (e.g. "needs 20 sessions") when the series is shorter than 20 sessions; when shown, the label says what window they cover so they can't be mistaken for Analysis's 1-year risk figure; tests cover the short-series case
- status: done (r005, 79aa805)

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
### B-074 Ex-dividend days don't reconcile: dividends are counted nowhere unless entered by hand
- kind: bug · severity: high
- reported by: income r005
- evidence: PG ex 10-23 ($1.089 × 31 = $33.76): Day P&L −$593.74 (adjusted prev close 164.501) but the performance series fell $627.50 (unadjusted 165.59); `totals.dividends` 0, TWR, drawdown and excess vs SPY treat every ex-date as a loss; only manual `DIVIDEND` transactions count (rounds/005/investor-income.md #1)
- acceptance: dividends a position held through its ex-date (from Argus's own payment history) are accrued automatically, unless a `DIVIDEND` transaction already records that payment (no double counting); they count as income in the performance series (so the ex-date day's change equals Day P&L), in TWR/gain and in `totals.dividends`, labeled as accrued/estimated where shown; tests cover accrual, a position bought after the ex-date (no accrual) and a manual DIVIDEND overriding the accrual
- status: done (r005, 2ad121f)

### B-075 Bitcoin 1D covers only the hours since midnight UTC; its history skips the 10-25 bar
- kind: bug · severity: medium
- reported by: macro r005 (follow-up to B-066)
- evidence: BTC quote `prev_close` is the 00:00 UTC open, so 1D at 22:15 ET Sunday covers ~2 h (rounds/005/investor-macro.md #1)
- status: open

### B-076 Brief "near_52w_extremes" lists every holding
- kind: ux · severity: low
- reported by: macro r005
- evidence: 11 rows for 11 positions (SGOV 0.07% from its high, SPY 2.8% from its high) (rounds/005/investor-macro.md #8)
- status: open

### B-077 Asking for BTC-USD returns symbol "BTC.USD"
- kind: bug · severity: low
- reported by: macro r005
- evidence: rounds/005/investor-macro.md #10
- status: open

### B-078 Alerts can't watch an index or yield (^TNX rejected as "not a US ticker")
- kind: feature · severity: medium
- reported by: income r005
- evidence: `argus alert add ^TNX price_above 5.25` → INVALID_SYMBOL while `argus quotes ^TNX` works (rounds/005/investor-income.md #2)
- status: open

### B-079 FCF margin divides SEC FCF by Yahoo revenue from a later window
- kind: bug · severity: low
- reported by: income r005 (related to B-056)
- evidence: KO 25.06% vs 25.49% over the same SEC quarters (rounds/005/investor-income.md #4)
- status: open

### B-080 Stale-SEC banner says a 10-Q "is due" when it was filed months ago; NEE's fundamentals card has no banner
- kind: ux · severity: low
- reported by: income r005 (follow-up to B-056)
- evidence: KO and NEE filed their 10-Qs; NEE's Yahoo FCF also has no source label (rounds/005/investor-income.md #5)
- status: open

### B-081 Stock page says "Not held in <portfolio>" when another portfolio holds it
- kind: ux · severity: low
- reported by: income r005
- evidence: /t/KO defaulted to loop-growth, "Not held in loop-growth", while showing the loop-income alert and thesis (rounds/005/investor-income.md #7)
- status: open

### B-082 Statements lose gross profit / operating income on some quarters (INOD Q1–Q2 2026; KRYS, GRND, TGTX gross profit; ESE op. income; BELFA EPS)
- kind: bug · severity: medium
- reported by: multibagger r005
- evidence: rounds/005/investor-multibagger.md #2
- status: open

### B-083 Momentum "1 week" (Finnhub, 4 sessions) contradicts the chart's 5D on the same page
- kind: bug · severity: low
- reported by: multibagger r005
- evidence: RMBS −7.6% vs −1.8% (rounds/005/investor-multibagger.md #3)
- status: open

### B-084 ESE and GRND classed as Technology; no warning that healthcare is 47% of the book
- kind: ux · severity: low
- reported by: multibagger r005
- evidence: rounds/005/investor-multibagger.md #6
- status: open


## Done

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

