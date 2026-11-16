# Round 017: trader (trading day, session 2026-11-13)

## Account
From `python scripts/sim.py status` after the trades, valued at the 11-13 close:
- Account value **$10,033.40**, return since the start **+0.33%**. SPY over the same window, from my SPY fill (752.66) to the close (754.37), is +0.23%. This was day one.
- Cash **$2,100.10** (21%), invested $7,933.30, no dividends accrued, realized P&L $0.

| Symbol | Qty | Avg cost | Close | Value | % of account |
|---|---|---|---|---|---|
| SPY | 4.6501 | 752.66 | 754.37 | $3,507.90 | 35.0% |
| ADBE | 4.9821 | 240.86 | 243.08 | $1,211.05 | 12.1% |
| XLV | 6.377 | 188.175 | 188.85 | $1,204.30 | 12.0% |
| META | 1.5764 | 634.35 | 641.69 | $1,011.56 | 10.1% |
| LNG | 3.234 | 309.2101 | 308.75 | $998.50 | 10.0% |

House rules: no stock is above 25% and the index ETF is at 35% (limit 50%). I hold 5 positions (4 to 10 allowed), there is no leverage, and each position has a thesis note (ids 1-5).

## What I did
**Market (Markets API, 11-13):**
- S&P 500 was −0.40% on the day, +2.5% for the week and −3.1% for the month. The Nasdaq 100 is −8.6% for the month.
- VIX 19.3; fear & greed 30 ("Fear").
- 10y at 5.15%; the curve is upward sloping (10y−2y +27 bp).
- Sectors: 7 of 11 are above their 50-day average. Health care (+11.3% 1M) and staples lead. Tech is breaking down (XLK −13.2% 1M, below its 50-day and 200-day).
- Calendar: PPI came in at or below consensus; retail sales are due 11-17 and the FOMC minutes 11-18 at 14:00. NVDA reports 11-17 after the close and INTU 11-19.

**Ideas:**
- Two screener runs on the 5,325-company universe:
  - quality-value: cap > $20B, revenue growth > 10%, op margin > 20%, FCF yield > 3%, P/E 5-30, ROE > 15;
  - growth at a reasonable price: cap > $10B, revenue growth > 20%, net margin > 15%, FCF margin > 15%, P/E < 40.
- I put 8 candidates on the watchlist `candidates`, then checked each one's fundamentals, research (analysts, estimate trend, valuation percentiles, quarterly growth, news) and earnings dates.

**Decisions:** all orders filled at the 11-13 mid.

| Trade | Fill | Reason |
|---|---|---|
| BUY 4.6501 SPY ($3,500) | 752.66 | Core position (35%) to keep tracking error against my benchmark low. Buying a pullback in a "Fear" tape. |
| BUY 4.9821 ADBE ($1,200) | 240.86 | P/E 13.6, the 0th percentile of its own 5-year P/E history (20 points, low was 14.5). FCF margin 41%. Revenue +12-13% YoY for four straight quarters. FY EPS consensus is flat to up over 90 days. Earnings 12-09. |
| BUY 1.5764 META ($1,000) | 634.35 | −15.8% over 1M, P/E 21.9 (30th percentile), revenue +26%. Sized smaller because Q3 op margin fell to 20% (Q1 41%), FY EPS consensus dropped from 31.8 to 29.1, and short interest doubled. |
| BUY 3.234 LNG ($1,000) | 309.2101 | Energy diversifier: Q3 revenue +42% and an EPS beat of +31%; FY+1 estimates up from 18.6 to 23.0 over 90 days. Its 1-year beta to SPY, from Argus's history, is about −0.5. |
| BUY 6.377 XLV ($1,200) | 188.175 | Strongest sector (1M +11.3%, YTD +22%), above its 50-day and 200-day, beta about 0.3. Defensive while rates are above 5%. |

**What I didn't buy:**
- UTHR: valuation is at the 100th percentile of its history and FY estimates fell 6% in a week.
- PAYX: analysts rate it hold, the mean target is below the price, and growth has slowed to 6%.
- INTU and NVDA: both report this week. I keep the 21% cash to act on NVDA's 11-17 report and on any further tech weakness.

**Alerts set:**
- price at or below: ADBE 215, META 560, LNG 261;
- NVDA moves 8% or more in a day.

## Last round's changes
- **B-163 (named watchlists on the Watchlist page): works and helped.** `/watchlist` opened straight on `candidates · 8`, with Fwd P/E, revenue growth and net margin side by side. It also shows an empty "Watchlist · 0" tab, although `GET /api/watchlists` returned `[]` before I created anything.
- **B-164 (FOMC minutes in the calendar): works.** `/api/market-context` lists `2026-11-18 14:00 FOMC Meeting Minutes`.
- **B-165 (EPS growth from SEC): works.** ADBE's stock page labels "EPS growth YoY +11.7%" as "SEC, 4Q to 2026-08-28". It matches the API (`eps_growth_yoy_pct` 11.7, source `sec`).
- **B-026 (slow risk): better on a small portfolio.** The first `/api/portfolios/bot0-sim/risk` after the trades took 3.44 s and the brief 1.34 s. It's only 5 positions, though.

## Findings

### Argus has no cash, so every weight, value and risk figure covers only the 79% that's invested
- kind: feature
- severity: high (blocks my house-rule checks)
- evidence:
  - Dashboard "total value" is **$7,933.30**, but the account is worth $10,033.40 (`sim.py status`).
  - Every weight uses $7,933 as the base: Holdings, Largest positions, `/exposure` (`top1_pct` 44.2), the brief (`weight_pct`) and `/risk` (SPY `weight_pct` 44.2, VaR $108 on $7,933).
  - So SPY shows **44.2%** when it's 35.0% of the account, and ADBE 15.3% instead of 12.1%. I can't check the 25%/50% caps in Argus.
  - Performance's TWR (+0.42%) is the return on invested money only; the account is +0.33%.
  - Related to B-024, but much wider than drift targets.
- suggestion: a per-portfolio cash balance (deposits and withdrawals; buys, sells and dividends post to it), included in total value, weights, exposure and risk, and shown as a "Cash" line.

### SPY's day low in the quote (745.20) disagrees with Argus's own daily bar (747.88) and looks like a bad print
- kind: bug
- severity: medium (wrong number; it sets my fill price)
- evidence:
  - `argus quotes SPY --json` (Finnhub) gives low **745.20**; `/api/history/SPY?period=1y` (Yahoo) gives low **747.88** for the 11-13 bar. Open, high and close agree.
  - Measured as low ÷ close:
    - SPY quote: 0.98784;
    - SPY bar: 0.99140;
    - ^GSPC: 0.99177;
    - VOO: 0.99152;
    - IVV: 0.99151.
  - The quote's low is out of line with the index and its ETF twins, so it looks like an outlier print.
  - `sim.py price SPY` uses the quote range (`range_from: "quote"`), so my fill was 752.66 instead of 754.00, a 0.18% edge I shouldn't get.
  - ADBE, META, LNG and XLV agree between the quote and the bar.
- suggestion:
  - for a completed session, prefer the stored daily bar's high and low over the live quote's (or show both);
  - flag a quote whose low or high falls outside the bar by more than a small tolerance.

### Day one shows three SPY figures for the same session, and excess return is overstated (B-053)
- kind: bug
- severity: medium
- evidence:
  - Dashboard tile "Portfolio vs SPY, last session" reads **+0.42% / −0.36%**. Performance on the same page reads SPY **0.00%** and excess **+0.42%**. My own SPY row shows **+0.23%** (fill to close).
  - The portfolio is measured from my fills, but SPY is measured close-to-close (tile) or from the 11-13 close (chart).
  - Measured from the same fill, SPY did +0.23%, so excess was about +0.19%, not +0.42%. Even the SPY I hold "beats SPY".
- suggestion: start the benchmark at the same price basis as the first flows (for the sim, the session mid; for real trades, the fill time). Label the tile as close-to-close.

### The two betas still disagree wildly and neither is labeled (B-021)
- kind: ux
- severity: medium
- evidence:

  | Stock | Stock page "Beta" (Finnhub) | `/risk` per-position beta (1-year daily) |
  |---|---|---|
  | ADBE | **1.46** | **0.185** |
  | LNG | 0.04 | −0.47 |

  - I reproduced the risk numbers from `/api/history` (ADBE 0.17, LNG −0.48).
  - My LNG-as-hedge thesis depends on which one is right.
- suggestion: label each beta with its window and source (e.g. "Beta (Finnhub, 5y monthly)" vs "Beta vs SPY, 1y daily") or show only Argus's own.

### The brief ignores my watchlist's earnings: NVDA reports 11-17 and the brief says nothing (B-106)
- kind: feature
- severity: medium
- evidence: `/api/brief/bot0-sim` returns `earnings_upcoming: []` and `watchlist_movers: []`, while `/api/events?days_ahead=21` lists NVDA earnings on 11-17 after the close (on watchlist `candidates`), and INTU on 11-19.
- suggestion: include named watchlists in the brief's earnings and movers, as B-106 proposes.

### No alert for "closes below its 50-day or 200-day average"
- kind: feature
- severity: low
- evidence:
  - Two of my exit rules are moving-average breaks: LNG below its 200-day (~261) and XLV below its 50-day.
  - The alert kinds are price, day move, 52-week, P/E, cost and earnings. I had to hard-code LNG at $261, which drifts as the average moves.
- suggestion: `close_below_sma` / `close_above_sma` with the period as a parameter (Argus already has `sma50`/`sma200` in fundamentals).

### On a phone, the Holdings table hides Price, Value and P&L
- kind: ux
- severity: low
- evidence:
  - `screenshot.py / --width 390 --full`: the Holdings table shows #, Symbol, Qty and Avg cost; Price is cut off and Day %, Value, Weight and P&L need a sideways scroll.
  - Avg cost matters less on a phone than value and P&L.
  - No page overflow. B-002 is the general phone item.
- suggestion: on narrow screens, show Symbol, Value, Day % and P&L % first, or drop Qty and Avg cost.

### META's TTM operating margin hides a collapse (B-151 again)
- kind: ux
- severity: low
- evidence:
  - `/api/fundamentals/META` gives `operating_margin_pct` 32.9 (TTM).
  - `/api/research/META` growth gives quarterly op margins of 41.3, 40.6, 30.9 and **20.1%** (Q3 2026).
  - Only the research tab reveals the trend that made me halve the position size.
- suggestion: show the latest-quarter margin, and its change, next to the TTM figure.

### Market context `as_of` is a Sunday date for Friday's data
- kind: ux
- severity: low
- evidence: `/api/market-context` returns `as_of: "2026-11-15"`, while every index gauge says `as_of: "2026-11-13"` (the run was Sunday 21:12 ET).
- suggestion: set the top-level `as_of` to the last session's date, or add a `session` field.

### The CLI has no screener, market context or watchlist commands
- kind: feature
- severity: low
- evidence: `uv run argus --help` lists quotes, fundamentals, financials, brief, events, alert and note, but nothing for screen, market context, watchlists or research. I did those steps with curl against the API.
- suggestion: add `argus screen`, `argus market`, `argus watchlist` and `argus research` with `--json`, all through the same facade methods.
