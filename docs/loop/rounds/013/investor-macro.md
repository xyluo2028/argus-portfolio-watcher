# Round 013: macro investor

## What I did
- **When:** Thu 11-05 at about 21:15 ET (02:13 UTC 11-06). The market was closed and the latest close was Thu 11-05.
- **Sources:**
  - `GET /api/market-context` (twice: before and after breadth loaded) and `argus quotes --json` for ES=F, NQ=F, ^VIX, ^VIX3M, ^TNX, ^IRX, HYG, LQD, TLT, TIP, IEF, UUP, EEM, EFA, BZ=F, HG=F, RSP, CL=F, GC=F, GLD, QQQ, SMH, NVDA, MTUM and SPLV.
  - The loop-macro endpoints: portfolio, drift, exposure, dividends, performance, risk, transactions, simulate and brief. Also `/api/returns/QUAL` and `/api/history/<sym>` for 11 ETFs, which I used to compute 20-day and 60-day correlations myself.
  - Screenshots of Markets (1400 px), Dashboard (1400 px and 390 px), Analysis and `/t/QUAL`.
- **Backdrop on 11-05: a tech/AI momentum unwind that credit didn't confirm.**
  - **Indices:** S&P 7,353.73 (−4.36%), NDX −6.36% (−14.3% over 1M), RUT −4.45%.
  - **Under the index:** XLK −8.0%, SMH −11.2%, NVDA −9.3% and MTUM −8.2%. EEM −5.8% and EFA −2.9%.
  - **Breadth:** 76 stocks up and 424 down.
  - **Defensives held up:** XLP −0.75%, XLU −0.71%, XLC −0.59% and SPLV −1.17%.
  - **Volatility:** VIX 28.18 (+69.7%). VIX ÷ VIX3M is 1.10, so the term structure is inverted.
  - **Credit barely moved:** HYG −0.31% and LQD +0.15%.
  - **Rates:** the 10Y fell 6 bp to 4.84%. 2s10s is +38 bp and 10s3m +67 bp.
  - **Dollar, gold and oil:** UUP was flat. GLD +0.81%, with gold futures at 4,113 on the session. WTI settled at 90.52 (from 88.12 on 11-04).
  - **Data:** claims 189K against 197K expected. ISM services on 11-04 came in at 54.5, with prices paid 73.0.
  - **Overnight:** ES +0.16% and NQ +0.95%.
- **Regime:** a positioning and valuation shock inside equities, not a growth or credit shock: credit is calm, claims are low and bonds are hedging. My book is built for this. Payrolls are tomorrow at 08:30 and CPI is on 11-10, so I'm not adding beta into an inverted VIX curve 11 hours before NFP.
- **Trades: none.** I staged a post-NFP add in note 80:
  - **Trigger:** NFP > 0, HYG > 76.5 and VIX/VIX3M < 1.0 at the close.
  - **Trade:** SELL 29 SGOV / BUY 4 SPY.
  - **Simulated:** net cash −$18.95, realized −$4.63, SPY 10.8% → 14.1%.
  - The XLE→RSP switch (notes 62 and 69) stays staged: RSP's 20-day correlation to SPY is 0.77, so it would add beta into the drawdown.
- **QUAL split 4:1 on 11-05, and Argus doesn't know (finding 1).**
  - I did **not** record a SPLIT transaction, because doing so breaks performance worse (finding 2). Note 79 explains this.
- **Book at the 11-05 close, as Argus shows it:**
  - value $88,394.12 and cost $98,404.56;
  - unrealized −$10,010.44 and realized −$287.03;
  - Day P&L −$1,335.99 (−1.49%).
- **The true book, with QUAL at 212 shares:**
  - value **$97,105.73** and unrealized −$1,298.83;
  - Day P&L **−$1,648.43 (−1.67%)** against SPY −4.41%.
- **Cash: $1,308.40**, unchanged (100,000 − 287.03 realized − 98,404.56 cost).
  - True value plus cash is $98,414.13, a return to date of **−1.59%**.
  - Argus's figures give −10.30%.
  - Accrued dividends of $65.83 are not counted in cash.

## Last round's changes
- **B-134 (the last session's close is filled from the quote while Yahoo's bar is missing): works, and it mattered tonight.**
  - Yahoo again has no 11-05 bar: history ends at 11-04 for every symbol, and `yf.Ticker('QUAL').history` shows 11-05 as NaN.
  - Performance reports `closes_from_quotes: {date: 2026-11-05, symbols: [...]}`, SPY is non-null (−4.69%) and excess is non-null.
  - **Last step vs Day P&L:**
    - The last step is 88,394.12 − 98,754.16 = −10,360.04, while Day P&L is −1,335.99.
    - The whole difference is QUAL: 53 × (54.79 − 227.02) − (−104.15) = −9,024.05.
    - Excluding QUAL, the last step equals Day P&L to the cent, so B-134 itself is right.
  - The UI still doesn't show that closes came from quotes.
- **B-133 (dividend history merged, not replaced): holds.**
  - Received is $65.83 (IEF $26.23 on 79 shares, SGOV $39.60), the same as last round.
  - IEF and SGOV `last_ex_date` are still 09-01. Yahoo hasn't restored the 10-01 rows, as expected.
- **VTIP 10-01 estimate (re-check request): correctly not counted.** loop-macro first bought VTIP on 10-20, after that ex-date.
- **B-135 (payrolls dropped off the calendar): back, by itself.**
  - NFP (65K expected), unemployment, AHE, U6 and Michigan sentiment are listed for Fri 11-06.
  - Nasdaq restored the rows, so nothing in Argus was fixed and the next gap would still vanish silently. B-135 should stay open.

## Findings

### 1. QUAL split 4:1 on 11-05 and Argus prices 53 old shares at the new price: −$9,058 phantom loss, and drift says buy $7,703
- kind: bug
- severity: high (wrong numbers on every portfolio page, and a drift instruction that would make me buy 4× the intended position)
- evidence:
  - **Quote:** `argus quotes QUAL --json` gives price 54.79, prev_close **56.755** and open 56.78. The 11-04 close in `/api/history/QUAL` is **227.02**, and 227.02 ÷ 4 = 56.755 exactly. Yahoo's `info.previousClose` is also 56.755, while its `splits` series is still empty.
  - **Position** (`/api/portfolios/loop-macro`): qty 53, avg_cost 225.695, market_value **2,903.87**, unrealized_pnl **−9,057.97 (−75.7%)**. The true value is 212 × 54.79 = 11,615.48.
  - **Day P&L for QUAL:** −104.15 (53 × −1.965). The true figure is 212 × −1.965 = **−416.58**.
  - **Totals:**
    - value 88,394.12, where 97,105.73 is right;
    - unrealized −10,010.44, where −1,298.83 is right;
    - Day P&L −1,335.99, where −1,648.43 is right.
  - **Drift:** QUAL weight 3.29% against a 12% target, `outside_band: true`, **trade_to_target +7,703.42**. QUAL's true weight is 11.96%. Every other weight is overstated by about 10% (XLV is "2.02 pp over, outside band", while it's really 12.76%).
  - **Performance:** TWR **−10.39%**, gain −10,231.65, max drawdown −10.82% and excess **−5.70%** vs SPY. The true figures are about −1.56% TWR and **+3.1 pp** excess. The Dashboard chart shows the book falling off a cliff below SPY.
  - **Stock page `/t/QUAL`:** 5D −75.6%, 1M −75.7%, 1Y −71.9%, and a 52-week range of 54.75–228.13.
  - **Brief:** QUAL "near 52w_low (gap 0.07%)", unrealized −75.7%.
  - **Dividends:** QUAL yield 3.45%, computing the pre-split $1.892 rate over the post-split price. The true yield is about 0.86%.
  - **Not just QUAL:** MTUM's prev_close is 68.215 as well, so other ETFs may have split (QUAL isn't the only one).
- suggestion:
  - Detect the split from the quote itself: when the prev_close the quote reports differs from the stored last daily close by a clean ratio (2, 3, 4, 5, 10, 1/2...) and Yahoo has no split row yet, flag the symbol "possible split 4:1" on the portfolio and position.
  - Better still, read Yahoo's split events when they arrive and apply them to positions automatically.
  - Until then, show a banner rather than a −75% loss and a "buy $7,703" drift row.

### 2. A user can't fix it either: recording the SPLIT makes performance +300% on day one, because stored history is never re-adjusted
- kind: bug
- severity: high (the documented workaround corrupts performance, and the cache will keep a permanent 4× cliff)
- evidence:
  - **Position math works:** `argus txn add loop-macro SPLIT QUAL --qty 4 --date 2026-11-05T09:30 --dry-run` gives 53 → 212 shares and avg cost 225.70 → 56.42.
  - **But performance assumes adjusted closes:** `performance.py` says "Closes are split-adjusted (Yahoo), so quantities before a recorded SPLIT are scaled". The stored QUAL bars are *unadjusted*: 227.02 on 11-04, 221.91 on 11-03 and so on.
  - **Replay check:** I ran `compute_series` in-process on QUAL alone (BUY 53 @ 225.695 on 10-20, closes from `/api/history/QUAL` plus 54.79 for 11-05). This is read-only; nothing was written.
    - without the split: 10-20 value 11,962 → 11-05 value 2,904 (−75.7%);
    - with SPLIT 4 on 11-05: 10-20 value **47,846 (+300.0%)** → 11-05 value 11,615.
  - **Why it won't heal:** `_ensure_daily_bars` only re-fetches the last 3 bars (`todo[sym] = last - timedelta(days=3)`). When Yahoo does adjust its history, Argus will re-download 11-02 to 11-05 at about 55. Everything before stays at about 222 in SQLite.
  - **Consequence:** QUAL's chart, returns, volatility, beta, correlations, VaR and stress tests keep a −75% one-day "crash", and the portfolio's performance stays wrong whether or not a SPLIT is recorded.
- suggestion:
  - When a split is detected (from Yahoo's split rows, or finding 1's ratio check), delete and re-download that symbol's whole daily history.
  - Make performance scale pre-split quantities only for bars older than the stored split adjustment. Or simpler: always re-download a symbol's full history when a SPLIT transaction is recorded.

### 3. The 1-year risk model badly understated today's loss: realized move was 3× beta, and the loss was 3.4× the 95% VaR
- kind: feature (re-sighting of B-067 and B-021, with live evidence)
- severity: medium-high (risk numbers I size positions with were off by a factor of 3 on the first real shock)
- evidence:
  - **Analysis → Risk ("to 2026-11-04", 252 days):**
    - beta 0.13; "SPY falls 10% (via beta)" gives −1.3% (−$1,178);
    - 1-day VaR 95% $436 (0.49%) and VaR 99% $609 (0.69%).
  - **What happened today:** SPY −4.41% and the true book −1.67% (−$1,648). That's a realized beta of about 0.38, **2.7× the 99% VaR**.
  - **The factor table on the same page** says market loading 0.28, which is closer.
  - **Position betas mislead:** XLE β −0.47 and DBC β −0.41, but XLE fell −2.98% today. My 20-day correlations from Argus's own history plus today's quote are XLE −0.07 (60d −0.13), USMV 0.75, RSP 0.77, XLV 0.43, IEF −0.27 and GLD 0.40 (it was 0.69 last round).
  - The 1-year window is dominated by the oil-shock months, when energy moved against stocks.
- suggestion:
  - Add a 20d / 60d / 1y window toggle for beta, VaR and correlations (B-067).
  - Label the two betas, and show the factor-model market loading next to the "SPY falls 10%" line (B-021).

### 4. Fear & greed read 1.2 "Extreme fear" at 21:12 ET, then 22.1 after breadth loaded; price strength said "Extreme greed" on a 76/424 day
- kind: ux
- severity: medium (re-sighting of B-036; tonight's jump was 21 points)
- evidence:
  - **First call:** the first `/api/market-context` returned `score 1.2`, 5 components and `errors.breadth: "needs the screener's universe"`.
  - **Later:** the screenshot and a second call minutes later showed `22.1`, 7 components and `errors {}`.
  - **The added components:** "Price strength 91 Extreme greed (81 new 52-week highs vs 8 lows)" and "Price breadth 58 Greed", on a day with 76 advancers and 424 decliners.
  - **Why the highs count is high:** `stock_breadth` counts a session *high* within 0.05% of Yahoo's 52-week high. AAPL's day high was 355.38 (prior max high 354.50), and it closed −1.53%. JNJ's high of 281.92 against a 52-week high of 282.02 counts too, even though it closed −1.45%.
  - On a day that opened higher and closed −4.4%, that counts morning highs as greed.
  - The API still has no component count or "partial" flag.
- suggestion:
  - B-036: show "5 of 7 readings (breadth loading)" while partial.
  - Count a new high only when the *close* is at the 52-week high (or label the component "touched a 52-week high intraday").

### 5. Markets 1D for gold and oil is still the overnight tick: gold is shown red on a green session
- kind: bug / ux
- severity: medium (re-sighting of B-016 and B-055)
- evidence:
  - Under "Market closed as of Thu, Nov 5, 4:00 PM ET", the cards read:
    - "Gold $4,072 −1.02%": the 11-05 session was 4,073.0 → 4,113.5, **+1.0%**;
    - "WTI $91.23 +0.78%": the session was 88.12 → 90.52, **+2.7%**.
  - Spark tails: GC=F `[3940.4, 4073.0, 4113.5, 4068.0]` and CL=F `[96.09, 88.12, 90.52, 91.41]`.
  - On the day equities fell 4.4%, the gold card says gold fell too. That's the opposite of what a macro reader needs to see about the hedge.
- backlog: B-016, B-055

### 6. Calendar: payrolls are back, but CPI/PPI/PCE rows are still unlabeled twins
- kind: ux
- severity: low (re-sighting of B-091)
- evidence:
  - `calendar.events` on 11-10 has "Core CPI" twice (previous 0.3% and 2.6%) and "CPI" twice (3.7% and 0.6%). 11-13 has "PPI" twice and 11-25 has "PCE price index" and "PCE Price index".
  - The footnote says "'Previous' tells them apart". For CPI, the week's key print, the consensus column is blank, so the m/m and y/y rows can't be told apart until the actuals come in.
- suggestion: append "(MoM)" / "(YoY)" to the event name (B-091).

### 7. ETF stock page still requests SEC financials (502) and shows "Company: Loading…"
- kind: bug
- severity: low (re-sighting of B-092)
- evidence: `scripts/screenshot.py /t/QUAL` reported `errors: ["Failed to load resource: ... 502 (Bad Gateway)"]`, and the Company card still read "Loading…" after 4 s.
- backlog: B-092

### 8. Re-sightings (short)
- **Risk endpoint:** 15.6 s cold (`/api/portfolios/loop-macro/risk`). Everything else took under 1.2 s (B-026).
- **Analysis "Targets & drift"** still opens "By sector" with "Targets sum to 0.0%" while 10 position targets summing to 100% are saved (B-022).
- **Brief:** still no macro events, so NFP tomorrow isn't in it (B-038). `theses_due` has 16 rows, most superseded (B-127).
- **Dashboard at 390 px:** the holdings table shows only symbol and name; the numbers are clipped off the right (B-002).
- **VTIP yield 5.58%:** the 0.68 July payment × 4, against a trailing-12m figure of 1.414 (2.9%). The trailing figure is low because Yahoo dropped the October row. Neither yield is right for a short-TIPS fund; low severity.

## Consistency checks that passed
- **Day P&L:** −$1,335.99 equals the sum of the position Day P&Ls and matches the brief and the Dashboard. QUAL's share is internally consistent (53 × −1.965), just on the wrong share count.
- **Simulate:** SELL 29 SGOV / BUY 4 SPY priced at the settled closes (100.45 and 733.00). Net cash −18.95 = 29 × 100.45 − 4 × 733, and realized −4.63 = 29 × (100.45 − 100.609).
- **Curve spreads:** 2s10s 38 bp (4.84 − 4.46) and 10s3m 67 bp (4.84 − 4.17) match the curve table. The 10Y card (4.84%, −6 bp) agrees with ^TNX 4.837.
- **Term structure:** VIX 28.18 ÷ VIX3M 25.55 = 1.10, which matches the fear & greed component.
- **Payrolls (B-135)** are listed again for 11-06.
- **Pages:** Markets, Dashboard and Analysis had no page errors and no horizontal overflow at 1400 px.

## Summary for the round lead
1. **No trades.** The tech-led −4.4% day wasn't confirmed by credit. I staged SELL 29 SGOV / BUY 4 SPY for after NFP (note 80). Argus shows loop-macro at $88,394.12; the true value is $97,105.73. Cash $1,308.40; the true return to date is −1.59%.
2. **High:** QUAL split 4:1 on 11-05 and Argus doesn't know. It shows −$9,058 unrealized, TWR −10.39% (true about −1.6%), excess −5.70% (true about +3.1 pp), and a drift row saying "buy $7,703". Recording a SPLIT makes day one +300%, because stored bars are unadjusted and never re-fetched beyond 3 days.
3. **Shipped items:** B-134 works (last step = Day P&L excluding QUAL), B-133 holds ($65.83), and payrolls are back (Nasdaq restored them, so B-135 stays open). The 1y risk model put beta at 0.13 and VaR99 at $609 against a −$1,648 day (B-067/B-021). F&G went 1.2 → 22.1 (B-036). Gold 1D shows the wrong sign (B-016/B-055).
