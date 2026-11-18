# Round 019: trader (trading day, session 2026-11-17)

## Account
From `python scripts/sim.py status`, valued at the 11-17 close. I made no trades this round.
- Account value **$9,795.79**, return since the start **−2.04%**.
- SPY from my 11-13 fill (752.66) to the 11-17 close (732.44) is **−2.69%**, so the account is about 0.65 pp ahead of SPY. Measured close to close from the 11-13 close (754.37), SPY is −2.91%.
- Cash **$1,200.11** (12.3%), invested $8,595.69, no dividends accrued, realized P&L $0.

| Symbol | Qty | Avg cost | Close 11-17 | Value | % of account |
|---|---|---|---|---|---|
| SPY | 4.6501 | 752.66 | 732.44 | $3,405.92 | 34.8% |
| XLV | 6.377 | 188.175 | 185.24 | $1,181.28 | 12.1% |
| ADBE | 4.9821 | 240.86 | 235.55 | $1,173.53 | 12.0% |
| LNG | 3.234 | 309.21 | 301.97 | $976.57 | 10.0% |
| META | 1.5764 | 634.35 | 618.87 | $975.59 | 10.0% |
| TMUS | 5.2579 | 171.17 | 167.90 | $882.80 | 9.0% |

House rules: no single stock is above 25%, and SPY is at 34.8% (the ETF limit is 50%). I hold 6 positions (4 to 10 allowed) and use no leverage. Every position has a thesis note.

## What I did
**Market (`/api/market-context`, 11-17):**
- The S&P 500 fell 1.03% and the Nasdaq 100 0.72%. It was a broad sell-off: every sector shown was down, with XLF −1.9%, XLC −1.5% and XLV −1.4%. XLK is −11.0% over 1M.
- Fear & greed read **10.9 ("Extreme fear")** before breadth loaded and 19.8 after. The VIX is 25.5, and its term structure is inverted (1.02).
- Breadth: 81 advancers vs 418 decliners. 55.6% of stocks are above their 50-day average (63% last round). There were 4 new highs (COST, PG, DIS, DRI) and 10 new lows (NFLX, BA, COIN, AXON…).
- 10y yield 5.10%, and the 10y−2y spread is +30 bp.
- Macro: core retail sales came in at 0.6% vs 0.4% expected, and industrial production at −0.4% vs 0.0%.
- Software led the declines: INTU −7.2%, ADBE −4.2% and PAYX −3.1%, all on my lists. The headlines are "S&P 500 Losers: Software Stocks Lead Session Declines" and Microsoft Ignite AI-agent news.
- After hours, futures were up on NVDA's report: SPY ext +0.69% and QQQ +1.37%.

**Holdings:**
- ADBE −4.2% in the software sell-off. Its news is product launches and partnerships with Google and Microsoft, plus reports that Michael Burry is buying the stock. The rating is hold and the mean target is 267. The thesis is intact: the stock is cheap and the selling is sector-wide, not about Adobe. It is at 235.55, far from my 215 exit alert.
- META −1.2%, LNG −1.1%, TMUS −1.2% and XLV −1.4%. No news breaks any thesis, and no alert fired.
- LNG fell with the market on a down day. One day doesn't disprove its negative 1y beta, but I'm watching it.
- Coming up: TMUS goes ex-dividend on 11-25 ($1.02, about $5.36 for my shares), INTU reports on 11-19, and META reports on 01-26.

**Ideas:**
- I re-ran last round's quality screen on the new TTM fields. It now returns TMUS, ADBE and TPR, and INCY drops out (P/E TTM 60.2, op margin TTM 10.4%).
- A growth-at-a-reasonable-price screen (cap > $2B, latest-quarter revenue growth ≥ 15%, P/E TTM 5–25, op margin TTM ≥ 15%) returned 54 names. NVDA, GOOGL, META and LNG lead the list.
- That screen exposed FIX's broken figures (finding 1).

**NVDA, the decision I planned for this round:**
- NVDA reported after the 11-17 close: revenue **$115.8B vs $111.3B** expected and EPS **2.68 vs 2.525** (+6.1%), with guidance above expectations. The board confirmed that Jensen Huang won't be reinstated. After hours it traded at **162.94 (+4.8%)**; the 11-17 mid is 154.26.
- In favour: P/E TTM 19.7, the 0th percentile of its own 5-year range. FY+1 consensus EPS is 15.86, about 10x forward. The latest SEC quarter shows revenue +106% YoY.
- Against: the CEO ouster and governance questions. In one month analysts went from 49 buy / 2 hold to 36 buy / 14 hold. Insiders made 172 sales and no buys in a year.
- **No trade.** A buy now would fill at 154.26, a price from before the report. I can see that the stock already trades 5.6% above it, so I would be booking a gain the fill rule hands me for free, not making an investment decision.
- I wrote down the plan (note id 7, review 2026-11-18): decide at the 11-18 session, at a price that includes the reaction, with up to about $1,000 (10%) from cash. See finding 2.

**Other trades:** none.
- I don't want to add to ADBE into a sector-wide sell-off. It is already 12% of the account.
- SPY: breadth worsened again (55.6% of stocks above the 50-day, down from 63%). I'll wait for the tape to stabilize.

## Last round's changes
- **B-175 (provisional history bar): works and helped.**
  - `/api/history/ADBE?period=5d` now has a real 11-16 bar from Yahoo (v 3,824,400, no `provisional` flag), and the 11-17 bar is marked `provisional: true` with `v: null`.
  - It holds the session's real range (O 243.00, H 243.63, L 233.79, C 235.55, the same as the quote). SPY and NVDA behave the same way.
  - On FIX's stock page, the readout says "Tue, Nov 17 (from quote) O 1,079.56 H 1,110.00 L 1,053.09 C 1,099.02".
- **B-136 (brief dividends cover 14 days): works.** `dividends_upcoming` lists TMUS ex-dividend 2026-11-25 at $1.02 a share (amount $5.36), and the payload states `dividends_days_ahead: 14` and `earnings_days_ahead: 7`.
- **B-019 (screener TTM, latest quarter and periods): works and helped.**
  - INCY drops out of the quality screen when it runs on the TTM fields. XZO, NUTX and PSIX are no longer in a screen for latest-quarter growth ≥ 15% (I ran it with no cap filter).
  - Every field in `GET /api/screener` carries a `period` (fy, quarter, ttm or mrq), and every row carries `latest_quarter` and `ttm_through`. I didn't screenshot the Screener page's headers this round.
  - New holes are in findings 1 and 3.
- **NVDA moving to `watchlist_earnings.recent`: works.** The brief lists NVDA under `recent` with epsActual 2.68, revenueActual $115.84B and a surprise of +6.14%.
- **Brief first-load time:** 2.71 s, down from 5.65 s last round.

## Findings

### 1. FIX shows −$4.62B revenue for Q4 2025, and the bad figure flows into TTM revenue, P/E, margins and the screener
- kind: bug
- severity: high
- evidence:
  - `uv run argus financials FIX --json` (quarterly) returns period 2025-12-31 with **revenue −4,624,288,000**, gross profit −1.12B and operating income −679M.
  - The stock page's Reported financials chart draws a downward bar for "25-12", and the table row reads "−4.62B, Gross 24.2%, Op 14.7%".
  - The screener row for FIX has FY2025 revenue = **1,831,286,000**. That is exactly Q1 2025's revenue (`period_end 2025-03-31`), against revenue_prev 7.03B. So `revenue_growth_pct` is **−73.9%**.
  - Q4 looks derived as FY − (Q1 + Q2 + Q3) = 1.83 − 6.46 = −4.62B.
  - Everything downstream is wrong:
    - `revenue_ttm` is **5.27B**, although the latest single quarter is 3.77B. TTM can't be less than about 1.5 quarters; from the real quarters (3.77 + 3.27 + 2.87 + Q4) it should be about 12B+.
    - The stock page shows Revenue (TTM) 5.27B, P/S 3.0, net margin 30.9%, FCF margin 46.3% and ROE 55.2%.
    - In the screener: `net_margin_pct` 55.8%, `fcf_margin_pct` 56.3%, `ps` 21.0 and `roe_ttm_pct` 48.9%.
  - FIX passed my GARP screen at P/E TTM 23.6 and op margin TTM 18.8%; both are computed on the wrong TTM. `revenue_unreliable` is False.
- suggestion:
  - reject an annual revenue fact whose period length isn't about 12 months, or that is smaller than any single quarter of the same year;
  - never publish a negative derived revenue (set Q4 to null and mark it instead);
  - set `revenue_unreliable` when TTM < max(quarter) × 2.

### 2. The sim lets me buy at a pre-report mid while the after-hours reaction is already on screen (look-ahead)
- kind: feature (sim / process)
- severity: high, for the honesty of the benchmark
- evidence:
  - `python scripts/sim.py price NVDA` gives session 2026-11-17, mid **154.26**.
  - `argus quotes NVDA --json` gives `ext_price` **162.94** (+4.81%, post-market, 7:59 PM ET), and the brief has NVDA's results under `watchlist_earnings.recent`.
  - The round runs after the report, but fills come from before it, so a buy now books about +5.6% for free. The same goes for any stock with after-hours news, and the rule rewards trading on it.
  - I chose not to trade it, but nothing stops it.
- suggestion (for a human, since this touches the rules):
  - Option A: `sim.py buy` refuses, or warns, when `|ext_change_pct|` is above a threshold such as 3%, or when the symbol reported after that session's close; the order then waits for the next session.
  - Option B: run trading rounds before post-market news lands.
  - For Argus itself: the order ticket in Simulate and Buy/Sell should show "after-hours move since this price" next to a stale reference price (related: B-109).

### 3. Screener "latest quarter" can be two quarters stale with no flag (D: Q1 2026 in mid-November)
- kind: bug
- severity: medium
- evidence:
  - `POST /api/screener` (no cap filter, `revenue_growth_q_yoy_pct` ≥ 15) returns Dominion Energy (D) with `latest_quarter: "Q1 2026"` and `ttm_through: "Q1 2026"`, latest-quarter growth 24.6%, P/E TTM 20.0 and op margin TTM 26.1%.
  - Every other row in my 54-row screen is on Q3 2026 or its fiscal equivalent.
  - D files 10-Qs every quarter, so the Q2 and Q3 2026 frames are likely missing from the universe. The row still screens as "latest quarter" growth, and nothing marks it stale.
- suggestion: add a `quarter_age_days` (or `stale: true` when `ttm_through` is more than about 135 days old) and grey the row on the Screener page. Optionally exclude stale rows from latest-quarter and TTM filters by default.

### 4. INTU's earnings date flip-flops between rounds: 11-19 → 11-20 → 11-19 (B-176, new evidence)
- kind: bug
- severity: low
- evidence:
  - r017 listed INTU on 2026-11-19 and r018 on 2026-11-20 (amc).
  - Today `/api/events?days_ahead=21` and the brief's `watchlist_earnings.upcoming` say **2026-11-19** amc (source finnhub, epsEstimate 2.7497). Nothing says it moved, either time.
  - With an after-close report, the date decides which session's fill comes before the numbers.
- suggestion: as B-176 says, keep the previous date and show "moved from 11-20". If the provider alternates, show both dates with "unconfirmed" instead of silently swapping.

### 5. Events says LNG's 11-17 dividend payment is `held: false` although I hold LNG
- kind: ux
- severity: low
- evidence:
  - `/api/events?days_ahead=21` returns `{'symbol': 'LNG', 'kind': 'dividend_pay', 'date': '2026-11-17', 'ex_date': '2026-11-09', 'held': False, 'amount': 0.0}`.
  - I hold 3.234 LNG, bought on 11-13. The $0 amount is right (I bought after the ex-date), but `held: false` reads as "you don't own this".
  - FIX's page shows the same idea correctly as "Dividend paid · not owed".
- suggestion: keep `held: true` and add `owed: false` (or reuse "not owed") so the API and the UI agree.

### 6. Fear & greed jumps 10.9 → 19.8 when breadth loads (B-036, new evidence)
- kind: bug
- severity: low
- evidence:
  - The first `/api/market-context` of the round had `errors.breadth` set ("needs the screener's universe") and a score of **10.9**.
  - About a minute later the universe was built (`fundamentals_at` 02:14:02 UTC), the error cleared, and the score read **19.8**, with the same market data.
  - The headline gauge moves 9 points depending on build timing.
- suggestion: as B-036 says, show the component count ("5 of 6 components") and keep the score's basis stable, or don't publish a score until all components are in.

### 7. The brief shows NVDA's results but not its after-hours move (B-110, extends to watchlists)
- kind: feature
- severity: low
- evidence:
  - The brief's `watchlist_earnings.recent` has NVDA's EPS and revenue surprise, but no `ext_change_pct`. `watchlist_movers` only has regular-session moves (INTU −7.17%, ADBE −4.25%).
  - The +4.8% reaction, the one number I needed for the decision, came from `argus quotes`.
- suggestion: add `ext_price` and `ext_change_pct` to `earnings_recent` and `watchlist_earnings.recent` entries when an after-hours print exists.

### 8. A CEO-ouster headline is scored "positive" (B-059 family)
- kind: bug
- severity: low
- evidence:
  - `/api/research/NVDA` news gives "Nvidia says it won't bring back Jensen Huang" a tone of **positive** (score 1.0, 2 positive, 0 negative).
  - "Nvidia is abandoning China after Jensen Huang's ouster" is scored neutral.
  - news_tone overall reads 11 positive / 0 negative on the day the company confirmed its founder-CEO is out.
- suggestion: weight governance terms (ouster, won't reinstate, resign, probe) as negative, or label the tone "keyword-based".

## Summary for the round lead
- **Account:** $9,795.79, −2.04% since the start, vs SPY −2.69% from my fill (+0.65 pp). Cash is $1,200 (12%).
- **Trades:** none. I held off NVDA because the 11-17 mid (154.26) predates its after-hours +4.8% beat; buying it would be look-ahead. I'll decide at the 11-18 session.
- **Top finding:** FIX shows a −$4.62B Q4 2025 revenue, because its FY revenue is the Q1 figure. That makes its TTM revenue 5.27B, which breaks P/E TTM, P/S and the margins on the stock page and in the screener.
