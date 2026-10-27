# Round 006: income investor

## What I did
- **Market (Argus market context, 10-26 close, reviewed Mon 10-26 about 22:15 ET):**
  - S&P 500 +0.70% to 7676.77 (1W −0.18%). XLK +1.7%, XLC −1.6%.
  - 10-year 4.99% (Treasury curve 5.00%), 2-year 4.68%, 1-month bill 4.11%. VIX 18.39 (−5.4%), WTI $100.85.
  - Fear & Greed 11.7 ("Extreme fear"). Breadth was still building (known).
  - This week: KO reports 10-27 (bmo), FOMC 10-28, MSFT 10-28 (amc), ABBV and XOM 10-30 (bmo), O 11-02 (amc).
- **Portfolio `loop-income` before trading:**
  - Value $99,366.91, cost $98,347.12, unrealized +$1,019.79 (+1.04%).
  - Last session +$205.82 (+0.21%) against SPY +0.71%. MSFT +1.5%, JNJ +0.9%. PG −0.7%.
  - Since inception (5 sessions): TWR +1.07% against SPY −0.48%. Gain $1,053.55 = unrealized $1,019.79 + PG accrual $33.76.
  - Risk (`/risk`): beta 0.13, volatility 7.4%, 1-year max drawdown −5.6%, 1-day 95% VaR $672. The 2022 rate-shock replay gives −13.9%.
  - Bond ETFs (BND, VCIT, VGIT, SCHP) make up 35.1%, above my 30% floor. Look-through shows them as "Unclassified" 35.1% (B-017).
  - Drift: every position is within ±0.30 pp of target. The largest gaps were JPM −0.29, MSFT −0.25, SCHD +0.23 and HD −0.18.
- **Decision: deploy part of the idle cash into the two underweights that don't report this week.** Cash was 1.65% of the book, earning nothing. I skipped MSFT, KO, ABBV and XOM because they report before Friday.
  - `simulate` (1 JPM + 1 HD): JPM 4.71% → 5.01%, HD 4.82% → 5.11%, net cash −$653.42 at the regular-session closes.
  - **Bought 1 JPM @ $334.40 and 1 HD @ $317.00.** These were the post-market quotes, the tradable prices at the time (txn 41 and 42, $651.40).
  - Thesis notes 44 (JPM, review 2027-01-15) and 45 (HD, review 2026-11-18).
- **After the trades:**
  - Value $100,020.33, cost $98,998.52, unrealized +$1,021.81.
  - Forward income **$3,348.30** a year (3.35% on value, 3.38% on cost; up from $3,332.38). The per-holding figures sum to the total, and rest-of-2026 sums to $617.23 both by holding and by month.
  - Largest drift is now MSFT −0.27 pp.
- **Housekeeping:** added **alert #8: ABBV `day_loss_pct 5`** (ABBV reports 10-30 bmo; ABBV's payout is my weakest). Alerts #6 (KO) and #7 (MSFT) are still active for this week's reports.
- **Cash: $1,001.48** ($1,652.88 − $651.40). Invested at cost: $98,998.52. Realized gains: $0. The PG dividend ($33.76, pays mid-November) is accrued by Argus but not yet recorded as a `DIVIDEND`.

## Last round's changes
- **B-074 (ex-dividend days reconcile): works, and it helped.**
  - The 10-26 series change (99,366.91 − 99,161.09 = **$205.82**) equals Day P&L ($205.82).
  - `totals.dividends` and `dividends_accrued` are both 33.759.
  - `/performance` gain $1,053.55 = unrealized $1,019.79 + accrued $33.76.
  - I re-derived the 10-23 TWR step by hand: (99,161.09 + 33.76) ÷ 99,788.59 − 1 = −0.595%. That matches the series (1.4657% → 0.8620%) and is exactly the reported max drawdown (−0.59%).
  - The Dashboard footnote explains the accrual clearly.
  - Still open: the stress scenarios are "Price only, no dividends", and the Dashboard tiles show no dividend figure (finding 7).
- **B-068 (volatility and Sharpe from too few sessions): works.**
  - `/performance` returns `volatility_pct null`, `sharpe null` and "needs 20 sessions, has 5". The Dashboard shows "Volatility (ann., 5 sessions): needs 20 sessions, has 5".
  - Analysis's 7.5% is now clearly a separate figure ("today's holdings over the last 252 trading days"). No more conflict.
- **B-025 (mover signs, Day % base): works where I could test it.**
  - The brief's 5 gainers are all positive and its 5 losers all negative.
  - For the post-close buys, Day P&L and Day % use the same fill-price base: HD Day P&L −$6.75 + (319.38 − 317.00) = −$4.37, and Day % −0.085% = −4.37 ÷ 5,114.45. They agree.
  - The same base still counts after-the-close shares in "last session" (finding 4, B-046).
  - A buy during the session couldn't be tested (market closed).
- **B-076 (near 52-week extremes): partly better.** 9 of 17 holdings are listed now. I checked BND (2.33% above its 52-week low of 69.65) and KO (2.80% below its high of 95.37) against `/api/history`. Both are right.
- **B-026 (slow risk): partly.** The first `/risk` of the session took 13.0 s. After my trades it took 1.06 s, so the "11–15 s after a trade" part looks fixed. A cold start is still slow.
- **Re-confirmed still open:**
  - B-013: finding 3.
  - B-017: bonds are "Unclassified" 35.1%.
  - B-021: three betas for JPM. The stock page says 1.04, Risk says 0.73, and the portfolio's market factor loading is 0.37 against the "Beta vs SPY 0.13" tile.
  - B-022: Targets & drift still opens on "By sector", with "Targets sum to 0.0%".
  - B-044: "Where the risk comes from" still lists 15 of 17; MSFT and SCHP are missing.
  - B-062: Payout ABBV 189.8%.
  - B-063: the footnote still says "Annual rate = latest payment × payments per year".
  - B-049: finding 4.

## Findings

### 1. Stock page returns 500s on first open: /api/profile and /api/holdings race to insert the same company_profile row
- kind: bug
- severity: medium (the page loses its profile and holdings cards on the first visit; it works on reload)
- evidence:
  - The first screenshot of /t/JPM this session reported two page errors: "Failed to load resource: 500".
  - `data/server.log`: `GET /api/profile/JPM 500` and `GET /api/holdings/JPM 500`, both with `sqlite3.IntegrityError: UNIQUE constraint failed: company_profile.symbol` on `INSERT INTO company_profile (symbol, as_of, data)`.
  - `company_profile()` (`backend/argus/app.py` ~305) reads the cached row and, if it's missing or stale, fetches and inserts it. `holdings()` calls `company_profile()` too, and the page fires both requests at once, so both try to insert.
  - A reload worked (row cached). Every symbol whose profile is older than a week will do this once.
- suggestion: write the profile with an upsert (`INSERT … ON CONFLICT(symbol) DO UPDATE`, or `session.merge`), or serialize the fetch per symbol.

### 2. Banks: "Revenue growth YoY +109.0%", "latest quarter +74.0%" and "Gross margin 0.0%" on /t/JPM; SEC statements show no revenue at all
- kind: bug
- severity: medium (wrong numbers on a holding; misleads any growth or margin read of a bank)
- evidence:
  - `/api/fundamentals/JPM`:
    - `revenue_growth_yoy_pct 108.98` and `revenue_growth_q_yoy_pct 73.97` (source finnhub).
    - `gross_margin_pct 0.0` (source yahoo).
    - `revenue_ttm 190.73B` (yahoo).
  - JPM's revenue did not double in a year.
  - The Peers table on the same page shows the same pattern for every money-center bank: BAC +99.4%, C +99.2%, USB +84.1%, WFC +72.7%, PNC +72.3%.
  - It looks like a definition change (gross interest income in one period, net revenue in the other).
  - Reported financials (`/api/financials/JPM`): the Revenue, Gross % and Operating % columns are "–" for all 8 quarters. JPM tags `RevenuesNetOfInterestExpense`, not `Revenues`. So there's no SEC figure to check Finnhub against, and no B-009-style warning appears.
- suggestion:
  - Read `RevenuesNetOfInterestExpense` (or net interest income + noninterest income) as bank revenue in SEC statements, and prefer that for growth when present.
  - Show gross margin as "–", not 0.0%, when the provider returns 0 for a financial company.
  - Flag provider growth above ~+50% for a large-cap with no SEC cross-check.

### 3. Upcoming dividends still disagree (B-013, sixth round): unentitled JPM pay now on /t/JPM too; four bond-ETF ex-dates missing from "Coming up"
- kind: bug
- severity: medium (existing B-013)
- evidence:
  - Dashboard Coming up, `/api/brief/loop-income` (`dividends_upcoming`) and now /t/JPM's Events card all show **"Sat, Oct 31 JPM Dividend paid", held: true**. Every JPM share I own was bought after its 10-06 ex-date. `/dividends` correctly projects JPM $0 for the rest of 2026.
  - Coming up says "next 14 days", but it omits the four estimated 11-01 ex-dates that `/dividends` projects: BND $42.08, VCIT $42.84, VGIT $26.46 and SCHP $20.55, which is $131.93 of my income. 11-01 is also a Sunday; these ETFs go ex on the first business day (Mon 11-02).
  - Other weekend estimates: NEE ~11-28 (Saturday). KO is still ~12-15 on Analysis, where the announced ex-date is 12-01.
- suggestion: as in B-013. Mark a pay event `held` only if shares were held on its ex-date. Feed Coming up from the same projection as Dividends, labeled "est.". Roll estimated dates to a business day.

### 4. Shares bought after the close count in "last session": HD +$2.38 of phantom gain, TWR moved; the trade is dated 10-27 on /t/JPM (B-046, B-049)
- kind: bug
- severity: medium (existing B-046 / B-049, new evidence)
- evidence:
  - I bought 1 HD at the post-market price $317.00 at 22:15 ET on 10-26. The share is marked at the regular close of $319.38.
  - Day P&L went from −$6.75 to −$4.37 (+$2.38), and the header from "+$205.82" to "+$207.84 (+0.21%) last session".
  - The after-hours line takes the same $2.38 back ($−38.08 = 16 × (317.00 − 319.38)), so the two lines net to zero. But "last session" now includes a gain that never happened in that session.
  - `/performance` folded the buy into 10-26 (`flow_in 651.4`), and gain rose $1,053.55 → $1,055.57. That's +$2.02, which is HD +2.38 plus JPM −0.36 (bought at 334.40 vs the 334.04 close).
  - The transaction is stored as `2026-10-27T02:15 UTC`. /t/JPM's "Your position" lists it as **2026-10-27**, while performance puts it on 10-26.
- suggestion: as in B-046 and B-049. Treat a fill after the close as next-session money: base it on its fill price, count it only in after-hours P&L, and date it by New York time everywhere.

### 5. Analysis on a phone hides the key numbers: stress scenarios show the date window but not the loss; factor table shows labels only
- kind: ux
- severity: medium (on a phone I can't read my 2022 rate-shock loss without side-scrolling a table)
- evidence:
  - `scripts/screenshot.py /analysis --width 390 --full` reports no page overflow.
  - In "Stress scenarios" the visible columns are the scenario name and a truncated window ("2007-10-09 → 20…"). SPY, "Your portfolio (est.)" (−24.5%, −14.0%) and the dollar change are off-screen.
  - In "Factor exposures" only the factor names show. Loading, t-stat and reading are cut off.
  - The Correlations matrix is similarly clipped at 7 columns.
- suggestion: at narrow widths, drop the window column (or put it under the name) and lead with "Your portfolio" and "$ change". In the factor table, show loading and reading and drop t-stat. Related to B-002.

### 6. Stock page momentum (Finnhub) contradicts the chart's own returns on 5 of 6 periods (JPM: 6 months +5.9% vs 6M +8.4%)
- kind: bug
- severity: low (existing B-083, broader than "1 week")
- evidence:
  - /t/JPM, all on one page. `/api/returns/JPM` gives the chart's bases; momentum comes from `/api/fundamentals/JPM`, source finnhub.

    | Period | Momentum card | Chart | Chart base |
    |---|---|---|---|
    | 1 week / 5D | −0.6% | +0.2% | 333.53 |
    | 3 months / 3M | −6.1% | −5.4% | 353.21 |
    | 6 months / 6M | +5.9% | +8.4% | 308.28 |
    | YTD | +2.9% | +3.7% | 322.22 |
    | 1 year / 1Y | +12.6% | +11.2% | 300.44 |

  - Only 1 month (−2.6%) agrees, because Argus computes that one itself (no source).
- suggestion: compute every momentum period from the same return bases the chart uses (as is already done for 1 month), and drop Finnhub's figures.

### 7. An unpaid accrual is called "received"; the Dashboard shows no dividend income at all
- kind: ux
- severity: low
- evidence:
  - `/dividends` returns `totals.received 33.759`, and `by_month[10].received 33.759`. Analysis's chart draws October as "Received (est.)" ($53.07 including O's projected 10-30). PG pays in mid-November, so nothing has been received. The card itself says, correctly, "2026 so far (est.)".
  - The Dashboard tiles are Unrealized $1,022, Cost basis, **Realized P&L $0** and vs SPY. The $33.76 that `totals.dividends` now carries (B-074) appears only in a footnote under the chart.
  - An income client's first question is "what has the portfolio paid me?".
- suggestion:
  - Rename the API field and legend to "accrued (ex-date)". When B-042 lands, show pay-date "received" separately.
  - Add "Dividends $33.76 (accrued)" under the Realized P&L tile, or as its own tile.
