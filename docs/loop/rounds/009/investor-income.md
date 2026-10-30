# Round 009: income investor

## What I did
- **Market (Argus market context, 10-29 close, reviewed Thu 10-29 at about 22:15 ET):**
  - S&P 500 −0.30% to 7720.39 and SPY −0.38%. Breadth was strong anyway: 376 advancers to 124 decliners, and XLK −1.18% and XLC −1.87% did the damage. Fear & Greed is 34.5 ("Fear"). Breadth loaded tonight, and `errors` is `{}`.
  - Treasury curve: 2-year 4.61%, 10-year 4.98%, 30-year 5.32%. A month ago the 2-year was 4.89%. Rates eased, and that helped my bond sleeve and the rate-sensitive names.
  - Argus doesn't show tonight's PCE and GDP prints at all (finding 1). I read them by calling the provider directly: core PCE 3.1% y/y against 3.1% expected, and GDP 3.4% against 3.2%.
  - My calendar: ABBV and XOM report 10-30 before the open. O goes ex-dividend 10-30 ($19.31 on 71 shares) and reports 11-02 after the close. The Vanguard and Schwab bond ETFs go ex around 11-02.
- **Portfolio `loop-income` (before my trade):**
  - Value $100,822.63, cost $99,089.75, unrealized +$1,732.88.
  - Last session +$1,019.43 (+1.02%) against SPY −0.38%. HD led at +3.60% (+$182.72), and SCHD added +$149.76. The only loser was MSFT, −0.16%: it gave back all of last night's +2.9% after-hours move.
  - After hours +$505.38 (+0.50%), with 100% coverage.
  - Since inception (8 sessions), TWR is +1.79% against SPY +0.04%. The gain of $1,766.64 is the unrealized $1,732.88 plus the $33.76 PG accrual, so it reconciles.
  - Risk (`/risk`): beta 0.13, volatility 7.6%, 1-year max drawdown −5.65%, 1-day 95% VaR $700.
  - Bond ETFs are 34.7% of the book after the trade (BND 11.9, VCIT 9.9, VGIT 7.9, SCHP 5.0), above my 30% floor.
- **Income:**
  - Forward income is $3,354.06 a year after the trade: 3.31% on value, 3.37% on cost.
  - Rest of 2026 projects $618.67. I added the 14 per-holding "Rest of 2026" cells on /analysis and got $618.67, the same as the tile.
  - The month bars read Oct $53.07 (the $33.76 PG accrual plus O's $19.31), Nov $238 and Dec $362.
- **Payout safety ahead of ABBV's report:**
  - Argus shows ABBV's payout at 189.8% and its P/E at 82.1 on GAAP EPS of $3.54.
  - From Argus's own SEC data, FCF TTM is $18.21B. Dividends are about $12.2B (rate $6.92 × 1.767B shares, from market cap ÷ price). That puts the FCF payout at about 67%, comfortably covered (finding 2).
  - No action needed before the print. Alert #8 (ABBV down 5% in a day) stays on.
- **Trade: BUY 1 MSFT at $529.05**, the post-market quote. Transaction 45; note 53, review 2026-11-20.
  - MSFT was −0.32 pp under its 4% target, my only real gap. Last round the gap (−0.28) matched the overshoot one share would cause; tonight the gap is larger.
  - After the trade MSFT is 4.18%, an overshoot of +0.18 pp, smaller than the −0.32 pp gap.
  - It was paid from idle cash and cut my cash drag. No other position is more than ±0.22 pp from target.
  - Every other position is within its band, so no other trades.
- **Alerts:** none fired. #7 (MSFT down 6% in a day) has outlived the earnings event, and I'll retire it next round. #8 (ABBV) and #4 (XOM) are on for tomorrow's reports.
- **Cash: $381.20** ($910.25 − $529.05).
  - Invested at cost: $99,618.80. Realized gains: $0.
  - Value after the trade: $101,352.77 (unrealized +$1,733.97).
  - Return to date: (101,352.77 + 381.20 − 100,000) ÷ 100,000 = **+1.73%**, or +1.77% with the PG accrual (PG's $33.76 pays 11-16).

## Last round's changes
- **B-104 (margins from the same SEC quarters): works.**
  - `GET /api/fundamentals/MSFT` returns gross, operating and net margin of 67.66 / 47.10 / 41.17%, all `sec`, with `ttm_quarters` running to 2026-09-30.
  - That matches my hand calculation from r008 exactly.
  - O's card shows the OCF margin of 68.8%, labeled SEC, with the FCF margin blank, as intended.
  - On mixed cards, see finding 4.
- **B-095 (P/E = price ÷ the EPS shown): works.**
  - MSFT 530.14 ÷ 19.16 = 27.67, and the card reads 27.67.
  - ABBV 290.79 ÷ 3.54 = 82.14, and XOM 183.29 ÷ 7.77 = 23.59. Both match their cards.
- **B-034 (calendar on the New York date): broken in the live server tonight** (finding 1).
- **B-115:** passes tonight, as the round lead reported. I didn't re-run it.
- **Side checks:**
  - **Works:** extended-hours P&L ignores the share I bought after the close (B-046). MSFT's `ext_pnl` stayed at −$7.61 for 7 shares, and only +$0.002 was added for the new share.
  - **Risk after a trade (B-026): 1.4 s**, down from the 11–15 s noted in B-026. The first risk load of the session is still slow (finding 5).
  - **The brief now has headlines for MSFT**, which reported last night: "Microsoft's Windows sales fell 22%…". That's better than r008.
- **Re-confirmed still open:**
  - B-063: the footnote "Annual rate = latest payment × payments per year" is still on the Dashboard and on /analysis.
  - B-022: Targets & drift opens "By sector" with "Targets sum to 0.0%".
  - B-012: the tile reads "50% / 50%" under "Stock / ETF".
  - B-087: PG's $33.76 shows under "2026 received" though it pays 11-16.
  - B-049: tonight's trade is stamped 2026-10-30T02:18 UTC, and Performance still ends on 10-29 without it ($100,822.63 against the header's $101,352.77).
  - B-023: simulate's `value_after` adds the cash spent.
  - B-109: simulate priced MSFT at the 530.14 close while the post-market quote was 529.05.
  - B-110: the brief's `totals` has no `ext_pnl`.

## Findings

### 1. Economic calendar still drops today's releases after 8 pm ET: no 10-29 PCE or GDP at 22:15 ET, though the provider returns them
- kind: bug
- severity: high (last round's B-034 fix doesn't hold in the running server; PCE and GDP were the night's macro prints for my rate-sensitive book)
- evidence:
  - At 22:16 ET on 10-29, `GET /api/market-context` returns `calendar.all_events` starting **2026-10-30**: 158 events, and none dated 10-29. `events[0]` is "Dallas Fed PCE" on 10-30 at 18:30.
  - In the same minute, calling the same code outside the server, `MacroProvider().economic_events(21)`, returns 181 events, **23 of them dated 2026-10-29**. They include Core PCE 3.1% (cons. 3.1%), GDP 3.4% (cons. 3.2%) and Continuing Claims 1,701K.
  - Raw Nasdaq tonight: the `date=2026-10-30` query returns 10-29's rows (PCE and GDP with actuals). `_nasdaq_days` maps those to 10-29 correctly in a fresh call.
  - So the server's cached answer under `econ:21:2026-10-29` was built from a different (probably transient) Nasdaq response and is pinned for 6 h. It was likely built at server start, about 02:12 UTC.
  - Re-requesting doesn't fix it; the server still returns 158 events.
- suggestion:
  - Don't cache an answer for 6 h when it has no rows for `today` on a weekday; retry soon instead (10 min).
  - Log the per-query row signatures when a day comes back empty, so the next miss can be diagnosed.
  - Consider a test where the `today+1` query lags or repeats.

### 2. Payout ratio misleads on exactly the holding reporting tomorrow: ABBV shows 189.8% (and P/E 82) while its dividend uses about 67% of SEC free cash flow
- kind: feature (B-070, B-062 and B-071; new evidence)
- severity: medium (a client would read "190% payout" as a dividend at risk, and I'd have to compute coverage by hand)
- evidence:
  - The Dashboard Dividends tab shows ABBV Payout 189.8% (Finnhub). Argus's own rate ÷ SEC EPS is 6.92 ÷ 3.54 = 195%.
  - `/api/financials/ABBV` quarterly: OCF for the four quarters to 06-30 is 3,436 + 3,829 + 5,218 + 7,024 = $19.51B, and capex is $1.30B, so FCF is $18.21B. That equals the card's `fcf_ttm`.
  - Dividends are $6.92 × 1.767B shares = $12.2B, so the **FCF payout is about 67%**.
  - EPS is depressed by one-off charges: SEC diluted EPS was 0.10 and 0.39 in two of the four quarters.
  - The same gap appears elsewhere:
    - MSFT: 19% on EPS against about 45% on FCF (r008).
    - O: 236% on EPS, while the SEC OCF margin of 68.8% on $6.05B revenue gives about 74% of OCF.
- suggestion: add a "Payout (FCF)" column computed from Argus's own data (annual rate × shares ÷ SEC FCF TTM). Flag an EPS payout over 100% while FCF covers the dividend as "EPS depressed by charges".

### 3. Bond sleeve: Argus still can't say what a rate move does, while four of my bond ETFs sit near their 52-week lows
- kind: feature (B-017, new evidence)
- severity: medium (35% of the book; the only rate scenario is a 2022 replay)
- evidence:
  - `GET /api/brief/loop-income` `near_52w_extremes` lists BND, VCIT, VGIT and SCHP, each 2.0–2.6% above its 52-week low.
  - The curve has rallied: the 2-year is 4.61% now against 4.89% a month ago.
  - `/risk` scenarios are gfc, covid, rates (the 2022 replay, −14.2%), q4_2018 and spy_down_10. There's no parallel-shift scenario.
  - `/exposure` lists `funds_without_profile` as BND, VCIT, VGIT and SCHP, and look-through shows "Unclassified" at 34.7%.
  - The maturities and coupons are in `/api/holdings/<ETF>` (r008: VGIT about 5.1 y, BND about 8.8 y).
- suggestion: a "Rates ±100 bp" row in Stress scenarios, using the weighted average maturity or duration from N-PORT, plus a "Bonds" asset class in place of "Unclassified".

### 4. ABBV's card mixes sources in one column: gross margin from Finnhub next to SEC operating and net margin
- kind: bug (a B-104 follow-up)
- severity: low (the label doesn't say the windows differ)
- evidence:
  - `GET /api/fundamentals/ABBV` sources: `gross_margin_pct: finnhub` (72.79), while `operating_margin_pct` and `net_margin_pct` are `sec` (26.20 and 9.80, `ttm_quarters` to 2026-06-30).
  - SEC has gross profit for only 1 of those 4 quarters (`gross_profit` is null on 06-30, 03-31 and 09-30).
  - O shows the same pattern: gross 92.67 and operating 20.19 from Finnhub, net 21.65 from SEC.
- suggestion: when SEC lacks gross profit, show "—" (or label the Finnhub value "Finnhub, window ≠ SEC"). Don't quietly sit it in a column labeled SEC.

### 5. First risk load of the session: 23.4 s; the Analysis risk card is still "Loading…" at 7 s even when warm
- kind: perf (B-026)
- severity: medium
- evidence:
  - The first `GET /api/portfolios/loop-income/risk` took 23.39 s (r008: 30.8 s). Repeat calls took 1.37–1.58 s, and 1.4 s even right after my trade.
  - Playwright on /analysis (loop-income, 1400 px), with the API already warm, rendered in 7.2 s and the Risk card still read "Loading risk… (the first time downloads long price history…)".
  - With a 15 s wait it rendered. The "first time" copy is misleading when the server already has it cached.
- suggestion: warm risk at startup (B-026), and check why the card waits several seconds longer than the 1.4 s endpoint (probably queued behind the page's other calls).

### 6. "Where the risk comes from" still lists 15 of 17 holdings
- kind: bug (B-044)
- severity: low
- evidence:
  - The /analysis card shows 15 rows, ending with XOM. SCHP (risk 1.22%) and MSFT (risk 0.82%) are missing, and nothing says so.
  - The API's `positions` has all 17, and their `risk_pct` sums to 100.0.
  - MSFT, which I just added to, is the one holding with beta 1.01, so leaving it out hides the only market-sensitive stock in the book.
- suggestion: show all positions, or add "+2 more (2.0% of risk)".

### 7. The brief doesn't explain the day's biggest mover (HD +3.6%), and its HD headlines are about other companies
- kind: bug (B-059 and B-096)
- severity: low
- evidence:
  - `GET /api/brief/loop-income`: the top gainer is HD at +3.60% (+$182.72).
  - `headlines.HD` has three items: "Dow Jones Top Movers for Oct. 29, 2026: Merck and Nike Lead Gainers…", "Dow Jones Top Movers Today: 8 Gainers, 4 Losers…" and "How Much Could You Lose In Target Stock?". None says why HD rose.
  - `headlines.SCHP` is a Fed/10-year story, and `headlines.O` includes "Verizon Used Just 49% of Its Free Cash Flow…".
- suggestion: as B-059. Keep a headline only if it names the ticker or company, and prioritize the largest dollar movers.

### 8. Simulate still prices at the 4 pm close in the post-market, and `value_after` grows by the cash spent
- kind: bug (B-109 and B-023, re-confirmed)
- severity: low
- evidence:
  - `POST /api/portfolios/loop-income/simulate` with BUY 1 MSFT and SELL 1 HD returned `price: 530.14` while the quote's `ext_price` was 529.05 (`ext_session: post`).
  - `value_before` was 100,822.63 and `value_after` 101,023.79: the +$201.16 is just the net cash spent.
  - There's no income-after figure, so I computed the +$3.64 in income by hand. Argus confirmed it after the trade: $3,350.42 → $3,354.06.
- suggestion: as B-109 and B-023. Add a `price_source`, keep value constant (positions plus cash), and return `annual_income_after`.

### 9. "Coming up" marks O's announced ex-dividend amount as approximate
- kind: ux
- severity: low
- evidence:
  - Dashboard Coming up: "Fri, Oct 30 · O · Ex-dividend · ≈ $19.31".
  - O's 10-30 ex-date and $0.272 are announced (`estimated_date: False` in `/dividends`), and /analysis shows the date without "~".
  - The estimated BND, SCHP, VCIT and VGIT rows also use "≈", plus "est.", so the "≈" doesn't tell announced amounts from estimated ones.
- suggestion: show "≈" only on estimated amounts.
