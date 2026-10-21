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
- reported by: seed (docs/deployment.md, "Should do" #12), macro r001, income r001, multibagger r001
- evidence: pages were mostly designed and checked at desktop width. r001 at 390 px: Markets is 5,418 px tall
  with one gauge per row and clips the sector and calendar tables; Analysis tables (stress, dividends) and the
  Screener results table clip after the first columns; yield-curve end labels overlap on desktop
  (rounds/001/investor-macro.md, investor-income.md, investor-multibagger.md). r002: at 390 px duplicate calendar
  names (CPI / CPI, Core CPI / Core CPI) can't be told apart because Previous is cut off; name them MoM/YoY
  server-side (rounds/002/investor-macro.md #7)
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
- reported by: multibagger r001, still present r002
- evidence: /t/BLLN shows −12.8% (Finnhub `revenue_growth_q_yoy_pct`) above SEC quarters giving +64.4%
- status: open

### B-011 VICR Q3 2025 revenue $407.7M: a mis-dated 10-K fact beats the 10-Q's $110.4M
- kind: bug · severity: medium
- reported by: multibagger r001
- evidence: `/api/financials/VICR` 2025-09-30 revenue 407,701,000; research shows +338% y/y
- status: open

### B-012 Analysis "Stocks / ETFs" tile prints the values in weight order under a fixed label
- kind: bug · severity: medium
- reported by: income r001, still present r002
- evidence: shows 51% / 49% while stocks are 49.4%, ETFs 50.6%; `frontend/src/pages/Analysis.tsx:23-25`
- status: open

### B-013 Upcoming dividends disagree across Dividends, Coming up, the brief and events
- kind: bug · severity: medium
- reported by: income r001
- evidence: Dividends projects ex-dates in the next 14 days but Coming up and `/api/brief` show none; events
  lists an ABBV pay the position isn't entitled to; estimated ex-dates on weekends; JPM/ABBV next ex-date null
  because it falls in 2027 (rounds/001/investor-income.md #4). r002: Dividends estimates PG ex-date Sat 10-24
  while events have the announced Fri 10-23; Coming up shows a JPM pay (Sat 10-31) for a position bought after
  the ex-date (rounds/002/investor-income.md #4)
- reported by (again): income r002
- status: open

### B-015 Research valuation bands come back with current: null on first open, and that result is cached
- kind: bug · severity: medium
- reported by: multibagger r001, still present r002 (INOD, BCRX)
- evidence: first `/api/research/LOAR` with cold fundamentals → bands `current: null`; stays until `?refresh=true`
- status: open

### B-016 Market context figures frozen up to 15 min with no fetched-at time (XLI 1D 0.00%)
- kind: bug · severity: medium
- reported by: macro r001
- evidence: XLI `1D: 0.0` while its quote is +0.05%; `as_of` is a date only (rounds/001/investor-macro.md)
- status: open

### B-017 Asset-class view: bonds, TIPS, gold, commodities and cash show as "Unclassified"; no asset-class targets or duration
- kind: feature · severity: high
- reported by: macro r001, income r001, income r002 (see B-041: SEC N-PORT data has asset classes)
- evidence: look-through "Unclassified" 39.3% (loop-macro) and 35.5% (loop-income); `funds_without_profile`
  lists BND/VCIT/VGIT/SCHP; can't check a bond floor or set drift targets by asset class; no rate-shock scenario
- status: open

### B-018 Notes (and cost alerts) aren't tied to a portfolio
- kind: feature · severity: medium
- reported by: macro r001, income r001, multibagger r001
- evidence: `note add` has no portfolio; theses for the same symbol mix across portfolios; no portfolio-level
  thesis; `below_cost_pct` uses cost averaged across portfolios
- status: open

### B-019 Screener has only the last calendar year: no TTM or latest-quarter growth
- kind: feature · severity: medium
- reported by: multibagger r001
- evidence: `fiscal_year: 2025` on 2026-10-20; LOAR +23% CY vs +36–39% latest quarters
- status: open

### B-020 Rows missing gross margin silently drop out of a gross-margin filter
- kind: ux · severity: medium
- reported by: multibagger r001
- evidence: APP, KLAC, DAVE, TGTX tag CostOfRevenue, not GrossProfit; no "N excluded" note
- status: open

### B-021 Two unlabeled betas; "SPY falls 10%" scenario understates risk next to the historical replays
- kind: ux · severity: medium
- reported by: income r001
- evidence: SCHD 0.71 (fundamentals) vs 0.22 (1y risk); scenario −1.5% vs replays −14% to −25%
- status: open

### B-022 Targets & drift card opens on "By sector" when targets are saved by position
- kind: ux · severity: medium
- reported by: income r001, still present r002
- status: open

### B-023 Simulate and alerts can't answer income or drift questions
- kind: feature · severity: medium
- reported by: income r001
- evidence: simulate has no income/drift after; no dividend or drift alert kinds
- status: open

### B-024 No cash line: targets under 100% produce phantom sells in drift
- kind: feature · severity: medium
- reported by: macro r001
- status: open

### B-025 Day % and Day P&L use different bases for positions bought today; brief "losers" include gainers
- kind: bug · severity: low
- reported by: multibagger r001, income r001
- evidence: LOAR Day % +1.70% vs Day P&L +$18.27 (0.17% since buy); brief `top_losers` lists VGIT +0.11%
- status: open

### B-026 Risk, events and the brief take 11–15 s on first load after a trade
- kind: perf · severity: low
- reported by: income r001, still present r002 (cold `/risk` 17.7 s)
- status: open

### B-027 Screener universe isn't built until someone runs a screen (breadth unavailable meanwhile)
- kind: ux · severity: low
- reported by: multibagger r001, multibagger r002 (opening the status didn't start the build)
- status: open

### B-028 Compare: PEG mostly empty (no fallback to peg_ttm); no growth/margin defaults
- kind: ux · severity: low
- reported by: multibagger r001
- status: open

### B-029 Yield gauge API returns percent-of-yield changes while the page shows bp
- kind: ux · severity: low
- reported by: macro r001
- status: open

### B-030 Look-through "top stock exposure" lists a money-market fund held by DBC
- kind: ux · severity: low
- reported by: macro r001
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
- reported by: macro r002
- evidence: at 22:15 ET 10-20, `calendar.all_events` starts 10-21 and the 10-20 housing prints are missing;
  `providers/macro.py::economic_events` uses `date.today()` on a UTC server (rounds/002/investor-macro.md #2)
- status: open

### B-035 Calendar shows no recent actuals or surprise vs consensus; 6 h cache leaves 08:30 actuals blank
- kind: feature · severity: medium
- reported by: macro r002
- status: open

### B-036 Fear & greed jumps (24.6 → 38.3) when breadth loads; no component count; new-highs scored differently
- kind: ux · severity: medium
- reported by: macro r002
- evidence: 22 highs vs 2 lows reads "Extreme greed" (rounds/002/investor-macro.md #4)
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
- status: open

### B-040 Fundamentals `fcf_ttm` is Yahoo's levered FCF: MSFT $16.5B vs $67.0B from SEC quarters
- kind: bug · severity: high
- reported by: income r002
- evidence: KO $5.2B vs $12.6B; dividends look unfunded (rounds/002/investor-income.md #1)
- status: open

### B-041 Look-through uses Yahoo's top-10 holdings though Argus has full SEC N-PORT holdings
- kind: bug · severity: medium
- reported by: income r002
- evidence: HD via ETFs shows $0 though SCHD holds 3.36%, VIG 1.43%; N-PORT also has asset classes (B-017)
- status: open

### B-042 Income calendar: next 12 months by pay date
- kind: feature · severity: medium
- reported by: income r002
- evidence: O's 12-30 ex-date counts in 2026 but pays in January; view stops at year-end
- status: open

### B-043 Two dividend yields for one stock (KO 2.74% Finnhub vs 2.27% Argus)
- kind: ux · severity: low
- reported by: income r002
- status: open

### B-044 "Where the risk comes from" card drops holdings without saying so (15 of 17)
- kind: ux · severity: low
- reported by: income r002
- status: open

### B-045 Earnings dates disagree on one stock page and drift day to day
- kind: bug · severity: high
- reported by: multibagger r002
- evidence: /t/TMDX Events card Nov 4 vs "Next report" Oct 29; `/api/events` (Finnhub) vs `/api/earnings` next
  (Yahoo+Finnhub) differ for KRYS, TOST, HRMY; HRMY announced Nov 4, events say Nov 3
  (rounds/002/investor-multibagger.md #1)
- status: open

### B-046 After-hours P&L counts shares bought after the close as a gain
- kind: bug · severity: medium
- reported by: multibagger r002
- evidence: header +$346.88 vs a real after-hours change of +$103.47
- status: open

### B-047 Screener P/E still 1000x when the company has no revenue figure (BANR 12,784)
- kind: bug · severity: medium
- reported by: multibagger r002 (follow-up to B-005)
- evidence: BANR, DX and five others; the B-005 guard needs revenue, so banks/REITs slip through. BANR statements
  also have no revenue (bank: the screener sums net interest + non-interest income, statements don't; developer r002)
- status: open

### B-048 Analyst consensus "None" when every analyst rates buy (GRND 5 buys, INOD 4)
- kind: bug · severity: medium
- reported by: multibagger r002
- status: open

### B-049 Evening trades are dated the next (UTC) day in positions/transactions/notes but today in performance
- kind: bug · severity: low
- reported by: multibagger r002
- evidence: `portfolio.py:338`; same UTC-vs-New-York root as B-034
- status: open

### B-050 Dashboard "vs IWM last session" tile disagrees with Performance's IWM 0.00%
- kind: ux · severity: low
- reported by: multibagger r002
- status: open

### B-051 Price-target bar puts the price at "low" when it's below every target
- kind: ux · severity: low
- reported by: multibagger r002
- status: open

### B-052 Screener filter on valuation percentile vs the company's own 5-year history
- kind: feature · severity: low
- reported by: multibagger r002
- status: open


## Done

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

