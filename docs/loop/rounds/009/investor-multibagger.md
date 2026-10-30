# Round 009: multibagger (growth) investor

## What I did
- **Timing:** about 02:13 to 02:50 UTC Fri 2026-10-30 (Thu 10-29, about 22:15 ET). The market was closed, so prices are the 10-29 close plus post-market quotes.
- **Book** (`GET /api/portfolios/loop-growth`):
  - 11 positions, cost $97,758.05, value **$96,096.06**, unrealized −$1,661.99.
  - Day P&L **+$911.77 (+0.96%)** against IWM's +0.97%. LOAR led at +5.8% (+$619). INOD fell another 3.1%.
  - Post-market the book is **−$851 (−0.89%)**. RMBS is at 86.50 (−4.9%, −$543) and INOD at 43.31 (−6.2%). The whole AI-infrastructure group sold off after hours: SMH −3.5%, ALAB −5.0%, CRDO −5.5%, MU −3.4%, and AMZN −7.3% on its report. Argus showed me this only because I queried the quotes myself (see finding 7).
- **Performance reconciles:** 96,096.06 − 95,184.29 = 911.77, which equals Day P&L. TWR is (1 − 0.0269478) × (1 + 911.77 ÷ 95,184.29) − 1 = −1.763%, which equals `twr_pct`. The IWM leg compounds to +2.984%, which also matches.
- **TOST:** the FTC sued Toast on 10-29. Argus gave me two headlines ("Toast Responds to FTC Lawsuit", "The FTC Lawsuit Could Burn Toast's Image…") and nothing on what the FTC alleges. The stock fell 1.4% while IWM rose 1.0%, so the market shrugged.
  - My thesis (note 31) rests on growth and operating margin, and nothing has broken it yet.
  - I wrote **note 55** (review 11-03): hold until the 11-03 report. I exit if Q3 growth is under 18% or if the suit forces changes to Toast's payments pricing.
  - Consensus Q3 revenue of $2.01B is +23% on Q3-25's $1.633B (SEC).
- **INOD:** I'm still holding under note 49 to the 11-05 report. The exit line (Q3 revenue under $78.2M) is unchanged. It's −17.6% on cost and 5.1% of the book.
- **RMBS:** the −4.9% post-market move follows the group, and there's no company news. Note 46's thesis (Q3 +22.3%, operating margin 38.3%) is intact, so I hold.
- **Hunt** (`POST /api/screener`, universe built, 5,351 companies, FY2025, each call under 0.03 s):
  - **Screen A:** market cap $0.7–10B, growth ≥30%, operating margin ≥12%, FCF margin ≥10%, P/S ≤8, liabilities/equity ≤1.5. It returned 11 names, mostly miners and energy (UROY, SSRM, HL, GPOR, LPG).
  - **Screen B:** market cap $0.4–12B, growth ≥20%, gross margin ≥45%, operating margin ≥5%, FCF margin ≥5%, P/S ≤10. It returned 11 names.
  - **NUTX** (screener: growth +82.4%, P/E 20.3): **pass.** The quarters run +2.2%, −41.1% and **−13.6%** (Q2-26). The revenue is lumpy arbitration income, and short interest is 28.6%.
  - **CRMD** (+617%, P/E 3.7): **pass.** Q2 revenue fell to $101.9M from Q1's $127.4M. Consensus EPS is **0.495 this year and 0.057 next year**, so a cliff is coming.
  - **XZO** (watchlist; screener +62.0%): **pass for now.** The latest quarter is **+3.0%** (SEC) and the card's TTM growth is +6.9%.
  - RIGL's P/E of 2.6 is a tax benefit (net margin 124.7%, B-071).
- **Trades: none.** No thesis broke today, 10 of my 11 holdings report in the next 7 days, and $2.2k of cash can't fund a real position.

  | Cost | Value | Unrealized | Cash | Return to date |
  |---|---|---|---|---|
  | $97,758.05 | $96,096.06 | −$1,661.99 | **$2,241.95** | (96,096.06 + 2,241.95 − 100,000) ÷ 100,000 = **−1.66%** |

## Last round's changes
- **B-104 (FCF margin from one source): works.**
  - HRMY: `fcf_margin_pct` null, `ocf_margin_pct` **36.99** (`sec`). I checked it against SEC OCF.
  - TOST: FCF margin null, OCF margin **9.33%** = (144 + 132 + 194 + 165) ÷ 6,804 ✓.
  - On /t/HRMY at 390 px, "Operating cash flow margin 37.0%" carries "capex not reported".
  - One leftover: the same card still shows Yahoo's FCF of $182.84M, about half of SEC's OCF (finding 5).
- **B-095 (P/E = price ÷ the EPS shown): works everywhere I looked.**

  | Where | Values |
  |---|---|
  | Fundamentals | HRMY 12.49 = 38.59 ÷ 3.09; TOST 39.87 = 31.50 ÷ 0.79; INOD 34.98 = 46.17 ÷ 1.32; BLLN 164.06 = 114.84 ÷ 0.70; RMBS 37.44 = 90.99 ÷ 2.43 |
  | Watchlist | DUOL 16.16 = 136.39 ÷ 8.44 |
  | `/api/compare` | identical figures |
  | Research valuation band `current` | HRMY 12.49, TMDX 17.39, RMBS 37.44 |

  - It helps: the P/E line now agrees with the EPS beside it on every page.
  - PEG still doesn't (finding 6).
- **B-034 (calendar):** this isn't part of my workflow, so I didn't check it.
- **B-113 (INOD timing):** the provider now says `amc`, and /t/INOD reads "Thu, Nov 5, after close". That's a data change, not a fix.

## Findings

### 1. Two different EPS consensus figures for the same quarter on one stock page (INOD 0.17 vs 0.27, BLLN 0.15 vs 0.30)
- kind: bug
- severity: medium (I size earnings risk on the beat/miss bar, and the two figures differ by up to 2x with no reason given)
- evidence:
  - For the Q3 report, I compared the brief and `GET /api/earnings/<sym>` → `next.eps_estimate` (Finnhub; also the stock page's Events card and the "Next report… EPS est." header) with `GET /api/research/<sym>` → `estimates.trend.0q.current` (Yahoo, Research → Estimates "This quarter"):

    | Symbol | Finnhub | Yahoo | Gap |
    |---|---|---|---|
    | INOD | 0.1724 | 0.2723 | +58% |
    | BLLN | 0.1486 | 0.30 | +102% |
    | TOST | 0.2564 | 0.3732 | +46% |
    | HRMY | 1.1679 | 1.4678 | +26% |
    | KRYS | 1.8065 | 1.9181 | +6% |
    | PODD, GRND, LOAR, TMDX | | | agree within 2% |

  - /t/INOD shows "EPS est. 0.17" in the Events card and the Reported financials header. The Estimates tab on the same page says 0.27.
  - The gap looks like GAAP vs adjusted EPS. TOST's Finnhub "actual" for Q2 is 0.26, which equals SEC GAAP diluted EPS. Neither figure says which basis it is.
- suggestion: label each estimate with its source and basis ("Finnhub" / "Yahoo, adjusted"). Or show one consensus per quarter: Yahoo's 0q in the Events card, or Finnhub's on the Estimates tab. When the two differ by more than 10%, show both with a note.

### 2. "P/E (forward) 5.5" on HRMY is price ÷ next year's adjusted consensus, shown unlabeled beside a GAAP trailing P/E of 12.5
- kind: ux
- severity: medium (it makes HRMY look half as expensive as it is on any like-for-like basis)
- evidence:
  - `GET /api/fundamentals/HRMY`: `pe_forward` 5.51 (`yahoo`), `eps_forward` **7.00454**.
  - In `GET /api/research/HRMY`, 7.00454 is `trend["+1y"]`, which is **FY2027**. FY2026, which ends in two months, is 5.22. The trailing EPS is SEC GAAP 3.09.
  - So the forward P/E jumps two fiscal years and from GAAP to adjusted at once.
  - /t/HRMY at 390 px: "P/E (TTM) 12.5, SEC, 4Q to 2026-06-30", then "P/E (forward) 5.5" with no label.
  - TMDX goes the other way: forward 29.8 against trailing 17.4. That's correct (its trailing EPS includes a tax benefit), but again nothing says why.
- suggestion: label the forward P/E "Yahoo, FY2027 consensus (adjusted)". Better, also show price ÷ the current fiscal year's consensus. HRMY would read 38.59 ÷ 5.22 = 7.4.

### 3. The screener's FY2025 growth keeps surfacing companies that have stopped growing (XZO "+62%" is +3% now, NUTX "+82%" is −14%) (B-019, new evidence)
- kind: feature
- severity: medium
- evidence:
  - This round, every name I opened failed on the first quarterly check:

    | Name | Screener (FY2025) | Latest quarter |
    |---|---|---|
    | XZO | +62.0% | **+3.0%** (`revenue_growth_q_yoy_pct`, SEC); card TTM +6.9% |
    | NUTX | +82.4% | **−13.6%** (`research.growth.quarters`); Q4-25 −41.1% |
    | CRMD | +617% | Q2 revenue down 20% from Q1; next-year EPS consensus 0.057 vs 0.495 this year |

  - That's four rounds running that the screener's top growth names failed research.
  - `revenue_growth_q_yoy_pct` (SEC) already exists per symbol in `/api/fundamentals`.
- suggestion: add a latest-quarter growth column and filter to the screener. Even a "Q yoy" column computed for the rows returned, at most 40, would have saved three research calls.

### 4. A lawsuit against a holding reaches me as two headlines with no detail, and there's no filings feed to check
- kind: feature
- severity: medium (the FTC suit against TOST is the most important thesis event this week, and I had to decide on headlines alone)
- evidence:
  - `GET /api/research/TOST` → `news` holds 5 items with `headline`, `source`, `url` and `tone`, and **no summary field**.
  - The brief's copy of the same item has a summary, but it says only "Toast responds to FTC lawsuit".
  - The links are finnhub.io redirects.
  - Argus already reads SEC EDGAR for statements, yet the stock page has no list of recent 8-K or 10-Q filings, where a material lawsuit or its response would appear.
- suggestion: add a "Filings" list to Research: the last 10 SEC filings with form type, date, item numbers (8-K 1.01, 2.02, 8.01…) and a link to EDGAR. Also keep the `summary` on Research → News items.
- decision it changes: whether to cut TOST before the 11-03 report. I held, partly because I couldn't size the allegation.

### 5. HRMY's card shows Yahoo FCF of $182.8M beside an SEC OCF margin that implies about $355M of cash flow
- kind: bug
- severity: low (labeled now, but the two figures on one card disagree by 2x)
- evidence:
  - /t/HRMY shows "Free cash flow (TTM) 182.84M, Yahoo", and under Profitability "Operating cash flow margin 37.0%, SEC, capex not reported".
  - 37.0% × $959.9M revenue = $355.1M OCF. SEC capex in the earlier quarters was about $0.1M, so FCF is about $355M, not $183M.
  - TOST is the same: Yahoo FCF $474M against SEC OCF $635M.
- suggestion: when SEC has OCF but no capex, show "Operating cash flow (TTM) 355.1M, SEC" in place of Yahoo's FCF. Or hide the Yahoo FCF the way the FCF margin was hidden.

### 6. Two PEGs, both under 1, for a company whose consensus EPS is expected to fall 42% (TMDX)
- kind: bug
- severity: low (new evidence for the PEG caveat noted under B-095)
- evidence:
  - `GET /api/fundamentals/TMDX`:
    - `peg` 0.573 (`yahoo`), which is what `/api/compare` shows.
    - `peg_ttm` 0.176 (`finnhub`), which is what the stock page's "PEG (trailing)" shows.
    - `eps_ttm` is 3.86 (SEC, includes a tax benefit) and `eps_forward` is 2.25, so consensus has EPS falling.
  - TOST's `peg_ttm` of 0.318 implies 125% EPS growth, from Finnhub's YoY EPS growth of 120.85%.
  - Neither PEG uses the P/E shown on the card.
- suggestion: compute PEG from the card's P/E ÷ forward EPS growth ((eps_forward ÷ eps_ttm − 1) × 100), and show "n/m" when growth is ≤ 0. Drop the second PEG.

### 7. Still present: the brief misses the after-hours rout, my watchlist movers and the full news window (B-110, B-106, B-105)
- kind: bug
- severity: medium (new evidence on existing items)
- evidence:
  - **B-110:** `GET /api/brief/loop-growth` has no after-hours section. RMBS −4.9% (−$543) and INOD −6.2% post-market are the book's biggest moves tonight, and the brief shows RMBS as a −0.04% loser and has no RMBS headline. The portfolio's own `totals.ext_pnl` of −$851.34 isn't in the brief either.
  - **B-106:** `watchlist_movers: []`. `GET /api/watchlists/growth-candidates` has VICR −4.63%, PEGA −3.56% and DUOL −3.22% post-market. The first two pass the brief's ≥3% rule on the regular session.
  - **B-105:** after the brief ran, `GET /api/research/TOST` → `news` holds 5 items, **all dated 10-29**. RMBS, which wasn't fetched by the brief first, holds 25 items back to 10-27.
- suggestion: as filed. B-110 matters most to me tonight.

### 8. Cold brief 7.5 s and cold watchlist 6.4 s, then 0.1 s warm
- kind: perf
- severity: low (new evidence for B-026)
- evidence:
  - The first `GET /api/brief/loop-growth` of the session took 7.50 s. The first `GET /api/watchlists/growth-candidates` (12 symbols) took 6.44 s.
  - Repeats took 0.12–0.15 s and 0.08 s.
  - Stock pages render in about 1 s, but Peers on /t/INOD still read "Loading…" after a 5 s settle (B-097).
- suggestion: warm the brief and watchlist quotes and fundamentals at startup or on a schedule, the way the screener universe is built in the background.

## Summary
1. **No trades.** I wrote note 55 on TOST's FTC suit (hold to 11-03, exit if growth is under 18%). INOD stays under note 49 to 11-05. RMBS's −4.9% post-market move follows the AI-semis group. NUTX, CRMD and XZO failed research. Value $96,096.06, **cash $2,241.95**, return to date −1.66%.
2. **Last round's fixes work:** B-104 (HRMY and TOST show no FCF margin and an SEC OCF margin of 37.0% / 9.3%) and B-095 (P/E = price ÷ EPS on fundamentals, watchlist, compare and the valuation band).
3. **Top findings:**
   - Two EPS consensus figures for one quarter on the same page: INOD 0.17 vs 0.27, BLLN 0.15 vs 0.30.
   - HRMY's unlabeled forward P/E of 5.5 uses FY2027 adjusted consensus.
   - Screener FY growth again surfaces companies that have stopped growing (XZO +62% → +3%).
   - There's no filings feed for a lawsuit like TOST's.
