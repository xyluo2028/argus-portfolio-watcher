# Round 008: income investor

## What I did
- **Market (Argus market context, 10-28 close, reviewed Wed 10-28 about 22:15 ET):**
  - S&P 500 +0.28% to 7743.98, SPY +0.34%. Fear & Greed 21.0, "Extreme fear"; junk vs investment-grade bond demand scores 3.0.
  - Treasury curve: 2-year 4.67% (−3 bp on the day), 10-year 5.05% (+6 bp), 30-year 5.37%. 10y−2y is +0.38 pp.
  - FOMC decided today (10-28), but Argus doesn't show the decision anywhere: the calendar already starts on 10-29 (B-034). Core PCE and GDP are tomorrow at 08:30.
  - Breadth was still building (known, B-027).
  - My calendar: MSFT reported tonight after the close. EPS 4.89 against 4.82 expected; revenue $92.28B against $92.49B expected. It's +2.88% after hours at $546.30. ABBV and XOM report 10-30 (bmo), O on 11-02 (amc). O goes ex-dividend 10-30 ($19.31).
- **Portfolio `loop-income`:**
  - Value $99,803.20, cost $99,089.75, unrealized +$713.45.
  - Last session −$69.19 (−0.07%) against SPY +0.34%. Rate-sensitive names fell: NEE −1.70%, O −1.04%, and the bond ETFs −0.14% to −0.18%. XOM, JPM and JNJ each gained about 1%.
  - Since inception (7 sessions), TWR is +0.76% against SPY +0.42%. The gain of $747.21 is the $713.45 unrealized plus the $33.76 PG accrual.
  - After hours: +$615.44, of which MSFT is $107.03.
  - Risk (`/risk`): beta 0.13, volatility 7.5%, 1-year max drawdown −5.6%, 1-day 95% VaR $688.
  - Bond ETFs are 35.1% of the book (BND 12.05, VCIT 10.02, VGIT 8.04, SCHP 5.03), above my 30% floor.
  - Drift: every position is within ±0.28 pp of target. The largest gaps are MSFT −0.28 pp and JNJ +0.16 pp.
- **Income:**
  - Forward income is $3,350.42 a year: 3.36% on value, 3.38% on cost.
  - Rest of 2026 projects $617.76. I checked it month by month: October $19.31 (O), November $236.88 and December $361.57. I summed the per-holding events by hand and they match the totals.
- **I checked SCHD's beta of 0.20 against VIG's 0.63**, because it looked wrong for a dividend-equity ETF.
  - I recomputed it from Argus's `/api/history` closes (252 days): SCHD's correlation with SPY is 0.22, so the beta is 0.198. VIG's is 0.794, giving 0.627.
  - The numbers are right for this tape. Value and energy decoupled from tech, and XOM's correlation with SPY is −0.33.
- **MSFT research.** The SEC quarter to 2026-09-30 was already in Argus tonight:
  - Revenue +18.8% y/y, diluted EPS 4.92, EPS TTM $19.16.
  - Capex was $39.4B in the quarter, so FCF TTM is $59.96B (17.3% margin).
  - Dividends are about $27B a year (market cap ÷ price ≈ 7.43B shares × $3.64). That's about 45% of FCF, against a 19% payout on EPS. Still safe, but the cushion is thinner than the EPS payout suggests.
- **Decision: no trades.**
  - MSFT is my only meaningful underweight (−0.28 pp). One share at about $546 would take it to 4.27% against a 4% target, an overshoot of the same size as the gap.
  - Everything else is within ±0.16 pp. With PCE tomorrow and ABBV and XOM on Friday, I'm holding the cash.
  - I wrote note 52 on MSFT (payout on FCF, and a check for the dividend raise at the 11-19 ex-date), review date 2026-11-20.
- **Alerts:** #6 (KO, down 4% in a day) is off now that KO has reported and the stock is steady. #7 (MSFT, down 6% in a day) didn't fire, and MSFT is up after hours; it stays on through tomorrow's session. #8 (ABBV, 10-30) and #4 (XOM) stay on.
- **Cash: $910.25**, unchanged. Invested at cost: $99,089.75. Realized gains: $0.
  - Return to date: (99,803.20 + 910.25 − 100,000) ÷ 100,000 = **+0.71%**, or +0.75% with the PG accrual.
  - PG's $33.76 pays 11-16. It isn't recorded as a `DIVIDEND` yet.

## Last round's changes
- **B-083 (momentum from Argus's own closes): works.**
  - /t/MSFT reads 1W −0.4%, 1M +4.3%, 3M +35.0%, YTD +9.8% and 1Y −2.0%. Each one matches 531.01 divided by the matching `/api/returns/MSFT` base: 532.95, 509.22, 393.35, 483.62 and 542.07.
  - They also match the chart's range buttons.
- **B-009 + B-079 (valuation card from SEC quarters): mostly works, and it helped tonight.**
  - MSFT filed the same evening it reported. The card already showed revenue TTM $346.45B, EPS TTM $19.16, latest-quarter growth +18.8% and FCF margin 17.3%, each labeled "SEC, 4Q to 2026-09-30". All four match my sum of the SEC table.
  - The margins on the same card are still one quarter behind (finding 1).
- **B-093 (announced ex-dates, duplicates, amounts): works.**
  - KO shows its December dividend once: ex 12-01 at $22.79, paid 12-15 at $22.79. That holds in `/api/events`, Coming up and the Dividends table.
  - Pay events and announced ex-dates now carry amounts, for example O pays $19.31 on 11-13 and PG pays $33.76 on 11-16. This closes my r007 #3.
  - The January projections are there: BND, VCIT, VGIT and SCHP ~01-04, JPM ~01-06, ABBV ~01-15, PG ~01-25.
  - The Dividends table uses the announced dates: NEE 11-27, KO 12-01, MSFT 11-19, O 10-30.
- **Side improvements I noticed:**
  - The Dashboard Dividends tab's "Fwd yield" now uses Argus's rate (KO 2.31%).
  - The Analysis dividend tile reads "2026 so far (est.)".
  - Brief `near_52w_extremes` now lists 8 of 17 holdings, not all of them (B-076 looks better).
- **Re-confirmed still open:**
  - B-017: look-through "Unclassified" 35.1%, no duration.
  - B-022: Targets & drift opens "By sector" with "Targets sum to 0.0%".
  - B-044: "Where the risk comes from" lists 15 of 17; MSFT and SCHP are missing.
  - B-063: the footnote still reads "Annual rate = latest payment × payments per year", though SCHP shows $1.26 against 0.056 × 12 = $0.67.
  - B-062: Dashboard payout is still Finnhub's: KO 77.2%, O 236.4%, ABBV 189.8%.
  - B-043: the stock page's "Dividend yield (TTM)" is Finnhub's (MSFT 0.67% against Argus 0.69%).
  - B-095: MSFT P/E 29.5 against 531.01 ÷ 19.16 = 27.7.
  - B-092: /t/BND makes a 502 call to `/api/financials/BND`, and its ownership card is empty.
  - B-034: no FOMC outcome after 8 pm ET.
  - B-012: the "Stocks / ETFs" tile reads 50% / 50% under "ETF / Stock".
  - B-023: simulate has no income after the trade, and `value_after` adds the cash spent.

## Findings

### 1. MSFT's card mixes windows: margins cover the four quarters to 06-30, while revenue, EPS and FCF on the same card are to 09-30
- kind: bug
- severity: medium (the same window mismatch as B-009, on the profitability column; it shows up on the night a company reports)
- evidence:
  - /t/MSFT (and `GET /api/fundamentals/MSFT`) shows gross margin 67.9%, operating margin 46.7% and net margin 40.3%, all `sources: finnhub`.
  - The same card shows revenue TTM, EPS TTM and FCF margin labeled "SEC, 4Q to 2026-09-30".
  - From `/api/financials/MSFT` quarterly, the four quarters to 09-30 give 67.66% / 47.10% / 41.17%. The four quarters to 06-30 give **67.94% / 46.78% / 40.31%**, exactly the card's figures.
  - So net margin is 0.9 pp stale next to a fresh EPS. ROE, ROA and EPS growth (Finnhub) are probably one quarter behind as well.
- suggestion: extend the B-009 rule to gross, operating and net margin. When SEC's quarters are newer, compute them from the same four SEC quarters and label them the same way.

### 2. Simulate prices a trade at the 4 pm close while the stock is +2.9% after hours on earnings
- kind: bug
- severity: medium (on earnings nights, which are exactly when I size trades, the what-if understates the cost)
- evidence:
  - `POST /api/portfolios/loop-income/simulate` with `{"trades":[{"side":"BUY","symbol":"MSFT","qty":1}]}` returned `price: 531.01`, `net_cash: -531.01` and MSFT weight 3.72% → 4.23%.
  - The portfolio's own quote has `ext_price 546.30`, `ext_session: post`, `ext_as_of 23:59 ET`. The dashboard shows "AH +2.88%".
  - At the post-market price the trade costs $546.30 and the weight goes to about 4.37%.
  - The response doesn't say which price it used.
- suggestion: in pre- and post-market sessions, price simulated trades at the extended-hours quote when there is one (or let me choose), and return `price_source` (close or post). The UI should show "at 546.30 (after hours)".

### 3. The brief doesn't mention the night's biggest move: MSFT +2.9% after hours on its report
- kind: feature
- severity: medium (the morning brief is what I'd hand a client; it misses the one event that moved the book overnight)
- evidence:
  - `GET /api/brief/loop-income`: `earnings_recent` has MSFT (EPS 4.89 vs 4.8165), and `totals` has no after-hours figure.
  - The gainers, losers and largest-dollar-move lists are regular-session only, so MSFT (−0.06% in the session) isn't in them.
  - `headlines` has no MSFT entry at all, though MSFT is the largest after-hours P&L (+$107.03 of +$615.44).
  - The revenue miss (92.28B vs 92.49B est.) isn't stated anywhere; the dashboard only shows "EPS 4.89 vs 4.82 (beat +1.5%)".
- suggestion: in the post and pre sessions, add `ext_pnl` and an extended-hours movers list to the brief, and include headlines for holdings that reported in the last session. Show the revenue surprise next to the EPS surprise. Related: B-055, B-096.

### 4. Bond sleeve: no duration or yield-to-maturity, though Argus already holds the maturities and coupons
- kind: feature
- severity: medium (B-017, new evidence: 35% of my book is bonds, and I can't answer "what does +50 bp do to it")
- evidence:
  - `GET /api/holdings/<ETF>` returns N-PORT rows with `maturity` and `coupon_pct`.
  - Weighting the rows Argus returns, as of 10-28:

    | ETF | Weighted average maturity | Coupon | Coverage |
    |---|---|---|---|
    | VGIT | 5.1 y | 3.57% | 98.7% |
    | SCHP | 6.8 y | 1.30% | 99.5% |
    | BND | 8.8 y | 3.42% | top 500 rows, 54.5% |
    | VCIT | 7.6 y | 5.02% | top 500 rows, 50.7% |

  - None of this is shown. The only yield on the stock page is the trailing distribution yield (BND 4.17%), while the 10-year is at 5.05%.
  - Stress scenarios are historical replays plus "SPY falls 10% (via beta)". There's no rate shock: beta to SPY says nothing about a bond fund.
- suggestion:
  - Show weighted average maturity and coupon on bond ETF pages, computed over all rows (the server has all 17,409 for BND). Add an approximate modified duration.
  - Add a "rates +100 bp" scenario: −duration × 1% per bond ETF, and the book total.
  - Longer term, show the fund's SEC 30-day yield or YTM next to the TTM distribution yield.

### 5. The first risk load of the session still takes 30.8 s
- kind: perf
- severity: medium (existing B-026; the Analysis risk card is blank for half a minute)
- evidence:
  - The first `GET /api/portfolios/loop-income/risk` tonight took 30.82 s (24.5 s in r007, 13.0 s in r006). It's getting worse.
  - The next calls took 1.12 s and 1.02 s. The other portfolio endpoints took 0.02 to 0.83 s, and the brief 1.20 s.
- suggestion: as B-026. Warm the risk matrix in the background after the close, or at startup.

### 6. BND's Peers card names its category and then says Yahoo lists none
- kind: bug
- severity: low
- evidence:
  - /t/BND Peers header: "Largest US ETFs in Intermediate Core Bond, most holdings overlap first". The body: "No similar funds found (Yahoo lists no category for this fund)".
  - `GET /api/peers/BND` returns `category: "Intermediate Core Bond"` with `peers: []`.
  - VCIT ("Corporate Bond") and SCHD ("Large Value") do get 9 peers each. AGG, the obvious peer, is missing for BND.
- suggestion: when the category exists but the lookup finds nothing, say "no other ETFs found in Intermediate Core Bond". Check why that category's lookup comes back empty.

### 7. The stock page shows Yahoo's total returns beside Argus's price returns, without saying which is which
- kind: ux
- severity: low (B-100, new evidence; the data for a total-return figure is already on the page)
- evidence:
  - The /t/BND Fund column shows "YTD total return −2.7%" and "3-year average return +5.2%". The Momentum column on the same card shows "Year to date −3.9%" and "Price CAGR 3Y +1.2%".
  - A client would see two YTD figures 1.2 pp apart. Only one of the four labels says "total", and "Year to date" doesn't say "price".
  - The 1Y figure (−5.2%) still has no total-return partner.
- suggestion: label the Momentum rows "price" ("Year to date, price"), and put the Yahoo total-return figures next to them as "total return". The quickest version of B-100.

### 8. The payout column uses GAAP EPS, which misleads for REITs and for heavy-capex payers
- kind: feature
- severity: low (B-062 and B-070, new evidence)
- evidence:
  - The Dashboard Dividends tab shows Payout O 236.4%, ABBV 189.8% and KO 77.2% (Finnhub).
  - For MSFT the column reads 19.8%, but the dividend (about $27B) is about 45% of SEC FCF TTM ($59.96B), because capex rose from $19.4B to $39.4B a quarter.
  - Argus already has every input for FCF payout: rate × shares, and SEC FCF.
- suggestion: add "Payout (FCF)" from SEC data next to the EPS payout, and use FFO or AFFO for REITs, or blank the EPS payout with a "REIT" note.

### 9. Brief headlines are still mostly about other companies
- kind: bug
- severity: low (existing B-059)
- evidence: `GET /api/brief/loop-income` `headlines`:
  - JNJ: "Bausch + Lomb Soars 16%…", "Genmab Stock Surges…" and "GSK Q3 Earnings Top Mark…".
  - JPM: "Bel Fuse (BELFA) Stock Sees Modest Fair Value Lift…".
  - NEE: "How Much Of PG&E Stock Rides On This Number?" and "Why Has Southern Stock Trailed Entergy?".
  - O: "Equinix (EQIX) Surpasses Q3 FFO…".
- suggestion: as B-059. Keep a headline only if it names the ticker or the company.
