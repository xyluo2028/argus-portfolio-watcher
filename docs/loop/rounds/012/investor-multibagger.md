# Round 012: multibagger (growth) investor

## What I did
- **Timing:** about 02:15 to 02:50 UTC on Wed 2026-11-04, which is Tue 11-03 evening ET. The market was closed. Prices are the 11-03 close plus post-market quotes. Yahoo's daily bars end at 11-02, so the 11-03 session isn't in history yet.
- **Book** (`GET /api/portfolios/loop-growth`, 0.05 s): 11 positions, cost $99,823.05, value **$97,941.31**, unrealized −$1,881.74. Day P&L for 11-03 was **+$1,509.93 (+1.57%)** against IWM's +0.23%.
  - The biggest moves were RMBS +4.96% (+$505), ESE +3.96% and KRYS +3.14% (+$372). HRMY was −2.35%.
  - After hours: TOST −3.76% on its report and PODD +2.00%. Total after-hours P&L was −$151.63.
- **TOST reported Q3 after the close.** All the figures below come from Argus (brief headlines, `/api/earnings/TOST`, SEC statements):
  - **Revenue:** $1.981B. Against SEC's Q3-25 figure of $1.633B, that's **+21.3% y/y**. Q2 was +23.1% (1.908 ÷ 1.550), so growth is slowing.
  - **Against consensus:** revenue was in line ($2.012B Finnhub estimate, −1.6%). GAAP EPS was $0.29 (headline). Adjusted EPS was 0.38 against 0.37 (Yahoo). The headline says "Q4 guidance moderates", but Argus has no guidance figures.
  - **Thesis (note 31, breaks below 18% growth): intact but slowing.** I'm holding with no add. The update is **note 66** (review 2026-11-20). The 10-Q isn't in SEC yet (latest period 2026-06-30), so operating margin waits for it.
- **Everything else: hold into this week's reports.** PODD and HRMY report Wed before the open and BLLN Wed after the close. LOAR reports Thu before the open, and GRND, INOD and TMDX Thu after the close. Each has a written exit line (notes 41, 49, 55 and others).
- **Hunt:** I re-ran Screen A (`POST /api/screener`: cap $0.5–15B, growth ≥25%, gross margin ≥40%, operating margin ≥8%, FCF margin ≥5%, P/S ≤12, liabilities/equity ≤2). It returned the same 8 names (FY2025 data): PODD, HL, DUOL, TAL, JOE, TMDX, NUTX and MNTN.
  - DUOL reported 11-03 (−5.4% in the session, then +12% after hours). Its SEC revenue gives Q3 at $309.0M against $271.7M a year earlier, which is **+13.7% y/y**, below my 25% bar. Its P/E of 15 includes the one-off Q3-25 tax gain (EPS 5.95; B-071). **Pass.**
- **No trades.** Cash is unchanged at **$176.95**. Return to date: (97,941.31 + 176.95 − 100,000) ÷ 100,000 = **−1.88%**.
- **Concentration:** healthcare is 47.2% and technology 40.7%. No position is above 12.9% at cost.

## Last round's changes
- **B-128 (bars without a close are dropped): works.** History returns 200, and the 11-02 bar is now in: SPY closed at 752.10, matching the quote's prev_close.
  - The 11-03 session isn't in Yahoo's daily bars yet, and two features handle that gap badly (findings 1 and 2).
- **B-130 (history failures fail soft): works.** Fundamentals, research, per-symbol earnings, performance, risk and the portfolio fundamentals/earnings endpoints all return 200 with `errors: {}`.
  - The stock page renders in 0.15 s with no errors or horizontal overflow.
  - Risk now labels itself `as_of: 2026-11-02`, which is correct.
- **B-088 on `/api/earnings/PAYS`: works.** PAYS now has report dates and reactions back to 2024-11, for example the Q2 report on 2026-08-05 (+29.3% next close). The next report is 11-09 after the close.
  - **One gap:** the Q1 2026 report (period 2026-03-31, around May) is missing entirely. The `event` table has no PAYS row between April and June. That's low priority.
- **B-129:** not part of my book, since I hold no dividend payers.

## Findings

### 1. Earnings reaction uses the wrong base close when the report day's bar isn't stored yet: DUOL shows +5.9% after hours on a +11.9% move
- kind: bug
- severity: high (the reaction is the first number I read after a print, and here it's off by half)
- evidence:
  - `GET /api/earnings/DUOL`: the Q3 report (11-03 after the close) has reaction `base_date 2026-11-02, base_close 135.27, close_pct +5.93, label "after hours"`.
  - The 11-03 close was 128.00 (quote) and the post-market price 143.29, so the after-hours move is **+11.95%**. The watchlist quote shows exactly that. Argus's figure also counts the −5.4% regular session before the report.
  - Same for TOST: `base_date 2026-11-02, base_close 33.42, close_pct −3.44`. The actual move is 32.27 ÷ 33.53 = **−3.76%**, which the portfolio shows as `ext_change_pct`.
  - Cause: `services/earnings.py reaction()`: for "amc", `base_day = report if report in bars else before[-1]`. Yahoo's daily bars end at 11-02, so it silently falls back to the day before.
- suggestion: for an after-close report whose report-day bar is missing, use the quote's regular close (`quote.price`, `session_date == report`) as the base. If that isn't available, return null rather than a prior day's close.

### 2. Performance shows 11-03 as a flat day and drops the benchmark, while the same Dashboard says +1.57% for the session
- kind: bug
- severity: high (wrong return on the main page every evening until Yahoo fills the bar)
- evidence:
  - `GET /api/portfolios/loop-growth/performance`: summary `end 2026-11-03, end_value 96,437.68, twr_pct −3.52, benchmark_pct null, excess_pct null`. The last series point has `bench_pct: null`, and `provisional_today` is false.
  - 96,437.68 is the 11-02 value (94,366.38) plus the 11-03 flow ($2,065) plus $6.30, so it's priced at **11-02 closes**.
  - The portfolio's value at the 11-03 close is **$97,941.31** (Day P&L +$1,509.93).
  - **Expected:** TWR ≈ (1 − 0.03531) × (1 + (97,941.31 − 2,065 − 94,366.38) ÷ 94,366.38) − 1 = **−1.99%**. IWM ≈ 1.01218 × 1.00233 − 1 = **+1.45%**.
  - **Dashboard screenshot (1400 px):** the header says "+$1,509.93 (+1.57%) last session" and the "Portfolio vs IWM" tile says "+1.57% / +0.23%". Just below, the Performance card reads "Return −3.52%, IWM –, Excess return –", and the 11-02→11-03 line is flat.
- suggestion: when the last session's daily bar is missing, value that session from the quotes' regular close (the `session_date` matches). Do it for the benchmark too, and mark the point provisional. Same rule as the B-128 follow-up the lead proposed ("fill the close from the quote").

### 3. Finnhub EPS is labeled "adjusted", but its past actuals equal SEC GAAP EPS; TOST's "beat +44.3%" compares adjusted with a GAAP-basis estimate (B-119)
- kind: bug
- severity: medium (beat size drives my read of a print; +44% vs +2% is a different story)
- evidence:
  - **Finnhub actuals match SEC GAAP:** in `/api/earnings/TOST`, Q2 has eps_actual 0.26 and Q1 has 0.20, both with `eps_basis: "adjusted"` (Finnhub). SEC diluted EPS (`argus financials TOST`) is **0.26 and 0.20**.
  - **Yahoo's figures look adjusted:** Yahoo's rows for those quarters (`event` table) have actuals of **0.36 and 0.29**. Yet the docstring and the footnote flag Yahoo as "reported, can be GAAP".
  - **The page contradicts itself:** on the stock page, the Reported financials table puts "EPS (dil.)" 0.26 / 0.20 (SEC) right beside "EPS actual" 0.26 / 0.20. The footnote under it says the latter are adjusted.
  - **Q3 mixes the two bases:**
    - Finnhub gives estimate 0.2564 and actual 0.37, so +44.3%. The Events card, the Dashboard's "Coming up" and the brief's `earnings_recent` all show "EPS 0.37 vs 0.26 (beat +44.3%)".
    - The headline in Argus says "GAAP profit of $0.29 per share was 14.3% above consensus", which puts the GAAP consensus at about 0.254. That's Finnhub's estimate.
    - Yahoo (adjusted) has 0.38 against 0.37 (+2.1%).
- suggestion:
  - Don't label Finnhub as adjusted. Where SEC diluted EPS for the period equals the provider's actual, label it GAAP.
  - When the two providers' actuals differ by more than about 10%, show both ("GAAP 0.29 vs est 0.25 · adj. 0.38 vs 0.37"), or don't compute a surprise across sources.

### 4. The brief's `watchlist_movers` is still empty while DUOL moved −5.4%/+12% AH on earnings and PTCT moved +11.9% (B-106)
- kind: bug
- severity: medium
- evidence:
  - `GET /api/brief/loop-growth` returns `watchlist_movers: []`.
  - `GET /api/watchlists/growth-candidates` shows PTCT +11.89%, DUOL −5.37% (after hours +11.95%), PAYS +5.07% and BCRX +3.94%.
  - DUOL's 11-03 report and XZO's 11-04 report aren't in the brief's earnings either. The watchlist earnings endpoint has them.
- suggestion: as filed. Feed the named watchlists into the brief's movers and earnings.

### 5. The stock page's Reported financials table has no row for the quarter just reported, though the Events card and `/api/earnings` have it
- kind: ux
- severity: medium (after a print I open the stock page and the table I read stops at last quarter)
- evidence:
  - `/t/TOST` (1400 px, full page): the Events card says "Tue, Nov 3 Reported, EPS 0.37 vs 0.26 (beat +44.3%)".
  - The Reported financials table's newest row is 2026-06-30. `/api/earnings/TOST` includes the 2026-09-30 report: revenue actual $1.981B against an estimate of $2.012B (miss −1.6%), the EPS figures and the after-hours reaction.
  - B-088 added pre-10-Q quarters to the API, but the table is still built on SEC periods only.
- suggestion: show a provisional top row for a reported quarter with no 10-Q yet. It would have revenue and EPS from the earnings data, "10-Q pending" in the margin columns, and the reaction. Then the beat/miss and the provisional move sit with the history.

### 6. Most holdings' "last report" still has no date (B-132)
- kind: ux
- severity: low (new evidence)
- evidence:
  - In `GET /api/portfolios/loop-growth/earnings`, KRYS, RMBS and TOST have `last.date`.
  - The other eight have only `period 2026-06-30`, for example PODD, which reports tomorrow.
- suggestion: as filed.

### 7. Research → Estimates "This quarter" is still the quarter that just reported
- kind: ux
- severity: low
- evidence:
  - `GET /api/research/TOST` returns `estimates.trend["0q"].current 0.373`. That's the Q3 consensus, and Q3 was reported three hours earlier.
  - Next to the Events card's "Reported", "This quarter: 0.37" reads like Q4's estimate. Q4's is actually 0.345 (Yahoo `+1q`) or 0.23 (Finnhub `next`).
- suggestion: when the `0q` quarter has a reported actual, label it "Q3 (reported)". Alternatively, label each column with its fiscal quarter end.

### 8. Cold watchlist 7.7 s; Peers still "Loading…" after 6 s (B-026, B-097)
- kind: perf
- severity: low
- evidence:
  - The first `GET /api/watchlists/growth-candidates` took 7.74 s and the second 0.04 s.
  - The first `/api/earnings/PAYS` took 9.26 s and `/api/earnings/TOST` 2.66 s.
  - The `/t/TOST` screenshot with `--settle 6` shows the Peers card on "Loading…".
  - Portfolio 0.05 s, performance 0.03 s, risk 1.6 s.
- suggestion: as filed.

## Summary
1. No trades. TOST Q3 revenue was +21.3% (slowing from +23.1%), in line with consensus, and the stock is −3.8% after hours. The thesis holds (note 66). Value is $97,941.31, cash **$176.95**, return to date **−1.88%**.
2. **Gaps from Yahoo's missing 11-03 bar:**
   - Earnings reactions use the 11-02 close as the base. DUOL shows +5.9% against a true +11.95% after hours.
   - Performance prices 11-03 at 11-02 closes: −3.52% and no benchmark, against about −1.99% and IWM +1.45%. The same Dashboard shows +1.57% for the session.
3. **EPS basis is backwards:** Finnhub "adjusted" actuals equal SEC GAAP EPS. TOST's "+44.3% beat" mixes an adjusted actual with a GAAP-basis estimate (B-119). B-128, B-130 and B-088 (PAYS) work.
