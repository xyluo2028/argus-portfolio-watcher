# Round 006: multibagger (growth) investor

## What I did
- **Timing:** about 02:14 to 02:40 UTC Tue 2026-10-27 (Mon 10-26, about 22:15 ET). The market was closed, so prices are the 10-26 close plus post-market quotes.
- **Book before trading** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost $95,500.05, value **$94,203.18**, unrealized −$1,296.87.
  - Day P&L on 10-26 was **+$855.97**, which equals the performance series change (93,347.20 → 94,203.17).
  - IWM was +0.45% on the day.
- **RMBS reported Q3 on 10-26 after the close. My exit rules (note 43) were due today.**
  - Argus's SEC statements already had Q3 the same evening, with `latest_period` 2026-09-30, `stale: false`:
    - Revenue was **$218.29M, +22.3% y/y**. The last three quarters went +8.1%, +20.4%, +22.3%, so growth is re-accelerating.
    - Operating margin was **38.3%**, against 35.4% a year ago. FCF TTM is $312.9M.
  - EPS was 0.84 adjusted against 0.80 expected. Revenue beat by 0.4%.
  - The only word on guidance was headlines in Research → News ("in-line Q4 guidance", "muted guidance"). The stock was −0.6% after hours.
  - Exit rule check: revenue growth was well above 12%. I couldn't check the product-revenue rule in Argus (finding 6). **Thesis intact.**
- **Trade:**

  | Action | Shares | Price | Amount |
  |---|---|---|---|
  | **BUY RMBS** | **25** | **$90.32** (10-26 close, the current quote) | $2,258.00 |

  - Why: the print resolved my main uncertainty. Growth re-accelerated and margins expanded, at 24× forward EPS, with the price 36% below the mean target.
  - The position is now 121 shares at an average of $92.98, a cost of $11,251.17. That's 11.25% of capital, under the 15% cap.
  - Thesis note 46 sets new exit rules (growth under 12%, or operating margin under 32% for two quarters) and says no more adds. Note 43 is archived.
- **Hunt** (`POST /api/screener`, with the universe built: 5,354 companies, FY2025):
  - **Screen D:** market cap $0.5–12B, growth ≥20%, gross margin ≥50%, FCF yield ≥3%, operating margin ≥5%, liabilities/equity ≤1.5. It returned 8 names, two of which I already hold (PODD, HRMY).
  - **Screen E:** market cap $0.5–8B, growth ≥30%, gross margin ≥40%, operating margin ≥3%, FCF margin ≥3%, P/S ≤6. It returned 8 names.
  - I researched six names (`/api/research`, 1.4–1.8 s each):
    - **HIMS:** operating margin is now −12.9%, and insiders sold $17.7M.
    - **LQDT:** quarterly growth has slowed to +8%. P/E is at the 100th percentile of its own history.
    - **HROW:** operating margin −15.6%. 23% of the float is short.
    - **CELH:** growth was acquisition-driven and organic growth has slowed to +10.6%. Insiders did buy $3.2M at about $28.
    - **VIAV:** growth was acquisition-driven, and insiders sold $62M with no buys.
    - **MNTN:** the one I liked.
  - **MNTN** (CTV performance ads):
    - Market cap $703M, P/S 2.3, gross margin 81%.
    - Revenue grew +20.6% in Q2. Operating margin has turned positive (8.6–13%).
    - No debt, and insiders own 19.5%.
    - Its P/E of 12.8 is flattered by a tax item in Q4-25, where net income was $34.5M against operating income of $20.5M.
  - I added MNTN to the `growth-candidates` watchlist with note 47. It reports 11-04, and I'll buy a 4–6% starter only if Q3 confirms: growth ≥20% and operating margin ≥10%.
- **Rest of the book:**
  - No news broke any thesis. GRND −4.1% and TOST −1.8% on the day were price moves, not thesis breaks.
  - KRYS reports 11-02 and TOST 11-03. Seven more holdings report 11-04 or 11-05. ESE reports 11-19.
- **After the trade:**

  | Cost | Value | Unrealized | Cash | Return to date |
  |---|---|---|---|---|
  | **$97,758.05** | **$96,461.18** | −$1,296.87 | **$2,241.95** | (96,461.18 + 2,241.95 − 100,000) ÷ 100,000 = **−1.30%** |

## Last round's changes
- **B-068 (volatility and Sharpe from too few sessions): works.**
  - `/performance` returns `volatility_pct: null`, `sharpe: null` and `risk_note: "needs 20 sessions, has 5"`.
  - The dashboard shows "Volatility (ann., 5 sessions) · needs 20 sessions, has 5". Clear.
- **B-025 (Day % base and brief movers): works as designed, but see finding 3.**
  - `top_gainers` has 5 entries, all positive. `top_losers` has exactly the 3 names that fell (GRND, TOST, TMDX), not padded.
  - After my evening buy, RMBS's Day % became 448.32 ÷ (96 × 85.65 + 25 × 90.32) = **4.28%**. That agrees with its Day P&L, but it's no longer the stock's move (+5.45%).
- **B-074 (dividends on ex-dates):** I hold no payers, and `dividends_accrued` is 0 as expected. Not exercised.
- **SEC pickup of RMBS Q3 (B-056 and B-073 watch): works and helps.**
  - Q3 and the previously missing Q2 are both in the statements the same night. FCF TTM is "SEC, 4Q to 2026-09-30".
  - The valuation card around it didn't move to the new quarter (finding 1).
- **Still open:**
  - **B-061:** the RMBS revenue chart now shows "218.29M" without clipping, but the axis and value labels are still drawn about twice the table font. A floating "218.29M" sits above the last bar.
  - **B-045 timing:** "Coming up" shows a plain "Earnings" for 7 of 9 holdings, although `/api/earnings` has `bmo` for HRMY, PODD and LOAR.
  - **B-051:** RMBS at 90.32 is below the 100.00 low target, and the price dot sits on "low 100.00".
  - **B-002:** at 390 px, the dashboard Holdings table shows only # / Symbol / Name. Qty, price and P&L are cut off.
  - **B-049:** the 22:17 ET buy is dated **2026-10-27** in the /t/RMBS "Your position" list, but 10-26 in the performance series.

## Findings

### 1. After a print, the stock page's valuation card is a quarter behind the SEC table under it, and FCF margin mixes the two windows (RMBS)
- kind: bug
- severity: medium (new evidence for B-009 and B-079; this is the case where it matters most)
- evidence:
  - /t/RMBS and `GET /api/fundamentals/RMBS` after the Q3 report. The Reported financials table on the same page already has Q3 at $218.29M.
  - The card still uses Q2:

    | Field | Card (source) | From SEC quarters on the same page |
    |---|---|---|
    | Revenue (TTM) | **$756.33M** (Yahoo, through Q2: 207.385 + 180.189 + 190.244 + 178.513) | **$796.11M** |
    | Revenue growth, latest quarter | **+20.4%** (Finnhub, Q2) | **+22.3%** (Q3) |
    | EPS (TTM) | $2.18 (Yahoo) | diluted 0.69 + 0.61 + 0.55 + 0.58 = **$2.43** |
    | FCF margin | **41.4%** | 312.93 ÷ 796.11 = **39.3%** |

  - The FCF margin divides the SEC FCF through 2026-09-30 by the Yahoo revenue through 2026-06-30.
  - P/E (39.9) and P/S (12.6) also sit on the old window.
  - Earnings night is exactly when I decide to add or exit, and the headline numbers lag the table directly below them.
- suggestion:
  - When SEC's `latest_period` is newer than the provider's window, compute TTM revenue, latest-quarter growth and FCF margin from the SEC quarters. Or at least use the same window for the FCF numerator and denominator.
  - Mark lagging provider fields "as of Q2".

### 2. MNTN's latest report (Q2, a 48% EPS miss) vanished from `/api/earnings` and the stock page within minutes
- kind: bug
- severity: medium
- evidence:
  - My first `GET /api/earnings/MNTN` (about 02:16 UTC) returned a 2026-06-30 report: date 2026-08-04, EPS estimate 0.1931, actual 0.10, reaction +3.78%.
  - Three later calls (02:2x, after I added MNTN to a watchlist) return reports starting at 2026-03-31. The Q2 report is gone.
  - On /t/MNTN, the 2026-06-30 row of Reported financials now has blank EPS estimate, actual, result and reaction.
  - The stored events (read-only look at `event`) still have Finnhub's `eps_result` for 2026-06-30 (0.10 vs 0.1931).
  - There's no `earnings` row for 2026-08-04, and Yahoo's `eps_report` list skips 08-04.
  - `EventsService.refresh` deletes the symbol's whole ±100-day window before re-inserting. My guess is that the refresh after the watchlist add replaced a calendar response that included 08-04 with one that didn't, so the most recent past report was dropped.
  - The quarter that vanished is the one that tells me MNTN missed.
- suggestion:
  - Don't delete past `earnings` rows that have an `epsActual` when a refresh no longer returns them. Only replace future dates.
  - Or join `eps_result` to the statement row by period even when no report date is known.

### 3. A buy after the close at the closing price changes the day's portfolio return and TWR, and the brief now misstates the stock's move
- kind: bug
- severity: medium
- evidence:
  - The book is the same before and after my 22:17 ET buy of 25 RMBS at the close price of 90.32. Day P&L stays +$855.97 and gain stays −$1,296.87, but:
    - **Header and dashboard "last session":** +0.92% became **+0.90%** (855.97 ÷ 95,605.20 instead of ÷ 93,347.20). "Portfolio vs IWM, last session" now reads +0.90% vs +0.45%.
    - **Performance TWR (all):** −1.358% became **−1.379%**, and excess return −1.797% became −1.818%. Recomputed: (1 − 0.022543) × (1 + 855.97 ÷ 95,605.20) − 1 = −1.379%. So the flow is treated as invested at the prior close, although the shares earned nothing that day.
    - **Brief `top_gainers` and the holdings Day % column:** RMBS **+4.28%**, while the stock closed **+5.45%** (quote, chart 1D, peers table).
  - A pure cash-flow event changed three performance figures and one stock fact.
- suggestion:
  - In daily TWR, treat a flow at or after the close as end-of-day (Modified Dietz weight 0), and don't change the session's portfolio Day %.
  - In the brief, report the stock's own `change_pct`. Use the position's blended figure only for P&L.

### 4. Valuation bands include pre-IPO or garbage points (MNTN P/S 0.019, P/B 0.020) that skew the percentile
- kind: bug
- severity: medium
- evidence:
  - `GET /api/research/MNTN`, `valuation`. MNTN listed on 2025-05-22.

    | Band | Points | Current | Percentile shown |
    |---|---|---|---|
    | `psTTM` | **0.019** (2025-06-30), **0.032** (2025-09-30), then 3.01, 2.17, 2.17 | 2.31 | **80** |
    | `pb` | 19 points back to 2021 (years before the listing), including **0.118, 0.020, 0.033** | 2.17 | **84** |

  - Without the bad P/S points, 2.31 sits between 2.17 and 3.01, which is about the 67th percentile.
  - The "cheap vs own history" read is the reason I use these bands, and for a recent IPO it's wrong.
- suggestion:
  - Drop points dated before the listing date (the company profile already has "Listed since 2025-05-22").
  - Drop points more than 20× below the median.
  - Show the point count next to the percentile.

### 5. Revenue guidance and segment revenue aren't anywhere in Argus, so I couldn't test my own exit rule
- kind: feature
- severity: medium
- evidence:
  - My RMBS exit rule (note 43) was "product (chip) revenue falls q/q with a guide below consensus".
  - `/api/financials`, `/api/earnings` and `/api/research` have total revenue only. There's no product/royalty split and no next-quarter guidance.
  - The only guidance signal was two headlines ("in-line Q4 guidance", "muted guidance outlook").
  - The decision it would change: with a weak product line or a guide below consensus, I would have held instead of adding.
- suggestion:
  - Show the 10-Q's segment revenue (`srt:ProductOrServiceAxis` or segment facts from the filing XBRL) as extra statement rows.
  - Put next-quarter consensus next to the reported quarter (the estimates trend `0q` is already fetched), so "guide vs consensus" has an anchor.

### 6. News tone calls the RMBS earnings night 10 positive, 0 negative, while the headlines say "falls" and "slip"
- kind: bug
- severity: low (related to B-059)
- evidence:
  - `GET /api/research/RMBS` gives `news_tone` {positive 10, neutral 7, negative 0}. Per article:
    - "Rambus (NASDAQ:RMBS) Q3 Beat Meets In-Line Q4 Guidance as Shares Slip" is scored **positive** (3 / 0).
    - "Rambus falls despite earnings beat on muted guidance outlook" is **neutral** (2 / 2).
  - Five of the "positive" articles are about other companies (Verizon/Welltower, Netlist, Cadence, Micron).
  - The stock fell after hours on the guide, and the tone says nothing negative happened.
- suggestion:
  - Add price-direction words (falls, slips, slides, muted, cut) to the negative lexicon.
  - Count only articles whose headline names the company (B-059).

### 7. The whole Momentum column is a session stale, and "6 months" is 8.7 pp off the chart (B-083, wider than "1 week")
- kind: bug
- severity: low
- evidence:
  - /t/RMBS on a +5.45% day.

    | Period | Momentum column (Finnhub) | Chart button (`/api/returns/RMBS`, anchored 10-26) |
    |---|---|---|
    | 1 week | −7.6% | 5D −2.5% |
    | 3 months | −10.8% | −5.9% |
    | 6 months | **−34.3%** | **−43.0%** (158.40 → 90.32) |
    | Year to date | −6.8% | −1.7% (91.89 → 90.32) |
    | 1 year | −15.7% | −14.3% |

  - Finnhub's YTD equals the **10-23** close (85.65 ÷ 91.89 = −6.8%). Only "1 month" (−14.1%) is current, because Argus computes it.
- suggestion: compute every momentum row from `/api/returns` bases (already anchored on the last session), and drop the Finnhub rows.

### 8. The screener's FY2025 margins and growth misled again: LQDT, HROW and HIMS (B-019)
- kind: feature
- severity: medium
- evidence:
  - Screen E hits compared with the SEC quarters in Research:

    | Symbol | Screener (FY2025) | Recent SEC quarters |
    |---|---|---|
    | **LQDT** | growth +31.2% | +8.1%, +3.7%, −0.9% |
    | **HROW** | operating margin +11.2% | −15.6% (Q2-26), −50.0% (Q1-26) |
    | **HIMS** | operating margin +4.5% | −12.9% in both of the last two quarters |

  - That's 3 of 8 hits. It's the fifth round in a row, and each one costs a research call to rule out.
- suggestion: add "latest-quarter revenue growth" and "TTM operating margin (SEC)" fields to the screener. Research's `growth.quarters[]` already computes both.

### 9. The stock page says "Not held in loop-growth" while the position is loading, above that position's own buys
- kind: ux
- severity: low
- evidence:
  - `scripts/screenshot.py /t/RMBS` with the default 2 s settle: the Your position card reads "Not held in loop-growth.", yet lists Buy 96 @ 93.68 and Buy 25 @ 90.32 directly beneath.
  - With `--settle 12` it shows 121 shares, $10,928.72.
  - On a slow load, a holder briefly reads that they don't own the stock.
- suggestion: show "Loading…" until the portfolio response arrives. Say "Not held" only when it's known.

## Summary
1. **Bought 25 RMBS at $90.32** after its Q3 print (revenue +22.3%, operating margin 38.3%). It's now 121 shares at $92.98, 11.25% of capital. MNTN is watchlisted with note 47 for its 11-04 report. Cost $97,758.05, value $96,461.18, **cash $2,241.95**, return to date −1.30%.
2. **Last round's fixes:** B-068 works. B-025's mover lists work, but an after-close buy now distorts the day %, TWR and the brief's RMBS move (finding 3). SEC picked up RMBS Q3 the same night.
3. **Top new findings:**
   - The valuation card lags the SEC table by a quarter after a print.
   - MNTN's Q2 report vanished from earnings.
   - The after-close buy distorts the performance figures.
   - Pre-IPO points skew the valuation bands.
   - There's no guidance or segment revenue.
