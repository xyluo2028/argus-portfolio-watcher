# Round 010: macro investor

## What I did
- **When.** Sun 11-01 at about 21:15 EST (02:15 UTC 11-02). US daylight saving time ended this morning, and the market has been closed since the 10-30 session. Sources:
  - `GET /api/market-context` (before and after breadth loaded);
  - `argus quotes --json` (ES=F, NQ=F, CL=F, GC=F, BTC-USD, ^VIX, ^TNX, JPY=X, HYG, LQD, TLT);
  - `/api/history` (1y daily for 10 ETFs and ^GSPC);
  - `/api/portfolios/loop-macro/{risk,drift,performance,dividends,simulate}` and `/api/brief/loop-macro`;
  - the raw Nasdaq calendar feed, to check Argus's calendar;
  - screenshots of Markets (1400 px and 390 px) and the loop-macro Dashboard.
- **Backdrop on 10-30:** megacap tech sold off under a rotation into defensives.
  - **Indices:** S&P 7,580 (−1.82%), NDX −3.46%, RUT −1.66%. XLK fell −4.9% and XLC −1.3%. XLE gained +1.9%, XLP +1.4%, XLU +0.7% and XLV +0.5%.
  - **Breadth:** 225 up / 275 down. RSP − SPY is +5.9 pp over 1M, and 8 of 11 sectors are above their 50-day average.
  - **Volatility:** VIX 19.42 (+12.9%). VIX ÷ VIX3M is 0.93.
  - **Rates:** 10Y 4.93% (−6 bp, −36 bp over 1M) and 2Y 4.56%, so 2s10s is +38 bp and 10s3m +78 bp.
  - **Commodities:** WTI settled at 104.12 (+2.1%). Gold fell to 3,899 (−3.3%) and GLD −3.47%.
  - **Sunday night:** ES +0.42%, NQ +0.76%, WTI 101.53 (−2.5%), gold +0.6%, USD/JPY 157.87, BTC 78.3k.
  - **Fear & greed:** 27 "Fear" with all 7 readings. Safe-haven demand reads −7.4 pp and junk vs IG −1.7 pp. I recomputed both from `/api/history` (−7.44 and −1.72) and they match.
- **Correlations with SPY,** computed from Argus history:

  | | 20 days | 60 days | 1 year |
  |---|---|---|---|
  | IEF | −0.52 | +0.15 | +0.28 |
  | GLD | **+0.76** | +0.54 | +0.40 |
  | XLE | −0.42 | −0.35 | −0.26 |
  | DBC | −0.22 | −0.33 | −0.24 |

  Bonds and energy hedge equities. Gold does not: it fell with stocks again and sits 0.3% above its 52-week low.
- **Regime:** unchanged. It's a late-cycle rotation into defensives with sticky inflation, and the defensive tilt paid off:
  - Since 10-20, TWR is **+0.42% against SPY −1.73%**, an excess of +2.15 pp. Max drawdown is −0.27%.
  - On 10-30 the book lost only −$60.62 while SPY fell −1.77%.
  - Drift is within ±0.5 pp everywhere: XLV +0.50 and XLE +0.45 are the largest, against a ±2 pp band.
- **Decision: no trade.** Payrolls come out Fri 11-06, with ISM on Monday and JOLTS on Tuesday. Drift is noise, and the regime hasn't changed.
  - I simulated exiting the 12 GLD shares into 46 IEF (`POST /simulate`): net cash +$48.40, realized −$280.08, and IEF would go from 7.3% to 11.6%.
  - I wrote that switch up as a conditional plan in **note 56** (GLD, review 11-09). The trigger is GLD closing below its 52-week low after NFP, or its 20-day correlation still above 0.5.
  - **Note 57** (DBC, review 11-09) holds DBC at 6%.
- **Portfolio:** 11 positions, value **$99,128.07**, cost $98,662.43, unrealized +$465.64, realized −$62.27.
  - `/risk` gives beta 0.223, volatility 5.80% and 95% VaR 0.54%.
  - IEF and SGOV are estimated to go ex-dividend Mon 11-02, for $24.25 and $38.83.
- **Cash balance: $1,275.30** (100,000 − 62.27 realized − 98,662.43 cost). Value plus cash is $100,403.37, a return to date of **+0.40%**.

## Last round's changes
- **B-117 (Day P&L after an after-close sale): works.**
  - Dashboard and brief Day P&L for 10-30 is −$60.62.
  - The `/performance` step for 10-30 is 99,128.07 − 99,210.11 = −82.04. My 10-29 evening trades are booked as 10-30 flows (B-049), and net flows of +21.42 bring the step to **−60.62**, so the two agree.
  - Gain also reconciles: 465.64 unrealized − 62.27 realized = $403.37, the same as Performance's gain of $403.
  - Nothing was sold out after the close this round, so I couldn't check the brief-movers question.
- **B-034 (the calendar keeps rows it has seen): works in the narrow sense, but not over a weekend.**
  - "Yesterday" tonight is Saturday. The store `data/cache/econ_releases.json` holds a single row, "10-31 GDPNow".
  - Friday's ECI (0.8%) and Chicago PMI (55.3), with their actuals, aren't shown anywhere (finding 2).
- **B-116 (core PCE, ECI and the GDP price index kept):** I couldn't verify it tonight. There's no PCE or GDP row in the 3-week window, and the 10-30 ECI row has dropped off (finding 2).
- **Fear & greed component count (part of B-036):** the Markets page now says "The average of 7 readings". The API still flips the band while breadth loads (finding 3).

## Findings

### 1. After DST ended, every release is a day late and an hour early: payrolls on Saturday 11-07 at 07:30, ISM on Tuesday at 09:00
- kind: bug
- severity: high (B-006 has regressed; the whole payrolls week is misdated on the Markets page and in the API)
- evidence:
  - What Argus shows: `GET /api/market-context` → `calendar.events` gives:
    - "2026-11-03 09:00 ISM Manufacturing PMI";
    - "2026-11-04 09:00 JOLTS Job Openings";
    - "2026-11-06 07:30 Initial Jobless Claims";
    - "**2026-11-07** 07:30 Nonfarm Payrolls / Unemployment Rate";
    - "2026-11-07 09:00 Michigan Consumer Sentiment".
  - The Markets page lists them under "Tue, Nov 3", "Fri, Nov 6" and "**Sat, Nov 7**".
  - The true schedule is ISM Mon 11-02 10:00, JOLTS Tue 11-03 10:00, claims Thu 11-05 08:30 and NFP Fri 11-06 08:30 ET.
  - The raw feed:
    - `api.nasdaq.com/api/calendar/economicevents?date=2026-11-07` returns NFP at gmt "08:30", Michigan at "10:00".
    - `?date=2026-11-03` returns ISM at "10:00".
    - `?date=2026-11-06` returns claims at "08:30".
    - So Nasdaq now gives New York clock times in winter, and each answer is the previous day's releases (the usual lag).
  - **The hour.** `nasdaq_slot` treats gmt as a fixed UTC-4 (`NASDAQ_TZ`). After 11-01 it subtracts an hour: `MacroProvider.nasdaq_slot(date(2026,11,6), "08:30")` → `(2026-11-06, "07:30")`.
  - **The day.** I ran `MacroProvider._nasdaq_days` on tonight's raw answers for queries 11-01 to 11-10:
    - The 11-02 query is a Monday whose only row is "OPEC Meeting", so the Monday rule marks it "own day".
    - The `own_prev` rule then marks every following query as its own day too: 11-03 → 11-03, …, **11-07 → 11-07 (Sat, 31 rows, NFP)**.
    - The cascade only stops at the empty Sunday 11-08.
- suggestion:
  - **Time:** read the gmt column as America/New_York local time. Or detect the offset from an anchor such as payrolls or claims at 08:30.
  - **Day:** don't let the Monday rule cascade through `own_prev`. A US weekday release must never land on a Saturday or Sunday, and claims must fall on a Thursday. If they don't, shift the whole run back by a day.
  - **Tests:** add a regression test on tonight's sequence: a Monday with only an OPEC row, then a normal week, after DST ends.
- backlog: B-006 (reopen)

### 2. Over the weekend, the last session's releases and actuals vanish: ECI 0.8% and Chicago PMI 55.3 aren't anywhere
- kind: bug / ux
- severity: medium
- evidence:
  - On Sunday, `calendar.all_events` (142 rows) starts with "2026-10-31 19:00 Atlanta Fed GDPNow" and then jumps to 11-02.
  - Friday 10-30's ECI 0.8% vs 0.8%, Chicago PMI 55.3 vs 55.8 and Michigan final are gone. Nasdaq still serves them at `?date=2026-10-31`.
  - `data/cache/econ_releases.json` contains exactly one row (`2026-10-31|19:00|Atlanta Fed GDPNow|1`).
  - "Yesterday" is the calendar day, so on Saturday, Sunday and a Monday morning, the latest prints a macro desk wants to review are missing.
- suggestion: start the window, and the kept-rows store, at the **last trading session**, not yesterday's calendar date. Over a weekend that means Friday. Keep that session's rows until the next session's rows arrive.
- backlog: B-034, B-035

### 3. Fear & greed reads 8.5 "Extreme fear" (5 readings) in the API, then 27.2 "Fear" (7 readings) once breadth loads
- kind: ux
- severity: medium (ninth sighting; the reading moves a whole band)
- evidence:
  - My first `/api/market-context` after the restart returned `fear_greed.score 8.5`, 5 components and `errors.breadth`.
  - After breadth built, it returned `27.2 "Fear"` with 7 components: Price strength 87 and Price breadth 61.
  - The page now prints "The average of 7 readings", which helps once breadth has loaded. But the API, and anything built on it (the MCP tool, an agent), gets 8.5 with no flag that it's partial.
- suggestion: B-036. Add `components_used` / `components_total` and `partial: true` to the payload. Or hold the score back, or mark it provisional, until breadth is in.
- backlog: B-036

### 4. `/risk` took 17.0 s on its first call after the restart
- kind: perf
- severity: medium
- evidence:
  - `curl -w %{time_total} /api/portfolios/loop-macro/risk` took **16.97 s** on the first call and 1.42 s on the second.
  - In the same session, `/drift` took 0.70 s, `/performance` 1.57 s and `/brief` 1.59 s.
  - The Dashboard took 5.9 s to settle.
- suggestion: B-026. Warm the 1-year histories for held symbols at startup, or load them in one batch call.
- backlog: B-026

### 5. On Sunday night, Markets shows the overnight move as "1D" under "Market closed as of Fri, Oct 30, 4:00 PM", and no index futures
- kind: bug / ux
- severity: medium (re-sighting)
- evidence:
  - Markets cards read "WTI $101.50 −2.52%", "Gold $3,920 +0.55%" and "USD/JPY +0.22%" under the Friday 4 PM banner.
  - The oil spark ends 102.00 → 104.12 → 101.57. Friday's session was **+2.08%**, the opposite sign, and nothing on the page shows it.
  - ES=F (+0.42%) and NQ=F (+0.76%) are trading. `argus quotes` has them, but Markets has no futures card, which is what you'd check on a Sunday night.
- suggestion: B-016 / B-055. Show the session (settle-to-settle) change as 1D, plus a separate "overnight" line for futures, oil, gold, FX and BTC since the settle.
- backlog: B-016, B-055

### 6. Theses stay "due" after I write a newer note, and the CLI can't move a review date
- kind: ux
- severity: low
- evidence:
  - `/api/brief/loop-macro` → `theses_due` still lists thesis 21 (DBC) and thesis 22 (GLD), both "review_on 2026-10-29", after I added notes 56 and 57 with reviews on 11-09.
  - `argus note` has only `add` and `list`. The API has `PATCH /api/notes/{id}`, but the CLI can't set a new review date or archive a thesis.
- suggestion: add `argus note update <id> --review-on/--archive`. Or let a new thesis or note on the same symbol supersede the older one's review.
- backlog: new (related to B-018)

### 7. The brief still has no macro section in a payrolls week
- kind: feature
- severity: low (re-sighting)
- evidence:
  - `/api/brief/loop-macro` keys are portfolio, market, totals, benchmark, movers, `near_52w_extremes`, earnings, dividends, alerts, theses, watchlist and headlines. There's no `macro` key.
  - So it doesn't mention ISM, JOLTS or NFP this week, Friday's ECI, or Sunday-night futures.
  - `near_52w_extremes` lists 9 of 11 holdings (B-076).
- suggestion: B-038. Add `macro_recent` (the last session, with actuals), `macro_upcoming` (the next 5 sessions) and an `overnight` line.
- backlog: B-038, B-076

### 8. `/?p=loop-macro` still opens loop-growth
- kind: ux
- severity: low (re-sighting)
- evidence:
  - `scripts/screenshot.py "/?p=loop-macro"` rendered the header portfolio as loop-growth.
  - To screenshot my own Dashboard I had to set `localStorage["argus.portfolio"]` in a custom script.
- suggestion: B-118
- backlog: B-118

## Consistency checks that passed
- **Dashboard vs API:**
  - Value $99,128.07, Day P&L −$60.62 and after hours +$40.41 match `argus portfolio show`.
  - Return +0.42%, SPY −1.73% and gain +$403 match `/performance`.
- **Day P&L vs Performance:** the 10-30 step net of flows is −60.62, the same as Dashboard Day P&L (B-117 holds).
- **Fear & greed details:** safe-haven −7.4 pp and junk −1.7 pp match my 20-day recalculation from `/api/history`. The momentum detail "0.0% below its 125-day average" matches my −0.035%.
- **Rates:** the 10Y gauge (4.93%) and the Treasury curve (4.94%) agree within the source difference. The 1M change of −36 bp matches the curve: 5.29 → 4.94.
- **Simulate:** `value_after` + `net_cash` = `value_before`.
- **Phone:** Markets at 390 px has no horizontal overflow and logged no page errors.

## Summary for the round lead
1. No trade. The defensive book is +2.15 pp ahead of SPY since 10-20, drift is within ±0.5 pp, and NFP is on Friday. The GLD → IEF switch is staged as conditional note 56; DBC is held in note 57. loop-macro is $99,128.07, cash $1,275.30, +0.40% to date.
2. High: after DST ended, the calendar puts every release a day late and an hour early, including NFP on Sat 11-07 at 07:30 and ISM on Tue at 09:00. B-006 has regressed: Nasdaq now gives ET clock times, and the Monday "own day" rule cascades through the week.
3. Over the weekend, Friday's ECI and Chicago PMI actuals vanish because "yesterday" is Saturday. Fear & greed reads 8.5 in the API before breadth loads and 27 after. `/risk` took 17 s cold. B-117 works.
