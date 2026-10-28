# Round 007: income investor

## What I did
- **Market (Argus market context, 10-27 close, reviewed Tue 10-27 about 22:15 ET):**
  - S&P 500 +0.60% to 7722.60 (SPY +0.56%). Fear & Greed 16.7, "Extreme fear".
  - Treasury curve: 1-month 4.10%, 2-year 4.70%, 10-year 4.99%, 30-year 5.30%. Fed decision is tomorrow (10-28 14:00, consensus 4.00%), Core PCE 10-29.
  - Breadth was still building (known, B-027).
  - My calendar: KO reported this morning (EPS 0.91 vs 0.907 est., revenue 13.35B vs 13.31B). Still to come: MSFT 10-28 (amc), ABBV and XOM 10-30 (bmo), O 11-02 (amc).
- **Portfolio `loop-income` before trading:**
  - Value $99,781.16, cost $98,998.52, unrealized +$782.64.
  - Last session −$237.15 (−0.24%) against SPY +0.56%. Staples and energy were weak: XOM −2.5%, KO −1.6% after its print, PEP −1.4%.
  - Since inception (6 sessions): TWR +0.83% against SPY +0.08%. Gain $816.40 = unrealized $782.64 + PG accrual $33.76.
  - Risk (`/risk`): beta 0.13, volatility 7.5%, 1-year max drawdown −5.6%, 1-day 95% VaR $688. The 2022 rate-shock replay gives −14.1%.
  - Bond ETFs make up 35.2% (BND 12.08, VCIT 10.04, VGIT 8.05, SCHP 5.04), above my 30% floor.
  - Drift: every position is within ±0.28 pp of target. The largest gaps are MSFT −0.27 and KO −0.16.
- **Income:** forward income $3,348.30 a year (3.36% on value). Rest of 2026 projects $617.23. Estimated 11-02 ex-dates (BND, VCIT, VGIT, SCHP) are worth $131.93.
- **I re-derived the risk numbers by hand**, from Argus's own `/api/history` bars over 2025-10-24 → 2026-10-27:
  - Every position's beta and volatility matches to 3 decimals, and so do the portfolio's volatility of 7.48% and beta of 0.134.
  - All 17 risk contributions match, for example SCHD 12.60, HD 12.09 and MSFT 0.40.
  - The drawdown (−5.63%, daily-rebalanced weights) matches too.
  - The risk card is right. It's also price-only (finding 2).
- **Decision: add 1 KO now that its report is out; hold everything else.**
  - KO beat on EPS and revenue and still fell 1.6%, so the yield rose to 2.33% (Argus rate $2.12). Rate ÷ EPS TTM is about 64%.
  - KO was my second-largest underweight. I skipped MSFT (reports tomorrow) and kept the rest of the cash until after FOMC and PCE.
  - Simulated first: KO weight 3.84% → 3.93%, net cash −$91.23.
  - **Bought 1 KO @ $91.23** at the post-market quote (txn 44, 22:20 ET). Thesis note 50, review 2027-02-20.
- **After the trade:**
  - Value $99,872.34, cost $99,089.75. Forward income $3,350.42.
  - Day P&L stayed at −$237.15: the after-close lot is treated as next-session money (B-046 works).
- **Alerts:** #6 (KO, down 4% in a day) didn't fire (KO −1.64%). #7 (MSFT) and #8 (ABBV) stay on for this week's reports.
- **Cash: $910.25** ($1,001.48 − $91.23). Invested at cost: $99,089.75. Realized gains: $0. The PG dividend ($33.76, pays 11-16) is accrued but not yet paid, so I haven't recorded a `DIVIDEND`.

## Last round's changes
- **B-046 (after-close trades count from the next session): works, and it helped.**
  - HD's Day P&L today is −$11.70 = 15 × (318.50 − 319.38) + 1 × (318.50 − 317.00). The after-close share runs from its fill, as specified. JPM is the same: 14 × 1.75 + 1 × (335.79 − 334.40) = $25.89.
  - `/performance` 10-27: 99,781.16 − 99,366.91 − 651.40 (flow) = **−$237.15**, which equals Day P&L. The TWR step (−0.2371%) chains to +0.8317%, as reported.
  - Tonight's KO buy left Day P&L and after-hours P&L unchanged: 42 × (91.23 − 91.18) = $2.10, and the new share contributes 0.
  - `/performance` `end_value` is 99,781.16 against the dashboard's 99,872.34 tonight. That's expected until the 10-28 point exists, and last round's two buys did line up once 10-27 was in.
- **B-013 slice (one ex-date view): mostly works.**
  - The JPM 10-31 and ABBV 11-16 pays are `held: false` and gone from Coming up and the brief.
  - Coming up and the brief show BND, VCIT, VGIT and SCHP on Mon 11-02, marked "est." with amounts ($42.08, $42.84, $26.46, $20.55).
  - New side effect: KO's dividend appears twice on /t/KO (finding 1).
- **B-085 (first-open 500s): works.** First opens of /t/KO, /t/O, /t/NEE and /t/VCIT gave no 500s. The only errors were the known ETF `/api/financials` 502s (B-092: BND, SCHP, VCIT).
- **Re-confirmed still open:**
  - B-017: look-through "Unclassified" 35.2%, `funds_without_profile` BND/VCIT/VGIT/SCHP, no duration.
  - B-041: HD $0 via ETFs.
  - B-022: Targets & drift opens "By sector", with "Targets sum to 0.0%".
  - B-044: "Where the risk comes from" lists 15 of 17; MSFT and SCHP are missing.
  - B-063: the footnote still says "Annual rate = latest payment × payments per year".
  - B-087: October drawn as "Received (est.)"; no dividend tile.
  - B-062: KO payout 77.2% vs 64% (rate ÷ EPS).
  - B-043: KO yield 2.78% vs 2.33%.
  - B-083: KO 1 year +33.0% vs chart 1Y +30.1%.
  - B-021: XOM beta 0.17 (Finnhub) vs −0.675 (1-year risk). "SPY falls 10%" gives −1.3%, against replays of −8% to −24.5%.
  - B-023: simulate has no income after, and `value_after` rises by the $91.18 spent.
  - B-093: NEE ~11-30 vs announced 11-27; KO ~12-15 vs 12-01.

## Findings

### 1. KO's December dividend shows twice on /t/KO: announced ex 12-01 plus an estimated ex 12-15 (≈$22.79)
- kind: bug
- severity: medium (an income client sees two KO dividends in December; Coming up will show both when they enter its 14-day window)
- evidence:
  - The /t/KO Events card lists "Tue, Dec 1 Ex-dividend", "Tue, Dec 15 Dividend paid" and "Tue, Dec 15 Ex-dividend · est. ≈ $22.79".
  - `GET /api/events?days_ahead=60&days_back=7&symbol=KO` returns `ex_dividend 2026-12-01` (yahoo), `dividend_pay 2026-12-15` (yahoo) and `ex_dividend 2026-12-15 estimated: true amount 22.79` (estimate). That's one payment shown as two.
  - NEE's estimate (11-30) is dropped next to its announced 11-27, and O's (10-30) next to its announced 10-30. The merge only catches estimates a few days from the announced date, and KO's estimate is 14 days off because the projection steps from the pay date (B-093).
  - The Dividends totals aren't doubled: KO projects $22.26 once.
- suggestion: when a quarter already has an announced ex-date (or pay date) for that symbol, drop that quarter's estimate. Match on "same payment period", not on a few days' distance. Fixing B-093's projection fixes the root cause.

### 2. Every return is price-only and unlabeled: BND shows 1Y −5.0% and "Max −5.2%" since 2007, though it paid ~4% a year
- kind: feature
- severity: medium (for a bond and dividend book, price return misstates what clients earned; I can't show a client BND's real 1-year result)
- evidence:
  - The /t/BND chart tabs read 1Y −5.0%, 5Y −16.6%, Max −5.2%. `/api/returns/BND` bases are raw closes: 1Y 75.06 → 71.31.
  - Adding Argus's own trailing-12-month dividend ($2.94) gives about −1.0% for 1Y. Since 2007, BND's price return is ≈ −5% but its total return is strongly positive.
  - Argus's `/api/history` closes drop on ex-dates (BND 10-01).
  - The risk card's volatility, drawdown and beta use the same price-only closes. The replays say "Price only, no dividends", but the chart and returns say nothing.
  - On my book, an approximate total-return 1-year result is +10.9% vs +7.3% price-only. The drawdown changes little (−5.45% vs −5.63%).
- suggestion: label the stock-page period returns "price return". Add a total-return figure, from Yahoo's adjusted close or Argus's own dividend history, at least for 1Y and for ETFs and payers. Longer term, compute risk on total return.

### 3. Dividend pay events carry no amount: "PG Dividend paid 11-16" without the $33.76 Argus already accrued; announced ex-dates also have no amount
- kind: ux
- severity: low (the client's question is "what lands in my account, and when")
- evidence:
  - `/api/events?symbol=PG` shows `dividend_pay 2026-11-16 amount: null`, while `/performance` `dividends_accrued` shows PG 31 × $1.089 = $33.76.
  - O: `dividend_pay 2026-11-13 amount: null`, though O's 10-30 ex is projected at $19.31.
  - In Coming up, the announced "Fri, Oct 30 O Ex-dividend" row has no amount, while the estimated rows below it show "≈ $42.08" and so on. KO 12-01 and NEE 11-27 are the same.
- suggestion: attach `per_share` and `amount` (shares held on the ex-date × the last or announced rate) to announced ex-dates and to pay events held through the ex-date. This is the core of B-042's pay-date income calendar.

### 4. Risk still takes 24.5 s on the first load of the session
- kind: perf
- severity: medium (existing B-026; the Analysis risk card is blank that long)
- evidence:
  - First `GET /api/portfolios/loop-income/risk` of the session: 24.46 s. Last round it was 13.0 s.
  - After my trade it took 1.31 s, then 3.37 s. Every other portfolio endpoint answered in under 2 s (`/performance` 1.86 s, `/fundamentals` 1.08 s).
- suggestion: as B-026. Precompute or cache the 252-day history matrix and factor data at startup, or after the daily close.

### 5. Tonight's KO buy is dated 2026-10-28 on /t/KO and in its thesis note; I bought it at 22:20 ET on 10-27
- kind: bug
- severity: low (existing B-049)
- evidence:
  - Txn 44 is stored as `ts 2026-10-28T02:20:09Z`.
  - /t/KO "Your position" lists it as **2026-10-28 Buy 1 @ 91.23**, and the thesis note header reads "2026-10-28".
  - Performance will count it at the 10-28 session, which is correct under B-046, but the trade date shown is wrong.
- suggestion: as B-049. Show New York dates for trades and notes everywhere.

### 6. Brief headlines for my holdings are about other companies (XOM → Chevron, Texas Pacific Land; KO → WPP)
- kind: bug
- severity: low (existing B-059, new surface)
- evidence:
  - The `/api/brief/loop-income` `headlines.XOM` items include "The Events That Matter Most For Chevron Stock" and "Is Texas Pacific Land Stock About To Rebound?".
  - `headlines.KO` includes "WPP (LSE:WPP) Stock May Be Priced About Right On AI Shopping Agent News".
  - None of these is about the holding.
- suggestion: as B-059. Keep a headline only if the ticker or company name appears in its headline or summary.

### 7. "EPS 0.91 vs 0.91 (beat +0.3%)" reads as a contradiction
- kind: ux
- severity: low
- evidence:
  - Dashboard Coming up and the /t/KO Events card both show "Reported EPS 0.91 vs 0.91 (beat +0.3%)".
  - The estimate is 0.9071 (`/api/brief` `earnings_recent`), rounded to 0.91.
- suggestion: show the estimate to 3 decimals when it rounds to the actual (0.91 vs 0.907), or say "in line" when the surprise is under ~0.5%.

### 8. Analysis on a phone: the Dividends table hides the annual income column; stress losses are still cut off
- kind: ux
- severity: low (existing B-002)
- evidence:
  - At 390 px, the Analysis Dividends table shows Symbol, Pays, Annual/share and Yield. Yield on cost, Annual income, 2026 received, Rest of 2026 and Next ex-date are off-screen.
  - Stress scenarios still show the name and window, but not "Your portfolio" or the $ change.
- suggestion: at narrow widths, lead with Symbol, Annual income and Next ex-date, and drop Annual/share and Pays.
