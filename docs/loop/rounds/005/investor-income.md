# Round 005: income investor

## What I did
- **Market (Argus market context, 10-23 close, reviewed Sun 10-25 about 22:15 ET):**
  - S&P 500 fell 0.52% (7663.43 to 7623.68) and is −0.47% on the week. Staples gave back Thursday's rally: XLP −1.9%, XLU −0.7%, XLV −1.1%. XLE rose 2.6% with WTI at $101.
  - 10-year 4.99% (+3.5 bp; Treasury curve 5.00%), 2-year 4.69%, 1-month bill 4.11%. VIX 19.45, Fear & Greed 25.3 ("Fear").
  - This week: KO reports 10-27 (bmo), FOMC 10-28, MSFT 10-28 (amc), ABBV and XOM 10-30 (bmo).
- **Portfolio `loop-income`:**
  - Value $99,161.09, cost $98,347.12, unrealized **+$813.97 (+0.83%)**.
  - Last session −$593.74 (−0.60%) against SPY −0.52%. Staples did the damage: KO −2.8%, HD −2.4%, PEP −2.2% and PG −2.1% (PG went ex-dividend that day). XOM +2.8%.
  - Since inception (4 sessions): TWR +0.83% against SPY −1.18%.
  - Risk (`/risk`): beta 0.13, volatility 7.5%, 1-year max drawdown −5.6%, 1-day 95% VaR $671. The 2022 rate-shock replay gives −13.9%. I re-derived it from Argus's own 5-year history: weighted price change 2022-01-03 to 2022-10-12 comes to −13.91%, an exact match. I also checked XOM, SCHD, KO and BND betas and volatilities against `/api/history` (for example XOM β −0.679, vol 26.2%). All match.
  - Income: forward income **$3,332.38** a year (3.36% on value, 3.39% on cost). The per-holding figures sum to the total, and the rest-of-year figures sum to $614.90. PG's ex-date (10-23) puts $33.76 in "2026 so far (est.)". The 2026 total is $648.66.
  - Bond ETFs (BND, VCIT, VGIT, SCHP): 35.4% by my own sum, above the 30% floor. Look-through still shows it as "Unclassified" (B-017).
  - Drift: everything is within ±0.32 pp of target (JPM −0.32, MSFT −0.30, SCHD +0.24). All inside the ±2 pp band.
- **Decision: no trades.** Nothing is near its band. I won't add to MSFT or KO the day before they report, or reshuffle bonds right before the FOMC decision. `simulate` showed that 1 JPM + 1 MSFT ($856.09) would bring both within 0.2 pp. That isn't worth doing before earnings.
- **Housekeeping:** added **alert #7: MSFT `day_loss_pct 6`** (reports 10-28 amc). I tried to add a 10-year-yield alert (`^TNX price_above 5.25`) to trigger a bond-duration review. Argus rejected it (finding 2).
- **Cash: $1,652.88**, unchanged. Invested at cost: $98,347.12. Realized gains: $0. The PG dividend ($33.76, payable mid-November) isn't recorded yet.

## Last round's changes
- **B-056 (stale SEC statements flagged): works, with gaps.**
  - `/api/fundamentals/KO` returns `sec.latest_period 2026-04-03`, `latest_period_age_days 206`, `stale true` and `fcf_ttm_through 2026-04-03`. `fcf_ttm_quarters` lists 2026-04-03, 2025-12-31, 2025-09-26 and 2025-06-27.
  - Those are exactly the quarters in the table: 1.755 + 2.874 + 4.564 + 3.369 = 12.562B.
  - /t/KO shows "SEC, 4Q to 2026-04-03" under FCF and the yellow stale banner in both the fundamentals and financials cards. NEE is flagged `stale true` (2026-03-31, 209 days).
  - It helped. I can now see that KO's FCF payout is a year-old window before its 10-27 report.
  - Gaps: NEE's fundamentals card has no banner and no FCF source line. The banner's wording is also misleading (finding 5).
- **B-066 (Markets 1D from the previous session close): works over the weekend.**
  - S&P 500 1D −0.519% = 7623.68 / 7663.43, which agrees with `argus quotes SPY` (−0.52%).
  - 1W −0.467% = against the 10-16 close of 7659.44.
  - Futures and FX now show the 10-26 session (WTI −1.9%), as described.
- **B-048 (consensus from its counts):** consistent on my holdings. KO reads "Buy, 25 analysts, mean 2.00" beside bars of 20 buy, 4 hold and 1 sell. NEE reads "Buy, mean 2.32, 22 analysts" beside 14 buy, 7 hold and 1 sell.
- **Re-confirmed still open:** B-013 (finding 3), B-017, B-022 (Targets & drift still opens on "By sector", "Targets sum to 0.0%"), B-024, B-044 ("Where the risk comes from" lists 15 of 17), B-062 (Payout O 236.4%, ABBV 189.8%), B-063 (the footnote still says "latest payment × payments per year") and B-068 (finding 6).
- **Perf:** cold `/portfolios/loop-income/fundamentals` dropped to 2.2 s, from 26.8 s last round. Cold `/risk` is still 15.5 s (B-026).

## Findings

### 1. On an ex-dividend day the portfolio's numbers don't reconcile: Day P&L −$593.74, but the value fell $627.50. The $33.76 PG dividend isn't counted anywhere.
- kind: bug
- severity: high (two figures for one session's P&L; total return understated for an income portfolio)
- evidence:
  - PG went ex-dividend 10-23 ($1.089 × 31 shares = $33.76).
  - `GET /api/portfolios/loop-income`: PG `prev_close 164.501`, `change_pct −2.116`. That previous close is the dividend-adjusted one, because `/api/history/PG` has the 10-22 close at **165.59** and 165.59 − 1.089 = 164.501. The portfolio's `day_pnl` is −593.74.
  - `GET /performance` series: 10-22 value 99,788.59, 10-23 value 99,161.09. That's a change of **−627.50**, measured from the unadjusted 165.59.
  - The difference is exactly $33.76, the dividend. The Dashboard header says "−$593.74 (−0.60%) last session". Performance and drawdown price the same day at −0.63%.
  - The dividend isn't booked anywhere else either. Portfolio `totals.dividends 0.0` and Realized P&L "$0", while Analysis → Dividends says "2026 so far (est.) $33.76 from ex-dates you held through". Performance `gain 813.97` and TWR +0.83% leave it out, so every ex-date shows up as a loss in TWR, Max drawdown and Excess vs SPY.
  - Argus only counts dividends recorded by hand as `DIVIDEND` transactions (`services/performance.py`). For 17 payers that's about 60 manual entries a year, and nothing prompts me to make them.
  - The stress scenarios also say "Price only, no dividends". I verified this: BND −16.0% in the 2022 window. For a bond-heavy book, that overstates the loss by the income received.
- suggestion:
  - Accrue dividends automatically from the ex-dates a position held through (Argus already computes them for "2026 so far"). Count them in performance as income on the ex-date, or on the pay date, and in `totals.dividends`. Label them "accrued (est.)" until a `DIVIDEND` transaction confirms them.
  - At the least, make Day P&L and the performance series use the same previous close.

### 2. Can't set an alert on a yield: `^TNX` is rejected although `argus quotes ^TNX` works
- kind: feature
- severity: medium
- evidence:
  - `uv run argus alert add ^TNX price_above 5.25 --json` returns `INVALID_SYMBOL "'^TNX' doesn't look like a US ticker."`
  - `uv run argus quotes ^TNX --json` returns price 4.988 and prev_close 4.953 from Yahoo, and Markets shows the 10-year gauge.
  - 35% of my book is bond ETFs, and the trigger I actually manage to is "10-year above 5.25%: review duration". Right now I'd have to watch BND's price as a proxy.
  - The decision it changes: whether to shorten duration (VGIT to a short-term fund) ahead of the FOMC.
- suggestion: allow `price_above`, `price_below` and `day_move_pct` on the index and yield symbols Markets already quotes (`^TNX`, `^VIX`, `^GSPC`). For yields, consider a `day_move_bp` kind.

### 3. Upcoming dividends still disagree across pages: an unentitled JPM payment and weekend ex-dates (B-013, fifth round)
- kind: bug
- severity: medium (existing B-013)
- evidence:
  - The Dashboard's Coming up and `argus brief loop-income --json` (`dividends_upcoming`) both list **"JPM dividend_pay 2026-10-31, held: true"**. I bought JPM on 10-20, after its 10-06 ex-date, and `/dividends` correctly projects JPM $0 for the rest of 2026.
  - Estimated ex-dates fall on weekends:
    - BND, VCIT, VGIT and SCHP "~Nov 1" (a Sunday).
    - NEE "~Nov 28" (a Saturday). /t/NEE Events shows "Fri, Nov 27 Ex-dividend" for the same payment.
  - KO is still "~Dec 15" on Dividends against "Tue, Dec 1 Ex-dividend" on /t/KO.
- suggestion: only mark a pay event `held` when the position was open on its ex-date. Roll estimated ex-dates to the previous business day, or to the next one for the "first business day" ETF payers. Prefer the announced date when events have one.

### 4. FCF margin divides SEC FCF by Yahoo revenue from a different window (KO 25.06% vs 25.49% same-window)
- kind: bug
- severity: low
- evidence:
  - `/api/fundamentals/KO`: `fcf_ttm 12.562B` (source `sec`, quarters 2025-06-27 to 2026-04-03) and `revenue_ttm 50.129B` (source `yahoo`). `fcf_margin_pct 25.06` is 12.562 ÷ 50.129.
  - SEC revenue for the same four quarters in `/api/financials/KO` is 12.535 + 12.455 + 11.822 + 12.472 = **49.284B**, which gives 25.49%.
  - The mix gets worse as SEC goes staler (KO reports 10-27). A ratio's numerator and denominator should cover the same quarters.
- suggestion: when `fcf_ttm` comes from SEC, compute the margin over the same `fcf_ttm_quarters` revenue from the SEC table (or show "–").

### 5. Stale-SEC banner says a 10-Q "is due" when it was filed months ago; NEE's fundamentals card shows no warning or FCF source
- kind: ux
- severity: low
- evidence:
  - /t/KO and /t/NEE: "SEC's data ends at the quarter ended 2026-04-03 (206 days ago): a newer 10-Q is due but isn't in SEC's XBRL data yet".
  - KO filed that 10-Q on 07-29. NEE has filed two since (07-24 and 10-21). /t/NEE's own Events section shows "Wed, Oct 21 Reported, EPS 1.24 vs 1.19".
  - On /t/NEE the fundamentals card has no banner (KO's does). "Free cash flow (TTM) −21.21B" has no source line, although it's Yahoo's levered FCF. Last round's Yahoo figure was −17.77B. KO's line reads "SEC, 4Q to 2026-04-03".
- suggestion:
  - Reword the banner to "newer filings exist; SEC's XBRL feed hasn't published them yet".
  - Show the banner on the fundamentals card whenever `sec.stale` is true.
  - Label non-SEC FCF "Yahoo (levered)".

### 6. Dashboard still annualizes volatility and Sharpe from 4 sessions (16.7%, Sharpe 3.17) next to Analysis's 7.5% (B-068)
- kind: bug
- severity: medium (existing B-068)
- evidence:
  - `GET /performance`: `sessions 4`, `volatility_pct 16.71`, `sharpe 3.17`.
  - The Dashboard card shows "Volatility (ann.) 16.7%". Analysis → Risk shows "Volatility (annualized) 7.5%".
  - Both are labeled the same way, for the same portfolio, on the same day.
- suggestion: as in B-068, show "–, needs 20 sessions", or label the figure "since inception (4 sessions)".

### 7. Stock page says "Not held in loop-growth" for a stock I hold in another portfolio
- kind: ux
- severity: low
- evidence:
  - I opened /t/KO in a fresh browser. The header picker defaulted to `loop-growth`, and the "Your position" card says "Not held in loop-growth".
  - The same page's Alerts card shows my `loop-income` KO alert, and Thesis & notes shows my loop-income thesis.
  - The page knows the stock is held elsewhere but implies it isn't held at all.
- suggestion: when the selected portfolio doesn't hold the symbol but another does, show "Held in loop-income: 42 sh @ 93.11" with a link to switch.

### 8. Risk is still slow on first open: `/risk` 15.5 s (B-026)
- kind: perf
- severity: low (existing B-026)
- evidence:
  - First calls of the session: `/risk` 15.52 s, `/dividends` 2.39 s, `/performance` 2.18 s, `/fundamentals` 2.17 s (down from 26.8 s), `/exposure` 0.81 s.
  - The Analysis page waits on `/risk` for the Risk card.
- suggestion: as in B-026, warm the risk history for held symbols at startup, or after a trade.
