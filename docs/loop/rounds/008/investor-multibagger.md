# Round 008: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:45 UTC Thu 2026-10-29 (Wed 10-28, about 22:15 ET). The market was closed, so prices are the 10-28 close plus post-market quotes.
- **Book** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost $97,758.05, value **$95,184.29**, unrealized −$2,573.76.
  - Day P&L **+$382.39 (+0.40%)** against IWM's +0.40%.
  - INOD bounced +6.5% (44.74 → 47.65). TMDX was the biggest loser at −4.06% (−$350.92), now −7.4% on cost and −45% YTD.
  - Post-market the book is −$880 (−0.92%). Most of that is RMBS at 88.40 (−2.9%) and KRYS at 317.20 (−1.3%).
- **Performance reconciles:** the 10-28 series point minus the 10-27 point is 95,184.29 − 94,801.90 = 382.39, which equals Day P&L. TWR is (1 − 0.030857) × (1 + 382.39 ÷ 94,801.90) − 1 = −2.695%, which equals `twr_pct`. The IWM leg also compounds correctly to +1.998%.
- **INOD:** I'm holding to the 11-05 print under the exit rules in note 49. One new fact from Argus helps: the Q3 consensus on the Reported financials header is **revenue $84.99M**.
  - That's −7.8% from Q2's $92.14M but +35.9% from Q3-25's $62.55M. So the Street already models a step down, and my exit line (growth under 25%, which means under $78.2M) sits below consensus.
- **TMDX:** on watch under note 41. It reports 11-05, and the exit rule (Q3 growth under 15%) stands.
  - Research → Growth shows quarterly growth slowing: 37.7 → 32.2 → 32.2 → 21.2 → 20.7%.
  - The cheap-looking P/E band (15.3, 11th percentile) depends on Q4-25 net income of $105.4M, a tax item (B-071).
- **Hunt** (`POST /api/screener`, universe built, 5,351 companies, FY2025, each call took under 0.01 s):
  - **Screen A:** market cap $0.5–8B, growth ≥25%, gross margin ≥50%, FCF margin ≥10%, P/S ≤10, liabilities/equity ≤1.5. It returned 9 names.
    - **KVYO** (Research, 3.5 s): **pass.** Growth is slowing from 34.0% to 26.4% over six quarters, it still has a GAAP operating loss, consensus has next fiscal year at +19.5%, and insiders sold $190M against $0.3M bought.
  - **Screen B:** market cap $0.3–6B, growth ≥20%, operating margin ≥15%, ROE ≥15%, P/E 5–30, liabilities/equity ≤1.5. It returned 8 names.
    - **PSIX** (screener: growth +51.8%, P/E 9.8): **pass.** The latest quarter is **−20.5%** and the one before −5.1%. The FY2025 screener figure hides the downturn (B-019 again).
    - **AUPH** (P/E 8.0, operating margin 37%, a $25M insider buy): **pass for now.** Forward growth is 13.8%, 11.1% and 17.6%, under my 20% floor. The P/E and the 100.8% net margin on Peers both come from Q4-25's $210.8M tax-driven net income.
- **Trades: none.** No thesis broke today, the next 8 days carry 10 of my 11 earnings reports, and $2.2k of cash can't fund a real position.

  | Cost | Value | Unrealized | Cash | Return to date |
  |---|---|---|---|---|
  | $97,758.05 | $95,184.29 | −$2,573.76 | **$2,241.95** | (95,184.29 + 2,241.95 − 100,000) ÷ 100,000 = **−2.57%** |

## Last round's changes
- **B-083 (momentum from Argus's own closes): works, and it helps.** On /t/INOD the Momentum column and the chart buttons now agree to the decimal.
  - 1W/5D −21.3% (47.65 ÷ 60.56), 1M −28.7%, 3M −17.2%, 6M +13.8%, YTD −6.5% (47.65 ÷ 50.95), 1Y −36.9%.
  - `/api/fundamentals` tags these fields `argus`. TMDX YTD −45.0% = 66.90 ÷ 121.65 ✓.
- **B-009 + B-079 (valuation card on SEC's window): works where SEC has capex.**
  - RMBS shows $796.11M / EPS 2.43 / +22.3% / FCF margin 39.3%, each labeled "SEC, 4Q to 2026-09-30".
  - INOD shows $317.16M / +57.8% / FCF $183.85M, all matching the sum of the SEC quarters.
  - It **doesn't** hold when SEC capex is missing. See finding 2 (HRMY, TOST).
- **B-093 (dividends):** I hold no payers, so there was nothing to check.

## Findings

### 1. The brief's 2-day news fetch is cached and reused by Research → News for an hour, so the day's biggest movers lose 5 of their 7 days of news (TMDX and LOAR show none)
- kind: bug
- severity: medium (the stocks I most need news on get the truncated list, and nothing says so)
- evidence:
  - The cause: `EventService.news(symbol, days, limit)` caches by symbol only. The brief calls it with `days=2` for the top 3 and bottom 3 movers (`app.py` ~968). Research calls it with `days=7` (`app.py` ~1235) and gets the 2-day result back for an hour.
  - Live check, run after `GET /api/brief/loop-growth`. The oldest headline in `GET /api/research/<sym>` → `news`:

    | Symbol | In the brief's movers? | Items | Oldest |
    |---|---|---|---|
    | INOD | yes | 16 | 10-27 |
    | RMBS | yes | 13 | 10-27 |
    | HRMY | yes | 3 | 10-28 |
    | PODD | yes | 3 | 10-27 |
    | **TMDX** | yes (biggest $ loser) | **0** | none |
    | **LOAR** | yes | **0** | none |
    | KRYS | no | 5 | 10-22 |
    | TOST | no | 7 | 10-22 |
    | GRND | no | 4 | 10-22 |

  - On a −4% day for TMDX, Research → News shows nothing and `news_tone` is 0/0/0.
- suggestion: include `days` in the cache key, or cache the 7-day list and filter it to 2 days for the brief.

### 2. FCF margin still divides Yahoo's levered FCF by SEC revenue when SEC capex is missing: HRMY shows 19.0% while its SEC cash flow says about 37% (B-069, B-079)
- kind: bug
- severity: medium (a wrong headline quality metric on a holding, with no source label. Last round's fix promised "always SEC FCF ÷ SEC revenue")
- evidence:
  - `GET /api/fundamentals/HRMY`:
    - `revenue_ttm` is 959.9M (`sec`).
    - `fcf_ttm` is **182.8M from `yahoo`**.
    - `fcf_margin_pct` is **19.05** with **no source**, and `sec.fcf_ttm_quarters` is null.
  - The SEC quarters (`argus financials HRMY --json`) give 4Q operating cash flow of 92.4 + 27.8 + 126.2 + 108.7 = **$355.1M**. Capex is null for Q1 and Q2 2026 and about $0.1M in the earlier quarters, so FCF is about $355M, a **~37% margin**.
  - The screener's FY2025 SEC figure for HRMY is 40.1%.
  - On /t/HRMY, "Revenue (TTM)" carries "SEC, 4Q to 2026-06-30", while "Free cash flow (TTM) 182.84M" and "FCF margin 19.0%" carry no label.
  - TOST is the same: capex is null in every quarter, so it shows Yahoo FCF $474M ÷ SEC revenue $6.80B = 6.97%. SEC OCF over 4Q is $635M.
- suggestion: when SEC has OCF but no capex, say so: show OCF margin labeled "capex not reported", or leave FCF margin blank. Don't divide a Yahoo numerator by an SEC denominator, and label every FCF field with its source.

### 3. The brief ignores named watchlists: `watchlist_movers` is empty while DUOL is −4.3% and XZO +6.1%
- kind: bug
- severity: medium (the brief is my morning screen, and it says nothing about my candidates)
- evidence:
  - `GET /api/brief/loop-growth` returns `watchlist_movers: []`.
  - `GET /api/watchlists/growth-candidates` (my only watchlist) has DUOL at −4.32%, XZO +6.09% and BCRX +3.33%. All three pass the brief's own ≥3% rule.
  - The cause: `self.watchlist(...)` in the brief uses `DEFAULT_WATCHLIST`, and `/api/watchlists/Watchlist` is empty.
  - Since B-033, watchlist earnings are also left out of the brief. `argus events` lists PTCT (10-29, tomorrow), DUOL (11-03), MNTN (11-04) and XZO (11-04), and the brief lists none of them, even though MNTN's report is a buy trigger in note 47.
- suggestion: build `watchlist_movers` across every watchlist, or let a portfolio name its watchlist. Add a `watchlist_earnings` list, kept separate from holdings so B-033 stays fixed.

### 4. The screener's FY2025 growth keeps leading to stocks whose revenue is falling (PSIX "+51.8%" is −20.5% in the latest quarter) (B-019)
- kind: feature
- severity: medium
- evidence:
  - Screen B ranked PSIX with growth +51.8%, P/E 9.8 and ROE 56%. `GET /api/research/PSIX` → `growth.quarters` shows Q2-26 at **−20.5%** and Q1-26 at −5.1%. Consensus for this fiscal year is −6.8%.
  - In screen A, KVYO's +31.6% is really 26.4% and slowing. Last round the same happened with DUOL.
  - Three rounds running, the screener's top growth name failed on the first research call.
- suggestion: add `revenue_growth_q_yoy_pct` (latest quarter, from SEC) to the screener. Research already computes it per symbol. With that field I'd have filtered out PSIX without opening it.

### 5. A one-quarter cash windfall shows as a 58% FCF margin with no warning (INOD)
- kind: feature
- severity: low
- evidence:
  - /t/INOD: "FCF margin 58.0%, SEC, 4Q to 2026-06-30". The same card shows a net margin of 14.7% and an operating margin of 18.4%.
  - SEC Q2-26 OCF is $127.2M on $92.1M of revenue, a customer prepayment that my own thesis note mentions. Without Q2, the other three quarters give (34.8 + 10.1 + 14.7) ÷ (90.1 + 72.4 + 62.6) = **26%**.
  - This is the cash-flow version of B-071's tax-benefit problem.
- suggestion: flag FCF margin when a single quarter's OCF is above that quarter's revenue, or when FCF margin is more than twice the operating margin. A small "one quarter is X% of TTM FCF" note would do.

### 6. P/E is still not price ÷ the EPS on the card now that EPS comes from SEC (BLLN 142.7 vs 162.9) (B-095)
- kind: bug
- severity: medium (new evidence)
- evidence: `GET /api/fundamentals/<sym>`, where `pe_ttm` is from `finnhub` and `eps_ttm` from `sec`:
  - **BLLN:** P/E 142.7, but 114.00 ÷ 0.70 = **162.9** (a 14% gap).
  - **RMBS:** 35.7 vs 91.03 ÷ 2.43 = 37.5.
  - **INOD:** 35.4 vs 47.65 ÷ 1.32 = 36.1.
  - HRMY matches: 12.4 vs 12.5.
  - The B-009 fix moved EPS to SEC, which widened the gap for recent IPOs like BLLN.
- suggestion: as filed under B-095, compute P/E from the price and the EPS that's shown.

### 7. Estimate revisions contradict themselves: 7-day counts exceed 30-day counts, and "18 down" sits beside a rising consensus
- kind: bug
- severity: low
- evidence:
  - `GET /api/research/RMBS` → `estimates.revisions.0q`: `upLast7days` **5**, `upLast30days` **4**. The 0y row has 6 against 5. A 7-day count can't exceed the 30-day count.
  - `GET /api/research/KVYO` → `revisions.0q`: `downLast30days` **18** and `downLast7Days` 18, yet `trend.0q` moved from 0.17241 (30 days ago) to **0.17247** now, slightly up.
  - The Estimates tab shows only the 30-day ↑/↓ counts, so KVYO reads as "18 cuts" with no sign of that in the consensus.
- suggestion: when the counts are inconsistent (7d > 30d), or the direction disagrees with the `trend` change, show the trend change (%) as the headline and mark the counts as Yahoo's. Or drop the counts.

### 8. Next report timing changed to "during market" for INOD, which has reported after the close 8 times in a row
- kind: ux
- severity: low
- evidence:
  - `GET /api/earnings/INOD` → `next.timing` is `dmh`. All 8 `reports[].timing` values are `amc`.
  - /t/INOD's Reported financials header reads "Next report Thu, Nov 5, during market". The Events card shows only "Thu, Nov 5".
  - For a 5% position with a binary print, whether the reaction comes on 11-05 or 11-06 matters.
- suggestion: when the provider's next timing is `dmh` or blank and the last 4+ reports share one timing, show that one with "(usual)", or show "time not confirmed".

## Summary
1. **No trades.** INOD bounced 6.5% and stays under note 49's exit rules for 11-05. Consensus Q3 revenue of $85.0M (+36% y/y) sits above my $78.2M exit line. TMDX stays on watch. KVYO, PSIX and AUPH all failed research. Cost $97,758.05, value $95,184.29, **cash $2,241.95**, return to date −2.57%.
2. **Last round's fixes:** B-083 works. INOD momentum and the chart agree to the decimal. B-009/B-079 work for RMBS and INOD, but HRMY and TOST still show Yahoo FCF ÷ SEC revenue with no label: HRMY 19.0% against about 37% on SEC.
3. **Top findings:**
   - The brief's 2-day news cache cuts Research → News short for the day's movers: TMDX and LOAR show 0 headlines.
   - HRMY's FCF margin is a mixed-source wrong number.
   - The brief ignores named watchlists: no movers and no MNTN/DUOL earnings.
   - The screener's FY2025 growth keeps surfacing shrinking companies (PSIX).
