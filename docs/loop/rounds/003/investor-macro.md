# Round 003: macro investor

## What I did
- **Backdrop.** I read `GET /api/market-context` and the Markets page at 22:13 ET Wed 10-21, after the close.
  - **Indices:** S&P 7,757.17 (+0.58% 1D, +0.50% 1W, −0.10% 1M). NDX +1.13% 1D. Russell +0.27% 1D and −6.9% 3M.
  - **Volatility:** VIX 16.68 (−3.6% 1D, +12.2% 1M).
  - **Rates:** the 10y is 5.15% (+3 bp 1D, +96 bp YTD). The curve is still bear-steepening: 2s10s +32 bp, 10s3m +88 bp, and the 20y is at 5.47%.
  - **Commodities, FX, crypto:** WTI $98.30 (−3.4% 1D, +71% YTD), gold $4,129 (−5.8% 1M), USD/JPY 158.05, BTC $83.3k.
  - **Sentiment and breadth:** fear & greed is 39.8 "Fear" with all 7 readings. 57% of the top 500 are above their 50-day average, 6 of 11 sectors are above theirs, and there were 26 new highs vs 4 lows.
  - **Leadership:** still defensives plus energy (XLV +5.9% 1M, XLP +6.3% 1M, XLE +52% YTD). XLK bounced +1.7% on the day. Small caps lag large by −10.1 pp over 3M.
- **Overnight.** `argus quotes ES=F` shows −0.46% (7,764 vs 7,800). SPY post-market is 769.46 (−0.47%), so the risk-on close is already being given back. Argus has these numbers, but the Markets page doesn't show them (finding #3).
- **New data**, read straight from Nasdaq because Argus drops the day's releases after 8 pm ET (B-034, still open).
  - EIA crude draw: −3.06M vs −0.10M expected.
  - Gasoline stocks: −2.95M.
  - MBA purchase index: 129.2, down from 139.3. The 30-year mortgage rate is 7.41%.
  - 20y auction stopped at 5.469%, which matches the curve's 20Y point of 5.47%.
  - Taken with 10-20's housing miss (starts −5.2% vs +1.9%, pending sales −7.3%), this is still a housing-led slowdown with sticky energy and high long rates. The stagflation-lite call is unchanged.
- **Catalysts** (from Argus's calendar): Michigan Fri 10-23, durable goods Tue 10-27, FOMC decision Wed 10-28 14:00, GDP and PCE Thu 10-29 08:30, NFP Fri 11-06, CPI Tue 11-10.
- **Portfolio** (`/api/portfolios/loop-macro`, `/drift`, `/risk`, `/performance`):
  - Value $98,865.32 vs cost $98,757.78, so +$107.54 (+0.11%). Day P&L is +$2.66 and after hours is −$181.08.
  - Drift is within ±0.22 pp against a 2 pp band.
  - Beta 0.25, vol 6.1% vs SPY 12.7%, 95% 1-day VaR 0.56% ($555).
  - I recomputed GLD's beta (0.798 vs Argus 0.800) and XLE's beta (−0.425 vs −0.424) from `/api/history?period=1y`. Both match. The sector 1D numbers match the quotes (XLE +0.28, XLP −0.73, XLV −0.49).
- **Decision: no trades.** I ran `POST /simulate` on a pre-FOMC de-risk: sell 3 SPY ($2,319) and buy $2,300 SGOV. That moves SPY from 10.2% to 7.8% and SGOV from 18.2% to 20.5%. The book's beta is already 0.25, the regime is unchanged, and drift is negligible, so the trade isn't worth it before the event. I'll review after FOMC and GDP/PCE (10-28/29), as planned.
- **Cash balance: $1,242.22** (100,000 − 98,757.78). No realized gains, no dividends received.

## Last round's changes
- **B-033 (brief scoped to its portfolio): works, and it helped.** `argus brief loop-macro --json` has empty `earnings_upcoming`, `dividends_upcoming`, `alerts_fired` and `theses_due`. No PEGA, VICR, NEE, PG, RMBS or KO. Movers and headlines are only my 10 ETFs.
- **B-010 (lumpy payers use the trailing 12 months): works for VTIP.** The rate is 2.347 = `trailing_12m`. I recomputed that from the cached history: 0.711 (12-18-25) + 0.023 + 0.680 + 0.933 = 2.347. The old figure would have been 0.933 × 4 = 3.73. But VTIP's December payment is missing from the rest-of-year projection (finding #2).
- **B-007 day-two check: works.**
  - `/performance` reports `gain 107.544`, and the portfolio reports `unrealized_pnl 107.542`.
  - `benchmark_pct 0.525` is non-zero and equals SPY's `change_pct 0.5253`.
  - Day P&L of +$2.66 equals the series value change (98,865.32 − 98,862.66).
  - The benchmark is measured over a different window from the portfolio, though (finding #1).

## Findings

### 1. "Excess return vs SPY" compares the portfolio since its buy fills with SPY since that day's close
- kind: bug
- severity: medium
- evidence: Dashboard, Performance "All", and `/api/portfolios/loop-macro/performance`:
  - It shows Return +0.11%, SPY +0.53%, Excess −0.42%.
  - The series gives the portfolio `twr_pct 0.106` on 10-20 (buy fill → close) but `bench_pct 0.0` on 10-20. So the benchmark starts at the 10-20 close, while the portfolio starts at its intraday fills.
  - My own SPY lot was bought at 769.47 on 10-20 and is now 773.09, which is +0.47%. The 10-20 close was 769.05.
  - Over the same window as the portfolio, SPY returned +0.47%, not +0.53%, so the true excess is about −0.36%.
  - On a volatile buy day the error can be a full percentage point, and it stays in "excess since inception" forever.
- suggestion: for the first flow day, start the benchmark at the same basis as the portfolio. Either use the benchmark's prior close for both (treat buys as made at the prior close for TWR), or scale the benchmark's day-one return by the fills. The simplest consistent rule: day-one portfolio TWR = close ÷ cost − 1, and day-one benchmark = close ÷ prev close − 1. Then say which convention is used in the footnote.

### 2. VTIP's December dividend isn't projected: rest of 2026 shows $0 and the next ex-date is blank
- kind: bug
- severity: medium
- evidence: `/api/portfolios/loop-macro/dividends` gives VTIP `frequency quarterly`, `last_ex_date 2026-10-01`, `next_ex_date_est null`, `projected_rest_of_year 0` and `events []`. The Analysis Dividends table shows "–" for Rest of 2026 and Next ex-date.
  - VTIP's own history (cached `dividend_history`) has December ex-dates every year: 2024-12-24 (0.529) and 2025-12-18 (0.711). The quarterly schedule is uneven: Apr 1, Jul 1, Oct 1, then mid/late December.
  - `services/dividends.py::analyze_holding` steps 3 months from the last ex-date (10-01 → 2027-01-01). That falls past year-end, so nothing is projected.
  - That is about $96–$117 missing from "2026 expected total" ($465.37): trailing ÷ 4 × 164, or the last December amount × 164.
  - The same rule puts SGOV's next ex-date on Sun 11-01 (see B-013's weekend dates).
- suggestion: when the last 2 years show a payment in a calendar month that the fixed step skips, project the next ex-date from last year's date for that month. Alternatively, use the median day-of-year of the past ex-dates for each quarter. Add a test with VTIP's dates.
- related: B-013 (estimated ex-dates), but this one drops a real payment, not just its date.

### 3. Markets shows nothing about the overnight session: no futures and no after-hours read
- kind: feature
- severity: medium
- evidence: at 22:13 ET the Markets gauges show the 10-21 close (S&P +0.58%, NDX +1.13%), and the header says "Market closed".
  - `uv run argus quotes ES=F --json` → `price 7764.25, prev_close 7800.25, change_pct −0.46`, as of 02:06 UTC.
  - SPY's `ext_price 769.46` (−0.47%) and QUAL −0.65% post-market are only on the Dashboard ("After hours −$181.08").
  - A macro desk's first evening question is "what is the overnight tape saying". Here the close says risk-on and futures say the gain is gone. That changes whether I'd add risk at the open.
- suggestion: when the session isn't regular, add a "Futures / overnight" row to the gauges: ES=F, NQ=F, RTY=F, ZN=F or the 10y, CL=F, with change vs the settle. Alternatively, show the indices' ETF post-market change under each index card ("SPY post −0.47%"). The quote path already serves `=F` symbols.

### 4. The economic calendar still starts on the UTC date: 10-21's releases are missing at 22:13 ET (B-034, still open)
- kind: bug
- severity: medium
- evidence: `calendar.all_events` (125 rows) starts on 2026-10-22, the first date being `Initial Jobless Claims 10-22`. Nasdaq's feed for 10-21 ET (its `date=2026-10-22` bucket) has these, all with actuals:
  - EIA crude −3.06M vs −0.10M
  - gasoline −2.95M
  - MBA applications −5.3%
  - 20y auction 5.469%
  - Argus's data shows none of them. Same root cause and fix as B-034.
- suggestion: as in B-034 (`datetime.now(NY).date()` in `economic_events`). This is the second round that I had to read the day's prints by hand.

### 5. Fear & greed still jumps when breadth loads: 27.0 with 5 readings → 39.8 with 7, minutes apart (B-036, still open)
- kind: ux
- severity: medium
- evidence: my first `/api/market-context` returned `score 27.0`, 5 components, `errors.breadth` set. A few minutes later, after another investor built the screener universe, it returned `score 39.8`, 7 components.
  - "Price strength" scores 86.7 "Extreme greed" from 26 highs vs 4 lows, which is 5.2% of stocks at new highs.
  - The page doesn't say how many readings are in.
  - That's a 13-point swing, about a whole rating band, with no change in the market.
- suggestion: as in B-036. Return and show `components_used`, and percentile-rank the two breadth readings like the other five.

### 6. Simulate can't tell me what a de-risk does to beta, volatility or VaR
- kind: feature
- severity: medium
- evidence: `POST /api/portfolios/loop-macro/simulate` with `SELL SPY 3, BUY SGOV $2,300` returns weights, concentration and look-through sectors before and after, but no beta, vol or VaR.
  - The whole point of a pre-FOMC trim is "how much does beta and VaR drop". I had to estimate it by hand from the `/risk` per-position betas: about 0.25 → 0.23.
  - `/risk` already has per-position beta and the full correlation matrix, so after-trade beta, vol and VaR are a weighted recompute.
- suggestion: add `risk_before` / `risk_after` (beta, vol, 95% VaR) to simulate, using the cached `/risk` inputs. Also show the cash this frees up: `net_cash` is there, but the UI doesn't show it.
- related: B-023 (simulate can't answer income or drift); this is the risk side of it.

### 7. Targets & drift still opens "By sector" (ETF 100%, targets sum 0.0%) though I saved position targets (B-022, B-024 still open)
- kind: ux
- severity: low
- evidence: Analysis for loop-macro. The card's default tab shows one row, "ETF 100.0%", with an empty target and "Targets sum to 0.0%".
  - `/api/portfolios/loop-macro/drift` (symbol level) shows my 10 targets and `warnings: ["targets sum to 99.0%, not 100%"]`. The missing 1% is the cash I hold on purpose (B-024).
  - For an ETF-only book the sector tab is never useful (see B-017).
- suggestion: as B-022, open the level the targets were saved at. As B-024, let a "cash" target fill the remainder.

### 8. On a phone, the Dashboard holdings table shows only symbol and name (more evidence for B-002)
- kind: ux
- severity: low
- evidence: a Dashboard screenshot at `--width 390` (2,479 px, no page overflow, no errors). The Holdings table clips after the name column, so Qty, Price, Day %, Value, Weight and P&L are all off-screen, and nothing shows that the table scrolls sideways.
- suggestion: at narrow widths, drop the long fund name (it's on the stock page) and show Symbol, Day %, Value and Weight. Alternatively, use a two-line row.

### 9. The brief's "top_losers" still lists flat or up positions (B-025, still open)
- kind: bug
- severity: low
- evidence: `argus brief loop-macro --json` → `top_losers` contains VTIP `change_pct 0.0` and SGOV `+0.0099`. Only 3 of my holdings were down, and the list is padded to 5.
- suggestion: as in B-025, keep only `change_pct < 0` (and only `> 0` for gainers).

## Still-open items I re-checked
- **B-026:** cold `/risk` took 18.6 s, then 0.85 s and 0.71 s warm.
- **B-017:** the look-through is still 39.3% "Unclassified" (SGOV, VTIP, GLD, DBC).
- **B-030:** AGPXX (a money-market fund held by DBC) is still #2 in "Single-stock exposure".
- **B-021:** "SPY falls 10%" gives −2.5%, next to −5.7% to −26.5% in the replays.
- **B-016:** couldn't reproduce this round. Sector 1D matched the quotes.

## Summary for the round lead
1. No trades. The regime is unchanged (stagflation-lite: housing-led slowdown, oil about $98, 10y 5.15%), and drift is under 0.25 pp. loop-macro is $98,865.32 (+$107.54), and cash is $1,242.22.
2. Verified: B-033 brief scoping works; B-010 VTIP rate = trailing 12m (2.347, recomputed); B-007 day-two gain = unrealized and the benchmark is non-zero. New bugs: the benchmark starts at the day-one close while the portfolio starts at its fills (excess −0.42% vs a true ~−0.36%), and VTIP's December dividend isn't projected (rest of 2026 $0; about $100 missing).
3. Still broken: B-034 (10-21 releases missing at 22:13 ET), B-036 (fear & greed 27.0 → 39.8 when breadth loads), B-022/B-024, B-025, B-026, B-017, B-030. Top wishes: overnight futures on Markets, and risk after the trade in simulate.
