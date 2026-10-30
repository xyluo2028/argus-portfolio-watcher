# Round 009: macro investor

## What I did
- **Backdrop.** I read it at about 22:14 ET on Thu 10-29 (02:14 UTC 10-30), after the close. Sources: `GET /api/market-context` (before and after breadth loaded), `argus quotes --json`, `/api/history` (2y daily for 14 ETFs, 5d for CL=F, GC=F and BTC-USD), `/api/portfolios/loop-macro/{risk,drift,performance,dividends,simulate}`, `/api/brief/loop-macro`, and screenshots of Markets (full page, 1400 px and 390 px) and the loop-macro Dashboard.
  - **Indices:** S&P 7,720.39 (−0.30%), NDX −1.38%, Russell +1.01%. Breadth was strong under a weak index: 376 up, 124 down, and RSP − SPY +4.4 pp over 1M. Leaders were XLV +2.4%, XLRE +2.2%, XLP +1.5% and XLU +1.5%. Laggards were XLC −1.9% and XLK −1.2%.
  - **Overnight:** ES=F −1.10%, NQ=F −2.41% and QQQ post-market −1.54%, after megacap reports.
  - **Rates:** 10Y 4.99% (−6 bp) and 2Y 4.61%, so 2s10s is +37 bp and 10s3m +80 bp. Over the month the 10Y is down 27 bp.
  - **Data:** PCE and GDP came out at 08:30. I read them from Nasdaq directly, because Argus's calendar had lost the day (finding 1).
    - Core PCE price index 0.3% m/m and 3.1% y/y, both in line.
    - Q3 core PCE prices 2.50% against 2.40% expected. GDP 3.4% against 3.2%. Claims 194K.
  - **Commodities, FX, crypto:** WTI 104.5 overnight (10-29 settle 102.00), gold 4,018, USD/JPY 157.5, BTC 76.8k.
  - **Volatility:** VIX 17.2, and VIX ÷ VIX3M is 0.89.
  - **Credit and havens:** over 20 days, stocks vs Treasuries (SPY − TLT) is −4.2 pp and junk vs IG −1.3 pp. I recomputed both from `/api/history` (−4.16 / −1.26) and they match.
- **Correlations with SPY,** computed from Argus history:

  | | 20 days | 60 days | 1 year |
  |---|---|---|---|
  | IEF | **−0.49** | +0.25 | +0.29 |
  | GLD | **+0.60** | +0.49 | +0.38 |

  Before the trade, Argus's book beta was 0.247 and volatility 6.13%. Mine were 0.247 and 6.13%, so they match.
- **Regime:** a late-cycle rotation into defensives with a sticky-inflation backdrop.
  - Growth is fine: GDP 3.4%.
  - Core inflation is 3.1% y/y, but it isn't accelerating.
  - The long end rallied on the data, and bonds still hedge equities over 20 days while gold doesn't.
- **Decision: I executed the staged switch from note 51.** Its stop needed both "core PCE beat" *and* "10Y > 5.15%". The 10Y fell to 4.99%, so the stop didn't trigger.
  - Simulated first with `POST /simulate`: net cash +$21.42, realized −$63.30. Weights go GLD 6.7% → 4.5% and IEF 5.1% → 7.3%.
  - Traded at the 4 pm closes: **SELL 6 GLD @ 368.57** (txn 46) and **BUY 24 IEF @ 91.25** (txn 47).
  - Targets changed from GLD 7 / IEF 5 to **GLD 4.5 / IEF 7.5**. Everything else is unchanged, with 1% cash.
  - Thesis note **54** (IEF, review 11-06), with the stop at a 10Y above 5.25%.
  - After the trade, `/risk` gives volatility 5.83% and beta 0.231. My own calculation gives 5.83% and 0.231, so they match.
- **Portfolio after the trade:** 11 positions, value $99,188.69, cost $98,662.43, unrealized +$526.26, realized −$62.27.
  - Performance gives TWR +0.48% since 10-20, against SPY +0.04%.
  - Drift is within ±0.43 pp everywhere (XLV +0.43 is the largest).
- **Cash balance: $1,275.30** (100,000 − 62.27 realized − 98,662.43 cost). The total is $100,463.99, a return to date of **+0.46%**.
- **Coming up:** IEF ($24.25 est.) and SGOV ($38.83 est.) go ex on Mon 11-02.

## Last round's changes
- **B-034, calendar on the New York date: broken in practice.**
  - The code does start the window on New York's date. But at 22:14 ET on 10-29, the served calendar starts on **Fri 10-30**, and today's PCE, GDP and claims, with their actuals, are gone again. Finding 1 has the cause.
  - It didn't help tonight. I had to query Nasdaq by hand to check note 51's stop condition.
- **B-104 (valuation card) and B-095 (P/E):** don't apply to my ETF book.
- **Re-checks:**
  - B-046 (after-close buys count from the next session) works for my IEF buy: its Day P&L is still 55 × 0.40 = $22.00.
  - The sell side doesn't work (finding 3).
  - `/risk` took 1.07 s before the trade and 1.09 s after it (B-026), so it's fast tonight.

## Findings

### 1. On PCE night the calendar again drops the day's releases and actuals: Nasdaq's day mapping flips, and Argus keeps no rows it has already seen
- kind: bug
- severity: high (the second key macro day in a row lost on its own evening, after the B-034 fix)
- evidence:
  - At 02:14 UTC (22:14 ET 10-29), `GET /api/market-context` returned `calendar.events[0]` = "2026-10-30 18:30 Dallas Fed PCE". The `all_events` list also starts on 10-30. There's nothing for 10-29: no PCE, GDP or claims. The Markets page shows the same thing, with "Fri, Oct 30" as its first row.
  - At 02:15 UTC, a fresh `MacroProvider().economic_events(21)` outside the server returned **23 rows on 10-29** with actuals. For example, "Core PCE Price Index 3.1% / cons 3.1%" and "GDP 3.4% / 3.2%".
  - At 02:21 UTC, the same call returned no 10-29 rows. The raw Nasdaq answers had changed in those six minutes:
    - At 02:15, `date=10-29` and `date=10-30` both returned the 10-29 (PCE/GDP) rows.
    - At 02:21, `date=10-29` returned 10-28's rows ("MBA 30-Year Mortgage Rate"…), `10-30` and `10-31` both returned 10-30's rows ("Employment Benefits"…), and the PCE/GDP rows were returned by **no** query.
  - `_nasdaq_days` infers each answer's day from whether the next query repeats it. So when Nasdaq's mapping flips, a whole day is either placed on yesterday (and filtered out) or never returned. The server's cached result, kept for 6 h, is the dropped version.
  - FOMC day showed the same symptom last round (in round 008 the 10-28 rows were also missing from every query).
- suggestion: keep what has been seen. Persist each release row by (release date, time, name), with its actual once it has one, and merge new fetches into it rather than replacing it. Always show today's and yesterday's stored rows. A day that vanishes from Nasdaq then can't drop out of Argus. Also log when the day mapping is ambiguous.
- backlog: B-034 (reopen), B-035

### 2. The calendar hides the Fed's own core PCE measure (and ECI, GDP deflator) and shows the quarterly annualized figure as "Core PCE"
- kind: bug
- severity: high (the curated calendar reports core inflation as 2.5% when the Fed's measure is 3.1% y/y)
- evidence:
  - `services/market_context.py` has `NOISE = re.compile(r"\bIndex\b|n\.s\.a|Cleveland")`. It's applied to both `events` and `all_events`.
  - I fed it tonight's Nasdaq names through `build()`:
    - The curated list keeps "Core PCE Prices", "PCE Prices", "GDP" and "Initial Jobless Claims".
    - Even `all_events` (the "all 158 US releases" toggle) drops **"Core PCE Price Index"** (0.3% m/m, 3.1% y/y), "PCE price index" (0.5% / 3.6%), "GDP Price Index" and **"Employment Cost Index"**. ECI is due 10-30 08:30, consensus 0.8%.
  - "Core PCE Prices" is 2.50% against 2.40% expected, with a previous of 3.30%. That's the quarterly annualized figure from the GDP report.
  - So the curated view says "core PCE 2.5%, beat". The Fed's target series says 3.1% y/y, in line. A reader would come away with the wrong inflation number.
  - ECI, the wage-inflation print the Fed watches most, can't be found at all.
- suggestion: narrow NOISE to the raw index-level rows: a level like "444.6", or names like "House Price Index" when a % variant exists. Or allow-list the names that end in "Index": "PCE Price Index", "Employment Cost Index", "GDP Price Index". Label quarterly annualized rows "(QoQ ann.)" (B-091).
- backlog: new (related to B-091, B-094)

### 3. Selling after the close at the close price changes Day P&L: Dashboard +$468.16 vs Performance +$438.52 for the same session
- kind: bug
- severity: medium (wrong number on the header, the brief and "vs SPY, last session")
- evidence:
  - Before my trade, `argus portfolio show loop-macro` gave `day_pnl` **438.52**, and GLD 18 sh × (368.57 − 373.51) = −88.92.
  - After SELL 6 GLD @ 368.57 at 22:18 ET (after the close, at the close price), `day_pnl` is **468.16** and GLD's is −59.28 (12 sh only). The Dashboard header reads "+$468.16 (+0.48%) last session", and so does the brief's `totals.day_pnl`.
  - `/performance` keeps the 10-28 → 10-29 step at 99,210.11 − 98,771.59 = **+$438.52**, which is correct.
  - The 6 shares I held all session lost $29.64. Selling them after the bell erased that loss from Day P&L.
  - The buy side is handled (B-046: IEF's 24 after-close shares are excluded, and IEF still shows +$22.00). The sell side isn't: Day P&L walks only the *open* lots, so shares sold after the close drop out of the session they were held through.
- suggestion: in the Day P&L loop, add lots closed by SELLs whose `trade_session` is after the quote's session. They count as held for the session: qty × (price − prev_close) in `day` and qty × prev_close in the base. A regression test can mirror the B-046 one.
- backlog: new (sell-side twin of B-046)

### 4. The after-hours total rests on two stale or contrary prints again: +$112.91 while ES is −1.1% and oil +2.5%
- kind: bug / ux
- severity: medium
- evidence:
  - The Dashboard reads "After hours +$112.91 (+0.11%)". ES=F is −1.10%, NQ=F −2.41%, SPY post −0.60% and QQQ post −1.54%.
  - Per position (`ext_pnl`), the total is mostly two rows:
    - **XLP** +1.36% (89.381 at 23:58 UTC) = +$109.29. VDC has no post print. XLP already closed +1.54%, and a further +1.4% after hours with futures down 1% is implausible.
    - **XLV** +0.77% = +$94.47. VHT is +0.61%, so plausible.
  - In the other direction, **DBC** −1.36% (33.26) is a print from **20:09 UTC (4:09 PM ET)**, six hours old, while WTI rallied +2.5% overnight. It accounts for −$82.80.
  - `ext_coverage_pct` is 100 regardless, and the Holdings row shows no print time.
- suggestion: as in B-108. Show the time of each AH print, flag prints more than 30 min old or contrary to the ES/NQ move, and show "n of 11 fresh".
- backlog: B-108

### 5. Oil "1D" is the overnight move, shown under "Market closed as of 4:00 PM"; history again lacks the latest settle
- kind: bug
- severity: medium (re-sighting, the third round in a row)
- evidence:
  - The Markets card reads "WTI $104.34 +2.29%" under "Market closed as of Thu, Oct 29, 4:00 PM ET".
  - `argus quotes CL=F` gives `prev_close 102.00`, the 10-29 settle, against a price stamped 02:04 UTC 10-30.
  - The 10-29 session itself was 102.78 → 102.00, i.e. **−0.76%**, the opposite sign.
  - `/api/history/CL=F?period=5d` has the 10-28 bar at 102.78 (now fixed) but the 10-29 bar at **104.54**, the overnight price; the 102.00 settle is missing. Gold is the same: its 10-29 bar is 4,017.6.
  - BTC history skips a day again: 10-28 is followed directly by 10-30 (B-075).
- suggestion: as in B-016 / B-055. Show the settle-to-settle session change, plus a tagged "overnight" line.
- backlog: B-016, B-055, B-075

### 6. Fear & greed reads 18.3 "Extreme fear" (5 readings), then 35 "Fear" (7) once breadth loads
- kind: ux
- severity: medium (eighth sighting; the label flips a whole band)
- evidence:
  - My first `/api/market-context` returned `score 18.3`, 5 components and `errors.breadth`.
  - About 5 minutes later the Markets page showed **35 Fear**, with Price strength 85 and Price breadth 66 added. The page doesn't say how many readings are in the score.
- suggestion: B-036. Show "5 of 7 readings" while breadth loads.
- backlog: B-036

### 7. The brief still has no macro section, so tonight's data and the overnight futures move are absent
- kind: feature
- severity: low (re-sighting)
- evidence: `/api/brief/loop-macro` has no `macro` key. It doesn't mention PCE or GDP actuals, tomorrow's ECI or Chicago PMI, or that ES is −1.1% and NQ −2.4% overnight. `near_52w_extremes` still lists 11 of 11 holdings (B-076).
- suggestion: B-038. Add `macro_recent` (last 24 h with actuals), `macro_upcoming`, and an `overnight` line (ES/NQ/CL change since the settle).
- backlog: B-038, B-076

### 8. A portfolio can't be linked to: `/p/loop-macro` silently opens loop-growth
- kind: ux
- severity: low
- evidence:
  - `scripts/screenshot.py /p/loop-macro` rendered the **loop-growth** dashboard ("loop-growth · total value $96,096.06"). The SPA falls back to `/`, and the portfolio comes only from `localStorage["argus.portfolio"]`, defaulting to the first portfolio.
  - To screenshot my own book I had to write a script that sets localStorage first.
  - No URL shows a given portfolio's dashboard, so it can't be bookmarked, shared or used to check one book at phone width.
- suggestion: accept `?p=<name>` (or `/p/:name`) and let it override localStorage.
- backlog: new

## Consistency checks that passed
- **Risk vs my own calculation:** book beta and volatility from `/risk` match mine to three decimals, both before (0.247, 6.13%) and after the trade (0.231, 5.83%).
- **Simulate:** `net_cash` +21.42 and realized −63.30 equal the executed transactions.
- **Fear & greed:** the safe-haven (−4.2 pp) and junk (−1.3 pp) details match my 20-day recalculations.
- **Performance vs Dashboard:** `/performance` `end_value` 99,210.11 equals the Dashboard value before the trade.
- **Phone:** Markets at 390 px has no horizontal overflow and logged no page errors.

## Summary for the round lead
1. Executed note 51 after PCE (the stop needed the 10Y above 5.15%; it fell to 4.99%): SELL 6 GLD @ 368.57 / BUY 24 IEF @ 91.25. Targets are now GLD 4.5 / IEF 7.5, under thesis note 54. loop-macro is $99,188.69, unrealized +$526.26, cash $1,275.30 (+0.46% to date). Book volatility 5.83%, matching my calculation.
2. B-034 is broken in practice. At 22:14 ET the calendar again starts on 10-30 and tonight's PCE/GDP actuals are gone, because Nasdaq's day mapping flipped within minutes. Argus should store the rows it has seen. Separately, the `\bIndex\b` noise filter hides the Fed's core PCE (3.1% y/y) and ECI, and shows the 2.5% quarterly figure as "Core PCE".
3. New bug: selling after the close at the close price drops those shares' session loss from Day P&L (Dashboard +$468.16 vs Performance +$438.52). After hours, +$113 rests on a stale XLP print and a 4:09 PM DBC print (B-108).
