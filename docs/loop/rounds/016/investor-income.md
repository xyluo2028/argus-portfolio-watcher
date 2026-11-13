# Round 016: income investor

## What I did
- **Market (Argus market context, reviewed Thu 11-12 ~21:15 ET, latest close Thu 11-12):**
  - A soft day for stocks: S&P 500 −0.35% to 7592.40, Russell 2000 −1.66%. VIX rose to 18.70 (+1.21).
  - Bonds sold off. ^TNX went 4.998 → **5.103** (+10.5 bp, `/api/quotes?symbols=^TNX`). The Treasury curve for 11-12 has the 10-year at 5.10% and the 2-year at 4.86% (4.73% last round), so the 10y–2y spread is +24 bp.
  - The 30-year auction cleared at 5.441% (in the calendar's `all_events`). Jobless claims came in at 200K against 194K expected.
  - PPI is out Fri 11-13 at 08:30 (consensus 0.4% m/m). HD reports 11-17 before the open. FOMC is 12-09.
  - Fear & Greed reads 25.3, "Fear", on five components.
- **Portfolio `loop-income` (11-12 close, `argus portfolio show --json`, before my trades):**
  - Value $102,665.67, cost $99,950.30, unrealized +$2,715.37.
  - Day P&L −$267.96 (−0.26%) against SPY −0.35%.
  - The bond sleeve did most of the damage: BND −$76.05, VCIT −$68.04, VGIT −$43.40 and SCHP −$21.56, so **−$209.05** in all. XOM (+$73.68) and JNJ (+$59.09) offset part of it.
  - Performance: TWR +2.93% since 10-20 against SPY −1.55%, so +4.48% excess. Gain $2,899.51 = unrealized $2,715.37 + accrued dividends $184.14, to the cent.
- **Bond sleeve, by hand again (B-017):**
  - My regression durations from last round (BND 5.42, VCIT 5.74, VGIT 4.80, SCHP 4.06) give −$906 per +50 bp.
  - For +10.5 bp that predicts −$190. The sleeve actually lost −$209. That's the third out-of-sample check in a row within about 10%.
- **Risk** (`/risk`, after the trade): beta 0.164, volatility 7.92%, VaR 95% $677, max drawdown −5.73%. Stress: 2022 rate shock −14.1%, "SPY −10%" −1.6%.
  - Last session (11-12) shows −$268 "held that session". That matches Day P&L, and it stayed −$267.96 after my evening trades.
- **Income** (`/dividends`):
  - Forward income was $3,408.10 before the trade, against $3,344.27 last round with no trade in between. After the trade it is **$3,425.64**.
  - Yield is 3.34% (= 3,425.64 ÷ 102,702.18). On cost it is 3.42% (÷ 100,042.70). I checked both by hand.
  - 2026: $184.14 received (est.) plus $610.75 projected, so $794.89.
  - Next up: O pays 11-13, PG pays 11-16, XOM goes ex 11-16, MSFT ex 11-19, JNJ ex 11-24, NEE ex 11-27.
- **Decision: my rule fired, so I made a small bond add.**
  - Notes 67, 81 and 87 say to add bonds only if the 10-year is above 5.1% and drift calls for it. Alert 10 (BND ≤ 70.70, my stand-in for the 10-year at 5.1%) fired at 70.65, and ^TNX closed at 5.103.
  - Drift was within band. The bond sleeve was at 33.9% against a 35% target, and BND (−0.37 pp) and VCIT (−0.33 pp) were the most underweight. HD (+0.43 pp, my largest risk contributor at 13.5%, reporting 11-17) and JNJ (+0.25 pp) were the most overweight.
  - I rebalanced those four lines to target at 5%+ yields instead of growing the sleeve before PPI. Simulated first, then entered at the 11-12 closing quotes:
    - SELL 1 HD @ 348.26 (txn 60). FIFO lot, realized +$31.98.
    - SELL 1 JNJ @ 283.52 (txn 61). Realized +$23.91.
    - BUY 5 BND @ 70.65 (txn 62).
    - BUY 4 VCIT @ 78.76 (txn 63).
  - Effect: forward income +$17.54 a year (+15.42 BND, +16.80 VCIT, −9.32 HD, −5.36 JNJ). The bond sleeve is now 34.5%, BND 11.97%, VCIT 9.97%, HD 5.09% and JNJ 4.97%.
  - Wrote thesis note 88 (BND, review 11-19). Set alert 11, `BND price_below 69.30`, as a stand-in for the 10-year at about 5.35%, my next add trigger. ^TNX was rejected again (B-078).
- **Cash: $13.19.**
  - Calculation: $49.70 + 348.26 + 283.52 − 353.25 − 315.04.
  - Invested at cost is $100,042.70, against $100,000 plus $55.89 realized.
  - Return to date: (102,702.18 + 13.19 − 100,000) ÷ 100,000 = **+2.72%**. With the $184.14 of accrued dividends it is +2.90%, but Argus doesn't book those as cash, so I don't count them as spendable.

## Last round's changes
- **B-156 (one failed day no longer empties the calendar): the normal path works.** Tonight Nasdaq answered.
  - `calendar.events` has 40 curated rows, `all_count` is 181, and there is no `errors.events`.
  - Thursday's claims actual (200K vs 194K) and Friday's PPI consensus are both visible, so the empty-calendar problem from last round is gone.
  - I couldn't see the partial-failure path (the "k of 24 days unavailable" note) because no day failed. I didn't find the live server's `econ_releases.json`; only pytest temp copies turned up.
- **B-152 (Risk Last session = Day P&L): works.** After four evening trades, Analysis → Risk shows "Last session (11-12) −$268, −0.26% · held that session". `last_day.basis` is `session_holdings` and `value` is −267.96. That's the same as Dashboard's "−$267.96 (−0.26%) last session" and the portfolio's `day_pnl`. B-117 still holds: Day P&L didn't change after I sold.
- **B-157:** not in my workflow.
- **Re-seen, still open:**
  - **B-148 (SCHP): partly better.**
    - SCHP now projects 0.10383 a month (= trailing 1.246 ÷ 12) on 12-01 and 12-18. So twelve payments would now add up to the annual figure.
    - But its latest actual payment was 0.08 (11-02). The December projection ($40.70) is 30% above what the latest payment implies ($31.36).
  - **B-153: the 11-02 bond payments are now actual** (no `estimated_date`; BND 0.257, VCIT 0.35, VGIT 0.199, SCHP 0.08). But forward income moved +$63.83 with no trade (finding 4).
  - **B-044:** "Where the risk comes from" still lists 15 of 17 holdings.
  - **B-022:** Targets & drift still opens on "By sector" with "Targets sum to 0.0%".
  - **B-118:** `/analysis?portfolio=loop-income` still opened loop-growth (localStorage stayed `loop-growth`).
  - **B-127:** the brief's `theses_due` still lists notes 67 and 81, which note 87 replaced.
  - **B-043/B-062:** KO yields 2.68% on fundamentals against 2.18% on Dividends. Its payout is 76.8% on Dashboard against 62.4% from Argus's own rate ÷ EPS.

## Findings

### 1. My bond-add rule fired today, and Argus still can't tell me what the sleeve is worth per basis point (B-017)
- kind: feature
- severity: high (34.5% of the book; I traded on a rate trigger today using numbers I computed outside Argus)
- evidence:
  - ^TNX rose 10.5 bp to 5.103. My duration estimate from Argus's own 1-year history predicted −$190, and the sleeve lost −$209.05. Over the last three rounds the estimate has been within about 10% every time.
  - Argus still shows the four bond ETFs as "Unclassified 34.5%" (`/exposure`, and simulate's `sector_lookthrough_after`).
  - Stress scenarios have no "10y +50/+100 bp" row.
  - The Dividends "Fwd yield" for BND is 4.37%, which is the distribution rate (0.257 × 12 ÷ 70.65). With the 10-year at 5.10%, BND's yield to maturity is clearly higher. A client asking "what are we locking in?" gets the lower figure.
- suggestion: as proposed before, add an "Est. rate sensitivity (1y regression vs ^TNX)" figure per bond fund and "10y +50 / +100 bp" stress rows, labelled as estimated. Separately, label Fwd yield as "distribution yield" for funds.

### 2. First risk load took 53.5 s, the slowest yet (B-026)
- kind: perf
- severity: medium (Risk is the card I open first on a rate-shock day)
- evidence:
  - The first `GET /api/portfolios/loop-income/risk` of the evening took 53.48 s (`curl -w`). It was 31.5 s last round and 25.6 s the round before.
  - The second call, after my trades, took 0.61 s.
  - Every other endpoint took under 1 s: dividends 0.67 s, exposure 0.75 s, drift 0.10 s, performance 0.08 s, brief 0.66 s.
- suggestion: warm risk in the background after startup and after the daily bars land, as B-026 already proposes. The trend is getting worse.

### 3. A yield alert still needs a duration proxy (B-078). The proxy fired correctly, but only because I did the math
- kind: feature
- severity: medium
- evidence:
  - `argus alert add '^TNX' price_above 5.35` returns `INVALID_SYMBOL: '^TNX' doesn't look like a US ticker.`
  - My stand-in, alert 10 (`BND price_below 70.70`), fired at 70.65 on the day the 10-year closed at 5.103. That only lined up because my by-hand duration (5.4) was right.
  - I set alert 11, `BND ≤ 69.30`, for the next trigger the same way.
- suggestion: allow `^`-prefixed index and yield symbols for `price_above`/`price_below`. The quote path already returns ^TNX.

### 4. Forward income rose $63.83 with no trade, and nothing says why (B-153)
- kind: ux
- severity: medium (I report this number to clients, and a 2% jump needs an explanation)
- evidence:
  - Last round, forward income was $3,344.27. Tonight, before any trade, `/dividends` `totals.annual_income` was $3,408.10.
  - The bond funds' rates now come from the actual 11-02 payments: BND 3.084 (= 0.257 × 12, against a 2.953 trailing figure) and VCIT 4.20 (= 0.35 × 12, against 4.006 trailing).
  - SCHP uses its 1.246 trailing figure even though its latest payment, 0.08 × 12, is 0.96.
  - So two monthly funds annualize their latest payment and one uses its trailing 12 months. The footnote still says "latest payment × payments per year" (B-063).
- suggestion: show which basis each holding uses (latest × freq or trailing 12m) in the Dividends table. Flag a change in forward income since the last view that isn't caused by a trade.

### 5. Simulate doesn't show the income effect of a rebalance (B-023)
- kind: feature
- severity: medium
- evidence:
  - `POST /simulate` with SELL 1 HD, SELL 1 JNJ, BUY 5 BND and BUY 4 VCIT returned weights, concentration and sector look-through.
  - It returned no `annual_income_after` or yield after, and no bond-sleeve weight.
  - I had to diff `/dividends` before and after the real trade to learn it adds +$17.54 a year.
  - `value_after` (102,702.18) is $36.51 above `value_before`. That's the net cash I put in, not value the trade created.
- suggestion: add `annual_income_before/after` and `yield_after` to simulate (holding qty × the Dividends rate), and a `net_cash` caption next to `value_after`.

### 6. A stale-looking VCIT print supplies half of tonight's after-hours P&L (B-108)
- kind: bug
- severity: low
- evidence:
  - Dashboard shows "After hours +$144.90 (+0.14%)". VCIT's row shows "AH +0.70%" from a 79.31 print at 6:02 PM ET (`ext_as_of` 23:02:30Z), worth +$71.6.
  - At the same time BND was +0.13% and VGIT −0.15%. A +0.70% move in an intermediate corporate bond fund after a −0.68% session, while Treasuries fell further, isn't plausible.
- suggestion: as B-108 proposes, show the print time on the row and leave prints that contradict their peers, or that are hours old, out of after-hours P&L.

### 7. At 390 px, the Stress table is still 855 px wide in a 324 px box, so every loss figure is hidden (B-002)
- kind: ux
- severity: low (re-check of last round's finding 3)
- evidence:
  - In Playwright at 390 px on `/analysis` (loop-income), the stress table's `scrollWidth` is 855 and its container's `clientWidth` is 324 (`overflow-x: auto`).
  - The screenshot shows Scenario and a cut-off Window column. "Your portfolio (est.)" and "Change in value" are off-screen, with no scroll hint.
- suggestion: on phones, hide the Window column and show Scenario, Your portfolio and Change in value.

### 8. Payout for a REIT is on GAAP EPS: O shows 223%
- kind: ux
- severity: low
- evidence:
  - Dashboard → Dividends shows O with Payout 223.3% (Finnhub `payout_ratio_pct` 223.28; Argus rate ÷ EPS gives 223.6%).
  - REIT payout is judged on FFO/AFFO. On those, O is around 75%. A client reading 223% would think the dividend is at risk.
  - ABBV's 117.4% has the same problem: GAAP EPS hit by one-off charges.
- suggestion: for REITs, show "n/m (REIT: use FFO)" or compute payout on operating cash flow. That's related to B-070 (FCF payout) and B-131.

## Summary for the lead
- **Trade:** the 10-year closed at 5.103%, above my 5.1% trigger, and proxy alert 10 (BND ≤ 70.70) fired. I sold 1 HD @ 348.26 and 1 JNJ @ 283.52 and bought 5 BND @ 70.65 and 4 VCIT @ 78.76 (txns 60–63). That adds $17.54 a year of income and realizes $55.89. Note 88, alert 11 (BND ≤ 69.30 as a stand-in for the 10-year at 5.35%). Cash $13.19, return to date +2.72%, TWR +2.93% against SPY −1.55%.
- **Confirmed:** B-152 works after evening trades (Risk Last session −$268 = Day P&L). B-156's normal path works now that Nasdaq answers (40 curated rows, claims actual, PPI consensus); the partial-failure path wasn't observed. B-153's 11-02 bond payouts are now actual.
- **Top items:** B-017 (I traded a rate trigger on my own duration math, which predicted −$190 against −$209 actual). B-026: first risk load 53.5 s, the worst yet. B-078: ^TNX alerts are still rejected. Forward income moved +$63.83 with no trade because of a mixed rate basis (B-153/B-063). Simulate has no income-after (B-023).
