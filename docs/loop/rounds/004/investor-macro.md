# Round 004: macro investor

## What I did
- **Backdrop.** I read `GET /api/market-context`, the Markets page (desktop and 390 px) and `argus quotes` at about 22:13 ET Thu 10-22, after the close.
  - **Indices:** S&P 7,663.43 (−0.64% 1D, −1.3% 1M). NDX −1.80% (−5.8% 1M). Russell +0.11%.
  - **Leadership:** XLK −3.29% and XLC −1.42%, against XLP +3.31%, XLU +2.36%, XLF +1.09% and XLV +0.82%. So it was a tech-led risk-off day with a rotation into defensives.
  - **Volatility:** VIX 19.03 (+14% 1D, +34% 1M).
  - **Rates:** a big rally. ^TNX is 4.95% (−19 bp). On the Treasury curve the 10Y is at 4.96, the 20Y fell from 5.47 to 5.32, 2s10s is +31 bp and 10s3m is +74 bp (it was +88).
    - SPY −1.18% vs TLT +1.87% and IEF +1.08%. Bonds hedged equities on the day.
  - **Commodities:** WTI settled at 99.47 (+2.4% on 10-21's 97.15) and trades at 100.76 overnight. Gold settled at 4,060.4 (−2.2%).
  - **Futures** (`argus quotes ES=F NQ=F ZN=F`): ES −0.20%, NQ −0.16%, ZN −0.09%. The overnight session is calm.
  - **Fear & greed:** 9.5 "Extreme fear" with 5 readings. After breadth loaded it was 27.8 "Fear" with 7 readings.
- **New data**, read from Nasdaq because Argus drops the day's releases after 8 pm ET (B-034).
  - Initial claims 194K vs 200K expected. Continuing claims 1,728K.
  - LEI 0.0% vs −0.1% expected.
  - The labor market is still firm. Housing is weak, with mortgages at 7.41%. Oil is about $100.
- **Regime:** still stagflation-lite. But the 5%+ long end met real buyers on a growth scare, and the 20-day stock–bond correlation has turned negative. From `/api/history` 1y, I computed SPY/IEF daily-return correlation of −0.28 over 20 days, +0.27 over 60 days and +0.30 over 1 year.
- **Decision: a half-sized duration step, cash-neutral.** I ran `POST /simulate` first: SELL 50 SGOV and BUY 55 IEF moves SGOV from 18.2% to 13.1% and IEF from 0 to 5.1%, with net cash +$15. Then I placed the trades at the post-market quote:
  - **SELL 50 SGOV @ 100.63:** realized +$1.03.
  - **BUY 55 IEF @ 91.27:** cost $5,019.85.
  - **Targets** (`PUT /targets`, symbol level): SGOV 13 and IEF 5. Everything else is unchanged, and the targets sum to 99% because 1% is held as cash on purpose.
  - **Note:** I added a thesis note on IEF (id 40), with a review date of 10-30, after the FOMC and PCE.
- **After the trade:**
  - **Portfolio:** 11 positions, value $98,931.61, cost $98,747.15, unrealized +$184.46, realized +$1.03.
  - **Risk:** beta went from 0.240 to 0.246, vol from 6.06% to 6.13%, and 95% VaR from $558 to $569.
  - **Drift:** within ±0.29 pp.
- **Cash balance: $1,253.87** (100,000 + 1.03 realized − 98,747.15 cost). The return to date is +0.19%. No dividends have been received yet.

## Last round's changes
Nothing that shipped in round 003 (B-040, B-058, B-015) touches an ETF-only book; those are single-stock fundamentals and research fixes. I re-checked my open items from round 003:
- **B-053 (benchmark start), still open.** `/performance` has `bench_pct 0.0` on 10-20 and starts SPY at the 10-20 close of 769.05.
  - Argus's benchmark return is −0.662% (763.96 ÷ 769.05). From my 10-20 fill (769.47) it would be −0.716%.
  - So Excess shows +0.85%, against a true value of about +0.90%.
- **B-054 (VTIP December dividend), still open.** `/dividends` VTIP: `next_ex_date_est null`, `projected_rest_of_year 0`, `events []`.
- **B-034 (calendar on the UTC date), still open.** This is the third round. See finding 2.

## Findings

### 1. Markets 1D for oil, gold, USD/JPY and bitcoin covers two sessions after the close (WTI +3.72% vs +1.30% / +2.4%)
- kind: bug
- severity: high
- evidence: these are from `GET /api/market-context` and the Markets gauge cards at 22:13 ET, compared with `argus quotes ... --json` taken at the same moment:

  | Gauge | Gauge last / 1D | Quote price / prev_close (settle) / change | True 10-22 session move |
  |---|---|---|---|
  | CL=F | 100.76 / **+3.72%** | 100.76 / 99.47 / +1.30% | +2.39% (99.47 vs 97.15) |
  | GC=F | 4,002.8 / **−3.55%** | 4,009.0 / 4,060.4 / −1.27% | −2.16% |
  | JPY=X | 156.90 / **−0.78%** | 156.87 / 156.775 / +0.06% | n/a |
  | BTC-USD | 81,339 / **−3.18%** | 81,285 / 81,316 / −0.04% | n/a |

  - **Cause:** `/api/history/CL=F` returns a daily bar dated 2026-10-22 with close **100.6**, which is the live overnight price. The real 10-22 settle of 99.47 is gone. The gauge then compares that live price with the 10-21 close (97.15), so "1D" holds the 10-22 session and the overnight session together.
  - GC=F has the same problem: its 10-22 bar closes at 4,010.3, not the 4,060.4 settle.
  - `/api/history/BTC-USD` jumps straight from 10-21 to 10-23, with no 10-22 bar.
  - **Why it matters:** the page header says "as of Thu, Oct 22, 4:00 PM ET", yet the oil card shows a 10 pm price. A gold move of −3.55% instead of −2.2% looks like a liquidation day, and it changed how I first read the commodity complex. Stocks and indices are unaffected: ^GSPC, ^VIX and ^TNX match their quotes.
- suggestion: for 24-hour symbols (`=F`, `=X`, `-USD`), take 1D as the quote's `change_pct` against its `prev_close`, which is the settle. Alternatively, drop a daily bar whose date is today while the instrument's session is still open, and show the price time on the card ("overnight 22:05 ET"). This also covers B-055, the overnight read.

### 2. The economic calendar still drops the day's releases after 8 pm ET: 10-22 claims and LEI are missing (B-034, third round)
- kind: bug
- severity: medium
- evidence: `calendar.all_events` (135 rows) starts on 2026-10-23 at 09:45 with S&P Global PMI. These 10-22 releases are in Nasdaq's feed with actuals, and none of them are in Argus:
  - Initial claims 194K vs 200K expected
  - Continuing claims 1,728K
  - LEI 0.0% vs −0.1%
  - Natural gas storage 77B vs 80B
  - KC Fed 11 vs 12
  - The 10-29 "Initial Jobless Claims" row then shows `previous: null`, so even next week's preview has lost this print.
  - `all_count` is 159, but `all_events` has 135 rows, and nothing says that the list was cut.
- suggestion: as in B-034, use `datetime.now(NY).date()`. If the 24 extra rows are dropped on purpose, say so in the response.

### 3. Fear & greed swung from 9.5 "Extreme fear" to 27.8 "Fear" when breadth loaded (B-036 still open)
- kind: ux
- severity: medium
- evidence:
  - My first `/api/market-context` returned `score 9.5`, 5 components, and `errors.breadth` set.
  - About 10 minutes later the screener universe was built. It returned `score 27.8` with 7 components.
  - "Price strength" scores 88 "Extreme greed" from 38 highs vs 5 lows. Every other reading is between 0.2 and 15.
  - The market didn't change. The 18-point jump comes from the raw 0–100 breadth readings, which aren't percentile-ranked like the other five.
  - The Markets card still doesn't say how many readings went into the score.
- suggestion: as in B-036. Percentile-rank the two breadth readings like the other five, and show "5 of 7 readings" while breadth is loading.

### 4. Risk has only a 1-year window, so the stock–bond correlation flip can't be seen
- kind: feature
- severity: medium
- evidence:
  - `/api/portfolios/loop-macro/risk` (`lookback_days 252`) gives IEF beta 0.12. That matches my own 1-year computation from `/api/history` (corr +0.30, beta 0.121).
  - Over the last 20 sessions, the SPY/IEF correlation is **−0.28** and beta is −0.16. Over 60 sessions it is +0.27.
  - Whether bonds hedge equities is the central allocation question this year. Argus can only tell me the 1-year answer, which says IEF *adds* beta: after the trade, book beta went from 0.240 to 0.246.
  - With a 20- or 60-day view I'd size the duration hedge on the current regime, not last year's.
- suggestion: add a `lookback` parameter to `/risk` (20, 60 or 252 days; the data is already cached), and a selector on the Analysis risk card. Alternatively, put one Markets row with "SPY–TLT correlation, 20d vs 1y".

### 5. An after-close, cash-neutral swap changes today's TWR and day P&L, and dates disagree (B-046, B-049 still open)
- kind: bug
- severity: medium
- evidence: I placed SELL 50 SGOV @ 100.63 and BUY 55 IEF @ 91.27 at 22:16 ET, post-market, after the 4 pm close.
  - **Position:** `/api/portfolios/loop-macro` shows IEF with `day_pnl −3.85` and `ext_pnl +3.85`. I didn't own it during the session, so both should be 0.
  - **Brief:** `argus brief loop-macro` lists **IEF +1.08%** among my top gainers, a gain I didn't have.
  - **Performance:** the 10-22 TWR fell from 0.1912% before the trade to 0.1840% after. The cause is the fill at 91.27 being marked at the 91.20 regular close.
  - **Dates:** the 10-22 row carries `flow_in 5019.85` and `flow_out 5031.50`, while the position shows `first_opened 2026-10-23` and the transaction `ts 2026-10-23T02:16Z`. That is the UTC date (B-049).
- suggestion: treat trades placed after the close as part of the next session for day P&L, movers and TWR. Mark them at the fill until the next close, and date them by the New York session (B-049).

### 6. Simulate still can't tell me that adding IEF raises beta
- kind: feature
- severity: medium
- evidence: `POST /simulate` with SELL 50 SGOV and BUY 55 IEF returned weights and concentration only.
  - I only found out after trading, from `/risk`, that beta goes *up*, from 0.240 to 0.246, and VaR from $558 to $569.
  - With that number up front, I might have used TLT or a smaller size, or decided the hedge isn't a hedge on a 1-year window.
- suggestion: as in B-023 (r003 macro #6), add `risk_before` / `risk_after` (beta, vol, 95% VaR) from the cached `/risk` inputs.

### 7. The brief's "top_losers" still includes SGOV at 0.00% (B-025)
- kind: bug
- severity: low
- evidence: `argus brief loop-macro --json` gives `top_losers [GLD −2.63, SPY −1.18, XLE −0.87, QUAL −0.65, SGOV 0]`.
- suggestion: as in B-025, keep only `change_pct < 0`.

### 8. `/performance` reports a Sharpe ratio of 18.3 from 3 sessions
- kind: bug
- severity: low
- evidence: `GET /api/portfolios/loop-macro/performance` gives `sessions 3, cagr_pct null, volatility_pct 0.84, sharpe 18.33`. CAGR is suppressed for a short history, but Sharpe isn't. The UI doesn't show it, but API and MCP users get a meaningless headline number.
- suggestion: return `sharpe: null` (and `volatility_pct: null`) below about 20 sessions, as is already done for CAGR.

### 9. Markets on a phone: nine full-width gauge cards (about 1,260 px) before fear & greed, and the Markets tab is off-screen
- kind: ux
- severity: low
- evidence: `scripts/screenshot.py /markets --width 390` rendered in 0.15 s with no overflow and no errors.
  - Each gauge card is full width and about 140 px tall, so fear & greed starts at about 1,440 px.
  - The nav row shows "Dashboard, Watchlist, Transactions, Analysis", and "Markets" (the page I'm on) is cut off with no scroll hint.
- suggestion: put the gauges in a 2-column grid under 600 px, either without the sparkline or with a smaller one. Keep the active tab scrolled into view. This is more evidence for B-002.

## Still-open items I re-checked
- **B-026:** the first cold `/risk` took **24.1 s**, then 0.95 s warm. The first call after my trade took 1.8 s.
- **B-039:** the 10-year card shows −19 bp in red and VIX +14% in green.
- **B-029:** the API reports ^TNX 1D as −3.75%, while the page shows −19 bp.
- **B-017:** the look-through after the trade is 39.1% "Unclassified", and it now includes IEF.
- **B-022/B-024:** targets still sum to 99% and produce a warning, because there is no cash line.

## Summary for the round lead
1. Trade: a cash-neutral duration step. SELL 50 SGOV @ 100.63 and BUY 55 IEF @ 91.27, about 5% of the book; targets set to SGOV 13 / IEF 5, with a thesis note. loop-macro is $98,931.61, unrealized +$184.46, realized +$1.03, and cash is $1,253.87.
2. New high-severity bug: after hours, the Markets 1D for futures, FX and crypto covers two sessions. Yahoo's daily bar for today holds the overnight price. Gauges show WTI +3.72%, gold −3.55%, USD/JPY −0.78% and BTC −3.18%, while the quotes show +1.30%, −1.27%, +0.06% and −0.04%. Also new: risk has no short window (SPY/IEF correlation is −0.28 over 20 days vs +0.30 over 1 year), and Sharpe is 18.3 from 3 sessions.
3. Still open: B-034 (10-22 claims and LEI missing, third round), B-036 (fear & greed 9.5 → 27.8), B-053, B-054, B-046/B-049 (an after-close swap moves the day's TWR and P&L), B-023 (simulate has no risk after), B-025 and B-026 (cold /risk 24 s).
