# Round 015: macro investor

## What I did
- **When:** Wed 11-11 at about 21:15 ET (02:15 UTC Thu 11-12). The market was closed. 11-11 was Veterans Day: stocks traded, the cash bond market was closed.
- **Sources:**
  - `GET /api/market-context`.
  - `argus quotes --json` for HYG, LQD, TLT, ^VIX3M, UUP, GLD, ES=F, NQ=F, ^IRX, TIP, RSP, HG=F, MTUM, SPLV, SMH, EEM, EFA and IWM.
  - `/api/history` (1mo) for IEF, VTIP, SPY, XLE, GLD and UUP.
  - The loop-macro endpoints: portfolio, performance, drift, risk, exposure, dividends, simulate, targets and `/api/brief/loop-macro`.
  - `/api/research/SPY` news, and `/api/notes`.
  - Screenshots: Markets (1400 px, full page, and 390 px), plus Analysis (1400 px) and Dashboard (390 px). For the last two I used a Playwright script that picks loop-macro in the header first (B-118).
- **CPI (Tue 11-10) is the event my plan depended on, and Argus couldn't show it.** The economic calendar is completely empty (finding 1), so I read the print from the tape on 11-10:
  - IEF −0.86% (91.80 → 91.01), VTIP −0.21%, GLD −2.7%, UUP +0.62% and SPY −0.37%;
  - 10Y 4.86 → 4.98 and 2Y 4.51 → 4.73 (curve table), so 2s10s narrowed from 35 to 25 bp.
  - That's a hot print followed by a hawkish bear flattening.
- **Backdrop since then: equities shrugged it off, and volatility normalised.**
  - **11-11 close:** S&P 7,619 (+1.31%), NDX +2.28%, XLK +3.2%, SMH +4.8%, MTUM +3.8% and RSP +0.8%.
  - **Volatility:** VIX 17.49 (−10%) and VIX3M 19.24, a ratio of **0.91**, so the curve is back in contango.
  - **Credit:** HYG 77.35 (+0.22%).
  - **Commodities:** WTI 85.7 (1M −8.5%, now below my 90 trigger), gold 3,989 (3M −10.7%). XLE is below its 50-day average.
  - **Dollar:** USD/JPY 159.75.
  - **Breadth, once loaded:** 343 up and 155 down; 69% above the 50-day average. Fear & greed is 38.
  - **After hours:** SMH −2.7% and ES −0.3%.
- **Regime:** sticky services inflation with a hawkish repricing at the front end. Growth is fine and the equity correction is healing. Commodities aren't carrying the inflation: oil and gold are both falling.
- **Decision under note 82: rule (c), hot CPI, so no beta add.**
  - The note-80 SPY add's other legs now all pass: VIX/VIX3M 0.91 and HYG > 76.5. I'm still not adding SPY into a 5% 10Y with a rising 2Y.
  - IEF stays: it hedged on 11-05, and the 10Y is 5%.
  - **The oil leg broke** (WTI < 90, XLE below its 50-day), so I trimmed the commodity hedge into T-bills, not into RSP, to add no new beta.
- **Trades (11-11 post-market quotes):**
  - SELL 50 XLE @ 63.51 (txn 58), realized −$196.00;
  - BUY 31 SGOV @ 100.52 (txn 59);
  - targets changed: XLE 10 → 6.5% and SGOV 13.5 → 17%;
  - thesis in note 85, review 11-19.
  - Simulate beforehand at the 4 pm close: net cash +52.38 and realized −203.00. Both tie to 50 × 63.37 − 31 × 100.52 and 50 × (63.37 − 67.43).
- **Book at the 11-11 close (after the trades):**
  - value $98,216.23 and cost $98,149.18;
  - unrealized +$67.05 and realized −$483.04;
  - Day P&L +$542.11 (+0.55%) against SPY +1.32%;
  - TWR since 10-20 −0.38% against SPY −1.20% (+0.82 pp).
  - All positions are inside the ±2 pp band.
- **Cash: $1,367.79** (1,308.41 + 3,175.50 − 3,116.12). Value plus cash is $99,584.02, a **return to date of −0.42%** (−0.35% with $63.08 of accrued dividends).

## Last round's changes
- **B-147 (simulate requires a side): works.**
  - `type:"SELL"` and a lowercase `type:"buy"` simulate correctly: XLE shows as a SELL with net cash +52.38.
  - A trade with no side gets a 400: "Trade 1 (XLE): give side (or type) BUY or SELL."
  - Conflicting side and type get a 400. The message's value order looks reversed (finding 8).
  - That fixes my round-014 #1.
- **B-146 (risk with one or zero holdings):** my book's risk is unchanged in form. Beta 0.23, vol 5.8%, VaR99 $774 before the trade, and the correlation and factor tables are intact.
- **B-139:** tests only; nothing to check from my side.
- **B-150 (split warning after a restart):** couldn't test, as no holding split this round. `split_warnings` is `[]` on the first summary call, which is correct.
- **B-117 (re-checked):** selling after the close kept Day P&L at +$542.11, which is right. The 31 SGOV shares bought after the close carry no day P&L.

## Findings

### 1. One 403 for one day empties the whole economic calendar, kept actuals included; CPI week's print is invisible
- kind: bug
- severity: high (this blocked my decision: note 82's rules were all keyed on core CPI, and I had to read it off bond and gold moves)
- evidence:
  - **API:** `/api/market-context` returns `calendar.events: []` and `all_count: 0`, with `errors.events: "econ:21:2026-11-11: Client error '403 Forbidden' …"`.
  - **Markets page:** "Economic calendar … all 0 US releases" over an empty table. The only hint is the raw error banner at the top of the page.
  - **Cause:** `macro.py` `economic_events()` fetches about 24 daily queries in a thread pool. `day()` raises on any non-200, so `pool.map` fails the whole fetch.
    - `_memo` only falls back to a cached value under the same key, and the key includes today's date. After a restart or at New York midnight there is nothing to fall back to.
    - `_keep_releases`, the kept store (B-034), is only reached on success, so the kept rows are never served on failure.
    - No `econ_releases.json` exists under the data directory at all.
  - **Brief:** the brief has no macro events either (B-038), so no screen in Argus showed CPI.
- suggestion:
  - Catch per-day errors in `day()`: return `[]` for that day and record which days failed. A single 403 should cost one day, not three weeks.
  - On a total failure, serve the kept store with a "calendar source unavailable since HH:MM; showing saved rows" note.
  - Longer term, add a second source for the big releases (BLS/BEA release dates, with FRED for actuals). Related to B-135.

### 2. Risk's "Last session (11-11)" changes when you trade after the close: +$484 vs Day P&L +$542
- kind: bug (a new cause for B-152)
- severity: medium (the two figures for one session disagree; an evening trader sees the last session move after recording a trade)
- evidence:
  - **Before the trades:** `/risk` gave `last_day.value` 542.11, matching `totals.day_pnl` 542.11.
  - **After selling 50 XLE post-market:** `last_day.value` is **483.80** (Analysis → Risk "Last session (11-11) +$484") while Dashboard Day P&L stays +$542.11.
  - **The difference** is 50 × (63.37 − 62.21) = $58: the sold shares' 11-11 move.
  - **Same session, other figures:** performance's 11-11 step (98,268.61 − 97,726.50 = 542.11) and its end value 98,268.61 also reflect the holdings at the close. Risk recomputes the session on today's holdings.
  - The `exceeds_var_99` check therefore tests a P&L the book never had.
- suggestion: take risk's last-session P&L from the same holdings-at-close series that performance and Day P&L use, and keep "today's holdings" for the forward-looking VaR. Or label the tile "on current holdings".

### 3. Markets error banner overflows the phone layout and shows a raw httpx message
- kind: ux
- severity: medium
- evidence:
  - **At 390 px:** `scripts/screenshot.py /markets --width 390` reports `horizontal_overflow: true`.
  - **The cause:** the red banner's unbroken URL `https://api.nasdaq.com/api/calendar/economicevents?date=2026-11-11` runs past the card. The desktop page has no overflow.
  - **The text:** the banner reads "events (econ:21:2026-11-11: Client error '403 Forbidden' for url … For more information check: https://developer.mozilla.org/…)". That's a stack-level message, not something a user can act on.
- suggestion:
  - Use `overflow-wrap: anywhere` on the banner.
  - Map provider errors to a plain line ("Economic calendar: Nasdaq refused the request (403). Showing saved releases.") and put it next to the calendar section, not above the indices.

### 4. Fear & greed reads "Extreme fear 20.8" from 5 of 7 components, then "Fear 38" once breadth loads
- kind: bug (re-sighting of B-036)
- severity: medium (a 17-point swing across the 25 threshold with no warning)
- evidence:
  - **First call (02:13 UTC):** `/api/market-context` gave `fear_greed.score` **20.8, "Extreme fear"**, with 5 components (no price strength or breadth) and `breadth.stocks: null`.
  - **Minutes later:** the Markets page shows **38, "Fear"**, with price strength 95 (19 highs vs 1 low) and breadth 69 added.
  - **On the first call:** neither the API nor the gauge said "5 of 7 components".
- suggestion: return `components_used` / `components_total`, and show "partial (5/7)" or withhold the headline score until breadth loads.

### 5. First loads are slow after a restart: risk 20.2 s, performance 7.7 s, portfolio 3.3 s
- kind: perf (re-sighting of B-026, slower than its 11–15 s)
- severity: medium
- evidence: first round of `curl -w %{time_total}` on loop-macro:
  - `/risk` 20.16 s;
  - `/performance` 7.65 s;
  - the summary 3.27 s;
  - `/exposure` 1.31 s.

  Warm, the same calls take 0.27 s, 0.12 s, 0.07 s and 0.03 s.
- suggestion: warm the held symbols' history and risk inputs at startup in the background, or show partial risk while the 1-year bars fetch.

### 6. Holiday: the 10-year card shows an 11-11 move ("5.00%, +2 bp") while the curve says "par yields, 2026-11-10"
- kind: ux
- severity: low
- evidence:
  - **The card:** `^TNX` last 4.998, `as_of 2026-11-11`, against 4.98 on 11-10. The cash Treasury market was closed for Veterans Day.
  - **The curve:** the curve card and table on the same page are dated 11-10 (10Y 4.98).
  - Nothing on the page mentions the bond holiday, so the +2 bp reads as a session that didn't happen.
- suggestion: use the bond-market calendar (SIFMA holidays) to mark yield cards "bond market closed" and keep the 1D on the last bond session.

### 7. Stale or odd after-hours prints still drive the "After hours" line (TIP −1.0%)
- kind: bug (re-sighting of B-108)
- severity: low
- evidence:
  - **TIP:** `argus quotes TIP` gives `ext_price` 104.21 at 00:13 UTC (−1.00%) on a 105.26 close. Meanwhile IEF post-market is +0.02% and TLT −0.06%. A 1% TIPS move after hours on a bond holiday isn't credible.
  - **SMH:** post-market −2.72% at 00:59 is plausibly real.
  - Argus treats both the same way.
- suggestion: ignore extended-hours prints that are thin or old, or flag moves more than 3σ beyond the ETF's own sibling (TIP vs IEF and VTIP) as "single print".

### 8. Simulate's side/type conflict message lists the values in the reverse order
- kind: ux
- severity: low
- evidence: `{"side":"SELL","type":"BUY",…}` returns "side and type disagree (**BUY vs SELL**)". Read in the order of the words, that says side=BUY.
- suggestion: print "side SELL vs type BUY".

### 9. Re-sightings (short)
- **Dashboard and performance disagree on the 11-11 value after an evening trade:**
  - the Dashboard says $98,216.23, the performance end value $98,268.61;
  - the trades are stamped `ts 2026-11-12T02:17Z` though they were made at 21:17 ET on 11-11 (B-049).
- **Brief:**
  - `theses_due` lists 20 notes, most superseded (B-127);
  - there are no macro events (B-038);
  - the IEF headline summary has mojibake ("Appleâ€™s", B-154);
  - `near_52w_extremes` lists 8 of 10 holdings, including SPY 2.8% from its high (B-076).
- **Analysis:**
  - Targets & drift opens on "By sector, Targets sum to 0.0%" though 10 position targets summing to 100% are saved (B-022);
  - VTIP's yield is 4.83%, and the footnote "latest payment × payments per year" doesn't match $2.35 (B-063, B-145);
  - look-through "Unclassified" is 41.8% (SGOV, IEF, VTIP, DBC), with no duration (B-017). After this trade that matters more: I have no way to see the book's duration or T-bill share as asset classes.
- **Notes:** every note has `portfolio: null`, so my theses mix with the other books' (B-018).

## Consistency checks that passed
- **Day P&L:** 11-11 minus 11-10 performance values = 98,268.61 − 97,726.50 = **542.11** = Day P&L = brief totals.
- **Benchmark:** SPY's 11-06 → 11-11 move from the series, (1 − 1.20%) ÷ (1 − 4.39%) = 1.0334, matches 759.81 ÷ 735.29 = 1.0333.
- **The trades:**
  - realized −196.00 = 50 × (63.51 − 67.43);
  - new cost 98,149.18 = 98,404.56 − 3,371.50 + 3,116.12;
  - SGOV average cost 100.592 matches the dry run.
- **Dividends after the trade:** XLE annual income 98 × 1.52 = $148.96 and SGOV 160 × 3.61 = $577.92, both matching the table.
- **Curve:** 2s10s 25 bp = 4.98 − 4.73 and 10s3m 68 bp = 4.98 − 4.30.
- **Volatility:** VIX/VIX3M 17.49 ÷ 19.24 = 0.91 = the term component. VIX 1D −10.12% = 17.49 ÷ 19.46 − 1.
- **Sectors:** the heatmap matches the API row for row.
- **Pages:** Analysis and Dashboard rendered with no page errors or overflow (Analysis at 1400 px, Dashboard at 390 px); Markets desktop rendered in 0.15 s.

## Summary for the round lead
1. **Trades:** CPI read as hot from the tape (Argus's calendar was empty), so no SPY add. The oil leg broke (WTI 85.7 < 90), so I SOLD 50 XLE @ 63.51 and BOUGHT 31 SGOV @ 100.52 (txns 58/59, note 85), with targets XLE 6.5% and SGOV 17%. loop-macro is $98,216.23, cash $1,367.79, return to date −0.42%.
2. **Confirmed fixes:** B-147 works (`type` alias, no-side rejection). B-117 holds after an evening sell.
3. **Top findings:**
   - **high:** a single Nasdaq 403 empties the whole calendar, kept actuals included, so CPI was invisible;
   - **medium:** risk "Last session" is recomputed on post-trade holdings (+$484 vs Day P&L +$542);
   - **medium:** the error banner overflows at 390 px;
   - **medium:** fear & greed showed 20.8 from 5/7 components, then 38;
   - **medium:** first-load risk takes 20 s.
