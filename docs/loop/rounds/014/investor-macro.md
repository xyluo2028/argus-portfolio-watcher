# Round 014: macro investor

## What I did
- **When:** Sunday 11-08 at about 21:15 ET (02:15 UTC on Mon 11-09). Markets were closed; the latest close was Fri 11-06. Globex had reopened, so futures and gold were trading Sunday night.
- **Sources:**
  - `GET /api/market-context`, plus `argus quotes --json` for CL=F, BZ=F, HYG, LQD, TLT, ^VIX3M, UUP, GLD, ES=F, NQ=F, ^IRX, TIP, EEM, EFA, RSP, HG=F, MTUM, SPLV, XLK and SMH.
  - The loop-macro endpoints: portfolio, performance, drift, dividends, risk, exposure, simulate and brief, each checked before and after recording the split. Also `/api/history` for QUAL, XLE, DBC, SPY, IEF and MTUM.
  - Screenshots: Dashboard (1400 px and 390 px), Analysis (full page), Markets and `/t/QUAL`. The bundled script always opens the localStorage portfolio (loop-growth, B-118), so I used a small Playwright script that picks loop-macro in the header first.
- **Backdrop: a strong jobs report and a tech bounce, with volatility still inverted and CPI on Tuesday.**
  - **Payrolls 11-06:** NFP **165K** against 65K expected (private 159K). Unemployment 4.1% (4.2% expected), AHE +0.4% m/m and 3.1% y/y, Michigan sentiment 51.0. Argus's calendar now shows these actuals.
  - **Equities Friday:** S&P 7,376.86 (+0.31%), NDX +1.35% (−13.6% over 1M), RUT +0.89%, SMH +3.6% and MTUM +1.9%. Defensives lagged: XLP −1.28% and SPLV −0.93%. Breadth 218 up and 282 down; 59% of stocks are above their 50-day average.
  - **Volatility:** VIX 25.64 (−9%), VIX3M 24.60, ratio **1.04**, so the curve is still inverted. Fear & greed 16.8 (Extreme fear), with all 7 components loaded.
  - **Credit:** HYG 77.23 (−0.06%) and LQD −0.12%. Junk vs IG is −2.1 pp over 20 days.
  - **Rates:** 10Y 4.86% (+2 bp), 2Y 4.51%, 2s10s +35 bp and 10s3m +67 bp. The curve fell about 40 bp across tenors over the month.
  - **Commodities:** WTI 90.6 (−6% on the week). XLE **−12.0% on the week** (70.02 → 61.62, confirmed from bars). Gold futures 4,135 on Sunday night; GLD −0.79% on Friday.
  - **Dollar:** UUP +0.73% and USD/JPY 158.2.
  - **Overnight:** ES +0.42%, NQ +0.43% and copper +1.5%.
- **Regime:** growth is re-accelerating and inflation is sticky (CPI 3.7% y/y previous, PPI 6.3% y/y previous). The equity correction looks like positioning in tech, not a growth or credit event. My defensive, inflation-hedged book did its job: TWR −1.67% against SPY −4.39%.
- **Trade 1: recorded the QUAL SPLIT** with `argus txn add loop-macro SPLIT QUAL --qty 4 --date 2026-11-05T09:30` (txn 55).
  - The dry run matched: 53 → 212 shares, average cost 225.695 → 56.42375, cost basis unchanged at $11,961.84.
- **No market trades.**
  - **The note 80 SPY add failed one of its legs.** NFP > 0 and HYG > 76.5 both held, but VIX/VIX3M was 1.04, not below 1.0.
  - **The XLE→RSP switch (note 62) passes its own WTI and ISM tests.** I'm holding it anyway: with hot wages and CPI on Tuesday 11-10, I want to keep the inflation hedge through the print.
  - **Simulated:** SELL 30 XLE / BUY 9 RSP: net cash −$95.85, realized −$174.30, XLE 7.5% and RSP 2.0%.
  - **Restaged after CPI in note 82:**
    - core CPI ≤ 0.2% m/m and VIX/VIX3M < 1: SELL 29 SGOV / BUY 4 SPY;
    - core CPI ≤ 0.2% and WTI < 90: XLE→RSP;
    - core CPI ≥ 0.4%: stay, and review duration.
- **Book at the 11-06 close (after the SPLIT):**
  - value **$96,993.64** and cost $98,404.56;
  - unrealized −$1,410.92 and realized −$287.03;
  - Day P&L −$112.09 (−0.12%) against SPY +0.31%.
  - All 10 positions are inside the ±2 pp drift band; the largest drift is XLV, +0.77 pp.
- **Cash: $1,308.41**, unchanged (100,000 − 287.03 realized − 98,404.56 cost). Value plus cash is $98,302.05, a **return to date of −1.70%** (−1.63% counting the $63.08 of accrued dividends).

## Last round's changes
- **B-140 (stock splits): works, and it fixed my book.**
  - **History re-based:** QUAL's history is split-adjusted in the cache (11-04 close is now 56.755, not 227.02). MTUM's is adjusted too (68.21 → 62.60).
  - **SPLIT recorded (txn 55), and every figure ties out:**
    - value $88,275.67 → **$96,993.64**;
    - the 11-05 point in performance is **$97,105.73, TWR −1.56%**, exactly last round's hand count;
    - 11-06 TWR is **−1.67%**, with no jump on 11-05 (the series goes 98,754 → 97,106 → 96,994);
    - last step = Day P&L = −$112.09;
    - excess return +2.72 pp (it showed −6.11 pp);
    - max drawdown −2.14% (it showed −10.50%).
  - **Warning:** `split_warnings` cleared in the API, the CLI and the brief.
  - **Drift:** QUAL is 11.98% against a 12% target, so "buy $15", not "buy $7,703".
  - **Stock page `/t/QUAL`:** 1D +0.1%, 5D −1.4% (I checked: 54.83 ÷ 55.6225 − 1), 1M −3.2%, and a 52-week range of 46.47–57.03.
  - **Yield and income:** yield **0.86%**, with $0.11825 a share on 212 shares (12-15 estimate $25.07).
  - **Risk:** QUAL β 0.87 and vol 12.6%, with no crash in its series.
  - **Brief:** QUAL is no longer "near 52w low".
  - **Other books:** no false "possible split" flags on loop-income or loop-growth.
  - **Gap:** see finding 3. The warning was missing on the first summary call after the restart.
- **B-141 (dividend calendars): works.**
  - IEF and SGOV project 12-01 and 12-21, VTIP 12-18, and nothing in January.
  - Rest-of-2026 projected income is $608.86 and the 2026 total $671.95.
  - IEF's and SGOV's `last_ex_date` is back to 10-01: Yahoo restored the row.
- **B-142 (risk uses the last session): works.**
  - The "Last session (11-06)" tile is −$112, which equals Day P&L, and is flagged "not beyond 99% VaR".
  - Risk `as_of` is 11-06, the same as performance. `closes_from_quotes` is null because Yahoo's bar arrived.
- **B-035 (calendar actuals): payrolls actuals now show** (NFP 165K, UR 4.1%, AHE 0.4%/3.1%, Michigan 51.0). That's helpful.

## Findings

### 1. Simulate silently treats a trade without `side` as a BUY, and ignores `type`, the field transactions use
- kind: bug
- severity: medium (a what-if I meant as a switch showed as $3,793 of new buying; an agent reading it would mis-size the trade)
- evidence:
  - **Request:** `POST /api/portfolios/loop-macro/simulate` with `{"trades":[{"type":"SELL","symbol":"XLE","qty":30},{"type":"BUY","symbol":"RSP","qty":9}]}`.
  - **Result:** `"side":"BUY"` for XLE, net cash **−3,793.05**, XLE 9.4% → **10.9%**, realized 0. It returned no error and no warning.
  - **With `side`:** the same request gives net cash −95.85, realized −174.30 and XLE 7.5%.
  - **Cause:** `app.py:1448` reads `t.get("side", "BUY")`. Unknown keys are dropped, because `SimBody.trades` is `list[dict]`.
  - **Why `type` is the natural key:** transactions, the CLI, the txn list JSON and `add_transaction` all call the field `type`.
- suggestion: make `side` required, or accept `type` as an alias, and reject unknown keys. Never default to BUY.

### 2. Markets gold and oil "1D" on a closed weekend is the Sunday-night futures tick against Friday, under "Market closed as of Fri 4:00 PM"
- kind: bug / ux (re-sighting of B-016 and B-055)
- severity: medium (the sign is again opposite to the session I was reviewing)
- evidence:
  - **The cards:** the Markets page shows "Gold $4,142 **+1.65%**" and the API shows `GC=F 1D +1.47, as_of 2026-11-09`.
  - **The 11-06 session:** spark 4,113.5 → **4,074.9 (−0.94%)**, and GLD −0.79% on Friday.
  - **Mixed dates:** indices carry `as_of 2026-11-06`, while futures, FX and bitcoin carry 11-09 on the same row of cards.
  - **Quote labels:** `argus quotes CL=F` gives `as_of 2026-11-09T02:05` with `session_date 2026-11-06`. That's a Sunday Globex print labeled as Friday's session.
- suggestion: when the equity market is closed, show each card's 1D for the last completed session, and show the overnight move as a separate "since close" line (B-055).

### 3. The split warning was missing from the first portfolio summary after the restart
- kind: bug (unconfirmed cause)
- severity: low-medium (on a different evening the user would see a −$9k phantom loss and no banner)
- evidence:
  - **First call:** `/api/portfolios/loop-macro` at 02:13:44 UTC returned value 88,275.67 (53 QUAL shares at 54.83) and **`split_warnings: []`**.
  - **A minute later:** the same call (and `argus portfolio show`) returned the QUAL 4:1 warning. In between, I had called `/api/history/QUAL`, which returned adjusted bars.
  - **Likely mechanism:**
    - The quote check (`split_suspects`) only fires on the split session itself. On 11-06 the quote's prev_close (54.79) equals the stored 11-05 bar, which already arrived on the new basis.
    - The `stock_split` row only appears once something refreshes that symbol's bars.
    - So a summary viewed before any chart or performance call has no warning.
- suggestion: also flag a position when the stored bars show a split-like jump across a session the ledger holds through (`splits.unadjusted` already exists). Or have the summary refresh the bars of held symbols whose last stored close jumped by a split factor.

### 4. The risk model still understates realized risk: VaR99 is $754 against a −$1,648 day three sessions ago, and three betas sit on one page
- kind: feature (re-sighting of B-067 and B-021)
- severity: medium
- evidence:
  - **Analysis → Risk:** beta 0.22, "SPY falls 10% (via beta)" −2.2%, and VaR99 $754 (0.78%).
  - **Factor table on the same page:** market loading 0.34.
  - **11-05 realized:** −$1,648 (−1.67%) on SPY −4.41%, a realized beta of about 0.38, which is **2.2× VaR99**.
  - **Why:** the 1-year window is dominated by the oil-shock months, so XLE shows β −0.36 even though it fell with stocks on 11-05.
- suggestion: add a 20d/60d window toggle (B-067), and label which beta drives the "SPY falls 10%" line (B-021).

### 5. Dividends table: the footnote and the VTIP rate contradict each other; VTIP's yield is 4.81%
- kind: bug (re-sighting of B-063 and B-145)
- severity: low
- evidence:
  - **Analysis → Dividends:** VTIP shows "Annual / share $2.35, yield 4.81%". `last_amount` is 0.933 (10-01) and the 12-18 estimate is 0.58675 (= 2.347 ÷ 4).
  - **The footnote** says "Annual rate = latest payment × payments per year". That would be 0.933 × 4 = 3.73, so the footnote doesn't describe the number shown.
  - The 4.81% yield is not a forward yield for a short-TIPS fund.
- suggestion: fix the footnote per row source ("trailing 12 months" vs "latest × n"), per B-063.

### 6. After-hours P&L on Sunday night is dominated by one stale DBC print
- kind: bug (re-sighting of B-108)
- severity: low
- evidence:
  - **The Dashboard** says "After hours −$20.48 (−0.02%)".
  - **The cause:** DBC `ext_price` 31.00 at 18:12 ET Friday (−1.71%, −$97.20), against a 4 pm close of 31.54. Commodities rose Sunday night: gold +1.5%, copper +1.5%, oil −0.3%.
  - Without DBC, the after-hours P&L would be about +$77.
  - The line is also still shown 50 hours after the post-market session ended.
- suggestion: ignore extended-hours prints older than about 30 min or on tiny volume. Hide the "After hours" line once the next pre-market or weekend begins.

### 7. News summaries arrive as mojibake ("Thursdayâ€™s") and are shown as-is
- kind: bug
- severity: low
- evidence:
  - **Brief:** the XLP headline "Midterm Election Goes Blue…" (SeekingAlpha via Finnhub) has the summary "Thursdayâ\u0080\u0099s 4.4% drop…".
  - **Source:** a direct Finnhub `/company-news` call returns the same bytes. Finnhub sends it this way, and Argus passes it on.
- suggestion: repair text that round-trips cleanly through `s.encode('latin-1').decode('utf-8')` when it contains `â€`/`Ã` sequences.

### 8. Re-sightings (short)
- **Analysis Targets & drift** still opens on "By sector, ETF 100%, Targets sum to 0.0%", although 10 position targets summing to 100% are saved and the API reports `targets_sum_pct 100` (B-022).
- **Brief:** `dividends_upcoming` is empty (B-136). `theses_due` lists **19** notes, most of them superseded (B-127). There are no macro events, so CPI on Tuesday isn't in the brief (B-038).
- **Look-through:** "Unclassified" is **39.4%**: SGOV, IEF, VTIP and DBC have no asset class or duration (B-017). AGPXX (DBC's cash sleeve) is listed as a "stock exposure" (B-030).
- **Calendar:** CPI, Core CPI, PPI, retail sales, industrial production, housing starts and PCE are all unlabeled m/m and y/y twins (B-091). For CPI week this matters most: the two "CPI" rows differ only by "previous 3.7%" vs "0.6%".
- **`/t/QUAL`** still requests SEC financials for an ETF and gets a 502 in the console (B-092).
- **10-year yield card** in the API: `returns.1D 0.45` is a percent of the yield, while the UI shows "+2 bp" (B-029).

## Consistency checks that passed
- **Performance after the SPLIT:**
  - the 11-05 value of $97,105.73 matches last round's hand-computed true value;
  - 11-06 minus 11-05 = −$112.09 = Day P&L = the risk "Last session" tile = brief totals;
  - net invested $98,628.52 = cost $98,404.56 + realized loss $287.03 − accrued dividends $63.08.
- **Simulate (with `side`):**
  - net cash −95.85 = 30 × 61.62 − 9 × 216.05;
  - realized −174.30 = 30 × (61.62 − 67.43).
- **COVID stress −22.1%:** my own weighted sum of each ETF's Feb–Mar 2020 move gives about −22.8%, so it agrees.
- **Curve:** 2s10s 35 bp = 4.86 − 4.51, and 10s3m 67 bp = 4.86 − 4.19, matching the curve table.
- **Term structure:** VIX 25.64 ÷ VIX3M 24.60 = 1.04, which matches the term-structure component.
- **Fear & greed** loaded all 7 components on the first call this round. Breadth was ready, so no partial reading.
- **QUAL dividend:** 0.11825 × 4 ÷ 54.83 = 0.86%.
- **Timings:**
  - portfolio, performance, drift, dividends and exposure took 20–50 ms;
  - risk took 0.41 s (warm);
  - market context took 1.3 s and the brief 1.4 s;
  - pages rendered with no page errors and no horizontal overflow, except the QUAL 502.

## Summary for the round lead
1. **Recorded the QUAL SPLIT (txn 55); no market trades.** The post-NFP SPY add failed its VIX/VIX3M < 1 leg (1.04). I'm holding XLE→RSP through CPI 11-10 (note 82). loop-macro is $96,993.64, cash $1,308.41, return to date −1.70%.
2. **Confirmed fixes:**
   - B-140 works end to end: value $96,994, TWR −1.67%, no 11-05 jump, warning cleared, drift sane, QUAL yield 0.86%.
   - B-141 (December dates) and B-142 (Last session = Day P&L −$112) also work.
   - Payrolls actuals now show in the calendar.
3. **Top findings:**
   - **medium:** simulate silently turns a trade without `side` into a BUY and ignores `type`;
   - **medium:** gold/oil 1D shows the Sunday futures tick (+1.5%) on a −0.9% session (B-016/B-055);
   - **low-medium:** the split warning was missing on the first summary after the restart, until the bars refreshed;
   - **medium:** VaR and beta still understate realized risk (B-067);
   - **low:** VTIP rate vs footnote, a stale DBC after-hours print, and Finnhub mojibake.
