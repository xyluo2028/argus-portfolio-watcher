# Round 006: macro investor

## What I did
- **Backdrop.** Read at about 22:14 ET on Mon 10-26 (02:14 UTC 10-27), after the close. Sources: `GET /api/market-context` (twice: before and after breadth loaded), `argus quotes ... --json`, `/api/history` for 16 ETFs (2y daily), and the Markets page at 1400 px and 390 px.
  - **Indices:** S&P 7,676.77 (+0.70% 1D, −0.86% 1M). NDX +1.09% (−4.4% 1M), Russell +0.38% (+2.1% 1W).
  - **Volatility:** VIX 18.39 (−5.45% 1D, +23.7% 1M). VIX ÷ VIX3M is 0.92.
  - **Rates:** ^TNX 4.99% (flat on the day, −20 bp over 1M). On the curve the 10Y is 5.00, 2s10s +32 bp and 10s3m +78 bp. The 2Y fell 13 bp in a month. FOMC on Wed 10-28, expected to hold at 4.00%.
  - **Oil, gold, FX:** WTI 100.86 overnight (−0.9%), gold 4,024 (−6.9% 1M), USD/JPY 157.6.
  - **Credit and havens (checked against my own numbers from `/api/history`):** over 20 days TLT is +3.9% while SPY is 0.0%, so "stocks vs Treasuries" is −3.9 pp. HYG is −0.4% while LQD is +1.5%, so "junk vs IG" is −2.0 pp. Both match Argus exactly. Credit got 0.3 pp worse than last round.
  - **Breadth:** 304 up and 194 down, 59% of stocks above their 50-day average, 12 new highs and 8 new lows. Fear & greed is 25.4 "Fear" with 7 readings (it was 11.7 with 5 readings before breadth loaded).
  - **Sectors:** a defensive rotation over 1M (XLP +7.2%, XLU +7.7%, XLV +5.0%, XLE +12.3%) while XLK is −5.1% and XLC −8.1%.
  - **Calendar this week:** FOMC (Wed), GDP, PCE and claims (Thu), Chicago PMI and ECI (Fri). Payrolls was 29K last time and Michigan sentiment 48.
- **Correlations with SPY.** I computed these myself; Argus's 252-day matrix and betas match mine to 2 dp.

  | | 20 days | 60 days | 1 year |
  |---|---|---|---|
  | IEF | **−0.42** | +0.29 | +0.30 |
  | TLT | −0.32 | +0.25 | +0.28 |
  | GLD | **+0.51** | +0.40 | +0.36 |
  | XLP | −0.43 | −0.12 | −0.08 |
  | XLE | −0.25 | −0.32 | −0.24 |
  | Book beta | **0.06** | 0.20 | 0.25 (Argus 0.245) |

- **Regime:** unchanged and slightly firmer. It is stagflation-lite with a growth scare on top: oil about $100 and ISM prices 77.9, but payrolls are weak, credit is widening and bonds are hedging equities again. Gold isn't working as a hedge: it fell 2.7% over 20 days while its correlation with SPY is +0.51.
- **Decision: no trades.**
  - Every position is within ±0.42 pp of target (`/drift`; XLE is the largest at +0.42).
  - I won't re-hedge 36 hours before an FOMC and a PCE print.
  - I pre-staged the trade instead. `POST /simulate` with SELL 6 GLD and BUY 24 IEF gives net cash +$20.04 and realized −$67.80 on GLD, taking GLD from 6.7% to 4.5% and IEF from 5.1% to 7.3%.
  - My own calculation from Argus history: 1-year book volatility 6.09% → 5.67%, beta 0.255 → 0.236, 95% VaR $575 → $543. Over 20 days the change is small (4.27% → 4.22%).
  - I added note 48 on IEF with the trigger: execute after the 10-29 PCE unless PCE runs hot and the 10-year gets back above 5.15%. Review date 10-29, the same day as GLD's note 42 and the DBC and GLD theses.
- **Portfolio:** 11 positions, value $98,889.95, cost $98,747.15, unrealized +$142.80, realized +$1.03.
  - Day P&L on 10-26 was +$128.53 (+0.13%) against SPY +0.71%; the per-position Day P&L adds up exactly.
  - TWR since 10-20 is +0.14% against SPY −0.48%. Risk: beta 0.25, volatility 6.1%, 1-day 95% VaR $566.
- **Cash balance: $1,253.87**, unchanged (100,000 + 1.03 realized − 98,747.15 cost). Total $100,143.82, a return to date of +0.14%. No dividends yet: no holding has had an ex-date since I bought.

## Last round's changes
- **B-068, volatility and Sharpe withheld under 20 sessions: works.**
  - `/performance` gives `volatility_pct null`, `sharpe null` and `risk_note "needs 20 sessions, has 5"`.
  - The Dashboard tile reads "Volatility (ann., 5 sessions) · needs 20 sessions, has 5". There is no longer a second volatility figure competing with Analysis's 6.1%.
  - It helped: the 0.38 Sharpe from last round is gone.
- **B-025, brief movers keep their sign: works.**
  - `top_gainers` lists 5 holdings, all positive (SPY +0.71 … QUAL +0.33).
  - `top_losers` lists 3, all negative (DBC −0.94, XLP −0.34, VTIP −0.06).
  - XLV at exactly 0.00% is in neither list, and the losers list comes back short rather than padded.
  - I couldn't check the same-session Day % base: the market was closed, the sixth round in a row outside the session.
- **B-074, dividend accrual:** nothing to check on this book yet. No holding has had an ex-date since 10-20, and `dividends_accrued` is 0 everywhere, which is correct. The first test will be SGOV and IEF in early November.

## Findings

### 1. Bitcoin "1D" shows the wrong sign: −0.09% on the card, +0.6% over a real 24 hours
- kind: bug
- severity: medium
- evidence:
  - At 02:15 UTC 10-27, `argus quotes BTC-USD --json` gives `price 79,940.19, prev_close 80,009.50 (= open), change_pct −0.087`, and Markets shows −0.14% (79,897).
  - `/api/history/BTC-USD?period=5d&interval=1h` gives 79,466.42 at 10-26 02:00 UTC, so the real 24-hour move is about **+0.6%**. The "1D" covers only the 2¼ h since 00:00 UTC.
  - The daily history now skips the **10-26** bar (10-25 80,024 goes straight to 10-27 79,920). Last round it skipped 10-25.
  - The quote says `session_date 2026-10-26` for a price stamped 10-27 02:15.
- suggestion: same as B-075. For `-USD` pairs, take 1D from the hourly bar at or before now − 24 h.
- backlog: B-075 (new evidence: wrong sign this time)

### 2. Economic calendar figures have no unit or period, and the footnote's "MoM/YoY" explanation is wrong for PCE on GDP day
- kind: ux
- severity: medium
- evidence:
  - Markets → Economic calendar on Thu 10-29 shows "Core PCE Prices · Previous 3.30%" and "PCE Prices · Previous 5.0%". These are the quarterly annualized (QoQ SAAR) prints from the GDP release, not the monthly PCE.
  - Nothing on the page says so. Last round I read 3.3% as the monthly core PCE rate in my own report.
  - Tue 11-10 shows "Core CPI 2.6%" and "Core CPI 0.3%", and Fri 11-13 "Core PPI 0.7%" and "Core PPI 5.0%", as same-named pairs.
  - The footnote says "Some appear twice (month-on-month and year-on-year): 'Previous' tells them apart", but that relies on guessing from magnitude.
  - The feed (`providers/macro.py`) only carries `eventName`, so the period is lost before it reaches the page.
- suggestion: a small curated table for the ~20 market-moving US releases (CPI, core CPI, PPI, PCE, GDP, NFP, AHE, ISM, claims) that adds "MoM", "YoY", "QoQ ann." or "level" to the name. Within a same-named pair, label each row and let the table win.
- backlog: new (related to the B-002 r002 note about duplicate names)

### 3. A bond ETF page shows maturities but no duration, and its peers mix 7-year and 25-year duration
- kind: feature
- severity: high (my main allocation question this week is "how much duration")
- evidence:
  - `/t/IEF` shows the SEC N-PORT holdings: 16 Treasuries maturing 2033–2036, with coupon and weight per bond. So Argus already has what it needs for a weighted-average maturity (about 8.5 years).
  - It shows neither maturity nor duration, and the category reads "Long Government".
  - The Peers card lists TLT, EDV, ZROZ and TLTW (17–27-year duration) next to IEF (about 7 years), with no maturity or duration column. A "peer" swap from IEF to EDV would roughly triple rate risk.
  - Analysis still puts IEF, VTIP and SGOV in "Unclassified" (39.1% of the book).
- suggestion: compute weighted-average maturity, and optionally modified duration from coupon and maturity, from the N-PORT holdings already on the page. Show it in the Fund box and as a Peers column. The same numbers would give B-017 a book-level duration and a "+100 bp" stress line.
- backlog: B-017 (new evidence)

### 4. Risk only offers 1 year: book beta 0.25 there, 0.06 over 20 days
- kind: feature
- severity: medium
- evidence:
  - Analysis → Risk (`/risk`, `lookback_days 252`) gives beta 0.25 and SPY/IEF correlation +0.30.
  - From Argus's own `/api/history`, the 20-day figures are book beta 0.06, IEF −0.42, GLD +0.51 and XLP −0.43. My 252-day figures match Argus's (6.09 vs 6.12 volatility), so the data is fine; only the window is missing.
  - The GLD → IEF switch looks like a 7% volatility cut on 1 year but almost nothing on 20 days. Which window I use changes how big the trade should be.
- suggestion: as in B-067, add a `lookback` parameter (20, 60 or 252) to `/risk` and a toggle on the correlation matrix.
- backlog: B-067

### 5. Simulate still has no risk change, and `value_after` moves by the cash freed
- kind: feature
- severity: medium
- evidence:
  - `POST /simulate` with SELL 6 GLD and BUY 24 IEF returns weights, concentration and look-through only.
  - I had to compute the risk change myself: volatility 6.09 → 5.67, beta 0.255 → 0.236, VaR $575 → $543.
  - `value_before` is $98,889.95 and `value_after` $98,869.91. The $20.04 of `net_cash` released shows up as a $20 *loss* (last round it showed up as a gain).
- suggestion: as in B-023, add `risk_before` / `risk_after` (beta, volatility, VaR) from the same code path as `/risk`. Show value as positions plus net cash, or label it "positions only" (B-024).
- backlog: B-023, B-024

### 6. SGOV and IEF ex-dates (~Sun 11-01) appear on Dividends only
- kind: bug
- severity: medium
- evidence:
  - `/api/portfolios/loop-macro/dividends` gives SGOV and IEF `next_ex_date_est 2026-11-01` (a Sunday; the real ex-date is the first business day, Mon 11-02). Together they make up November's projected $55.71.
  - In the same session these all show nothing:
    - the Dashboard "Coming up · next 14 days" says "Nothing scheduled";
    - `argus brief loop-macro --json` gives `dividends_upcoming []`;
    - `argus events --json` doesn't mention SGOV or IEF;
    - `/t/IEF` → Events says "Nothing scheduled".
  - IEF also has two yields: 4.14% (`/t/IEF` "Dividend yield (TTM)" and Peers) against 4.04% (Analysis → Dividends). That's B-043 on an ETF.
  - VTIP is still "quarterly" with no next ex-date and $0 for the rest of 2026 (B-054).
- suggestion: as in B-013. Feed Coming up, the brief and events from the dividends projection, and roll weekend estimates to the next business day.
- backlog: B-013 (sixth sighting), B-043, B-054

### 7. Fear & greed: 11.7 "Extreme fear" (5 readings) becomes 25.4 "Fear" (7 readings) once breadth loads
- kind: ux
- severity: medium
- evidence:
  - The first `/api/market-context` returned `score 11.7`, 5 components, `errors.breadth` set.
  - Minutes later it returned `25.4` with 7 components. The two added readings, "Price strength" 60 (12 highs vs 8 lows) and "Price breadth" 59, sit far above the five history-ranked readings (0.6–20.4).
  - It's the same dial and the same day, with a different regime label depending on when you look.
- suggestion: as in B-036. Show "5 of 7 readings" while breadth loads, and rank the two breadth readings against their own history.
- backlog: B-036 (fifth sighting)

### 8. The 10-year card says "−0 bp" in red
- kind: ux
- severity: low
- evidence:
  - The Markets 10-year card reads "−0 bp · 1M −20 bp · YTD +82 bp", with "−0 bp" in red. ^TNX moved −0.2 bp (`change −0.002`).
  - A falling yield is colored red (B-039), and a sub-1 bp move rounds to a signed zero.
  - The API still gives 1D as `−0.04` (percent of the yield, B-029).
- suggestion: show one decimal below 1 bp ("−0.2 bp"), or "0 bp" with no sign or color. Color yields neutrally (B-039).
- backlog: B-039, B-029

### 9. ETF pages call SEC financials and fail with a 502, and show an empty ownership card
- kind: removal
- severity: low
- evidence:
  - Opening `/t/IEF`, the browser console logs "Failed to load resource: 502". It is `GET /api/financials/IEF?period=quarterly&limit=8`.
  - The page then shows a "Reported financials" card that says "sec: IEF not found in EDGAR (ETFs and funds have no financials)".
  - The Research → "Ownership & short" card is all dashes for an ETF (held by institutions, short interest, days to cover).
- suggestion: skip the financials request and hide both cards when the symbol's type is ETP (Argus already knows: "ETF" next to the name). If the call is still made, return 404 rather than 502.
- backlog: new

## Still-open items I re-checked
- **B-076:** `near_52w_extremes` still lists all 11 holdings (SGOV 0.06% from its high, IEF 2.8% from its low).
- **B-077:** `argus quotes BTC-USD` and `/api/history/BTC-USD` still return `"symbol": "BTC.USD"`.
- **B-055/B-016:** Markets reads "as of Mon, Oct 26, 4:00 PM ET" while WTI, gold, USD/JPY and BTC are 10-27 overnight prices (`as_of 2026-10-27`), with no tag on the cards.
- **B-053:** the Dashboard chart starts loop-macro at +0.11% and SPY at 0.00% on 10-20. Measured from my 769.47 SPY fill, excess would be +0.67% instead of +0.62%.
- **B-026:** first `/risk` after the server started took 8.26 s with no trade since (warm: 0.64 s). `/performance` took 1.31 s.
- **B-022/B-024:** Analysis Targets & drift opens "By sector" with ETF 100% and "Targets sum to 0.0%". `/drift` warns "targets sum to 99.0%" because there is no cash line.
- **B-021:** Analysis shows beta 0.25 (vs SPY, 1y) next to a factor "Market" loading of 0.36 (to 08-31), neither labeled as the other.
- **B-034:** at 22:14 ET on 10-26 the calendar starts on 10-27 (the UTC date).
- **B-038:** the brief still has no FOMC or this week's releases.
- **B-002:** Markets at 390 px is 5,756 px tall.
- **Not a bug, checked:** breadth shows 295 above and 205 below for both the 50-day and the 200-day average. I checked 40 large caps: Yahoo's `fiftyDayAverage` and `twoHundredDayAverage` equal SMAs from Argus history to the cent, so the matching totals are a coincidence.

## Summary for the round lead
1. No trades: every position is within ±0.42 pp of target, the regime is unchanged and FOMC and PCE are 36–60 h away. I pre-staged SELL 6 GLD / BUY 24 IEF (simulated net cash +$20.04) in note 48, review date 10-29. loop-macro is $98,889.95, unrealized +$142.80, and cash is $1,253.87 (+0.14% to date).
2. B-068 and B-025 work as shipped; B-074 has nothing to check yet on this book. New: the economic calendar has no units or periods (PCE 3.3% and 5.0% are QoQ annualized, not monthly, though the footnote says MoM/YoY), and ETF pages fire a 502 SEC financials call. B-075 got worse: bitcoin 1D shows −0.09% when the 24-hour move is +0.6%.
3. Still most wanted: duration on bond ETFs and in peers (B-017, high), 20/60-day risk windows (B-067), and risk before/after in simulate (B-023). Re-sighted: B-013 (SGOV/IEF ex-dates on Dividends only) and B-036 (fear & greed 11.7 → 25.4).
