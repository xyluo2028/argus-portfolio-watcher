# Round 011: macro investor

## What I did
- **When.** Mon 11-02 at about 21:15 ET (02:15 UTC 11-03). The market is closed and the latest close is Mon 11-02. Sources:
  - `GET /api/market-context` (1.5 s; `errors` was `{}`, so breadth had already loaded);
  - `argus quotes --json` for ES=F, NQ=F, ^VIX, ^VIX3M, ^TNX, ^IRX, HYG, LQD, TLT, TIP, BZ=F, HG=F, EEM, EFA, SGOV, IEF, GLD, XLE and CL=F;
  - the portfolio endpoints: `/api/portfolios/loop-macro`, `/drift`, `/exposure`, `/dividends`, `/simulate`, `/risk` and `/performance`, plus `/api/brief/loop-macro`;
  - screenshots of Markets (1400 px and 390 px), Analysis, Dashboard and `/t/GLD`.
- **Backdrop on 11-02: oil broke, and growth data beat.**
  - **Indices:** S&P 7,541 (−0.51%), NDX −1.39% and RUT −0.21%.
  - **Sectors:** XLK fell −2.95% and is −12.8% over 1M, below its 50-day average. XLE fell −3.96%. Cyclicals and defensives rose: XLY +2.41%, XLF +1.86%, XLB +1.76%, XLP +1.58% and XLI +1.38%.
  - **Breadth is broadening under a weak cap-weighted tape:**
    - 317 up and 183 down;
    - 64% of stocks are above their 50-day average;
    - 32 new highs against 3 new lows;
    - RSP − SPY is +7.2 pp over 1M.
  - **Oil:** WTI went from 104.12 to 96.46 (−7.4%) and DBC fell −3.42%. The Sunday OPEC meeting is in the calendar.
  - **Gold** settled at 3,969.6 (+1.8%). GLD rose +1.65% while SPY fell.
  - **Rates:** 10Y 4.91% (curve) or 4.894% (^TNX), −3.5 bp. 2Y 4.59% (+3 bp), so 2s10s is +32 bp (was +38) and 10s3m +70 bp. The 3M bill auction cleared at 4.04%.
  - **Volatility:** VIX 21.15 (+8.9%). VIX ÷ VIX3M is 0.98.
  - **Credit was soft:** HYG −0.70% and LQD −0.54%.
  - **Fear & greed:** 25.6 "Fear". Strength (91) and breadth (64) read greed. Volatility, term structure, safe-haven and junk all read extreme fear.
  - **Data:**
    - ISM manufacturing 55.5 vs 54.5 expected, with prices paid 75.2 vs 77.2 and employment 52.4.
    - Atlanta Fed GDPNow 3.7% (was 3.2%). S&P Global manufacturing PMI 54.9.
    - Construction spending −1.9%.
- **Regime:** growth is firming and the oil-led inflation impulse is fading. Leadership is broadening away from megacap tech. That leans away from my late-cycle, sticky-inflation defensive tilt, but one day of oil isn't a regime. Payrolls are Friday 11-06, and the tools I would use to size a change (risk, correlations, performance) are down (finding 1).
- **Book on 11-02:** value **$98,547.21** and cost $98,662.43. Unrealized −$115.22 and realized −$62.27.
  - Day P&L was −$513.81 (−0.52%) against SPY −0.48%. XLE (−$409.96) and DBC (−$207.00) did the damage, and XLP (+$128) and GLD (+$70) offset part of it.
  - Drift is within ±0.55 pp everywhere. The largest are XLV +0.55 and XLP +0.39, against a ±2 pp band.
- **Decision: no trade.**
  - I simulated `SELL 30 XLE` plus `BUY $2,000 RSP`:
    - net cash +$17.50 and realized −$5.40;
    - XLE would go from 10.10% to 8.05%, and RSP would be 2.03%;
    - effective positions would go from 10.16 to 10.50.
  - I staged that as a conditional plan in **note 62** (XLE, review 11-09): do it after NFP if WTI stays below 98 and ISM services prices ease.
  - **Note 63** (GLD): note 56's trigger is the 20-day GLD/SPY correlation, and it can't be tested tonight because there's no price history. GLD moved opposite to SPY today and is about 2% above its 52-week low. I keep the 12 shares.
- **Cash balance: $1,275.30**, unchanged (100,000 − 62.27 realized − 98,662.43 cost).
  - Value plus cash is $99,822.51, a return to date of **−0.18%**. That excludes about $67 of 11-02 ex-dividends on SGOV and IEF that Argus doesn't count (finding 2).

## Last round's changes
- **B-006 (calendar dated and timed by the feed's real clock after DST): works.**
  - ISM is Mon 11-02 at 10:00 with actuals.
  - JOLTS Tue 11-03 10:00, ISM services Wed 11-04 10:00, claims Thu 11-05 08:30, and NFP, AHE and unemployment Fri 11-06 08:30. Michigan is Fri 10:00.
  - Nothing lands on a weekend except Nasdaq's own "OPEC Meeting" on Sun 11-01 at 05:00. I'd keep that row: it explains today's oil move. Saturday's GDPNow row is gone.
  - It helped. This is the first payrolls week whose calendar I could trust without checking the raw feed.
- **B-126 (window starts on the last trading session): works.** On Monday evening, `calendar.events` starts with Fri 10-30 ECI 0.8% vs 0.8%. `all_events` has 20 Friday rows with actuals (Chicago PMI 55.3, rig counts, CFTC), and every 11-02 actual is present. Helped.
- **B-088 (past earnings survive a refresh):** this doesn't touch an ETF book.
- **B-116 (core PCE y/y, ECI):** ECI is shown. There's still no PCE row in the window (next PCE is late November), so that part is unchecked.

## Findings

### 1. Missing price history (known; lead fixing) takes out risk, performance, charts and fundamentals, and blocked my trade trigger
- kind: bug (impact evidence for the known `price_bar.c` NaN bug, not a new item)
- severity: high
- evidence:
  - These calls return HTTP 500 "Internal Server Error":
    - `GET /api/portfolios/loop-macro/risk` (2.5 s) and `/performance` (0.6 s);
    - `/api/history/GLD?period=1y`, `/api/returns/GLD` and `/api/research/GLD`;
    - `/api/fundamentals/GLD`, which needs history although the ETF has no fundamentals.
  - **What I lost:** beta, volatility, VaR and the risk-contribution card. I also lost TWR against SPY (the measure of whether the defensive tilt works), 20-, 60- and 1-year correlations, and the 52-week check for my GLD switch trigger (note 56).
  - **What still works:** drift, exposure, dividends, simulate, the brief and market context (its gauges and sparks come from another path).
  - **The UI shows raw errors:**
    - The Dashboard "Performance vs benchmark" card and the Analysis "Risk" card each print a red "Internal Server Error".
    - `/t/GLD` shows "Internal Server Error" in place of the chart, dashes on every period, and "Valuation & fundamentals: Loading…" forever.
  - **It's all or nothing:** a read-only query of `price_bar` returns **0 rows** for every symbol. One NaN bar for 11-02 cost every symbol its whole year of history, not just the last bar.
  - Yahoo direct (`Ticker('SGOV').history(period='5d', auto_adjust=False)`) shows 10-27 through 10-30 fine and only 11-02 NaN.
- suggestion:
  - Besides skipping or dropping NaN bars, serve the bars already cached when the latest fetch fails, with a "history as of 10-30" note.
  - Have the cards show "Price history unavailable (provider)" rather than the raw 500 text.
  - `/api/fundamentals` for an ETF shouldn't depend on history.
- backlog: the round lead's NaN-bar item

### 2. SGOV and IEF went ex-dividend 11-02: Day P&L counts the dividend, but it's never credited, so about $67 vanishes
- kind: bug
- severity: high (a wrong number; income and total return are understated, and Day P&L doesn't reconcile with value)
- evidence:
  - **Quotes:** `argus quotes SGOV IEF --json` returns SGOV `prev_close 100.401` and IEF `prev_close 91.4485`. Yahoo's unadjusted Friday closes were **100.73** and **91.76**. So Argus uses a dividend-adjusted prior close: SGOV paid about $0.329 and IEF about $0.312.
  - **Day P&L vs value:**
    - Day P&L shows SGOV **+$3.74** and IEF +$4.07. But the value change is 129 × (100.43 − 100.73) = **−$38.70** for SGOV and 79 × (91.50 − 91.76) = −$20.54 for IEF.
    - Portfolio Day P&L is −$513.81. Value went from $99,128.07 on 10-30 to $98,547.21, a change of **−$580.86**.
    - The gap of $67.05 is exactly the two dividends (129 × 0.329 + 79 × 0.3115).
  - **The dividend is credited nowhere:**
    - `/api/portfolios/loop-macro` gives `totals.dividends 0.0` and `dividends_accrued 0`.
    - `/dividends` gives `received 0.0`. SGOV and IEF show `last_ex_date 2026-10-01` and `next_ex_date_est 2026-12-01`.
    - The Analysis page reads "2026 so far (est.) $0.00", and the Nov bar is empty.
    - Last round projected exactly these: an 11-02 ex-date for $38.83 + $24.25. The estimated event dropped out of "projected" when its date passed and never moved into "received".
  - **Cause:** Yahoo's `.dividends` series doesn't list 11-02 yet. Argus's `dividend_history` row was refreshed at 02:13 UTC, and its last row is 2026-10-01. The 11-02 bar is the NaN bar.
  - So Argus prices the ex-date (adjusted prev close) but books the income only once Yahoo's dividend list catches up, and it won't refetch for 24 hours.
- suggestion:
  - When `prev_close` from the quote is below the stored last close by about the expected per-share amount on an estimated ex-date, or the ex-date simply passes, count the estimated dividend as "accrued (est.)" until the provider confirms it. Don't let it vanish.
  - At minimum, keep a passed estimated ex-date in the projection, marked "unconfirmed".
- backlog: related to B-074 and B-087 (new symptom)

### 3. On a weekday evening Markets hides the session: WTI card says −0.20% on the day oil fell 7.4%
- kind: bug / ux
- severity: medium-high (re-sighting of B-016 / B-055, now on a weekday, with a large miss)
- evidence:
  - Markets cards under "Market closed as of Mon, Nov 2, 4:00 PM ET":
    - "WTI crude oil $96.27 **−0.20%**": the session was 104.12 → 96.46, **−7.4%**;
    - "Gold $3,953 **−0.41%**": the session was 3,898.9 → 3,969.6, **+1.8%**;
    - "Bitcoin +0.27%".
  - The API sparks confirm it: `CL=F [..., 104.12, 96.46, 96.26]` and `returns.1D −0.21`. So 1D is the overnight tick since the 11-02 settle.
  - The day's biggest macro move (oil, which drove my −$617 in XLE and DBC) can't be seen on the macro page. I had to read the spark arrays.
  - In the same response, `ES=F` has `prev_close 7614`, so its −0.45% looks like the full session. Futures and commodities use different change bases.
- suggestion: B-016 / B-055. For futures, FX and crypto, show the last session's settle-to-settle change as the main 1D, plus a small "since settle" line for the overnight.
- backlog: B-016, B-055

### 4. A passed ex-date (or any provider gap) leaves no flag anywhere; the brief's dividends section is empty on an ex-day
- kind: ux
- severity: medium
- evidence: `/api/brief/loop-macro` → `dividends_upcoming: []`, on the day two holdings went ex. Nothing in the brief, Dashboard or Analysis says "SGOV, IEF ex-dividend today" (see finding 2).
- suggestion: add `dividends_recent` (ex-dates in the last session, est. or confirmed) to the brief.
- backlog: B-013 area, new symptom

### 5. The dollar index can't be quoted: `DX-Y.NYB` becomes "DX.Y.NYB" and errors
- kind: bug / feature
- severity: medium (the dollar is one of the core macro inputs, and it's missing from Markets too)
- evidence: `argus quotes DX-Y.NYB --json` → `errors: {"DX.Y.NYB": "unknown symbol or no provider returned a quote"}`. The hyphen is rewritten the same way as BTC-USD → BTC.USD.
- suggestion: B-077 / B-037. Pass Yahoo index and FX symbols through unchanged, and add a DXY card (or UUP) to Markets.
- backlog: B-077, B-037

### 6. `/?p=loop-macro` still opens loop-growth; the Analysis drift card still opens "By sector"
- kind: ux
- severity: low (re-sighting)
- evidence:
  - `scripts/screenshot.py "/?p=loop-macro"` rendered loop-growth. I again had to set `localStorage['argus.portfolio']` in my own script.
  - Analysis "Targets & drift" opens "By sector" with an empty "ETF 100%" row and "Targets sum to 0.0%", although 11 position targets are saved (`/drift` shows `targets_sum_pct 99`).
- backlog: B-118, B-022

### 7. Theses due lists 17 items, including notes reviewed in a week
- kind: ux
- severity: low (re-sighting)
- evidence:
  - `/api/brief/loop-macro` → `theses_due` has 17 rows. They include note 57 (review 11-09) and thesis 54 (11-06), because the lookahead is `today + 7 days`. Old theses 21 and 22 (10-29) remain beside the notes that superseded them.
  - The list doesn't say which rows are overdue and which are upcoming.
- suggestion: split it into `overdue` and `due_this_week`, and let a newer note on the same symbol supersede the older review (B-127).
- backlog: B-127

### 8. What a macro desk still wants on one screen
- kind: feature
- severity: low
- evidence: tonight I had to use the CLI for HYG/LQD (credit), the VIX3M ratio, futures (ES −0.45%, NQ −1.0%), the dollar index (not available) and GDPNow (only in `all_events`, not the curated list). Markets also has no per-period numbers for cross-asset sleeves (bonds, credit, commodities).
- suggestion: B-037 and B-055. Add a compact cross-asset strip: DXY, HYG−LQD, TIP−IEF (breakeven proxy), ES/NQ, and GDPNow beside the calendar.
- backlog: B-037, B-055

## Consistency checks that passed
- **Day P&L:** portfolio Day P&L −$513.81 equals the sum of the position Day P&Ls, and the brief's totals agree. The exception is the dividend gap in finding 2.
- **Simulate:** value_after $98,529.71 = value_before $98,547.21 − net cash $17.50.
- **Spreads:** 2s10s +32 bp and 10s3m +70 bp agree with the curve points (4.91 − 4.59 and 4.91 − 4.21). The 10Y card (4.89%) and the curve (4.91%) agree within the source difference.
- **Fear & greed:** term structure 0.98 matches VIX 21.15 ÷ VIX3M 21.6 from `argus quotes`. All 7 components were present, and the page says so.
- **Benchmark:** the brief's SPY −0.479% matches the S&P gauge (−0.51%) within the ETF/index difference.
- **Phone:** Markets at 390 px has no horizontal overflow and no page errors.

## Summary for the round lead
1. No trade. Oil −7.4%, ISM beat with easing prices, and breadth is broadening. I staged XLE 10→8% into RSP after NFP (note 62) and recorded that GLD's trigger is untestable (note 63). loop-macro is $98,547.21, cash $1,275.30, −0.18% to date.
2. High: SGOV and IEF went ex-dividend 11-02. Day P&L uses Yahoo's dividend-adjusted prev close, but the ~$67 of dividends is credited nowhere. Day P&L (−$513.81) misses the value change (−$580.86) by exactly that amount, and the estimated ex-dates vanished from projections.
3. Missing history (known) takes out risk, performance, correlations, charts and ETF fundamentals with raw "Internal Server Error" cards. `price_bar` holds 0 rows, so one NaN bar cost a whole year. Markets' WTI card shows −0.20% on a −7.4% oil day (B-016/B-055). B-006 and B-126 work.
