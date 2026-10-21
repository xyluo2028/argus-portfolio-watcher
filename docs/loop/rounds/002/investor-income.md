# Round 002: income investor

## What I did
- **Market (Argus market context, as of the 10-20 close):** the 10-year is at 5.12% (5.10% yesterday). The curve runs 2Y 4.79%, 10Y 5.12% and 30Y 5.42%. Fear & Greed is 24.6, "Extreme fear", down from 38. The S&P is +0.28% on the day, VIX 17.3, and FOMC is on 10-28. Rates barely moved and my thesis (lock in 4 to 5% on high-quality duration) still holds.
- **Portfolio `loop-income`:** value $98,375.25, cost $98,347.12, unrealized +$28.13 (+0.03%). After hours it was −$140.31. Beta 0.15, volatility 7.2%, 1-year max drawdown −5.6%, 1-day 95% VaR $668. The 2022 rate-shock replay gives −14.0%. Forward income is $3,217.53 a year (3.27%), which Argus understates by about $115 a year because of SCHP (B-010). All 17 positions are within ±0.25 pp of target, inside the ±2 pp band. No alerts fired.
- **Research:** I checked payout safety. I cross-checked fundamentals yields against the dividend run rates, and the FCF figures against SEC cash flows (finding 1). I also checked this week's events: NEE reports on 10-21, PG reports on 10-22 and goes ex-dividend on 10-23, and O goes ex-dividend on 10-30.
- **Decision: no trades.** It is day two, nothing has drifted, rates are flat, and no dividend changed. I'm still waiting on income figures in simulate (B-023) before I swap SCHP into VCIT.
- **Cash:** $1,652.88, unchanged. Invested at cost: $98,347.12. Realized gains: $0.

## Last round's changes
- **B-007 (day-one performance): works.** `/performance` returns `gain 28.13`, which equals `totals.unrealized_pnl 28.13`, and `net_invested 98,347.12`. TWR is +0.0286%, the same as the chart's last point and the dashboard's "Gain +$28". The day-two check isn't possible yet, because there is still only one closed session (10-20) since I bought. Re-check next round.
- **B-005 and B-006** don't touch my work. The FOMC date of 10-28 shows correctly in the market calendar.
- **Not shipped, but changed:** the duplicate XOM earnings (B-014) are gone. Events and Coming up show only Fri 10-30, which matches `/api/earnings/XOM` `next.date 2026-10-30`. Yesterday the earnings endpoint said 10-23, so the provider's data moved. Close it, or keep it open as a dedupe safeguard.
- **Still open, re-confirmed today:**
  - B-010: SCHP still shows `rate 0.672` against `trailing_12m 1.258`, with `irregular: false`.
  - B-012: the tile still reads "Stocks / ETFs 51% / 49%".
  - B-022: Targets & drift still opens on "By sector" with empty boxes.
  - B-026: a cold `/risk` call took 17.7 s.

## Findings

### 1. Fundamentals' free cash flow is 4x too small for MSFT, which makes a safe dividend look unfunded
- kind: bug
- severity: high
- evidence:
  - `GET /api/fundamentals/MSFT` returns `fcf_ttm 16,545,500,160` (source `yahoo`) and `fcf_margin_pct 4.99`.
  - Argus's own `GET /api/financials/MSFT` gives quarterly free cash flow of 19.64B, 15.80B, 5.88B and 25.66B, which sums to $67.0B TTM. The annual figure for FY2026 is also $66.99B, so the FCF margin is about 20%.
  - KO shows `fcf_ttm 5.22B`, while the SEC quarters sum to $12.6B over the last four reported quarters.
  - The Yahoo field `freeCashflow` (`providers/yahoo.py:361`) is "levered" FCF, not operating cash flow minus capex.
  - Effect on my work: dividends ÷ FCF comes out at about 163% for MSFT and 175% for KO, which looks unsafe. It is really about 40% for MSFT.
  - The stock page shows "Free cash flow (TTM)" and "FCF margin" from this field, next to the SEC table that contradicts them.
- suggestion:
  - When SEC quarterly cash flows exist, compute `fcf_ttm` as the sum of the last four quarters (operating cash flow − capex). Fall back to Yahoo only when they don't.
  - Label the source.

### 2. The daily brief for one portfolio includes other portfolios' holdings and every watchlist
- kind: bug
- severity: medium
- evidence:
  - `GET /api/brief/loop-income` lists `earnings_upcoming` RMBS 10-26 with `held: true`. RMBS is in loop-growth, not loop-income.
  - It also lists PEGA, VICR and USLM, which are on the `growth-candidates` watchlist and marked `held: false`.
  - PEGA and VICR are dated 10-20 and already carry `epsActual`, yet they appear under "upcoming". The brief runs at 22:15 ET, and the filter is `date >= today`.
  - Cause: `daily_brief` calls `self.upcoming_events(days_ahead=7, days_back=3)` without `portfolio=` (`app.py`), and `held` checks every portfolio. The dashboard's Coming up is correctly scoped to the portfolio.
  - A client brief would show names the client doesn't own.
- suggestion:
  - Pass `portfolio=ref` to `upcoming_events` in the brief. Compute `held` against that portfolio.
  - Move events that have actuals into "recent".

### 3. Look-through uses Yahoo's top 10 even though Argus already has the full SEC holdings (HD overlap shows $0)
- kind: bug
- severity: medium
- evidence:
  - On Analysis, "Single-stock exposure", HD shows Via ETFs **$0**, and PG/KO show SCHD only.
  - `GET /api/holdings/SCHD` (source `sec`, 102 holdings) lists HD at 3.36%, so about $336 comes through SCHD. `GET /api/holdings/VIG` (341 holdings) lists HD at 1.43%, PG at 1.45% and KO at 1.47%, so about $70 each comes through VIG.
  - `services/analysis.py` reads only `prof["top_holdings"]`, which comes from Yahoo. The page footnote calls the result a "lower bound".
  - The same SEC data would also fix B-017:
    - `/api/holdings/BND` has `asset_classes {bondPosition 99.03, cashPosition 0.97}` and bond ratings (AA 72.6%).
    - `/api/holdings/SCHP` has `bondPosition 100`.
    - `/api/profile/BND` has `category "Intermediate Core Bond"`.
  - Even so, exposure still puts BND, VCIT, VGIT and SCHP in `funds_without_profile` and shows 35.4% as "Unclassified".
- suggestion:
  - Feed the SEC N-PORT holdings, and their asset classes, into look-through and exposure. Keep Yahoo's top 10 as the fallback.
  - That gives a bond/equity split (B-017) without a new data source.

### 4. The Dividends page ignores announced dates that Argus already has, and still counts a payment I'm not entitled to (B-013)
- kind: bug
- severity: medium
- evidence:
  - Dividends projects PG's next ex-date as `2026-10-24` (a Saturday, estimated). Events, Coming up and the brief show the announced PG ex-dividend date, Fri **10-23** (source `yahoo`).
  - The bond ETFs are still projected for Sun 11-01.
  - Coming up shows "Sat, Oct 31 · JPM · Dividend paid" with `held: true`. I bought JPM on 10-20, after its 10-06 ex-date. The Dividends page correctly gives JPM $0 for the rest of 2026, so the two pages disagree.
  - JPM and ABBV still have `next_ex_date_est: null`, because their next ex-date falls in 2027.
- suggestion:
  - In `dividends.analyze_holding`, prefer an announced ex-date from events over the extrapolated one, and roll estimates to a business day.
  - Drop `dividend_pay` events when the portfolio held no shares on the matching ex-date.

### 5. The income calendar is by ex-date and calendar year only; a client needs cash by pay date over the next 12 months
- kind: feature
- severity: medium
- evidence:
  - `/dividends` `by_month` puts October at $53.07 (PG ex 10-23/24, O ex 10-30). Both pay in November.
  - O's estimated ex-date of 12-30 is counted in the "2026 expected total" of $629.52, but it pays in January 2027.
  - Projection stops at 12-31 (`year_end` in `services/dividends.py`). In January the chart would show only one month ahead.
  - For a retiree, the decision this drives is how much cash to hold for the next three months of withdrawals. I can't read that from Argus.
- suggestion:
  - Add a "next 12 months, by expected pay date" view (pay date ≈ ex-date + the symbol's typical lag from its history, or the announced pay date when there is one).
  - Keep the calendar-year view for tax.

### 6. Two dividend yields per stock disagree (KO 2.74% vs 2.27%)
- kind: ux
- severity: low
- evidence:
  - `/api/portfolios/loop-income/fundamentals` returns `dividend_yield_pct` from Finnhub. `/dividends` computes `yield_pct` from the last payment × frequency ÷ price.
  - KO: 2.74% vs 2.27%. Its rate is $2.12 and price $93.49, so 2.27% is right.
  - SCHD: 3.24% vs 3.08%. NEE: 3.00% vs 3.16%.
  - The stock page and Analysis can show a client different yields for the same holding.
- suggestion: show Argus's computed forward yield everywhere a held stock's yield appears, or label the Finnhub figure "provider, may lag".

### 7. "Where the risk comes from" silently drops two holdings
- kind: ux
- severity: low
- evidence:
  - The Analysis risk card lists 15 rows. SCHP (1.2% of risk) and MSFT (0.8%) are missing, with no "+2 more" line.
  - `/risk` `positions` has all 17, and their shares of risk sum to 100%. The card's shares therefore add up to only 98%, and a reader can't tell why.
- suggestion: show every position (17 rows is short), or add an "Other (2) 2.0%" row.

Other notes (not counted above):
- Cold timings this round: `/risk` 17.7 s, `/dividends` 2.0 s, `/performance` 1.5 s and `/exposure` 1.4 s. The brief took 1.1 s warm. This is B-026.
- KO's latest SEC quarter in Argus is 2026-04-03, although KO filed a 10-Q for 2026-07-03 on 07-29. SEC's own companyfacts also lacks that quarter, so this isn't an Argus bug. A "latest filing is newer than the data" hint would still help.
- The four alerts are intact. Alerts and notes are still global, not per portfolio (B-018).

Summary for the round lead:
1. No trades: the 10-year is flat at 5.12%, every position is within 0.25 pp of target, and cash is $1,652.88. B-007 works: gain $28.13 equals unrealized P&L. XOM's duplicate earnings date is gone.
2. Top new bug: fundamentals' `fcf_ttm` (Yahoo levered FCF) is 4x below the SEC cash flows for MSFT ($16.5B vs $67.0B), so FCF payout ratios look unsafe. Also, the portfolio brief lists other portfolios' holdings (RMBS `held: true`) and watchlist names.
3. Look-through ignores the full SEC holdings Argus already fetches (HD overlap shows $0), and the same data has bond asset classes for B-017. Dividends still mis-dates PG's ex-date (estimated Sat 10-24 vs announced 10-23) and counts JPM's pay.
