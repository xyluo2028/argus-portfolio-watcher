# Round 018: trader (trading day, session 2026-11-16)

## Account
From `python scripts/sim.py status` after the trade, valued at the 11-16 close:
- Account value **$9,933.04**, return since the start **−0.67%**.
- SPY from my 11-13 fill (752.66) to the 11-16 close (739.95) is **−1.69%**, so the account is about 1.0 pp ahead of SPY.
- Cash **$1,200.11** (12.1%), invested $8,732.93, no dividends accrued, realized P&L $0.

| Symbol | Qty | Avg cost | Close | Value | % of account |
|---|---|---|---|---|---|
| SPY | 4.6501 | 752.66 | 739.95 | $3,440.84 | 34.6% |
| ADBE | 4.9821 | 240.86 | 246.00 | $1,225.60 | 12.3% |
| XLV | 6.377 | 188.175 | 187.88 | $1,198.11 | 12.1% |
| META | 1.5764 | 634.35 | 626.41 | $987.47 | 9.9% |
| LNG | 3.234 | 309.21 | 305.20 | $987.02 | 9.9% |
| TMUS | 5.2579 | 171.17 | 170.01 | $893.90 | 9.0% |

House rules: no stock is above 25%, and the index ETF is at 34.6% (limit 50%). I hold 6 positions (4 to 10 allowed), with no leverage. Every position has a thesis note (ids 1–6).

## What I did
**Market (`/api/market-context`, 11-16):**
- The S&P 500 fell 1.9% and the Nasdaq 100 2.7%. XLK fell 3.2%, is down 10.2% over 1M, and is below its 50-day and 200-day averages.
- Fear & greed is **11.8 ("Extreme fear")**; every component reads fear, and the VIX is 22.9.
- 10y yield 5.12%; the 10y−2y spread is +29 bp.
- Breadth, once the universe had built: 139 advancers vs 360 decliners. 63% of stocks are above their 50-day average. There were 21 new highs, all defensive (LLY, JNJ, COST, KO, PG, MO…), and 7 new lows (NFLX, BA, COIN…).
- In short, a defensive rotation inside a tech sell-off.
- Calendar: retail sales and industrial production are due 11-17. NVDA reports 11-17 after the close, the FOMC minutes are 11-18, and INTU reports 11-20.

**Holdings:**
- ADBE rose 1.2% against the tape.
- META fell 2.4%, LNG 1.1% and XLV 0.5%.
- No news or events broke any thesis.
- The nearest events are ADBE earnings on 12-09 and META earnings on 01-26. No exit alert fired.

**Ideas:**
- I screened for quality value: cap > $20B, P/E 5–20, revenue growth > 8%, op margin > 20%, FCF yield > 5%, ROE > 15. It returned 4 names: ADBE (held), TMUS, TPR and INCY.
- **INCY was rejected.** The screener's FY2025 figures look great, but its Q3 2026 shows a $785M loss, TTM P/E is 64 and it is rated hold (see finding 3).
- **TMUS was picked.** Research and fundamentals:
  - P/E ttm 16.4, the **5th percentile** of its own 5-year range; forward P/E 11.9.
  - FCF $18.7B ttm (FCF yield about 10%); dividend 2.4%, with a $1.02 ex-dividend on 11-25.
  - Revenue +7–11% YoY for 3 quarters; Q3 EPS beat by 8%.
  - FY+1 EPS consensus rose over 90 days; analysts rate it 24 buy / 4 hold, with a mean target of 225.
  - 1y daily beta to SPY about −0.34, which I computed from Argus history.
  - The stock is down 21% over 1Y and below its 200-day, but back above its 50-day.

**Trade** (filled at the 11-16 mid, thesis note id 6 written first):

| Trade | Fill | Reason |
|---|---|---|
| BUY 5.2579 TMUS ($900) | 171.1701 | Defensive value in an "Extreme fear" tape: cheapest P/E in 5 years, ~10% FCF yield, low beta to the tech-heavy core. Sized at 9%. |

**What I didn't do:**
- **No NVDA yet.** It reports 11-17 after the close, so a fill at the 11-17 mid would come before the reaction. I keep about 12% cash to decide at the 11-18 session.
- **No SPY add.** Breadth is still deteriorating and fear readings can stay extreme; I'd rather add once the S&P stabilizes.

**Alert set:** TMUS at or below $150. TMUS is on the `candidates` watchlist.

## Last round's changes
- **B-053 (benchmark from the first day's fills): works.**
  - Before my trade, the Dashboard tile read **−1.19% / −1.91%, "day change"**, i.e. SPY's plain day change on a session with no buys, as promised.
  - The chart's SPY line starts at +0.23% on 11-13 and ends at −1.69% (= 739.95 / 752.66 − 1, checked).
  - Excess return is +0.92% on invested money.
  - After my buy, the tile switches to a blended SPY figure; see finding 1.
- **B-106 (the brief reads every named watchlist): works and helped.**
  - `watchlist_earnings.upcoming` lists NVDA (11-17, amc) and INTU, each with its list name.
  - `watchlist_movers` shows NVDA −4.12% (on `candidates`).
  - NVDA hasn't reported yet, so I can't check the move to `recent` until next round.
- **B-021 labels: work.**
  - ADBE stock page: "Beta (5y monthly) 1.46, Finnhub, 5y monthly vs S&P 500".
  - Risk card: "Beta vs SPY · 1y daily 0.63"; the API's `beta_basis` is "Argus, vs SPY, 252 daily returns (1y)".
  - Per-position β: ADBE 0.16, LNG −0.45.
  - The SPY −10% row says "(each holding's 1y daily beta vs SPY)".
  - The factor Market row says "all US stocks minus T-bills, with the other factors; not the beta vs SPY".
  - Now I can tell which beta my LNG hedge thesis rests on.
- **B-168 (cash): still open, as expected.**
  - After my buy, the Dashboard total reads $8,732.93 against an account of $9,933.04.
  - The Dashboard shows SPY at 39.4% (34.6% of the account) and TMUS at 10.2% (9.0%).

## Findings

### 1. After a same-day buy, the Dashboard's "SPY, last session" is a blended number that matches no SPY move
- kind: ux
- severity: medium
- evidence:
  - The Dashboard tile "Portfolio vs SPY, last session" read −1.19% / **−1.91%** before my TMUS buy. After the buy it reads −1.14% / **−1.77%**, with the caption "day change; today's buys from the fills, SPY alike".
  - SPY's day was −1.91% close to close and −0.54% from mid to close; nothing on any page says −1.77%.
  - I reproduced it: (7,933.30 × −1.9115% + 900 × (739.95 / 743.945 − 1)) / 8,833.30 = **−1.771%**. That is a money-weighted SPY shadow of my flows.
  - It is defensible, but it is labeled "SPY". Next to the Holdings row "SPY −1.91%" it reads like a wrong quote.
  - Same family: TMUS's Holdings "Day %" reads −0.68% (fill to close) while the stock rose 0.04% (B-162).
- suggestion: when buys enter, label the figure "SPY, same flows" (or show "SPY −1.91% · same flows −1.77%"), so the plain index day change stays visible.

### 2. The stock-page chart and `/api/history` stop at 11-13 hours after the 11-16 close; the header says 11-16
- kind: bug
- severity: medium
- evidence:
  - At about 02:15 UTC on 11-17, `/api/history/ADBE?period=1mo` and `/api/history/TMUS?period=1y` both end with the 11-13 bar. SPY's does too.
  - `/t/ADBE`: the header reads "246.00 · close Mon, Nov 16", and the 1D chip reads +1.2%. But the chart's last candle and its OHLC readout are 11-13 ("O 240.35 H 243.78 L 237.94 C 243.08"), and the price tag 246.00 floats beside a missing candle. `/t/TMUS` likewise ("C 169.95" under a 170.01 header).
  - Performance and risk already fill the session from quotes (`closes_from_quotes: {date: 2026-11-16}`), and momentum returns are right: ADBE 1W 246.00 / 237.32 = +3.66%, the card shows +3.7%.
  - Only the chart and the raw history miss the day. So any beta or return I compute from `/api/history`, such as my TMUS 1y beta, silently ends a session early.
- suggestion:
  - append a provisional bar for the last completed session from the quote (open, high, low, close), flagged `provisional: true`, until Yahoo's bar arrives, the same way B-134/B-142 fill it;
  - give the chart readout a date so a stale bar is visible.

### 3. The screener passed INCY as "quality" on FY2025 figures while its latest quarter lost $785M (B-019, new evidence)
- kind: bug
- severity: medium
- evidence:
  - `POST /api/screener` (op margin > 20, ROE > 15, P/E 5–20, FCF yield > 5) returns INCY at **P/E 19.1, op margin 29.5%, ROE 22.8%** (`fiscal_year: 2025`).
  - `/api/fundamentals/INCY` gives P/E ttm **64.0**, op margin **10.4%** and ROE **7.1%**.
  - `/api/research/INCY` growth shows Q3 2026 net income **−$785M** and op margin **−45.5%**.
  - 1 of my 4 hits fails every filter on trailing numbers. The screener rows carry no year label.
- suggestion: as B-019 says, screen on TTM from the SEC quarters (or add TTM columns next to the FY ones) and label the FY columns "FY2025".

### 4. An earnings date moved a day with no sign it changed (INTU 11-19 → 11-20)
- kind: feature
- severity: low
- evidence:
  - Last round, the brief and `/api/events` listed INTU earnings on **2026-11-19** (r017 trader report and summary).
  - Today, `/api/events?days_ahead=21` and the brief's `watchlist_earnings` say **2026-11-20** amc. There is no note, no "moved" marker, and no previous date.
  - For a name I'm planning to trade around, a silent one-day shift changes which session's fill comes before the report.
- suggestion: keep the last date seen per event, and show "moved from 11-19" on events, the brief and Coming up when it changes; optionally add an `earnings_date_changed` alert.

### 5. The brief still omits a holding's announced ex-dividend that Coming up shows, and Coming up marks it "≈" (B-136, B-125 still open)
- kind: bug
- severity: low
- evidence:
  - After buying TMUS, the Dashboard's Coming up (next 14 days) lists "Wed, Nov 25 · TMUS · Ex-dividend · **≈ $5.36**".
  - `/api/events` has it as `source: yahoo` with no `estimated` flag. It's announced, so "≈" is wrong.
  - `/api/brief/bot0-sim` returns `dividends_upcoming: []`, because the 11-25 date is 9 days out.
- suggestion: give the brief the same 14-day window as Coming up (or say its window in the payload), and drop "≈" when `estimated` is false.

### 6. The brief's first load after the session closed took 5.6 s (B-026)
- kind: perf
- severity: low
- evidence:
  - First `/api/brief/bot0-sim` of the round: **5.65 s**. Later calls took 0.08 s.
  - `/risk` 0.90 s, `/api/events?days_ahead=21` 0.78 s, `/api/research/INCY` 1.6 s.
  - Much better than earlier rounds, but the brief is my first call every round.
- suggestion: warm the brief (and risk) for each portfolio when a session closes.

## Summary for the round lead
- **Account:** $9,933.04, −0.67% since the start, vs SPY −1.69% from my fill.
- **Trade:** BUY 5.2579 TMUS at 171.1701 ($900, defensive value). I'm holding 12% cash for NVDA's 11-17 report.
- **Top finding:** after a same-day buy, the Dashboard's "SPY, last session" shows a blended −1.77% that matches no SPY move (the real day change was −1.91%).
