# Round 013: income investor

## What I did
- **Market (Argus market context, Thu 11-05 close, reviewed about 21:15 ET):**
  - A risk-off day. The S&P 500 fell 4.36% to 7353.73, SPY 4.41% to 733.00, and the Nasdaq 100 6.36%. XLK fell 8.0%.
  - VIX went from 16.61 to 28.18 (+69.7%). Fear & Greed is 1.2 ("Extreme fear"), with all five components in extreme fear.
  - Bonds caught a bid. ^TNX went from 4.894 to 4.837. On the curve the 10-year is 4.84%, down from 4.95% on Tuesday and 5.31% a month ago, and the 2-year is 4.46%.
  - Macro data: claims came in at 189K against 197K expected. ISM services was 54.5 on Wednesday.
  - Payrolls (Fri 11-06, consensus 65K, unemployment rate 4.2%) are back on the calendar.
- **Portfolio `loop-income` (11-05 close):**
  - **Value and P&L:** value $102,239.61 before my trade, cost $99,618.80, unrealized +$2,620.81. Day P&L was −$1,046.11 (−1.01%) against SPY −4.41%. Wednesday's +2.13% (SPY +1.65%) explains why the value is still above Tuesday's $101,126.84.
  - **Cross-check:** I rebuilt the 11-02, 11-03 and 11-04 values from `/api/history` closes × quantities. They match the performance series to the cent (101,778.32 / 101,126.84 / 103,285.72). The 11-05 point is built from quotes (`closes_from_quotes`), and the step from 11-04 to 11-05 equals Day P&L exactly.
  - **What moved:** the losers were JPM −4.19%, MSFT −3.58%, VIG −3.34%, ABBV −2.24% and SCHD −2.18%. The bond ETFs gained: VGIT +0.36%, VCIT +0.23%, BND +0.21% and SCHP +0.12%. With bonds at 34.5% of the book, the sleeve did its job.
  - **Drift:** every position is within ±0.48 pp of target, against a ±2 pp band. The largest drifts were XOM −0.44, HD +0.48 and NEE +0.32.
- **Risk (Argus card "to 2026-11-04"):** beta 0.15, volatility 7.9%, 95% VaR $656, 99% VaR $1,028, max drawdown −5.7%. Today's loss of $1,046 was larger than the 99% VaR, and the card doesn't know (finding 2).
- **Income:**
  - Forward income is $3,361.73, a 3.29% yield (3.37% on cost).
  - 2026 received is $185.64, the same as last round, so B-133 holds.
  - The 2026 expected total is $653.71. That figure is about $133 short, because Argus moves the bond ETFs' late-December payment into January (finding 1).
- **Trade:**
  - **BUY 2 XOM at 165.75** (post-market quote, txn 54, thesis note 78, review 11-17).
  - **Why:** it puts idle cash into the most underweight position, at 3.56% against a 4% target. It also catches the 11-16 ex-date and adds an energy holding with negative beta to a book that just watched tech fall 8%.
  - **Before the trade:** `simulate` gave weight 3.56% → 3.87%. It priced the trade at the 4 pm close of 165.30, not the post-market 165.75 (B-109).
  - **Alert:** I added a JPM day-loss alert at 4% (id 9). It fired at once for today's −4.19%, which is the right behaviour.
- **No other trades:**
  - Drift is a quarter of the band.
  - I'm not selling bonds into a rally or buying equities into a −4% day before payrolls.
  - Note 67 (BND, review 11-10) stands. The 10-year moved away from the 5.1% add trigger.
- **Cash: $49.70.**
  - Invested at cost: $99,950.30. Realized gains: $0.
  - Value at the 11-05 close, including the new XOM shares at 165.30: $102,570.21.
  - Return to date: (102,570.21 + 49.70 − 100,000) ÷ 100,000 = **+2.62%**. Adding Argus's $185.64 of accrued dividends gives +2.81%.

## Last round's changes
- **B-133 (dividend history merged, not replaced): works.**
  - Received is still $185.64. November shows $132.57 received plus $105.86 projected, $238.43 in total.
  - Yahoo still hasn't published the bond ETFs' 10-01 or 11-02 rows. The stored history ends at 09-01 for BND, VCIT, VGIT and SCHP. The 11-02 estimate keeps counting, as designed.
  - `trailing_12m` stays low (VCIT 3.316 against a rate of 4.08). That is expected until Yahoo catches up. It has now been four days since the 11-02 ex-date.
- **B-134 (last session from quotes): works, and it helped tonight.**
  - Yahoo had no 11-05 daily bar for any holding or SPY. Performance filled it from quotes, so `closes_from_quotes` lists all 18 symbols.
  - Return is +2.84%, SPY −4.69% and excess +7.52%. The last step equals Day P&L (−$1,046.11).
  - **Two gaps:**
    - The dashboard doesn't say the point is from quotes.
    - Risk doesn't use the fill (finding 2).
- **B-115 (month-end and first-day payers): works.**
  - O's next dates are 11-30, 12-31, 01-29 and 02-26.
  - The bond ETFs project 12-01, then 01-04, 02-01 and 03-01 (`/api/events?days_ahead=120`). The 01-04 date is itself wrong for Vanguard and Schwab bond funds (finding 1).
- **B-135 (payrolls missing): it's back, but because Nasdaq's feed restored 11-06, not because of a code change.**
  - `calendar.events` now has NFP, unemployment and AHE on 11-06. B-135 is still open, and the next dropped day will repeat it.
- **B-136:** the brief's `dividends_upcoming` is still `[]`, while Coming up lists O paying 11-13, PG paying 11-16 and the XOM ex-date 11-16. The brief's window is 7 days and Coming up's is 14. Still open.
- **Still open, re-seen:**
  - **B-131:** "O EPS 1.12 vs 0.43 (beat +162.2%)" is on Coming up and in the brief.
  - **B-132:** HD's 11-17 earnings row is labelled "quarter 3, year 2027".
  - **B-022:** Targets still opens "By sector" with "Targets sum to 0.0%".
  - **B-118:** `/?portfolio=loop-income` still opened loop-growth.
  - **B-026:** the first `/risk` took 21.2 s and the second 0.31 s.
  - **B-012:** the tile reads "51% / 49%". That matches Stock 50.7% and ETF 49.3%, but Stock is now the larger weight, so I can't tell whether the label order is fixed.

## Findings

### 1. Bond ETFs' second December dividend is projected on 01-04, so 2026 income is $132.57 short and January 2027 gets a payment that doesn't exist
- kind: bug
- severity: high (a wrong number on the client tile: the 2026 expected total is 20% low, and the December bar is wrong)
- evidence:
  - **Argus's own history (`dividend_history`) shows the pattern.** Vanguard's and Schwab's bond funds pay twice in December and skip January:
    - BND: 2024-12-02, 2024-12-24, 2025-02-03, then 2025-12-01, 2025-12-18, 2026-02-02.
    - VCIT and VGIT have the same dates.
    - SCHP: 2024-12-02, 2024-12-20, then 2025-12-01, 2025-12-19, with no January row.
  - **What Argus projects instead:** `/api/events?portfolio=loop-income&days_ahead=120` gives BND, VCIT, VGIT and SCHP an ex-date on 2026-12-01, then **2027-01-04**, 02-01 and 03-01. There's nothing near 12-18 to 12-24.
  - **Effect:**
    - `/dividends` gives `year_total` $653.71 and December $362.21.
    - The late-December payments (BND $42.76, VCIT $42.84, VGIT $28.84, SCHP $18.13, total $132.57) belong in 2026: about $786 for the year and $495 for December.
    - Forward annual income is unaffected, since it's still 12 payments.
  - **Smaller, same cause:** SCHD is projected for 12-23, stepped 3 months from 09-23, but its history shows December ex-dates of 12-11 and 12-10.
- suggestion:
  - When the last two years of history show a month with two ex-dates and a skipped month (Dec ×2, no Jan), project that calendar rather than a fixed monthly step.
  - More simply: for each projected month, use the same month's ex-day(s) from the prior year's history.
  - Test: BND-like history, with today = 11-05 → 2026 projections are 12-01 and ~12-18, with none in January.

### 2. The risk card stops at 11-04 and misses the year's worst session; today's loss exceeded the 99% VaR and nothing says so
- kind: bug
- severity: medium (the risk view a client sees after a −4.4% day is computed as if the day never happened)
- evidence:
  - **`GET /api/portfolios/loop-income/risk`:** `as_of 2026-11-04`, VaR 95% $656.40 and 99% $1,028.30. The same was true after my trade: `as_of 2026-11-04`, 99% VaR $1,027.03.
  - **Performance for the same evening** uses `closes_from_quotes` for 11-05, covering all 17 holdings and SPY. The helper `_fill_last_session` (app.py:1468) is only called from performance.
  - **Realized day:** −$1,046.11, which is larger than the 99% one-day VaR. A risk manager wants that flagged, and wants the 11-05 return in the volatility, beta and VaR window.
- suggestion:
  - Feed risk the same quote-filled last session (mark it as performance does).
  - Add "last session P&L vs VaR" to the risk card: "−$1,046 (exceeded 99% VaR)".

### 3. Today's move is 1.5× what beta predicts; "SPY falls 10% (via beta)" still understates (evidence for B-021)
- kind: ux
- severity: medium
- evidence:
  - The risk card has beta 0.15, and its scenario "SPY falls 10% (via beta)" gives −1.5% (−$1,541).
  - **Realized on 11-05:** SPY −4.41% and the portfolio −1.01%, a ratio of 0.23. Scaled to a 10% fall, that is about −2.3% (−$2,350).
  - The factor "Market" loading of 0.39 sits on the same page, still unexplained.
  - The historical replays (−8% to −25%) bracket this, but the only quick stress a client reads is the beta line.
- suggestion: show the beta scenario as a range: 1-year beta, the factor market loading, and down-day beta (beta on SPY down days only). Label which beta is which. That is the B-021 fix with fresh evidence.

### 4. Bond sleeve rate sensitivity is still absent on the day rates moved (B-017)
- kind: feature
- severity: medium
- evidence:
  - ^TNX went from 4.894 to 4.837 (−5.7 bp). BND rose 0.21%, VCIT 0.23% and VGIT 0.36%.
  - From that one day I can back out an effective duration of only about 3.7–6. Credit widened, with junk against IG at −2.0 pp in the Fear & Greed card.
  - /analysis still shows the bonds as "Unclassified 34.5%", and `/exposure` lists `funds_without_profile: [BND, VCIT, VGIT, SCHP]`.
  - My decision for 11-10 (add bonds if the 10-year is above 5.1%) needs dollars per +50 bp. I can't get that from Argus.
- suggestion: per-fund duration from N-PORT, plus a "rates ±50/±100 bp" row in Stress scenarios.

### 5. Announced ex-dates carry the last payment's amount, so the November raises are missed (B-064)
- kind: bug
- severity: low
- evidence:
  - **XOM:** the announced 11-16 ex-date (`event` table `data: {}`) is projected at 1.03 × 24 = $24.72. XOM's own history shows a raise at every November ex-date (0.95 → 0.99 in 2024, → 1.03 in 2025), and r011 recorded the declared $1.07 ($25.68).
  - **MSFT:** its 11-19 ex-date (0.91) follows the same history pattern (0.75 → 0.83 → 0.91 at November ex-dates). Argus has no declared amount, so nothing warns that the projection may be stale.
- suggestion: store the declared amount with announced events. Failing that, flag "usually raised at this payment" from the payer's history.

### 6. At 390 px, the factor and dividend tables on Analysis hide their numbers
- kind: ux
- severity: low
- evidence:
  - The /analysis full-page screenshot at `--width 390` (no page overflow, no errors) shows "Factor exposures" with only the factor names. Loading, t-stat and reading are cut off to the right, and the card scrolls internally with no visible hint.
  - The Dividends table shows Symbol, Pays, Annual/share and Yield. Yield on cost, Annual income, Received, Rest of 2026 and Next ex-date are off screen.
- suggestion: on phones, stack these as two-line rows (name on top, key numbers below), or pin the first column and show a scroll shadow.

### 7. After an evening trade, the header value and the Performance card's end value differ by the trade, with no explanation
- kind: ux
- severity: low
- evidence:
  - After txn 54 (2 XOM at 21:18 ET), `/api/portfolios/loop-income` shows a market value of $102,570.21.
  - Performance shows `end_value` $102,239.61 and `net_invested` unchanged. That follows B-046's design: after-close trades are booked on the next session.
  - Gain and TWR stay consistent, but the dashboard shows two "values" $330.60 apart with no note.
- suggestion: one line under Performance, such as "1 after-close trade ($331.50) counts from Fri 11-06". The same applies to the quote-filled point: "11-05 from quotes; Yahoo's bar not in yet".

### 8. First risk load is still 21 s (B-026)
- kind: perf
- severity: low (known)
- evidence: the first `/api/portfolios/loop-income/risk` of the evening took 21.24 s, then 0.31 s, and 0.60 s just after my trade. The other portfolio endpoints took 0.03–2.4 s.
- suggestion: as in B-026, warm risk in the background after the preflight.

## Summary for the lead
- Bought 2 XOM at 165.75 with idle cash (txn 54, note 78), closing the largest underweight. Cash is $49.70 and return to date +2.62%. The book fell −1.01% against SPY's −4.41%, with bonds up.
- Top finding (new, high): the bond ETFs' second December dividend is projected on 01-04 instead of ~12-18, so 2026 income is $132.57 short ($653.71 shown against about $786). Argus's own history shows the Dec ×2 / no-January pattern.
- Second (new, medium): risk stops at 11-04 and ignores the quote-filled 11-05. Today's $1,046 loss beat the 99% VaR ($1,028) without a flag. B-133, B-134 and B-115 are verified working. Payrolls are back but B-135 isn't fixed. B-136, B-131, B-022, B-118 and B-026 are still open.
