# Round 002: macro investor

## What I did
- **Backdrop** (`GET /api/market-context` and the Markets page, 2026-10-20 close, read at 22:15 ET). S&P 7,712.57 (+0.28% 1D, −1.19% 1W), NDX −3.5% 1W, Russell +1.65% 1D but −5.7% 3M. VIX is 17.31 (−6.1% 1D, +16.9% 1M). The 10y is at 5.12%. The curve is still bear-steepening: 2s10s +33 bp, 10s3m +86 bp, and 10y is +95 bp YTD. WTI is $99.06 (−4.4% 1D, +72.5% YTD), gold $4,137 (−6.5% 1M), USD/JPY 158.25. Fear & greed is 38 "Fear" with breadth included. Breadth is 53% of the top 500 above the 50d average and 5/11 sectors above the 50d. Leadership is still defensive plus energy: XLV +6.8% 1M, XLP +6.0%, XLE +52% YTD. Small vs large is −9.3 pp over 3M.
- **New data.** I read the 10-20 prints straight from Nasdaq, because Argus no longer shows them (finding #2). Housing Starts came in at −5.2% vs +1.9% consensus (1.221M vs 1.300M). Pending Home Sales were −7.3% vs −0.7%. NAHB was 29 vs 31. GDPNow is 3.5%. This is a housing-led slowdown with oil still near $100, so the stagflation-lite call is reinforced, not changed.
- **Catalysts** (calendar, checked against bea.gov): FOMC decision Wed 10-28 14:00. GDP advance and Personal Income/PCE Thu 10-29 08:30, which match BEA's schedule. NFP Fri 11-06 08:30. CPI Tue 11-10 08:30.
- **Portfolio check** (`/api/portfolios/loop-macro`, `/drift`, `/risk`). Value is $98,862.66 against $98,757.78 cost, so +$104.88 (+0.11%). The post-market move is −$87.87. Every drift is within ±0.22 pp (band 2 pp). Beta 0.25, vol 6.1% vs SPY 12.7%, 95% 1-day VaR 0.56%. The largest position is SGOV at 18.2%.
- **Decision: no trades.** It's one session after building the book, the regime is unchanged, the data supports the thesis, and drift is negligible. I'll review after FOMC and GDP/PCE (10-28/29), as my notes say.
- **Cross-checks that agree.** I recomputed the XLV, XLE and SPY 1W/1M/3M/YTD/1Y returns from `/api/history/<sym>?period=1y`, and they match the heatmap to 0.01 pp. 2s10s and 10s3m match the curve points. The ^TNX gauge (5.117) matches the curve's 10Y (5.12). The 10y "+95 bp YTD" on the card matches the API's +22.92% of yield. The sectors-above-50d count (5) matches the flags.
- **Cash balance: $1,242.22** (100,000 − 98,757.78). No realized gains, no dividends yet.

## Last round's changes
- **B-006 economic calendar dates/times: works, and it helped.** No weekend dates in the 31 major or 154 total rows. The Fed decision is on 10-28 14:00, the FOMC end date. Michigan is on Fri 10-23 10:00. NFP is on Fri 11-06 08:30. ISM is at 10:00 after DST ends (11-02, 11-04). JOLTS is at 10:00. For the re-check the summary asked for: Mon 10-26 shows Chicago Fed NAI at 08:30 plus bill and 2y auctions, which is plausible. Thu 10-29 shows GDP, PCE, Personal Income/Spending at 08:30, which matches bea.gov ("October 29 8:30 AM: GDP (Advance Estimate), 3rd Quarter 2026; Personal Income and Outlays, September 2026"). Trade Balance on 11-04 08:30 also matches BEA. BLS pages refused the request, so NFP and CPI aren't checked against BLS. A new problem is that the calendar's start day uses UTC (finding #2).
- **B-007 day-one performance: works.** `/performance` shows `net_invested 98,757.78`, `gain 104.88`, which equals `unrealized_pnl 104.88`. `twr_pct 0.1062` equals `unrealized_pct 0.1062`. The benchmark is 0% because it's still day one in ET, as expected. It isn't day two yet, so the "gain = unrealized on day two" re-check has to wait for the next round.
- B-005 (screener) doesn't touch my workflow.

## Findings

### 1. The daily brief for loop-macro lists other portfolios' earnings and dividends, plus all alerts and theses
- kind: bug
- severity: medium
- evidence: `uv run argus brief loop-macro --json`:
  - `earnings_upcoming` holds PEGA, VICR, NEE (`held: true`), PG (`held: true`), RMBS (`held: true`), KO and USLM.
  - `dividends_upcoming` holds a PG ex-dividend on 10-23.
  - loop-macro holds none of these. It is 10 ETFs.
  - `GET /api/events?portfolio=loop-macro` correctly returns `upcoming: []`.
  - Cause: `backend/argus/app.py::daily_brief` calls `self.upcoming_events(days_ahead=7, days_back=3)` without `portfolio=ref`, so it uses every portfolio plus the watchlist. `held` is computed across all portfolios. `alerts_fired` and `theses_due` aren't scoped either.
- expected: the loop-macro brief shows events for loop-macro's holdings only, and `held` refers to this portfolio.
- suggestion: pass `portfolio=ref` to `upcoming_events` in `daily_brief`, compute `held` from that portfolio, and filter alerts and theses to its symbols. Add a test with two portfolios.

### 2. The economic calendar starts on the UTC date, so today's releases and their actuals disappear after 8 pm ET
- kind: bug
- severity: medium
- evidence: at 22:15 ET on Tue 10-20 (02:15 UTC on 10-21), `/api/market-context` `calendar.all_events` starts at **2026-10-21**. The first major event is Thu 10-22 jobless claims.
  - The 10-20 releases are missing: Housing Starts −5.2% vs +1.9% consensus, Building Permits, Pending Home Sales −7.3% vs −0.7%, GDPNow 3.5%. Nasdaq returns all of these, with actuals, under its `date=2026-10-21` bucket.
  - Cause: `providers/macro.py::economic_events` uses `today = date.today()` (the server runs in UTC: `date` → `Wed Oct 21 02:14 UTC`). `market_context` itself passes `datetime.now(NY).date()` to `build`.
- expected: the day boundary in New York time, so a desk reviewing the session that evening sees that day's prints.
- suggestion: use `datetime.now(NY).date()` in `economic_events`, and include the memo key's date so the cache rolls over at NY midnight. Add a test at 23:00 ET.

### 3. The calendar never shows recent actuals or surprises, and actuals can lag a release by up to 6 h
- kind: feature
- severity: medium
- evidence: every major row in `calendar.events` has `actual: null`. The window is today plus 21 days, so yesterday's CPI or payrolls print and its miss or beat are never visible. Even same-day actuals depend on when the memo last refreshed: `economic_events` has `_memo("econ:21", 6 * 3600)`, and `/api/market-context` has no refresh parameter. An 08:30 print can show "—" until 14:30.
- Why it matters: a macro desk positions on the surprise. Today's housing miss (−5.2% vs +1.9%) is the main evidence supporting my slowdown call, and I had to query Nasdaq by hand to see it.
- suggestion: include the last 5 trading days of major releases with actual, consensus and a surprise column (actual − consensus where both parse). Shorten the TTL to about 15 min for today's rows on release days.

### 4. The fear & greed composite moves 14 points depending on whether a background job has finished, with no sign of which components are in
- kind: ux
- severity: medium
- evidence: two `/api/market-context` calls a few minutes apart on the same closes:
  - Before the screener universe was built: `score 24.6 "Extreme fear"`, 5 components, `errors.breadth` set.
  - After: `score 38.3 "Fear"`, 7 components. The added "Price strength" component scores 91.7 "Extreme greed" from 22 highs vs 2 lows.
  - The response and the gauge don't say how many of the 7 components are included.
  - The two breadth components are raw shares (22 of 24 highs/lows gives 92), while the other five are 1-year percentiles. A day with only 4.4% of stocks at new highs therefore scores "Extreme greed".
- suggestion: return `components_used: 5/7` and show it under the gauge ("5 of 7 readings; breadth pending"). Alternatively, hide the composite until all 7 are in. Score price strength as a percentile too, or say in its detail line that it's a share.

### 5. No real-yield, breakeven, dollar-index or credit-spread readings
- kind: feature
- severity: medium
- evidence: `gauges` covers indices, VIX, ^TNX, USD/JPY, WTI, gold and BTC. The curve card shows nominal par yields only. HYG/LQD and VIX3M are fetched for fear & greed but never shown as levels. Nothing shows the 2y yield on its own, the 10y real yield or 10y breakeven, a broad dollar index, or a high-yield spread.
- Why it matters: my VTIP (8%) vs SGOV (18%) split is a bet on breakevens, and gold is a bet on real yields. Today I can't see either. Credit is the first place a slowdown shows up.
- suggestion: add a small "Rates & credit" row with these readings:
  - 2y yield
  - 10y real yield, from treasury.gov's daily real yield curve, the same source as the nominal curve
  - 10y breakeven (nominal − real)
  - DXY (`DX-Y.NYB` on Yahoo)
  - HYG/LQD or HYG/IEF ratio change over 1M/3M

  Changes should be in bp where it's a rate.

### 6. The brief has nothing macro: no FOMC or major releases in the next 7 days
- kind: feature
- severity: low
- evidence: `argus brief loop-macro --json` keys are movers, `near_52w_extremes`, earnings, dividends, alerts, theses, watchlist and headlines. For an ETF-only book, the event sections are (correctly) empty once #1 is fixed, so the brief for 10-21 won't mention that the FOMC is in 7 days or that GDP/PCE is in 8.
- suggestion: add `macro_upcoming`, the major `calendar.events` within 7 days plus the next FOMC date, to the brief for every portfolio. The data is already in `market_context`.

### 7. On a phone, duplicate calendar names (CPI, CPI, Core CPI, Core CPI) can't be told apart
- kind: ux
- severity: low
- evidence: `scripts/screenshot.py /markets --width 390 --full` (5,540 px, no errors, no page overflow). The calendar shows Date, Time and a truncated Event column only. On 11-10 there are two "CPI" and two "Core CPI" rows. The footnote says "'Previous' tells them apart", but Previous is cut off at 390 px. The API has the same ambiguity: `{"event": "CPI", "previous": "0.6%"}` and `{"event": "CPI", "previous": "3.7%"}`. This relates to B-002 (phone layout), but here it's the data label that's ambiguous.
- suggestion: add a `(MoM)`/`(YoY)` or unit suffix to duplicate event names on the server. When a row has a `%` previous, pick YoY if its magnitude is larger than its twin's, or keep Nasdaq's order. Then the name alone is unambiguous on every surface.

### 8. Color semantics on the VIX and yield cards
- kind: ux
- severity: low
- evidence: on the Markets desktop page, VIX "−6.13%" is red and the 10-year "−2 bp" is red, while "+95 bp YTD" is green. A falling VIX and falling yields are risk-on or bond-positive, and a +95 bp sell-off isn't good news. Up/down coloring on these two cards is misleading at a glance.
- suggestion: use neutral (grey) coloring for the VIX and yield gauge changes, or invert them for VIX.

## Summary for the round lead
1. No trades: the regime (stagflation-lite, housing-led slowdown with oil near $99) and the book are unchanged. loop-macro is $98,862.66 (+$104.88), drift is under 0.25 pp, and cash is $1,242.22. B-006 and B-007 verified working (calendar matches bea.gov, and day-one gain = unrealized).
2. Top bugs: the brief for loop-macro shows other portfolios' earnings and dividends (`daily_brief` doesn't pass the portfolio). The calendar uses the UTC date, so that day's releases and actuals vanish after 8 pm ET.
3. Top wishes: recent releases with surprise vs consensus (plus a shorter cache), a fear & greed component count (the score jumps 24.6 → 38.3 when breadth loads), and real yield, breakeven, DXY and credit-spread readings.
