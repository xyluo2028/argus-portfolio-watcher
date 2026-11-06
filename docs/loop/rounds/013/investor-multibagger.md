# Round 013: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:45 UTC on Fri 2026-11-06, which is Thu 11-05 evening ET, after the close. Prices are the 11-05 close plus post-market quotes. Yahoo's daily bars end at 11-04, so Argus fills 11-05 from the quotes (B-134).
- **Market:** heavy risk-off day. SPY −4.41%, QQQ −6.49% and IWM −4.59%. Semis were hit hardest: SMH −11.2%, SOXX −12.2%, MU −17.5%, AMD −17.3% and MRVL −16.4% (`argus quotes`).
- **Book before trades** (`GET /api/portfolios/loop-growth`, 0.30 s): 11 positions, value $95,417.18, Day P&L **−$4,278.62 (−4.29%)** against IWM's −4.59%. After hours the book was +$949.92, mostly TMDX (+11.6%) and INOD (+8.0%) on their reports.
  - RMBS fell −15.9% with the semis rout. Argus has no company news for it, so I treat it as a price move, not a thesis break (note 75).
- **Seven holdings reported this week.** I checked each one against its written exit line, using SEC quarterlies from `/api/financials`. The 10-Qs were already in Argus for six of them.

| Symbol | Q3 revenue y/y | Prior quarter | Op margin | Exit line | Verdict |
|---|---|---|---|---|---|
| LOAR | +39.0% | +39.4% | 26.2% (Q2 24.4%) | margin < 20% | strengthened; **add** |
| TMDX | +41.1% | +20.7% | 13.9% (Q2 12.5%) | growth < 15% | passed; **add** |
| INOD | +52.9% | +57.8% | n/a (net 10.8%, Q2 15.6%) | growth < 25% / customer loss | hold; Q3 OCF −$84M |
| BLLN | +47.2% | +64.4% | 9.0% | growth < 30% | hold |
| PODD | +19.2% | +23.5% | 22.5% (16.7% a year ago) | growth < 15% | hold, slowing |
| GRND | ~+22% (headline only) | +32.5% | — | growth < 20% | hold, re-check when the 10-Q lands |
| HRMY | +12.3% | +30.3% | 20.2% (27.3% a year ago) | growth < 10% | **exit** |

- **Trades (all through `argus txn add`):**
  - SELL 205 HRMY @ 32.47, the 11-05 close (txn 51). Realized **−$1,324.30**.
    - It was still above the hard <10% line, but both thesis pillars broke in the same quarter (24% growth and 24% op margin). EPS was −30% vs consensus, and gross margin fell 5 pp.
    - A single-product franchise with generic risk is not a compounder. Note 70 records the reasoning.
  - BUY 65 TMDX @ 77.00, the post-market quote (txn 52). TMDX is now 14.0% of capital at cost, so no more adds (thesis note 71).
  - BUY 20 LOAR @ 72.02, the post-market quote (txn 53). LOAR is now 12.4% at cost (thesis note 72).
  - Notes 73–77 cover INOD, GRND, RMBS, PODD and BLLN.
- **Hunt:** I ran two screens (`POST /api/screener`, 7 ms each).
  - Screen B: cap $1–20B, growth ≥25%, op margin ≥10%, FCF ≥10%, ROE ≥15%, P/S ≤10. It returned 7 names, and 4 of them I already own. The other three:
    - GPOR is an energy name, which doesn't fit.
    - NUTX and JOE I passed on earlier.
  - Screen C (gross margin ≥50%) adds VIAV, TAL and CTO. All are low quality or don't fit.
  - Both screens are still FY2025-only (B-019).
  - My watchlist's **MNTN fell −54.7%** on a ~10% revenue miss. It sat in last round's Screen A and I passed on it.
  - No new buys.
- **After trades:** 10 positions, cost $98,287.80, value **$94,704.33**, realized −$1,324.30, cash **$387.90**.
  - Return to date = (94,704.33 + 387.90 − 100,000) ÷ 100,000 = **−4.91%**.
  - By value, LOAR is the largest position at 15.0% (12.4% at cost). Healthcare is 45.7% and technology 39.3%.

## Last round's changes
- **B-134 (the last session's close comes from the quote): works and helped.**
  - `/performance` reports `closes_from_quotes {date: 2026-11-05, symbols: [all 11 + IWM]}`.
  - The last step, 95,417.18 − 99,695.81, is −4,278.63, which equals Day P&L (−4,278.62).
  - IWM's step, 0.982595 ÷ 1.029879 − 1, is **−4.59%**, which equals IWM's quote.
  - Earnings reactions for tonight's after-close reports use the 11-05 close as base: TMDX base 68.98 → +11.63% and INOD base 38.62 → +8.04%, both labeled "after hours". This was exactly last round's finding 1.
  - The Dashboard, the Performance card and the brief all agree (screenshot at 390 px).
- **B-137 (Reported financials table missing the just-reported quarter): partly moot, still open.**
  - SEC 10-Qs arrived the same day for TOST (op margin 8.3%, up from 8.0%), HRMY, PODD, BLLN, LOAR, TMDX and INOD, so their tables are complete.
  - GRND (reported tonight, no 10-Q yet) shows the gap again, worse than before: see finding 1.
- **B-119 (EPS basis): still broken**, with new evidence in finding 3.
- **B-138 (Estimates "This quarter" is the quarter that just reported): partly.**
  - TOST's `0q` has rolled to Q4: 0.362 vs 0.373 two days ago.
  - LOAR (`0q` 0.329) and TMDX (0.293) are still the Q3 consensus they reported against today. The label problem remains for the first day or two after each print.
- **B-132 (last report has no date): improved by new data.** 9 of 11 rows now have `last.date`, because each one reported this week. ESE still has only a period.

## Findings

### 1. A company that reported tonight drops out of every "what's happening" view until Finnhub fills the actuals (GRND)
- kind: bug
- severity: medium (the night of a print is when I need it, and the press release is already in Argus)
- evidence:
  - GRND released Q3 at 21:05 UTC (16:05 ET). Research → News has "Grindr Inc. Reports Third Quarter 2026 Revenue Growth of 22%, Raises 2026 Guidance…". At 02:20 UTC Argus still shows:
    - **`/api/earnings/GRND`:** `next: {date: 2026-11-05, timing: amc}`. `reports[0]` is Q2 2026, with no Q3 row.
    - **`/t/GRND` (1400 px):** the Events card says "Nothing scheduled". The Reported financials header still says "Next report Thu, Nov 5, after close". The table ends at 2026-06-30.
    - **Dashboard "Coming up" (390 px):** lists the other seven reports this week as "Reported", but GRND appears **neither as upcoming nor as reported**.
    - **`/api/brief/loop-growth`:** `earnings_recent` does include GRND, with no actual.
  - So one event shows four different ways in one evening.
- suggestion:
  - Once the scheduled time has passed, show the row as "Reported, results pending". Use the post-market price move as the provisional reaction (the same as TMDX/INOD's "after hours" reaction, which already works).
  - Link the matching press-release headline.
  - Make "Next report" switch to "Reported today" after the time passes.

### 2. The brief's `watchlist_movers` is still empty while a watchlist name fell −54.7% (B-106)
- kind: bug
- severity: medium (I learned about MNTN's collapse only by opening the watchlist)
- evidence:
  - `GET /api/brief/loop-growth` returns `watchlist_movers: []`.
  - `GET /api/watchlists/growth-candidates` shows MNTN −54.7% (Q3 revenue $80.3M vs $89.4M estimate, from `/api/earnings/MNTN`; reaction −54.68%), VICR −15.1%, BELFA −11.2% and XZO −10.9%.
- suggestion: as filed. Feed the named watchlists into the brief's movers and earnings.

### 3. Finnhub "adjusted" EPS is GAAP for some companies and adjusted for others, so the surprise % is unreliable (B-119)
- kind: bug
- severity: medium
- evidence: from `/api/earnings/<sym>` (all three labeled `eps_basis: "adjusted"`) against SEC diluted EPS from `/api/financials`.
  - **INOD:** Finnhub actual 0.29, SEC 0.29, so it's GAAP. Argus shows a "beat +68.2%" against est 0.1724. The Zacks headline in the same brief says a surprise of **+38.10%**.
  - **LOAR:** Finnhub actual 0.39, SEC 0.20, so it's adjusted. Argus shows +16.3%.
  - **TMDX:** Finnhub actual 0.51, SEC 0.46. Argus shows +71.3%.
- suggestion: compare the provider actual with SEC diluted EPS for the same period. When they match, label it "GAAP". When they don't, label it "adjusted". When the bases differ, show the surprise only against an estimate on the same basis, or show both.

### 4. Simulate still prices trades at the 4 pm close during post-market (B-109)
- kind: bug
- severity: medium (I sized TMDX off a price $8 below where I could actually buy)
- evidence:
  - `POST /api/portfolios/loop-growth/simulate` for SELL 205 HRMY, BUY 65 TMDX and BUY 20 LOAR returned TMDX at **68.98** and LOAR at **72.99**.
  - The quotes' `ext_price` was **77.00** (+11.6%) for TMDX and 72.02 for LOAR.
  - Net cash came out at +$347.90. The real figure at post-market prices is +$210.95, and nothing says which price was used.
  - The simulator also reports weights by value (LOAR 15.3%), while my limit is by cost. Showing both would help.
- suggestion: as filed. Use `ext_price` when `ext_session` is pre or post, and echo `price_basis` per trade.

### 5. INOD's prepayment windfall is reversing (Q3 operating cash flow −$84M) and nothing flags it
- kind: feature
- severity: low (follow-up to B-111)
- evidence:
  - `/api/financials/INOD` quarterly OCF: Q2 **+$127.2M**, Q3 **−$84.0M**, on revenue of $92M and $96M.
  - The stock page's FCF margin still reads off TTM, which is inflated by Q2. Nothing says the cash came in early and is now going back out.
- suggestion: flag a quarter where |OCF| is more than half of revenue, or where OCF changes sign by more than revenue. "Working-capital swing: Q2 +127M, Q3 −84M" on the Valuation card would do.

### 6. Quote open below the day's low (LOAR open 69.99, low 70.21) (B-098)
- kind: bug
- severity: low
- evidence: `argus quotes LOAR --json` returned `open 69.99, high 76.01, low 70.21` on 11-05. This is the same class as MNTN's open above its high.
- suggestion: as filed. Clamp the low to min(open, low), or take OHLC from one source.

### 7. Cold loads are still slow: watchlist 8.8 s, LOAR earnings 6.7 s, Peers on "Loading…" after 6 s (B-026, B-097)
- kind: perf
- severity: low
- evidence:
  - First `GET /api/watchlists/growth-candidates` took 8.78 s.
  - First `/api/earnings/LOAR` took 6.65 s, HRMY 3.19 s and BLLN 3.39 s.
  - `/api/portfolios/loop-growth/earnings` took 3.73 s.
  - In the `/t/GRND` screenshot with `--settle 6`, Peers still reads "Loading…".
  - Portfolio took 0.30 s, performance 0.03 s and financials ~0.03 s.
- suggestion: as filed.

### 8. Phone Dashboard: the Coming up and Holdings tables clip at the right edge
- kind: ux
- severity: low
- evidence: `/` at 390 px shows "EPS est. 2." and "EPS 0.37 v" cut off. The Holdings table shows Qty, then a cut-off "A…" column. There is no page overflow (the script reports `horizontal_overflow: false`), so the content is clipped inside the card with no scroll cue.
- suggestion: on phone width, put the EPS detail on a second line under the symbol, or show a fade or scroll hint on clipped tables. Related to B-002.

## Summary
1. **Trades:**
   - Sold all 205 HRMY @ 32.47, realized −$1,324.30. Growth halved to +12.3% and op margin fell to 20.2%.
   - Added 65 TMDX @ 77.00 (Q3 +41%) and 20 LOAR @ 72.02 (Q3 +39%, op margin 26%).
   - Cash is **$387.90** and value $94,704.33, so return to date is **−4.91%**, after a −4.29% day in a semis-led selloff.
2. **B-134 works:** performance's last step equals Day P&L, IWM is −4.59%, and the TMDX/INOD after-hours reactions are correct.
   - **Still broken:**
     - B-106: watchlist movers are empty while MNTN fell −54.7%.
     - B-119: Finnhub "adjusted" EPS is GAAP for INOD and adjusted for LOAR.
     - B-109: simulate uses the close in post-market.
3. **New:** a company that reported tonight (GRND) shows four different ways across Argus, and is missing from Coming up entirely, until Finnhub fills the actuals.
