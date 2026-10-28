# Round 007: macro investor

## What I did
- **Backdrop.** Read at about 22:14 ET on Tue 10-27 (02:14 UTC 10-28), after the close. Sources: `GET /api/market-context` (twice: before and after breadth loaded), `argus quotes ... --json`, `/api/history` (2y daily for 14 ETFs, plus 1h bars for GC=F, CL=F and BTC-USD), `argus brief loop-macro --json`, and the Markets, Dashboard and Analysis pages at 1400 px, plus Markets and Dashboard at 390 px.
  - **Indices:** S&P 7,722.60 (+0.60% 1D, −0.27% 1M), NDX +1.29%, Russell +1.16%. Tech led (XLK +1.7%) while the defensive and real-asset sectors gave some back: XLE −2.1%, XLP −0.9%, XLRE −0.8%.
  - **Volatility:** VIX 17.52 (−4.7%). VIX ÷ VIX3M is 0.90.
  - **Rates:** 10Y 4.99%, 2s10s +29 bp (was +32), 10s3m +77 bp. The 2Y is 4.70, down 11 bp in a month. FOMC is tomorrow, with consensus at 4.00% (a hold).
  - **Oil, gold, FX:** WTI 101.27 and gold 4,061 on tonight's overnight session (see finding 1). USD/JPY is 157.96 and UUP +1.7% 1M.
  - **Credit and havens (checked against my own numbers from `/api/history`):** over 20 days SPY is +0.71% and TLT +4.35%, so "stocks vs Treasuries" is −3.6 pp. HYG is +0.31% and LQD +1.85%, so "junk vs IG" is −1.5 pp. Both match Argus exactly. Both are 0.3–0.5 pp less stressed than last round.
  - **Breadth and sentiment:** 263 up and 237 down, 59% of stocks above their 50-day average, 12 new highs and 6 new lows. Fear & greed is 29.9 "Fear" with 7 readings (16.7 "Extreme fear" with 5 before breadth loaded).
- **Correlations with SPY.** I computed these myself from Argus history. Argus's 252-day beta (0.2475) and volatility (6.13%) match mine to 2 dp.

  | | 20 days | 60 days | 1 year |
  |---|---|---|---|
  | IEF | **−0.44** | +0.31 | +0.30 |
  | GLD | **+0.58** | +0.42 | +0.37 |
  | XLP | −0.47 | −0.12 | −0.08 |
  | XLE | −0.33 | −0.31 | −0.24 |
  | DBC | −0.42 | −0.45 | −0.25 |
  | Book beta | **0.02** | 0.19 | 0.25 |
  | Book volatility | 4.4% | 5.2% | 6.1% |

- **Regime:** unchanged. It is stagflation-lite with a growth scare: oil about $100, ISM prices 77.9, payrolls 29K. Bonds are hedging equities over 20 days and gold is not: its 20-day correlation with SPY rose again, from +0.51 to +0.58. Credit stress eased slightly.
- **Decision: no trades.**
  - Every position is within ±0.23 pp of target (`/drift`; XLE is the largest at +0.23).
  - FOMC is about 16 h away and PCE is on 10-29. I'm keeping note 48's plan: execute SELL 6 GLD / BUY 24 IEF after PCE unless the 10-year gets back above 5.15%.
  - I re-simulated the trade at tonight's prices with `POST /simulate`: net cash +$47.28, realized −$41.04 on GLD, GLD 6.8% → 4.5% and IEF 5.1% → 7.3%.
  - My own calculation of the risk change from Argus history: 1-year volatility 6.13% → 5.82% and beta 0.248 → 0.232. On 60 days volatility goes 5.23 → 5.02; on 20 days it barely moves (4.38 → 4.34).
- **Portfolio:** 11 positions, value $98,654.91, cost $98,747.15, unrealized −$92.24, realized +$1.03.
  - Day P&L on 10-27 was −$235.04 (−0.24%) against SPY +0.56%. XLE −$211.64 accounts for 90% of it, and GLD +$80.28 was the best.
  - TWR since 10-20 is −0.08% against SPY +0.08%. Risk: beta 0.25, volatility 6.1%, 1-day 95% VaR $565.
- **Cash balance: $1,253.87**, unchanged (100,000 + 1.03 realized − 98,747.15 cost). Total $99,908.78, a return to date of −0.09%. No dividends accrued yet: SGOV and IEF go ex (est.) on Mon 11-02.

## Last round's changes
- **B-013, one ex-date view for upcoming dividends: works, and it helped.**
  - Dashboard "Coming up" lists "Mon, Nov 2 IEF Ex-dividend · est. ≈ $16.88" and "SGOV ≈ $38.83".
  - The brief's `dividends_upcoming` has both, with `estimated: true` and dates moved off the weekend to 11-02.
  - They agree with Analysis → Dividends (annual $3.61 and $3.68 per share ÷ 12 = 0.301 and 0.307).
  - November projects $55.71 and December $413.
  - VTIP still shows no next ex-date and $0 for the rest of 2026 (B-054).
- **B-046, after-close trades:** I made no after-close trade, so I couldn't test a new one. What I could check works:
  - `/performance` `end_value` 98,654.91 equals the dashboard value.
  - The 10-26 → 10-27 series change (−$235.04) equals Day P&L exactly.
  - The per-position Day P&L adds up to the total.
- **B-085, first opens:** works. These pages had never been opened and none returned a 5xx: `/t/UUP` gave no errors. `/t/SCHP` gave none except the known B-092 `502 /api/financials/SCHP`.

## Findings

### 1. Oil and gold "1D" show tonight's overnight move under an "as of 4:00 PM" header, with the wrong sign for the day, and futures history drops the settle
- kind: bug
- severity: medium (on FOMC eve I read "oil up, gold down"; on the day it was the reverse)
- evidence:
  - The Markets header reads "Market closed as of Tue, Oct 27, 4:00 PM ET".
  - The cards read "WTI $101.27 +1.37%" and "Gold $4,061 −0.33%".
  - `argus quotes CL=F GC=F` gives `prev_close 99.90` and `4074.6`, which are the **10-27 settles**, against prices stamped 02:04 UTC 10-28. So "1D" is the 10-28 overnight session, though `session_date` says 2026-10-27.
  - On the 10-27 session itself, oil fell from 101.76 to 99.90 (**−1.8%**; XLE −2.05%) and gold rose from 4,038 to 4,075 (**+0.9%**; GLD +1.21%).
  - The page puts "oil +1.4%" beside "Energy −2.1%", and "gold −0.3%" beside a dashboard where GLD is my top gainer.
  - `/api/history/CL=F?period=1mo` has a 10-27 bar of o 100.17 / c 101.26, which is the overnight session. The 99.90 settle exists nowhere in the history. Gold is the same (10-27 bar c 4060.5; the 4074.6 settle is missing).
  - The Markets sparkline does include 99.90, so Markets and `/api/history` disagree about the 10-27 close.
- suggestion: when the cash market is closed, show futures, FX and crypto 1D as the settle-to-settle change for the session in the header, with the overnight move as a separate tagged line ("overnight +1.37% · 02:04 UTC"). For futures, write the quote's `prev_close` as the session's daily close in history.
- backlog: B-016 / B-055 (new evidence: wrong sign for the session). Related to the B-066 note about overnight daily bars.

### 2. The curated economic calendar drops the FOMC press conference, monthly personal income and spending, ECI and Chicago PMI
- kind: bug
- severity: medium
- evidence:
  - Markets → Economic calendar (`calendar.events`) for 10-28 to 10-30 lists the FOMC Statement, the rate decision, GDP, "GDP Sales", claims, PCE Prices and "Dallas Fed PCE". Friday 10-30 has nothing at all.
  - `calendar.all_events` has these releases, but the curated list doesn't show them:
    - **FOMC Press Conference** 10-28 14:30
    - Personal Income (cons 0.3%) and Personal Spending (cons 0.6%), both 10-29 08:30
    - Employment Wages / Employment Benefits (ECI), 10-30 08:30
    - Chicago PMI (cons 54.8, prev 58.8), 10-30 09:45
    - the 7-Year Note Auction, 10-29 13:00
  - The cause is the `MAJOR` regex in `backend/argus/services/market_context.py`. It matches "FOMC (Statement|Minutes|Economic Projections)" but not "Press Conference", and it has no Personal Income/Spending, Employment Cost/Wages or Chicago PMI. Meanwhile "Dallas Fed PCE" and "GDP Sales" get in through the bare "PCE" and "GDP" matches.
  - For a macro desk the press conference is the event of the week. Right now the only way to see it is the 151-row "all releases" toggle.
- suggestion: add `FOMC Press Conference|Personal Income|Personal Spending|Employment (Wages|Benefits|Cost)|Chicago PMI|Treasury Note Auction` (or similar) to `MAJOR`, and drop the regional-Fed PCE variants.
- backlog: new (related to B-091)

### 3. Fear & greed: 16.7 "Extreme fear" (5 readings) becomes 29.9 "Fear" (7 readings) once breadth loads
- kind: ux
- severity: medium
- evidence:
  - The first `/api/market-context` at 02:14 UTC gave `score 16.7`, 5 components, and `errors.breadth` set.
  - Minutes later it gave `29.9`, 7 components, and no errors. "Price strength" 67 (12 highs vs 6 lows) and "Price breadth" 59 sit far above the five history-ranked readings (2–32).
  - It's a different regime label depending on when you look. This is the sixth sighting.
- suggestion: as in B-036. Show "5 of 7 readings" while breadth loads, and rank the two breadth readings against their own history.
- backlog: B-036

### 4. Risk only offers 1 year; `?lookback_days=20` is silently ignored
- kind: feature
- severity: medium
- evidence:
  - `GET /api/portfolios/loop-macro/risk?lookback_days=20` returns `lookback_days 252` and the same beta 0.2475, with no error.
  - From Argus's own history, book beta is 0.02 over 20 days, 0.19 over 60 days and 0.25 over 1 year. IEF's correlation with SPY is −0.44 over 20 days and +0.30 over 1 year; GLD's is +0.58 and +0.37.
  - The parked GLD → IEF switch cuts 1-year volatility by 5% but 20-day volatility by 1%. The window decides how big the trade should be.
- suggestion: honor a `lookback` of 20, 60 or 252 on `/risk`, and add a toggle on the correlation matrix and the risk tiles.
- backlog: B-067

### 5. Bitcoin 1D still covers only the hours since midnight UTC (+0.14% vs +1.6% over 24 h), and the daily history skips 10-27
- kind: bug
- severity: medium
- evidence:
  - `argus quotes BTC-USD` gives price 80,933.91 and `prev_close 80,800.42` (= `open`, the 00:00 UTC 10-28 bar), so `change_pct +0.17`. Markets shows +0.14% / +0.20%.
  - `/api/history/BTC-USD?period=5d&interval=1h` gives 79,674.58 at 10-27 02:00 UTC, a real 24-hour move of **+1.6%**.
  - The daily bars go 10-26 (80,006.66) straight to 10-28 (80,912.10), skipping **10-27**. Last round the gap was 10-26, and the round before 10-25.
  - The symbol still comes back as `BTC.USD` (B-077).
- suggestion: as in B-075. Take crypto 1D from the hourly bar at or before now − 24 h, and stop dropping the previous UTC day's bar.
- backlog: B-075, B-077

### 6. The brief still has no FOMC the night before the decision
- kind: feature
- severity: low
- evidence:
  - `argus brief loop-macro --json` has holdings movers, two dividend estimates and five theses due, but no macro events.
  - FOMC (14:00 ET) and the press conference (14:30 ET) are tomorrow, and GDP and PCE are on Thursday. All three are in `/api/market-context` `calendar`.
  - My three review-date theses (DBC, GLD, note 48) all hinge on these events.
- suggestion: as in B-038. Add `macro_upcoming` to the brief (next FOMC, plus the next 7 days of curated releases), from the same list as Markets.
- backlog: B-038

### 7. Cold `/risk` took 15.7 s
- kind: perf
- severity: medium
- evidence: the first `GET /api/portfolios/loop-macro/risk` of my session took 15.71 s; the next two took 0.95 s and 0.75 s. I hadn't traded since 10-23. Other investors may have been loading their own pages at the same time. `/performance` took 1.61 s and `/portfolios/loop-macro` 1.35 s.
- suggestion: as in B-026. Warm the risk inputs (2y bars for held symbols) at startup and after the close, or show the page from cached results while it refreshes.
- backlog: B-026

### 8. Simulate still has no risk change, and `value_after` falls by the cash it frees
- kind: feature
- severity: low (re-sighting)
- evidence:
  - `POST /simulate` with SELL 6 GLD and BUY 24 IEF gives `value_before 98,654.91` and `value_after 98,607.63`. The difference is exactly the `net_cash` +$47.28, shown as a loss.
  - There is no beta, volatility or VaR before and after; I computed 6.13 → 5.82 and 0.248 → 0.232 myself.
- suggestion: as in B-023 and B-024. Add `risk_before` / `risk_after` from the `/risk` code path, and either include net cash in `value_after` or label it "positions only".
- backlog: B-023, B-024

### 9. Bond ETF pages still have no duration, and ETF pages still fire a 502 financials call
- kind: feature / removal
- severity: medium (re-sighting)
- evidence:
  - `/t/SCHP` logs `502 /api/financials/SCHP?period=quarterly&limit=8` (B-092).
  - Analysis look-through is still 39.3% "Unclassified": SGOV, VTIP, IEF and GLD, with no duration anywhere (B-017).
  - `/t/UUP` (the dollar ETF) has an empty Peers card ("Yahoo lists no category") and shows a single holding, AGPXX at 49.4%. Its "Asset mix" says Cash 100%, which hides that the fund is long dollar-index futures.
- suggestion: B-017 (duration from N-PORT) and B-092 (skip financials for ETPs). For futures-based funds, label the asset mix "collateral; exposure via futures".
- backlog: B-017, B-092

## Still-open items I re-checked
- **B-076:** `near_52w_extremes` now lists 9 of 11 holdings, down from 11. GLD and XLP have dropped out, but IEF (2.8% from its low) and XLE (2.4% from its high) are still in.
- **B-053:** the 10-20 performance point still starts loop-macro at +0.106% and SPY at 0.00%.
- **B-022/B-024:** `/drift` still warns "targets sum to 99.0%" because there is no cash line.
- **B-034:** at 22:14 ET on 10-27 the calendar starts on 10-28 (the UTC date).
- **B-039/B-029:** the 10-year card reads "+1 bp" for a +0.7 bp move, while the API's 1D is 0.14 (percent of the yield).
- **B-021:** Analysis still shows beta 0.25 next to a factor "Market" loading of 0.37, neither labeled as the other.
- **B-054:** VTIP still has no next ex-date and $0 for the rest of 2026.
- **B-063:** the Dividends footnote still says "Annual rate = latest payment × payments per year".
- **Phone:** Markets is 5,864 px tall at 390 px with no horizontal overflow; the Dashboard is 2,614 px with no overflow.

## Summary for the round lead
1. No trades: drift is within ±0.23 pp, the regime is unchanged and FOMC (10-28) and PCE (10-29) are imminent. The SELL 6 GLD / BUY 24 IEF trade stays parked in note 48 (re-simulated net cash +$47.28). loop-macro is $98,654.91, unrealized −$92.24, cash $1,253.87 (−0.09% to date).
2. B-013 works: Coming up and the brief show the IEF and SGOV 11-02 estimates, consistent with Dividends. B-046 checks out on what I could test: the series change equals Day P&L and `end_value` equals the dashboard. B-085 is fine: no 5xx on first opens.
3. New: oil and gold "1D" show tonight's overnight move with the opposite sign to the 10-27 session (oil +1.37% card vs −1.8% on the day; gold −0.33% vs +0.9%), and futures history drops the settle. The curated calendar omits the FOMC press conference, personal income/spending, ECI and Chicago PMI. Re-sighted: B-036, B-067, B-075, B-038 and B-026.
