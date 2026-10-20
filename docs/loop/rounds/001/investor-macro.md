# Round 001: macro investor

## What I did
- **Backdrop** (`GET /api/market-context`, Markets page, 2026-10-20 ~11:20 ET): S&P 7,725 (+0.4% 1D, -1.0% 1W), NDX -3.2% 1W, Russell -5.5% 3M. VIX 17.6, up 19% over 1M. The 10y is at 5.10% (+93 bp YTD). The curve is bear-steepening: 2s10s +38 bp, 10s3m +88 bp, against an inverted front end a year ago. WTI is $96 (+68% YTD), gold is -6% 1M, USD/JPY is 158. Fear & greed is 24-38 (fear). Leadership is defensive plus energy: XLV +6.7% 1M, XLP +6.0%, XLE +51% YTD. Only 4 of 11 sectors are above their 50d average. The calendar shows FOMC on Oct 28, then PCE/GDP and NFP (last print 29K).
- **Regime call:** an inflationary slowdown (stagflation-lite). Rates are high and the long end is selling off, oil shock, labor is weakening, small caps are lagging. My stance: underweight equity beta, tilt defensive/quality, add real-asset hedges, keep duration short.
- **Created `loop-macro`** (benchmark SPY). I ran `simulate_trades` first (`POST /api/portfolios/loop-macro/simulate`), then bought whole shares at the current quote:
  SGOV 179 @ 100.6095, QUAL 53 @ 225.695, XLV 67 @ 179.6401, XLE 148 @ 67.43, SPY 13 @ 769.47, XLP 91 @ 87.76, USMV 78 @ 102.17, VTIP 164 @ 48.6654, GLD 18 @ 379.12, DBC 180 @ 33.375.
  The total cost is $98,757.78.
- **Targets** (symbol level): SGOV 18, QUAL 12, XLV 12, XLE 10, SPY 10, XLP 8, USMV 8, VTIP 8, GLD 7, DBC 6 (99%, with 1% cash). I added a thesis note to each position, with review on 2026-10-29 (after FOMC).
- **Risk check** (`/risk`): beta 0.25, vol 6.1% (vs SPY 12.7%), 95% 1-day VaR 0.56%. I recomputed GLD beta (0.80) and XLE beta (-0.43) from Argus's own `/api/history` closes and they match. The largest position is 18%, below the 25% cap.
- **Cash balance: $1,242.22** (100,000 − 98,757.78). No realized gains.

## Last round's changes
None. This is round 001.

## Findings

### Economic calendar dates are one day late (releases land on Saturdays; Fed decision one day after FOMC)
- kind: bug
- severity: high
- evidence: in `/api/market-context` `calendar.events` and on the Markets page:
  - "Fed Interest Rate Decision" is dated **Thu 2026-10-29 14:00**, but `calendar.fomc` (federalreserve.gov) says the meeting ends **2026-10-28**. The page header says "decision on the last day, 2:00 pm ET".
  - "Michigan Consumer Sentiment" is dated **Sat Oct 24**, and NFP / Unemployment Rate / AHE are dated **Sat Nov 7**.
  - "Housing Starts" is dated **Wed Oct 21** but already shows actuals (-5.2%, 1.221M) at 11:20 ET on Tue Oct 20.
  - Querying Nasdaq directly (`api.nasdaq.com/api/calendar/economicevents?date=2026-11-07`) returns the payrolls rows under that Saturday. So Nasdaq's `date` bucket is one day ahead, and `providers/macro.py::economic_events` stamps rows with the query date unchanged.
- expected: payrolls on Fri Nov 6, the Fed decision on Oct 28, Housing Starts on Oct 20.
- suggestion: shift Nasdaq rows by one day, or derive the date from the row's own timestamp if Nasdaq provides one. Add a sanity check that no release falls on a weekend and that "Fed Interest Rate Decision" matches an FOMC end date. A macro desk plans trades around these dates, so a one-day error is the worst kind of error here.

### Calendar times are off by one hour after DST ends (Nov 1)
- kind: bug
- severity: high
- evidence: before Nov 1, rows show 08:30 / 10:00 (Housing Starts 08:30, Michigan 10:00). From Nov 3 on, ISM shows **11:00**, NFP/Unemployment **09:30** and Michigan (Nov 7) **11:00**. These releases are at 10:00 and 08:30 ET all year. The field is Nasdaq's `gmt`, which appears to use a fixed EDT offset, and Argus labels it `time_et` as-is.
- suggestion: treat Nasdaq times as a fixed UTC-4 offset and convert to America/New_York per date, or apply the known release times. Add a test with a post-DST date.

### Exposure lumps 39% of the book into "Unclassified": no asset-class view
- kind: feature
- severity: high
- evidence: `GET /api/portfolios/loop-macro/exposure` → `by_sector_lookthrough` shows `{"key": "Unclassified", "weight_pct": 39.3}` (SGOV, VTIP, GLD, DBC). `by_type` shows `ETF 100%`. `simulate` shows the same "Unclassified" 39.4%.
- expected: a macro allocator's first question is equity / rates (by duration bucket) / inflation-linked / commodities / gold / cash. Today I can't see that the book is ~50% equity and ~26% T-bills+TIPS without doing the sums by hand.
- suggestion: add an asset-class field per ETF (equity, govt bond, TIPS, commodity, gold, cash-like, crypto), with duration for bond ETFs. Show it as a `by_asset_class` breakdown in exposure and simulate, and allow drift targets at `level=asset_class`. That would let me rebalance at the allocation level, which is how I decide.

### Performance summary says gain 0 and net_invested 0 while the portfolio is down $15
- kind: bug
- severity: medium
- evidence: `GET /api/portfolios/loop-macro/performance` → `summary: {"net_invested": 0, "gain": 0.0, "twr_pct": 0.0, "start_value": 98742.59, "end_value": 98742.59}`. In the same response, the series row shows `flow_in: 98757.78`. `GET /api/portfolios/loop-macro` → `unrealized_pnl: -15.19`, `day_pnl: -15.19`.
- expected: on the first day, start value = 0 (or the cost), net_invested = 98,757.78, gain = -15.19, and TWR = -0.015%.
- suggestion: when the range starts on the first flow day, take the start value before that day's flows.

### Market-context "1D" for a sector reads 0.00% while the live quote moved; no fetched-at time shown
- kind: bug
- severity: medium
- evidence: `/api/market-context` returns XLI `1D: 0.0` (also "0.0%" on the Markets heatmap), and it returned the same value again a few minutes later. Meanwhile `argus quotes XLI` gives 166.77 vs prev 166.68 (+0.05%), and `/api/history/XLI` shows today's bar closing at 166.77. All the other figures on the page were also frozen across both calls (S&P 7,724.62), because of the 15-minute memo in `MacroProvider.closes`. `as_of` is only a date, so I can't tell how stale the intraday values are.
- suggestion: show a fetched-at time ("as of 11:20 ET") on the Markets page and in the API. Alternatively, overlay the cached live quotes on the last bar during the session, as the portfolio page does.

### No cash line: targets below 100% produce phantom sells
- kind: feature
- severity: medium
- evidence: `argus portfolio targets loop-macro symbol ... (sum 99%)` → drift warns "targets sum to 99.0%, not 100%". Every row then shows a small `trade_to_target` sell (SGOV -234.72, XLV -186.77, ...), totalling about -$987, because weights are computed on invested value only. I keep 1% cash on purpose and have to track it by hand ($1,242.22).
- suggestion: add an optional cash balance per portfolio (or a CASH pseudo-symbol that drift and exposure understand). Weights and drift would then include cash, and a 99% target would read as "1% cash".

### Notes are per symbol, not per portfolio; a macro thesis has nowhere to live
- kind: feature
- severity: low
- evidence: `argus note add SYMBOL TEXT --thesis` has no portfolio argument. My regime thesis ("inflationary slowdown, review after FOMC") is a portfolio-level view, so I had to copy pieces of it onto 10 symbols. A SPY note from another investor's portfolio would also mix with mine.
- suggestion: allow `note add --portfolio <name>` with no symbol (portfolio thesis and review date), and filter notes by portfolio.

### The yield gauge shows bp, but the API returns percent-of-yield
- kind: ux
- severity: low
- evidence: `/api/market-context` gauge `^TNX` returns `returns: {"YTD": 22.41, "1M": 1.96}`. These are percentage changes of the yield level, which no rates desk uses. The UI card correctly shows "+93 bp YTD", so the CLI/MCP consumer gets a different and misleading number from the screen.
- suggestion: for `kind: "yield"`, return changes in bp (or add a `changes_bp` field) so the API agrees with the page.

### Markets page on a phone: 9 full-width gauge cards, and the sector and calendar tables are cut off
- kind: ux
- severity: low
- evidence: `scripts/screenshot.py /markets --width 390 --full` → page is 5,418 px tall. The nine gauges stack one per row and fill about the first 1,000 px. The sector heatmap shows only the 1D/1W columns, and the calendar rows clip the Consensus/Previous/Actual columns. On desktop, the yield-curve end labels overlap ("today 5.48%" sits on "1 month ago 5.34%" at 30Y). There is no horizontal page overflow and no errors.
- suggestion: use a 2-column gauge grid at phone width and stack the calendar into two lines per row. Offset the curve end labels, or rely on the legend.

### Look-through "top stock exposure" lists a money-market fund as a stock
- kind: ux
- severity: low
- evidence: `/exposure` → `top_stock_exposure[1]` = `AGPXX "Invesco Shrt-Trm Inv Gov&Agcy Instl"` via DBC, 2.5%. That is the futures collateral, not an equity exposure.
- suggestion: exclude cash/money-market holdings from top stock exposure (they belong in a cash-like asset class, see above).

## Summary for the round lead
1. I ran `loop-macro` as an inflationary-slowdown book: 10 ETFs, $98,757.78 invested, $1,242.22 cash, beta 0.25. The risk numbers match my own recomputation from Argus history.
2. The top bugs are in the economic calendar: dates are one day late (NFP and Michigan on Saturdays, Fed decision a day after FOMC) and times are one hour late after DST ends. The performance summary also says gain 0 while the book is down $15.
3. The main feature gaps: an asset-class exposure view (39% shows as "Unclassified"), cash in drift, and portfolio-level thesis notes.
