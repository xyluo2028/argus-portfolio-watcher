# Round 010: income investor

## What I did
- **Market (Argus market context, 10-30 close, reviewed Sun 11-01 at about 21:15 ET):**
  - Friday was a risk-off day. The S&P 500 fell 1.82% to 7580.07, the Nasdaq 100 fell 3.46% and SPY fell 1.77%. VIX is 19.4 (+12.9%), and Fear & Greed is 8.5 ("Extreme fear", without breadth, which is still building).
  - Rates eased again. The 10-year is 4.94%, down from 5.29% a month ago, and the 2-year is 4.56% (4.88% a month ago). WTI is $101.6.
  - This week: O reports Mon 11-02 after the close, the Vanguard and Schwab bond ETFs go ex around 11-02, XOM goes ex 11-16 and PG pays 11-16. The calendar dates for the week's macro releases are wrong (finding 1), so I took them from the raw feed instead.
- **Portfolio `loop-income`:**
  - Value $101,709.19, cost $99,618.80, unrealized +$2,090.39.
  - Last session +$376.79 (+0.37%) while SPY fell 1.77%. PEP +2.65% (+$131), XOM +2.16% and NEE +1.91% led. JPM −1.90% (−$98) and MSFT −1.53% lagged.
  - Day P&L reconciles with Performance: 101,709.19 − 100,822.63 − 529.05 (the MSFT buy) + 19.31 (O's dividend) = $376.82, against the header's $376.79.
  - Since inception (9 sessions), TWR is +2.17% against SPY −1.73%. Gain is $2,143.46: the unrealized $2,090.39 plus $53.07 of accrued PG and O dividends. It reconciles.
  - Risk: beta 0.13, volatility 7.5%, 1-year max drawdown −5.6%, 1-day 95% VaR $660. Bond ETFs are 34.7% of the book (BND 11.9, VCIT 9.9, VGIT 7.9, SCHP 5.0), above my 30% floor.
  - Drift: every position is within ±0.18 pp of target. The largest gaps are VIG −0.13, VCIT −0.13 and HD +0.18. The band is ±2 pp.
- **Income:** forward income is $3,354.06, a 3.30% yield (3.37% on cost). 2026 expected is $652.43: $53.07 accrued plus $599.36 projected (Nov $238, Dec $362). The 17 per-holding "Rest of 2026" cells sum to $599.36, the same as the tile.
- **Post-earnings review (ABBV, XOM, both 10-30 before the open):**
  - **ABBV:** adjusted EPS 3.82 against 3.823 expected, revenue $17.40B against $17.66B, and the 2026 guide was raised. The stock rose 1.41% to 294.89, near its 52-week high. Argus's news says the dividend was raised 5.2% (from $1.73 to about $1.82). On coverage, the adjusted EPS run rate covers the dividend about 2.2×, and the dividend takes about 67% of SEC FCF TTM.
  - **XOM:** EPS 4.23 against 4.12 expected, revenue $113.2B against $104.1B. The stock rose 2.16%. Argus's news says the dividend was raised 3.9% (from $1.03 to about $1.07).
  - Both theses are intact, and Argus's income figures don't yet include either raise (finding 2). I wrote notes 59 (ABBV) and 60 (XOM).
- **Trades: none.**
  - Every gap is a tenth of the ±2 pp band.
  - Cash is $381.20 (0.37%), which I keep as a buffer.
  - Buying the bond ETFs at Friday's price on a Sunday, the day before their ex-date, would book a dividend I couldn't get in reality, since a Monday buy misses the 11-02 ex-date.
  - O's report on Monday is the next decision point (note 39 is due 11-03).
- **Alerts:** I turned off #7 (MSFT down 6% in a day) and #8 (ABBV down 5% in a day), because their earnings events have passed. #4 (XOM down 4% in a day) and the below-cost alerts on O, NEE and SCHD stay on. None fired.
- **Cash: $381.20.**
  - Invested at cost: $99,618.80. Realized gains: $0.
  - Return to date: (101,709.19 + 381.20 − 100,000) ÷ 100,000 = **+2.09%**, or +2.14% with the $53.07 of accrued dividends.

## Last round's changes
- **B-034 (the calendar keeps the rows it has seen) and B-116 (PCE, ECI and the GDP price index): can't fully check on a Sunday night, and the calendar is now wrong in another way.**
  - The window starts on yesterday (Sat 10-31), as designed. That means on a weekend or a Monday, Friday's actuals (ECI, personal income and spending, Chicago PMI on 10-30) aren't shown at all (finding 7).
  - Every upcoming release is now dated a day late and timed an hour early (finding 1).
  - "Dallas Fed PCE" is still in the curated list (B-094).
- **B-117 (after-close sells):** not in my workflow this round. As a related check, Day P&L equals the Performance step for 10-30 within $0.03, including last round's after-close MSFT buy and O's ex-date.
- **Income re-check (ABBV after its report):**
  - The ABBV card changed overnight, with no label saying why (finding 3).
  - The Q3 report is in the brief and the Events card but missing from `/api/earnings/ABBV` (finding 4).
  - PG's dividend still shows as "2026 received" $33.76 though it pays 11-16 (B-087).
- **Still open, re-confirmed:**
  - B-063: the footnote "Annual rate = latest payment × payments per year" is still on /analysis.
  - B-022: the Targets card opens "By sector" with "Targets sum to 0.0%".
  - B-012: the tile reads "50% / 50%" under "Stock / ETF".
  - B-044: "Where the risk comes from" lists 15 of 17 holdings; SCHP and MSFT are missing.
  - B-101: the Events card says "EPS 3.82 vs 3.82 (miss −0.1%)".
  - B-021: risk beta 0.13 against a factor market loading of 0.38 (t 10.9) on the same page.

## Findings

### 1. Economic calendar: after DST ended, every release this week is dated a day late and timed an hour early (payrolls on Saturday 11-07 at 07:30)
- kind: bug (a B-006 regression, caused by the B-034 day mapping)
- severity: high (wrong dates for payrolls, ISM, CPI and claims; I time bond-ETF trades around these)
- evidence:
  - `GET /api/market-context` `calendar.events` lists:
    - Nonfarm Payrolls and Unemployment Rate on 2026-11-07, a **Saturday**, at 07:30;
    - Initial Jobless Claims on Fri 11-06 at 07:30, though claims come out on Thursdays at 08:30;
    - ISM Manufacturing PMI on Tue 11-03 at 09:00 (the actual release is Mon 11-02 at 10:00);
    - CPI on 11-10 at 07:30.
  - Raw Nasdaq, through `MacroProvider()._client`:
    - the `date=2026-11-07` query returns payrolls with `gmt` "08:30", and `date=2026-11-03` returns ISM at "10:00";
    - so in winter the feed's clock is New York time. It is not the "09:30" that the comment above `NASDAQ_TZ` predicts, and the fixed UTC−4 conversion takes an hour off every row.
  - The date shift: `_nasdaq_days` on the raw answers for queries 11-01 to 11-09 places:
    - the `2026-11-02` (Monday) answer, a single "OPEC Meeting" row, as Monday's own day, because of the "Monday with releases" rule;
    - every later answer as its own day too, because `own_prev` carries forward.
  - So Redbook (a Tuesday release) lands on Wed 11-04, MBA mortgage applications (Wednesday) on Thu 11-05, and payrolls on Sat 11-07.
- suggestion:
  - Convert `gmt` as New York local time, or detect the feed's offset from a known anchor such as payrolls at 08:30.
  - Don't let a Monday answer that has only a non-economic row (OPEC, a Fed speaker) start an own-day chain.
  - Add a sanity check: an economic release can't land on a Saturday or Sunday.
  - Add a test with this week's answers.

### 2. Declared dividend raises don't reach the income figures: ABBV (+5.2%) and XOM (+3.9%) are still projected at the old amounts, including XOM's announced 11-16 ex-date
- kind: bug (related to B-064)
- severity: medium (the dollar amount is small, but "who raised and by how much" is the main question for an income book after earnings week)
- evidence:
  - `GET /api/portfolios/loop-income/dividends`:
    - ABBV: `rate 6.92`, `last_amount 1.73`, next ex-date 2027-01-15 (announced);
    - XOM: `rate 4.12`, next ex-date 2026-11-16 (announced), projected at `per_share 1.03` (≈ $22.66).
  - `GET /api/research/ABBV` news: "AbbVie Stock Hits a Record After a 5.2% Dividend Raise…" (11-01).
  - `GET /api/research/XOM` news: "Exxon Just Raised Its Dividend By 3.9%…" (11-01).
  - Forward income is understated by about $9.64 a year: ABBV 17 × (7.28 − 6.92) = $6.12, and XOM 22 × (4.28 − 4.12) = $3.52.
  - Nowhere in Argus (Dividends table, Coming up, brief, stock page) says a holding just raised its dividend.
- suggestion:
  - When a declared amount is available for an announced ex-date, use it for that event and for the annual rate.
  - Add a "Last raise" column (date and %, from payment history; B-064), so a raise shows once it's paid even without a declared amount.
  - Flag "raised this week" in the brief.

### 3. ABBV's card silently switched windows after the report: EPS through Q3 (Yahoo $5.82, P/E 82 → 50.7) next to a 189.8% payout and margins and FCF through Q2
- kind: bug (related to B-062 and B-124)
- severity: medium (a client sees a 190% payout next to EPS that implies 119%)
- evidence:
  - `GET /api/fundamentals/ABBV` now returns `eps_ttm 5.82` and `pe_ttm 50.67` (source `yahoo`), with `sec.ttm_quarters: null`. The provider was ahead of SEC, so the `provider_ahead_of_sec` path dropped SEC's window.
  - Last round the same card read EPS $3.54 and P/E 82.1 (SEC, through 06-30).
  - `payout_ratio_pct` is still 189.83 (Finnhub), but 6.92 ÷ 5.82 = **118.9%**.
  - `fcf_ttm` (SEC) and `fcf_ttm_quarters` still run through 2026-06-30. Operating margin 26.2% and net margin 9.8% are now labeled `finnhub` and are identical to last round's SEC Q2 figures.
  - /t/ABBV shows "EPS (TTM) $5.82 Yahoo", "P/E 50.7 Yahoo" and "Payout ratio 189.8%" in the same panel, and nothing gives the quarter each one runs through.
  - XOM switched the same way: EPS 9.72 (Yahoo), against 7.77 last round.
- suggestion:
  - Show "through <quarter>" beside the EPS, P/E and payout figures.
  - Recompute payout as rate ÷ the EPS shown, or hide Finnhub's figure when it disagrees by more than 20 pp.
  - Long term, the FCF payout of B-070.

### 4. ABBV's 10-30 report is missing from its earnings history, though the Events card and the brief have it; the next report is Feb 3 on the stock page and Feb 2 in the portfolio
- kind: bug (related to B-088 and B-045)
- severity: low
- evidence:
  - `GET /api/earnings/ABBV` `reports[0]` is the 2026-06-30 quarter. There's no row for the quarter to 09-30, so no Q3 EPS result and no reaction (+1.41%).
  - `GET /api/brief/loop-income` `earnings_recent` and `/api/portfolios/loop-income/earnings` both have ABBV on 10-30, with `epsActual 3.82` against 3.823 and revenue $17.40B against $17.66B.
  - /t/ABBV shows "Fri, Oct 30 · Reported" in Events, but the Reported financials table starts at 2026-06-30.
  - Next report dates: `/api/earnings/ABBV` `next.date` is 2027-02-03 (amc), and `/api/portfolios/loop-income/earnings` `next.date` is 2027-02-02.
  - XOM's `/api/earnings` also has no Q3 row.
- suggestion: add an estimate/actual/reaction row once the report is out, before SEC has the 10-Q (revenue can stay "–"), and take `next` from a single source.

### 5. First risk load of the session: 61.6 s (23.4 s last round)
- kind: perf (B-026)
- severity: medium
- evidence:
  - `curl -w %{time_total}` on `GET /api/portfolios/loop-income/risk`, the first call after the restart: **61.62 s**.
  - In the same minute, dividends took 0.18 s, drift 0.26 s, performance 1.34 s and the cold brief 6.55 s.
  - Past first loads: r008 30.8 s, r009 23.4 s.
- suggestion: warm risk (1 year of history for the held symbols) in the background at startup, as B-026 proposes, and log what the cold path waits on.

### 6. Bond sleeve: with the 10-year down 35 bp in a month, Argus still can't say what that did or would do to my 35% in bond ETFs
- kind: feature (B-017, new evidence)
- severity: medium
- evidence:
  - The yield curve: the 10-year is 4.94% against 5.29% on 09-30, and the 2-year 4.56% against 4.88%.
  - The /analysis stress table has only historical replays plus "SPY falls 10% (via beta)", which gives −1.3%. Bond ETFs get beta 0.07–0.15 there, so a rate move barely registers.
  - Look-through shows "Unclassified 34.7%" for BND, VCIT, VGIT and SCHP.
  - The brief's `near_52w_extremes` still flags all four bond ETFs as within 2.5–2.9% of their 52-week lows, even after the rally.
- suggestion: as B-017. Add a "Rates ±100 bp" scenario using duration from the N-PORT maturities, and a "Bonds" asset class.

### 7. On a weekend or a Monday, the calendar has no Friday actuals: it starts on "yesterday", a Saturday
- kind: ux (a B-034 follow-up)
- severity: low
- evidence:
  - Sunday 21:15 ET: `calendar.all_events[0]` is 2026-10-31 (Atlanta Fed GDPNow), and nothing is dated 10-30.
  - 10-30 carried ECI, personal income and spending, and Chicago PMI, which B-116 just added for this purpose.
  - On Monday morning they'll still be missing, because "yesterday" is Sunday.
- suggestion: start the window on the previous trading day, not the previous calendar day.

### 8. Fear & Greed scores "S&P 500 0.0% below its 125-day average" as Extreme fear (9.3)
- kind: ux (related to B-036)
- severity: low
- evidence:
  - `fear_greed.components[0]`: score 9.3, detail "S&P 500 0.0% below its 125-day average".
  - From `GET /api/history/^GSPC?period=1y`, the last close is 7580.07 and the 125-day mean is 7582.74, a gap of −0.04%, so the detail is correct.
  - A flat reading scores near the bottom of the scale, and the page doesn't explain why (percentile against what history?).
- suggestion: show the basis in the detail ("0.0% below; lowest X% of the last N years"), or use a gap that leaves 50 for a flat market.
