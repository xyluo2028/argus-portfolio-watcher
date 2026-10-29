# Round 008: macro investor

## What I did
- **Backdrop.** Read at about 22:13 ET on Wed 10-28 (02:13 UTC 10-29), after the FOMC close. Sources: `GET /api/market-context` (twice: before and after breadth loaded), `/api/quotes`, `argus quotes --json`, `/api/history` (2y daily for 14 ETFs, 5d daily for CL=F, GC=F and BTC-USD), `/api/brief/loop-macro`, `/risk`, `/drift`, `/performance`, `/simulate`, and screenshots of Markets (1400 and 390 px), the Dashboard (1400 and 390 px) and `/t/GLD`.
  - **Indices:** S&P 7,743.98 (+0.28%), NDX +0.55%, Russell +0.41%. Tech led (XLK +0.8%); utilities and real estate lagged (XLU −0.8%, XLRE −0.7%).
  - **After hours:** ES=F is −0.45% and SPY post-market −0.39%, after a weak GOOGL report (from a SPY headline in the brief).
  - **Volatility:** VIX 16.91 (−3.5%). VIX ÷ VIX3M is 0.88.
  - **Rates:** the Fed held and is "leaning hawkish". I learned this only from IEF and SPY headlines (finding 1).
    - 10Y 5.05% (+5 bp) and 2Y 4.67% (−3 bp), so 2s10s widened from +29 bp to **+38 bp** in a day: a bear steepener. 10s3m is +87 bp.
    - Over the month the 2Y is down 25 bp and the 10Y down 19 bp.
  - **Oil, gold, FX:** WTI settled 102.78 on 10-28 (+2.9%), gold 4,051.6 (−0.6%). USD/JPY is 157.68.
  - **Credit and havens:** over 20 days, stocks vs Treasuries is −2.86 pp and junk vs IG −1.36 pp. I recomputed both from `/api/history`, and they match Argus's −2.9 / −1.4 exactly. Both are slightly less stressed than last round.
  - **Breadth and sentiment:** 264 up, 236 down; 60% of stocks are above their 50-day average; 19 new highs and 8 new lows. Fear & greed is 33.6 "Fear" with 7 readings (21.0 "Extreme fear" with 5 before breadth loaded).
- **Correlations with SPY** (my calculation from Argus history; Argus's own 252-day book beta 0.2488 and volatility 6.135% match mine, 0.249 and 6.14%):

  | | 20 days | 60 days | 1 year |
  |---|---|---|---|
  | IEF | **−0.47** | +0.26 | +0.30 |
  | GLD | **+0.58** | +0.44 | +0.38 |
  | XLP | −0.55 | −0.17 | −0.09 |
  | XLE | −0.35 | −0.31 | −0.24 |
  | DBC | −0.40 | −0.39 | −0.25 |
  | Book beta | 0.00 | 0.19 | 0.25 |
  | Book volatility | 3.9% | 5.2% | 6.1% |

- **Regime:** unchanged. It's stagflation-lite with a growth scare, and the Fed held with a hawkish lean.
  - The bear steepener says the market is pricing term premium and inflation, not cuts.
  - Bonds still hedge equities over 20 days (IEF −0.47) while gold does not (+0.58, unchanged).
  - Credit stress eased a little.
- **Decision: no trades tonight.**
  - Drift is within ±0.26 pp everywhere (XLE +0.26 is the largest).
  - Note 48's plan was to switch GLD into IEF *after* PCE (08:30 tomorrow), and PCE is 10 hours away. A hawkish hold with the 10Y at 5.05% doesn't break the plan's 5.15% stop.
  - I re-simulated SELL 6 GLD / BUY 24 IEF at tonight's closes: net cash +$60.66, realized −$33.66 on GLD, GLD 6.8% → 4.5%, IEF 5.1% → 7.3%.
  - Risk change (my calculation): 1-year volatility 6.14 → 5.82%, 60-day 5.19 → 4.98%, 20-day 3.94 → 3.90%.
  - Updated the plan in **note 51** (IEF, review 10-29): execute after PCE unless core PCE beats 2.4% and the 10Y breaks 5.15%.
- **Portfolio:** 11 positions, value $98,771.59, cost $98,747.15, unrealized +$24.44, realized +$1.03.
  - Day P&L on 10-28 was +$116.68 (+0.12%) against SPY +0.34%.
  - TWR since 10-20 is +0.03% against SPY +0.42%.
  - Risk: beta 0.25, volatility 6.1%, 1-day 95% VaR $565.
- **Cash balance: $1,253.87**, unchanged (100,000 + 1.03 realized − 98,747.15 cost). Total $100,025.46, a return to date of **+0.03%**. IEF (≈$16.88) and SGOV (≈$38.83) go ex (est.) on Mon 11-02.

## Last round's changes
- **B-083, momentum from Argus's closes: works, and it helped.**
  - On `/t/GLD` the Momentum card shows 1W −1.4, 1M −1.2, 3M +1.1, 6M −11.5, YTD −5.8 and 1Y +2.5. These match the chart's range buttons exactly.
  - They also match `/api/returns/GLD` (e.g. 373.51 ÷ 377.91 for 1M = −1.164%) and the Dashboard Momentum data (`return_1m_pct −1.1643`).
  - IEF and XLE match too. "vs S&P 500, 1 year" (−10.9) is still Finnhub's.
  - One new mismatch sits on the same page: "YTD total return" (finding 3).
- **B-009 + B-079 (valuation card):** doesn't apply to ETFs.
- **B-093 (announced ex-dates):** nothing announced in my book. Coming up, the brief and Dividends still agree on IEF and SGOV for 11-02.
- **Perf, B-026:** `/risk` took 0.79 s on my first call this session (15.7 s last round). Another agent may have warmed it first, so I can't say it's fixed.

## Findings

### 1. On FOMC night Argus can't tell me what the Fed did
- kind: bug / feature
- severity: high (the single event of the week for a macro book; I had to find it in ETF headlines)
- evidence:
  - At 22:13 ET on 10-28, the Markets → Economic calendar (`calendar.events` and `all_events`) starts at **Thu 10-29**. The 10-28 FOMC statement, rate decision and press conference rows are gone, so there's no actual.
  - The FOMC strip still lists "October 27-28" with no outcome, and nowhere shows the fed funds target range.
  - The only trace is `/api/brief/loop-macro` `headlines`: under IEF and SPY, "Fed Holds Rates Steady Despite Inflation Being Too High" (20:35 UTC) and "Rates Spark: Leaning Hawkish, But No Action" (21:45 UTC).
  - It's the same cause as B-034, the UTC date (fifth round). Combined with B-035 (no actuals), the most important release of the month vanishes the evening it happens.
- suggestion:
  - Start the calendar on the New York date (B-034), or always keep the last 24 h.
  - Show the latest FOMC outcome on the FOMC strip: "Oct 28: hold, 4.00% upper bound". It can come from the calendar row's actual, or from the 1-month T-bill and fed funds via the existing Treasury curve feed.
- backlog: B-034, B-035 (new evidence)

### 2. Oil and gold "1D" show the opposite sign to the session again; futures history still drops the latest settle
- kind: bug
- severity: medium
- evidence:
  - The Markets header reads "Market closed as of Wed, Oct 28, 4:00 PM ET". The cards read "WTI $101.77 −0.98%" and "Gold $4,075 +0.57%".
  - `argus quotes CL=F GC=F` gives `prev_close 102.78` and `4051.6`, which are the **10-28 settles**, against prices stamped 02:03 UTC 10-29 with `session_date 2026-10-28`.
  - On the 10-28 session itself, oil rose 99.90 → 102.78 (**+2.9%**) and gold fell 4,074.6 → 4,051.6 (**−0.6%**). Both cards have the wrong sign for the day, as on 10-27.
  - `/api/history/CL=F?period=5d`: the 10-27 bar now holds the 99.90 settle (fixed overnight), but the 10-28 bar is 101.71, the overnight price. The 102.78 settle is missing.
  - Gold is the same: the 10-28 bar is 4,074.2, and the 4,051.6 settle is missing.
  - So each day's settle only appears once the next day's bar replaces it.
- suggestion: as last round. After the cash close, show the settle-to-settle change for the session in the header, and the overnight move as a separate tagged line. Write `prev_close` as the session's daily close in history.
- backlog: B-016, B-055

### 3. "YTD total return" is Yahoo's month-end (9-30) figure, shown beside a live YTD price return
- kind: bug
- severity: medium (two YTD numbers disagree on one card, and the "total" one is impossible)
- evidence:
  - `/t/GLD`, Valuation & fundamentals. The Momentum column has "Year to date −5.8%"; the Fund column has "YTD total return −3.3%".
  - GLD pays **no** dividend, so its total return can't beat its price return by 2.5 pp.
  - `/api/portfolios/loop-macro/fundamentals` gives:
    - GLD: `ytd_return_pct −3.34` vs `return_ytd_price_pct −5.75`
    - DBC: **44.4 vs 51.1** (a dividend payer whose total return is below its price return)
    - IEF: −4.59 vs −5.52
  - I backed out the price each figure implies from the 12-31 close in Argus history:
    - GLD 383.06 is the 9-29/9-30 close of 382.89.
    - DBC 32.29 is the 9-30 close of 32.32.
  - So it's a month-end NAV figure with no date. The page header says "as of Wed, Oct 28, 10:13 PM ET · same figures as the dashboard tabs".
- suggestion: label it "YTD total return (as of 9-30, Yahoo)". Or compute it from Argus's own closes plus recorded and estimated distributions, as B-083 did for price returns. The same applies to 3- and 5-year average return.
- backlog: new

### 4. After-hours P&L (+$298.88) rests on stale, thin ETF prints that contradict the futures
- kind: bug / ux
- severity: medium
- evidence:
  - The Dashboard header shows "After hours +$298.88 (+0.30%)". At the same moment ES=F is −0.45%, SPY post −0.39%, IVV −0.37% and QQQ −1.05%.
  - The +$298.88 comes mostly from:
    - **QUAL** AH +1.04% (+$122.96), a print from 21:44 UTC (5:44 PM ET). Peers are MTUM −1.48%, IVV −0.37% and QQQ −1.05%.
    - **XLP** AH +0.81% (+$63.70); VDC is +0.25%.
    - **XLV** +1.00% (+$120.60); VHT is +0.91%, so plausible.
  - A quality fund heavy in mega-cap tech can't be up 1% while QQQ is down 1%. It's a stray print, 4.5 h old, with no time shown in the Holdings row ("AH +1.04%").
  - `ext_coverage_pct 100` says every position is covered.
- suggestion:
  - Show each AH figure's print time, and grey out or exclude prints older than ~30 min from the header total ("after hours, 9 of 11 updated in the last 30 min").
  - Optionally, show the ES=F overnight change beside it as a sanity anchor.
- backlog: new (related to B-055)

### 5. Fear & greed: 21.0 "Extreme fear" (5 readings) becomes 33.6 "Fear" (7 readings) once breadth loads
- kind: ux
- severity: medium
- evidence: the first `/api/market-context` at 02:13 UTC had `score 21.0`, 5 components and `errors.breadth`. Later the page and the API gave 33.6 with 7 components; Price strength (70) and Price breadth (60) pull it up. It's the seventh sighting.
- suggestion: as in B-036. Show "5 of 7 readings" while breadth loads, and rank the breadth readings against their own history.
- backlog: B-036

### 6. The brief lists 12 theses due 10-29 "after FOMC/PCE" but no macro events, and the Fed decision only appears in per-ETF headlines
- kind: feature
- severity: low
- evidence:
  - `/api/brief/loop-macro` `theses_due` has 12 entries reviewed on 10-29. Several say "review after FOMC 10/28 and PCE".
  - It has no `macro` section: no FOMC outcome, and nothing for tomorrow's 08:30 PCE, GDP or claims, though all are in `/api/market-context` `calendar`.
  - `near_52w_extremes` still lists 9 of 11 holdings (B-076).
- suggestion: as in B-038. Add `macro_recent` (the last 24 h of curated releases with actuals, plus the FOMC outcome) and `macro_upcoming` (next 7 days) to the brief.
- backlog: B-038, B-076

### 7. Bitcoin's daily history skips the previous UTC day again, and 1D is still since midnight UTC
- kind: bug
- severity: low (re-sighting)
- evidence:
  - `/api/history/BTC-USD?period=5d` goes from 10-27 (80,805.08) straight to 10-29 (79,842.96), skipping **10-28**.
  - `argus quotes BTC-USD` gives `prev_close 81,262.04` = `open` = `high`, the 00:00 UTC bar. The symbol comes back as `BTC.USD`.
- suggestion: B-075 / B-077.
- backlog: B-075, B-077

### 8. Two betas for one fund: GLD 0.19 on its page vs 0.85 in Risk
- kind: ux
- severity: low (re-sighting)
- evidence:
  - `/t/GLD` "Dividends & risk" shows Beta 0.19 (Yahoo). `/api/portfolios/loop-macro/risk` gives GLD beta 0.845 (252-day vs SPY). That one checks out: corr 0.38 × vol 28.3% ÷ 12.7% = 0.85.
  - DBC: 0.11 vs −0.40. XLE has no page beta but −0.43 in Risk.
  - For hedging decisions the page figure is the misleading one.
- suggestion: as in B-021. Show Argus's 1-year beta on the stock page, labeled "1y daily vs SPY", or label the Yahoo one "Yahoo, 5y monthly".
- backlog: B-021

## Still-open items I re-checked
- **B-024/B-023:** `/simulate` `value_after` 98,710.93 is $60.66 below `value_before`, exactly the net cash freed. It still has no risk before and after. `/drift` still warns "targets sum to 99.0%" for my 1% cash.
- **B-017:** look-through is still 39.3% "Unclassified" (`sector_lookthrough_after`). GLD's page shows asset mix "Other 100%" and an empty Peers card.
- **B-092:** `/t/GLD` shows a "Reported financials" table from SEC (net income −19.38B in Q2 2026, gold mark-to-market). It's noise on an ETF page, though it no longer 502s.
- **B-091:** the calendar still lists "Core CPI" twice and "CPI" twice (MoM and YoY) with no unit.
- **B-094:** Personal Income/Spending (10-29), ECI and Chicago PMI (10-30) are still only in `all_events`, not in the curated list.
- **Phone:** Markets is 5,900 px tall at 390 px and the Dashboard 2,606 px. Neither overflows horizontally, and the pages logged no errors.
- **Consistency checks that passed:**
  - `/performance` `end_value` 98,771.59 equals the Dashboard value.
  - The 10-27 → 10-28 series change (+$116.68) equals Day P&L.
  - SPY's benchmark step 0.0793% → 0.4239% compounds to SPY's +0.344%.
  - The fear & greed safe-haven and junk details match my own calculations.

## Summary for the round lead
1. No trades: drift is within ±0.26 pp, the Fed held (hawkish lean) and PCE is 10 h away. GLD → IEF stays staged for after PCE (sim net cash +$60.66) and is updated in note 51. loop-macro is $98,771.59, unrealized +$24.44, cash $1,253.87 (+0.03% to date).
2. B-083 works on ETFs: GLD's momentum card, chart buttons, `/api/returns` and the Dashboard Momentum data agree for every period.
3. Top finds:
   - On FOMC night the calendar has already rolled to the UTC date, so the Fed decision is nowhere in Argus except ETF headlines (B-034/B-035).
   - Oil and gold 1D have the wrong sign for the session again (oil −0.98% vs +2.9% on the day).
   - New: "YTD total return" is a stale 9-30 Yahoo figure (GLD −3.3% vs YTD −5.8%, with no dividend).
   - New: after-hours +$299 rests on a 4.5 h-old QUAL print (+1.04% while QQQ was −1.05%).
