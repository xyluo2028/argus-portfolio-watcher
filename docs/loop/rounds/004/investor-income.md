# Round 004: income investor

## What I did
- **Market (Argus market context, as of the 10-22 close, reviewed about 22:30 ET):**
  - It was a sharp risk-off rotation. SPY fell 1.18% (773.09 to 763.96) and XLK fell 3.3%, while XLP rose 3.3%, XLU rose 2.1% and XLF rose 1.1%.
  - The 10-year fell 19 bp to 4.95% (`^TNX` 5.146 to 4.953; Treasury curve 4.96). The 2-year is 4.65%, and 10y−2y is +31 bp.
  - VIX is 19.0 (+14%). Fear & Greed is 27.8 ("Fear"). FOMC is on 10-28.
  - Rates are back where they were a month ago (the 10-year was 4.96% on 09-22), so the "bonds near 52-week lows" worry from last round has eased.
- **Portfolio `loop-income`:**
  - Value $99,788.59, cost $98,347.12, unrealized **+$1,441.47 (+1.47%)**.
  - Last session was **+$1,703.70 (+1.74%)** against SPY's −1.18%. Big gainers: PG +5.6% (earnings beat: EPS 2.00 vs 1.94), HD +4.3%, NEE +4.6%, O +3.1%, JNJ +3.8%, and BND +0.9% and VCIT +0.9% on the rate drop. MSFT was the only real loser (−2.2%).
  - Risk: beta 0.13, volatility 7.5%, 1-year max drawdown −5.7%, 1-day 95% VaR $681. The 2022 rate-shock replay gives −14.0%.
  - Income: forward income is **$3,332.38** a year (3.34% on value, 3.39% on cost). $648.66 is projected for the rest of 2026.
  - Drift: everything is inside the ±2 pp band. The largest gaps are MSFT −0.34 pp, JPM −0.28 pp and SCHD +0.22 pp.
  - The bond ETFs (BND, VCIT, VGIT, SCHP) make up 35.2%, still above my 30% floor. I had to add that up myself (B-017).
- **Payout safety, computed from Argus's SEC tables (FCF TTM ÷ dividends):**
  - ABBV: about 67% (FCF 18.21B against about 12.2B of dividends). The Finnhub "Payout" of 189.8% looks alarming, but FCF covers the dividend comfortably.
  - KO: about 73%.
  - PG: about 66% (FCF 15.34B).
  - JNJ: about 63% (FCF 20.59B), although EPS payout is about 81% on SEC EPS after Q3's $0.09 charge quarter.
  - No dividend changed. PG goes ex-dividend today (10-23), and I hold the shares, so I get $33.76.
- **Decision: no trades.** Nothing is outside its band. Today's +1.7% day is a rotation I'm happy to hold, not a reason to rebalance. Bonds rallied into the FOMC, so selling stocks to buy bonds now would chase the move.
- **Housekeeping:**
  - Turned off alert #5 (PG `day_loss_pct 4`). PG has reported, and it rose 5.6%.
  - Added **alert #6: KO `day_loss_pct 4`** ("KO reports 10-27 bmo").
- **Cash:** $1,652.88, unchanged. Invested at cost: $98,347.12. Realized gains: $0.

## Last round's changes
- **B-040 (fundamentals FCF from SEC quarters): partly works.**
  - Where it applies, the numbers are right:
    - KO `fcf_ttm 12,562,000,000` (source `sec`) equals 1.755 + 2.874 + 4.564 + 3.369.
    - ABBV 18.21B, PG 15.34B, JNJ 20.59B and MSFT 66.99B match their SEC tables.
  - It helped. I could build FCF payout ratios for four holdings for the first time.
  - Gaps:
    - NEE (−17.77B), HD, O and PEP still fall back to `yahoo`, because their capex isn't read.
    - KO's "TTM" window ends at Q1 2026, because Argus lacks its Q2 10-Q (finding 2).
- **B-058 (fiscal-Q4 EPS): works where the quarter exists.**
  - KO 2025-12-31 0.53 and JNJ 2025-12-28 2.09 are both flagged `annual_less_ytd`.
  - PG 2026-06-30 is 1.26 and HD 2026-02-01 is 2.58.
  - PEP has no fiscal-Q4 row at all (finding 3).
- **B-015 (research bands on first open):** doesn't touch my work.
- **Still open, re-confirmed today:**
  - B-013: on the same Dashboard page, Dividends says PG's next ex-date is "~Oct 24" while Coming up says "Fri, Oct 23 PG Ex-dividend". Announced dates are MSFT 11-19, JNJ 11-24 and KO 12-01, but Argus shows estimates of ~11-20, ~11-25 and ~12-15. Events now also lists "ABBV dividend_pay 11-16 held: true", although I bought after its 10-15 ex-date.
  - B-063: the footnote still reads "latest payment × payments per year" on both pages.
  - B-062: the Payout column is still Finnhub's (KO 77.2%, ABBV 189.8%).
  - B-002: at 390 px, the Dividends table still cuts off after Price and Fwd yield.
  - B-022: Targets & drift still opens on "By sector" with empty targets and "Targets sum to 0.0%".
  - B-012: the tile reads "Stocks / ETFs 50% / 50%" with the subtitle "ETF / Stock".
  - B-017: look-through still shows 35.2% as "Unclassified".
  - B-026: cold `/risk` took 21.5 s (it was 33.4 s).

## Findings

### 1. Market context's 1-day moves skip a day for some symbols: S&P 500 −0.64% (really −1.21%), Nasdaq 100 −1.80% (really −2.90%), XLU +2.36% (really +2.07%)
- kind: bug
- severity: high (wrong numbers on the market page and in the brief's market view)
- evidence:
  - `GET /api/market-context`: the `^GSPC` gauge has `last 7663.43`, `change −49.14`, `1D −0.637`. Its spark ends `…7690.73, 7712.57, 7663.43`, so the 10-21 close is missing.
  - `GET /api/history/^GSPC` has that bar: 10-20 7712.57, **10-21 7757.17**, 10-22 7663.43. The real day move is −1.21%, and it agrees with SPY's −1.18% from `argus quotes SPY`.
  - `^NDX` is the same. The spark skips 10-21's 29822.52, so the gauge shows −1.80% instead of −2.90%.
  - Of the sectors I cross-checked, XLU is wrong: context says +2.364%, history says +2.071%. XLK, XLP, XLE and XLF match.
  - `^RUT` and `^TNX` are right.
  - The page shows SPY −1.18% on the Dashboard and S&P 500 −0.64% on Markets for the same session. A client would ask which is right.
  - Likely cause: `providers/macro.py` `closes()` uses one `yf.download` batch, then `dropna()` per column. A NaN cell in the batch (a row Yahoo hadn't filled for that ticker) silently drops that day. Period returns then measure against the day before.
- suggestion:
  - Build the gauges and sectors from the same cached daily bars that `/api/history` uses (`daily_closes_many`).
  - Or, after the batch, detect missing dates against the union of trading days and re-fetch those symbols individually.
  - A test with a NaN in one ticker's row should cover it.

### 2. "SEC" FCF and EPS TTM use stale quarters with no as-of date: KO stops at Q1 2026, NEE at Q1 2026 (B-056 hits my holdings)
- kind: bug
- severity: high
- evidence:
  - `GET /api/financials/KO?period=quarterly`: the latest period is **2026-04-03**. SEC's submissions list has KO's 10-Q for **2026-07-03, filed 2026-07-29**.
  - NEE's latest row is 2026-03-31. SEC has its 10-Qs for 2026-06-30 (filed 07-24) and 2026-09-30 (filed 10-21).
  - The other holdings are current: JNJ 09-27, PG 09-30, PEP 09-05, HD 08-02, ABBV, MSFT, JPM and O 06-30.
  - So KO's `fcf_ttm 12.56B (sec)` is really Q2 2025 to Q1 2026, one quarter stale. Neither the API nor /t/KO says which quarters went into it.
  - KO's SEC EPS over those four quarters is 3.18, against `eps_ttm 3.33` (Yahoo), and you can't tell they cover different windows.
  - This is the same failure as B-056 (RMBS), now on a dividend core holding. KO reports Q3 on 10-27, so it will soon be two quarters stale.
- suggestion:
  - Add `fcf_ttm_through: "2026-04-03"` (the last quarter used) and show it on the stock page.
  - If the latest quarter is more than about 100 days old while the company has filed a newer 10-Q, flag `stale` and fall back to the provider's figure.
  - Root fix: fall back to the filing's own XBRL when the companyfacts frames lack it (B-056).

### 3. PepsiCo's fiscal-Q4 quarter is missing entirely, so any four-row TTM spans 15 months
- kind: bug
- severity: medium
- evidence:
  - `GET /api/financials/PEP?period=quarterly` returns 2026-09-05, 06-13, 03-21, then **2025-09-06**, 06-14, 03-22, then 2024-09-07. There is no Q4 for either year.
  - The annual table has FY2025 (2025-12-27): revenue 93.925B, EPS 6.00. Argus could derive Q4 2025 as revenue 93.925 − (17.919 + 22.726 + 23.937) = **29.34B** and EPS 6.00 − (1.33 + 0.92 + 1.90) = **1.85**.
  - PEP's fiscal Q4 is 16 weeks, against a 12-week Q1 to Q3 and a 40-week year-to-date. The B-058 derivation probably requires a quarter-length span and skips it.
  - Anything summing the last four rows is wrong for PEP. Its FCF already falls back to Yahoo because capex is missing, too.
- suggestion: allow the annual-less-YTD derivation when the 10-K's year ends right after the last 10-Q's year-to-date period, whatever the quarter's length (a 16- or 17-week Q4). Add a test with PEP-shaped periods.

### 4. Two "Volatility (ann.)" figures for one portfolio: Dashboard 17.3%, Analysis 7.5%; the API reports a Sharpe of 7.1 over 3 sessions
- kind: bug / ux
- severity: medium
- evidence:
  - The Dashboard's "Performance vs SPY" card shows **Volatility (ann.) 17.3%** and Max drawdown −0.30%.
  - The Analysis Risk card shows **Volatility (annualized) 7.5%** and Max drawdown (1 year) **−5.7%**.
  - `GET /performance` returns `sessions: 3`, `volatility_pct 17.33`, **`sharpe 7.13`**.
  - The Dashboard figure annualizes two daily returns, one of them today's +1.74% outlier. Both are labeled the same way.
  - A client would see a 7% Sharpe and a portfolio twice as volatile as the risk page says.
- suggestion:
  - Don't show annualized volatility or Sharpe until there are 20 or more sessions (show "–" and "needs 20 sessions").
  - Or label the Dashboard's figure "since inception (3 sessions)".

### 5. Payout safety still needs hand math: no FCF payout, and the Finnhub payout calls ABBV unsafe at 190%
- kind: feature (extends B-062)
- severity: medium
- evidence:
  - The Dashboard Dividends tab shows Payout ABBV **189.8%** and O **236.4%** (Finnhub, EPS-based).
  - From Argus's own data:
    - ABBV: SEC FCF TTM 18.21B against about 12.2B of dividends ($6.92 × about 1.77B shares) is **about 67%**.
    - KO: about 73%.
    - PG: about 66%.
    - JNJ: about 63%.
  - Argus now has trustworthy SEC FCF (B-040) for 4 of my 11 stocks, but I had to look up share counts outside the page to turn it into a ratio.
  - The decision it changes: on the EPS figure I'd trim ABBV, a 190% payout. On FCF it's a hold.
- suggestion:
  - Add "FCF payout" = annual rate × diluted shares ÷ `fcf_ttm` next to Payout, labeled with the FCF source and the quarter it runs through (finding 2).
  - Show "–" where FCF is from Yahoo or missing.

### 6. Capex isn't read for HD, NEE, PEP and O, so 4 of 11 dividend stocks still use Yahoo FCF
- kind: bug
- severity: medium
- evidence:
  - `GET /api/financials/HD` has operating cash flow for every quarter (5.39B, 6.03B, 3.35B, 4.01B) but `capex None`.
  - NEE, PEP and O are the same.
  - `/api/fundamentals/HD` gives `fcf_ttm 10.76B` with source `yahoo`. NEE's `yahoo` −17.77B is a levered figure that makes a utility's dividend look entirely debt-funded.
  - These are large filers. I didn't confirm the exact tags, but they likely use alternatives to `PaymentsToAcquirePropertyPlantAndEquipment`, such as `PaymentsToAcquireProductiveAssets` or utility-specific PP&E tags.
- suggestion: add the common alternative capex tags (`PaymentsToAcquireProductiveAssets`, `PaymentsToAcquireOtherPropertyPlantAndEquipment`, `PaymentsForCapitalImprovements`, utility construction tags) in priority order, as revenue did in B-008.

### 7. Cold portfolio fundamentals took 26.8 s and then returned every symbol as "pending"
- kind: perf
- severity: medium
- evidence:
  - The first call of the session, `GET /api/portfolios/loop-income/fundamentals`, took **26.8 s**. It returned `pending` with all 17 symbols, and only `return_1m_pct` and `cagr` metrics.
  - A second call a few minutes later took 0.9 s, with `pending []` and full metrics.
  - The cold `/risk` took 21.5 s and `/performance` 3.4 s. `/dividends` 3.2 s, the brief 1.6 s, `/exposure` 1.1 s.
  - The Dashboard's Dividends tab gets Payout and Div CAGR from this call, so on first open it waits half a minute and then shows dashes.
- suggestion:
  - If the response is going to say "pending" anyway, return it immediately, without blocking on whatever takes 27 s (probably the history used for returns), and let the UI poll.
  - Warm fundamentals and history for held symbols at startup, as already suggested in B-026.

### 8. The Dividends ex-date column contradicts Coming up on the same page (B-013, a new instance)
- kind: bug
- severity: medium (existing B-013)
- evidence:
  - On the Dashboard, the Dividends tab shows PG "~Oct 24" (a Saturday). Directly below it, Coming up shows "Fri, Oct 23 · PG · Ex-dividend".
  - `/api/events` has the announced dates MSFT 11-19, JNJ 11-24 and KO 12-01. Dividends shows ~Nov 20, ~Nov 25 and ~Dec 15.
  - New this round: Events lists `ABBV dividend_pay 2026-11-16 held: true`, but my ABBV lots were bought after its 10-15 ex-date. `/dividends` correctly projects $0 for ABBV.
- suggestion: as in B-013, use the announced ex-date from events when there is one, and drop pay events for lots opened after the ex-date.

## Summary for the round lead
1. **High:**
   - Market context's 1-day moves skip a day for some symbols: S&P 500 −0.64% vs a real −1.21%, NDX −1.80% vs −2.90%, XLU off by 0.3 pp. The cause is NaN rows dropped from the `yf.download` batch.
   - KO's and NEE's SEC quarters stop at Q1 2026, so KO's "SEC" FCF TTM is a quarter stale, with no as-of date (B-056 on income names).
2. **Medium:**
   - PEP has no fiscal-Q4 rows (16-week quarter).
   - Dashboard volatility 17.3% vs Analysis 7.5%, and a Sharpe of 7.1 from 3 sessions.
   - FCF payout wanted (ABBV is 67% on FCF vs 190% on EPS).
   - Capex is missing for HD, NEE, PEP and O.
   - Cold fundamentals took 27 s and returned "pending".
   - B-013 is still open.
   - B-040 and B-058 work where data exists.
3. **No trades.** Value $99,788.59 (+1.47%), income $3,332/yr, drift within ±0.34 pp, cash $1,652.88. Alert #5 (PG) turned off, alert #6 (KO −4% on earnings) added.
