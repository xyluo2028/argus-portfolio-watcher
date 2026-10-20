# Round 001: income investor

## What I did
- **Market view (from Argus market context):** 10-year Treasury at 5.10% (+28% over 1 year), curve upward-sloping
  from 2 years out (2Y 4.77%, 10Y 5.15%, 30Y 5.48%), WTI at $96, Fear & Greed 38 ("Fear"), and FOMC on Oct 28.
  Bond ETFs are within about 1.5% of their 52-week lows. Locking in about 4 to 5% on high-quality duration looks
  attractive for clients who live on income, so I put 35% in bonds (the floor is 30%).
- **Research:** pulled yield, payout ratio, 5-year dividend growth and beta for 18 candidates
  (`/api/fundamentals/{sym}`). I dropped TXN (payout 84%, beta 1.4). I kept ABBV and O even though their GAAP
  payout ratios are 190% and 236%, because amortization and AFFO make GAAP payout misleading for them. I flagged
  both in their theses.
- **Created `loop-income` (benchmark SPY) and bought 17 positions on 2026-10-20 at the live quote**, one thesis
  note each (review on 2027-01-20). I then set symbol targets equal to the intended weights:
  - Bonds, 35%: BND 169 @ 70.78 (12%), VGIT 140 @ 57.08 (8%), VCIT 126 @ 78.89 (10%), SCHP 196 @ 25.43 (5%)
  - Dividend ETFs, 15%: SCHD 288 @ 34.63 (10%), VIG 20 @ 243.17 (5%)
  - Stocks, 50%: JNJ 19 @ 259.61, PG 31 @ 158.53, PEP 37 @ 134.46, JPM 14 @ 336.50, HD 15 @ 316.28,
    ABBV 17 @ 288.73 (5% each); KO 42 @ 93.11, XOM 22 @ 176.15, NEE 50 @ 79.15, O 71 @ 56.20,
    MSFT 7 @ 530.51 (4% each)
- **Invested at cost: $98,347.12. Cash: $1,652.88.** Realized gains: $0.
- **What Argus says I own:** forward income $3,217.53 a year (3.27% yield). Beta 0.15, volatility 7.2%,
  1-year max drawdown −5.6%, 1-day 95% VaR $668. The 2022 rate-shock replay shows −14.0%. All 17 positions are
  inside the ±2 pp drift band.
- **Alerts:** below_cost 10% on O, 12% on NEE and 8% on SCHD; day_loss 4% on XOM.
- **Simulation:** swapping SCHP into VCIT. I didn't trade, because the simulation can't show what the swap does
  to income (see finding 8).

## Last round's changes
None. This is the first round.

## Findings

### 1. The TIPS ETF's income is understated by half: the run rate uses one lumpy monthly payment
- kind: bug
- severity: high
- evidence:
  - `GET /api/portfolios/loop-income/dividends` for SCHP returns `rate 0.672` (last payment 0.056 × 12) but
    `trailing_12m 1.258`, with `irregular: false`. That gives a yield of 2.64% and $131.71 a year.
  - `/api/fundamentals/SCHP` gives `dividend_yield_pct 5.10`, and 1.258 / 25.43 is 4.95%.
  - TIPS distributions swing with CPI accruals, so the last payment × 12 is the wrong estimate. Portfolio
    forward income is understated by about $115 a year (196 × (1.258 − 0.672)).
  - The Analysis page shows "$0.672 · 2.64%" with no warning.
- suggestion:
  - Flag a payer as irregular when the last payment differs from the 12-month average by more than about 30%.
  - For irregular payers, use the trailing 12 months as the annual rate.

### 2. The "Stocks / ETFs" tile on Analysis shows the numbers in the wrong order
- kind: bug
- severity: medium
- evidence:
  - The tile reads "Stocks / ETFs **51% / 49%**", but stocks are 49.4% and ETFs 50.6% (`/exposure` `by_type`).
  - The subtitle underneath says "ETF / Stock". `frontend/src/pages/Analysis.tsx:23-25` joins `by_type` in
    weight order under a fixed label.
- suggestion: look up the Stock and ETF entries by key instead of relying on array order.

### 3. Bonds are invisible as an asset class, and there is no rate sensitivity
- kind: feature
- severity: high
- evidence:
  - My 35% of bond ETFs shows up only as "ETF" (direct sectors) or "Unclassified 35.5%" (look-through). It is
    grouped with the equity ETFs SCHD and VIG in the dashboard's sector card ("ETF 50.6%") and in sector targets.
  - `/exposure` lists `funds_without_profile: [BND, VCIT, VGIT, SCHP]`.
  - I can't check my "at least 30% bonds" rule, set an asset-class target, or see duration. How rates on the
    curve affect my bonds is the main risk question for this book, and the only answer is the 2022 rate-shock
    replay.
- suggestion:
  - Add an asset-class split (equity / fixed income / other) to exposure and to the drift targets. Even an
    ETF-category lookup would do.
  - Add effective duration per bond ETF and a "+100 bp parallel shift" scenario (−duration × 1%) next to the
    stress scenarios.

### 4. Upcoming dividends disagree across Dividends, Coming up, the brief and events
- kind: bug
- severity: medium
- evidence:
  - Dividends projects ex-dates for PG (~10-24), O (~10-30) and the four bond ETFs (~11-01).
  - The dashboard's "Coming up · earnings & dividends, next 14 days" lists only earnings.
  - `/api/brief/loop-income` returns `dividends_upcoming: []`.
  - `/api/events?portfolio=loop-income` lists an ABBV `dividend_pay` on 11-16, with `held: true`. I bought after
    the 10-15 ex-date, so I won't receive it, and Dividends correctly projects $0 for ABBV.
  - Smaller issues in the projection itself:
    - Some estimated ex-dates fall on weekends: PG on Sat 10-24, NEE on Sat 11-28, and the bond ETFs on
      Sun 11-01.
    - JPM and ABBV have `next_ex_date_est: null` because their next ex-date falls in 2027.
- suggestion:
  - Feed estimated ex-dates (marked "est.") into Coming up and the brief.
  - Skip pay events for payments the position isn't entitled to.
  - Move estimated dates to the nearest business day.
  - Compute the next ex-date regardless of the calendar year.

### 5. XOM earnings are listed twice, on different dates
- kind: bug
- severity: medium
- evidence:
  - `/api/events` and the dashboard's Coming up show XOM earnings on both Fri Oct 23 and Fri Oct 30. Both
    entries have EPS est. 4.11 and revenue est. 103.49B.
  - `/api/earnings/XOM` gives `next.date 2026-10-23`.
- suggestion: deduplicate earnings per symbol and fiscal quarter, keeping the date the earnings endpoint
  reports.

### 6. Two different betas, and a "SPY −10%" scenario that understates the risk
- kind: ux
- severity: medium
- evidence:
  - Fundamentals beta (Finnhub, longer window) vs risk beta (252 days):
    - SCHD: 0.71 vs 0.22
    - KO: 0.28 vs −0.26
    - XOM: 0.17 vs −0.67
    - JNJ: 0.21 vs −0.20
  - I recomputed the 252-day betas from Argus's own `/api/history` closes and they match, so the arithmetic is
    right. The 1-year regime is just unusual.
  - The scenario "SPY falls 10% (via beta)" tells a client −1.5%. On the same page the historical replays show
    −14% (2022), −22% (COVID) and −25% (2008). The factor regression gives market beta 0.36.
  - A client handout with "beta 0.15" would mislead.
- suggestion:
  - Label each beta with its source and window.
  - Next to the beta scenario, show the factor-model beta or a 3-to-5-year beta, or note that a 1-year beta is
    unstable for low-correlation holdings.

### 7. Targets & drift opens on "By sector" with empty inputs, although I set targets by position
- kind: ux
- severity: medium
- evidence:
  - I set symbol targets with `argus portfolio targets loop-income symbol ...`, and `/drift` returns
    `level: symbol` with all 17 targets.
  - The Analysis "Targets & drift" card defaults to "By sector", with blank target boxes and "Targets sum to
    0.0%". It looks as if no targets exist until you click "By position".
- suggestion: open on the level that has targets saved.

### 8. Simulate and alerts can't answer income questions
- kind: feature
- severity: medium
- evidence:
  - `POST /api/portfolios/loop-income/simulate` with SELL 196 SCHP / BUY 63 VCIT returns weights,
    concentration and sectors. It doesn't return the change in forward income or yield, the drift after the
    trades, or the change in beta. Income and drift were the deciding questions, so I didn't trade.
  - The alert kinds are price, move, 52-week, P/E, cost and earnings only. `argus alert add O
    dividend_yield_above 7` gives "Unknown alert kind".
  - There are no alerts for a dividend cut or raise, an ex-date within N days, a position drifting outside its
    band, or the yield or payout ratio crossing a level.
- suggestion:
  - Add `income_before/after` and `drift_after` to the simulate result.
  - Add the alert kinds `dividend_change`, `ex_div_within_days` and `drift_outside_band`.

### 9. Risk, events and the brief take 11 to 15 seconds on first load
- kind: perf
- severity: low
- evidence:
  - First calls after buying: `/risk` 15.3 s, `/events?portfolio=…` 13.7 s, `/brief/loop-income` 11.1 s.
  - Repeat calls: 0.32 s, 0.02 s and 0.03 s (cache).
  - Dividends: 2.3 s cold.
  - The UI pages render in 0.15 s, but their risk and event sections fill in late.
- suggestion: warm these caches when a portfolio's holdings change, in the background after a trade.

### 10. Day-one figures and brief labels contradict each other
- kind: ux
- severity: low
- evidence:
  - On the dashboard, "Unrealized P&L −$75" sits above "Performance vs SPY … Gain $0".
  - `/performance` reports `net_invested: 0` with `flow_in 98,347` on the same day.
  - In `/api/brief/loop-income`, `top_losers` includes VGIT (+0.11%) and SCHP (+0.18%), which were up on the
    day. `top_gainers` lists JNJ at +2.28% with a day P&L of −$0.86, because I bought intraday.
- suggestion:
  - Make Gain equal value minus net invested, so it matches unrealized P&L on day one, or hide Gain until the
    second session.
  - Leave positive movers out of "losers".

Other notes (not counted above):
- Notes and alerts are not tied to a portfolio. `below_cost_pct` uses the cost averaged across all portfolios
  (`held_positions`), so two investors holding the same ticker would share theses and cost alerts.
- The CLI has no dividends or risk commands. I used the HTTP API for those.
- Phone width (390 px): the Analysis tables clip to their first columns (stress scenarios, dividends' annual
  income column). This is relevant to B-002.

Summary for the round lead:
1. I built `loop-income`: 17 positions, 35% bond ETFs, $98,347 invested, $1,653 cash, $3,218 a year forward
   income (3.27%), targets set.
2. Top bug: the SCHP (TIPS) run rate uses the last payment × 12 and understates its income by half. Also, the
   "Stocks / ETFs" tile is mislabeled, dividend events are missing from Coming up and the brief, and XOM
   earnings appear twice.
3. Top features: an asset-class split (bonds vs equity) with duration and rate shocks, and income and drift
   figures in simulate and alerts.
