# Round 020: trader (trading day, session 2026-11-18)

## Account
From `python scripts/sim.py status` after my trade, valued at the 11-18 close.
- Account value **$9,645.73**, return since the start **−3.54%**.
- SPY from my 11-13 fill (752.66) to the 11-18 close (730.20) is **−2.98%**, so the account is now **0.56 pp behind** SPY. Close to close from the 11-13 close (754.37), SPY is −3.20%.
- The account lost 1.28% on 11-18 against SPY's −0.31%. Health care (XLV −2.2%), telecom (TMUS −2.3%), ADBE (−4.0%) and LNG (−1.8%) all fell harder than the index.
- Cash **$250.11** (2.6%), invested $9,395.62, no dividends accrued, realized P&L $0. There are 7 trades in all.

| Symbol | Qty | Avg cost | Close 11-18 | Value | % of account |
|---|---|---|---|---|---|
| SPY | 4.6501 | 752.66 | 730.20 | $3,395.50 | 35.2% |
| XLV | 6.377 | 188.175 | 181.17 | $1,155.32 | 12.0% |
| ADBE | 4.9821 | 240.86 | 226.20 | $1,126.95 | 11.7% |
| META | 1.5764 | 634.35 | 616.38 | $971.66 | 10.1% |
| LNG | 3.234 | 309.21 | 296.49 | $958.85 | 9.9% |
| NVDA (new) | 6.127 | 155.05 | 150.96 | $924.93 | 9.6% |
| TMUS | 5.2579 | 171.17 | 164.02 | $862.40 | 8.9% |

House rules: no single stock is above 25%, SPY is at 35% (the ETF limit is 50%), I hold 7 positions (4 to 10 allowed) and use no leverage. Every position has a thesis note.

## What I did
**Market (`/api/market-context`, as_of 11-18):**
- The S&P 500 fell 0.23%, while the Nasdaq 100 rose 0.42% and the Russell 2000 0.46%. The S&P is −3.9% over 1W and −4.4% over 1M.
- Sectors were mixed. Defensives and energy fell: XLE −3.3%, XLV −2.2%, XLF −1.1%. XLY gained 1.8%, and XLK +0.3% was its first up day after −10.7% over 1M. 6 of 11 sectors are above their 50-day average, but XLK and XLC are below both their 50-day and 200-day.
- Breadth (500 stocks): 227 advancers vs 273 decliners, 55% above the 50-day average, 3 new highs (DIS, TGT, DRI) vs 9 new lows (NFLX, BA, COIN…).
- Fear & greed read **16.5, "Extreme fear"**. The VIX is 24.6, with an inverted term structure (1.01).
- 10y yield 5.07%. Housing starts came in at 1.309M vs 1.25M expected. The FOMC minutes came out on 11-18, and they are now in the curated calendar. Next week: PCE and GDP on 11-25, and the FOMC meets on 12-09.
- Background: an Anthropic IPO priced on 11-18 and dominates the headlines.

**Holdings** (brief, quotes and news; no exit alert fired):
- **ADBE −4.0%** (226.20). The software selling continues. The headlines are positive on value: "Printing Cash While Wall Street Writes Its Obituary" (about 9x FCF) and Burry adding to his position. The thesis is intact, at 11.7 pp above my 215 exit level. I won't add, because it is already 11.7% of the account.
- **XLV −2.2%.** Health care gave back some gains ("UnitedHealth again"). It is still above its 50-day, so the thesis is intact.
- **TMUS −2.3%**, in the "S&P 500 gap-down movers". It goes ex-dividend on 11-25 ($1.02, about $5.36 for my shares). The thesis is intact, well above my 150 exit level.
- **LNG −1.8%**, with energy (XLE −3.3%, crude −6.8% 1W). It is 13.6% above my 261 exit level.
- **META −0.4%.** The news is the capex question ("$225B AI spending forecast comes with a cash-flow question"). That is a known risk in my thesis.
- **SPY −0.3%.** It is the core position, and its thesis is unchanged.

**NVDA (the decision I planned last round):**
- 11-18 was the first session after the 11-17 after-close report, so its mid is a fair, post-report price.
- What the report did: NVDA gapped up to an open of 159.19, sold off to a low of 150.40 and closed at **150.96 (−2.9%)**. On the same day AMD rose 5.3% and AVGO 3.6% (`/api/compare`). The market is applying a governance discount (the CEO ouster), not punishing the numbers.
- The numbers:
  - revenue $115.8B vs $111.3B expected, and EPS 2.68 vs 2.525;
  - FY+1 consensus EPS went from 15.91 to **16.54** in 7 days (`research.estimates`), about 9.4x at 155;
  - P/E TTM 19.1, the 0th percentile of its own 5-year range;
  - net margin 64%, and the latest SEC quarter's revenue was +106% YoY.
- Against:
  - 172 insider sales and no buys in a year;
  - analysts moved from 59 buy/strong buy to 46 in a month, and hold from 2 to 15;
  - XLK is below its 200-day.
- **Trade: BUY NVDA, 6.127 shares at $155.05** (the 11-18 mid: H 159.70 / L 150.40), $949.99. I sized it at about 10%, not more, because of the governance risk.
  - I wrote the thesis note first (id 8, kind thesis, review 2027-02-25), with these exits: a close below 130, revenue growth below 40% YoY next quarter, or more management turmoil that hits guidance.
  - I added the alert "NVDA price at or below $130" (id 6) and turned off the old pre-entry move alert (id 4).
- After hours, NVDA was at 151.96 (+0.66%), so this fill carries no meaningful look-ahead.

**Ideas:** I re-ran my r019 GARP screen (cap > $2B, latest-quarter revenue growth ≥ 15%, P/E TTM 5–25, op margin TTM ≥ 15%).
- It returned 54 names again. NVDA, GOOGL, META, ORCL and UNP lead; FIX and D are gone, and no stale rows pass.
- No other buys. Cash is down to 2.6%, I hold 7 positions, and I would rather keep a small buffer than add a 4% position.

## Last round's changes
- **B-178 (FIX's negative Q4): works.**
  - `argus financials FIX` quarterly shows 2025-12-31 revenue at $2.65B. All 8 quarters are positive and rise from 1.87B to 3.77B.
  - The stock page shows Revenue (TTM) 12.54B, P/S 3.2, net margin 13.0%, FCF margin 19.5% and P/E TTM 24.6. Every SEC-derived figure is labeled "SEC, 4Q to 2026-09-30". The Reported financials chart has no negative bar (screenshot `/t/FIX`, rendered in 0.14 s, no errors).
  - The screener row has `revenue: null`, `revenue_unreliable: true`, `ps: null` and `net_margin_pct: null`.
  - The stock page's ROE of 55.2% (Finnhub) is unchanged, as the summary said. The screener's ROE TTM is 48.9%.
- **B-180 (stale quarter tags): works and helped.**
  - In my r019 growth screen (latest-quarter growth ≥ 15, no cap filter, 1,143 matches), no row is `quarter_stale` and D is gone.
  - On the Screener page, PTC "Q2 2026", INTU "Q1 2026" and ESE "Q2 2026" carry amber tags, and their latest-quarter growth and P/E TTM show "–".
  - Side effect: 27 of 240 companies above $50B are now stale (AAPL, V, MU, COST, QCOM, DIS, CEG, WMB, JCI…), so they drop out of any TTM screen without any sign (finding 3).
- **B-036 (fear & greed partial flag): works.**
  - Before breadth loaded: `score 7.1, rating null, partial true, components_used 5/7, missing [Price strength, Price breadth]`.
  - About a minute later: `score 16.5, "Extreme fear", partial false, 7/7`.
  - The 9.4-point jump is still there, but it is now explained by the flag. I didn't screenshot the Markets gauge.
- **B-164 (FOMC minutes in the curated calendar): confirmed live.** The 11-18 "FOMC Meeting Minutes" row is present.
- **B-136 (the brief's 14-day dividends): still works.** It lists TMUS's 11-25 ex-dividend.

## Findings

### 1. `argus fundamentals` (CLI) returns `pe_ttm: null` for any symbol the server hasn't quoted yet, even with EPS present
- kind: bug
- severity: medium
- evidence:
  - `uv run argus fundamentals DE --json`, run three times in a row, returned `pe_ttm: null` each time, with `eps_ttm: 18.0` and `sources.pe_ttm: "sec"`.
  - `curl /api/fundamentals/DE` returned `pe_ttm: 35.82` (644.75 / 18.0).
  - After that API call, the same CLI command returned 35.82.
  - The same happened for FIX (CLI null, then 24.63 after the API call) and CMI (`eps_ttm` 23.96, `pe_ttm` null).
  - `app.fundamentals()` calls `self.market.get_quotes([sym])` before `with_pe`, but in the CLI process that quote apparently doesn't reach the price that `with_pe` uses.
  - A bot screening by CLI gets "no P/E" for most names.
- suggestion: pass the quote's price straight into `with_pe` in `fundamentals()` (not via a cache lookup), and add a test that calls the CLI path on a symbol with an empty quote cache.

### 2. Plan notes on watchlist names never surface in the brief: my NVDA note due 11-18 was missing from `theses_due`
- kind: ux
- severity: medium
- evidence:
  - `GET /api/notes` shows note 7 (NVDA, kind note, `review_on: 2026-11-18`).
  - `GET /api/brief/bot0-sim` on the evening of 11-18 has `theses_due: []`.
  - `app.py:1223` filters notes to `mine` (held symbols). The brief already has `watchlist_movers` and `watchlist_earnings`, but it has no place for a due note on a watchlist name.
  - The whole point of the note was "decide at this session". I only remembered it because last round's report said so.
- suggestion: add `watchlist_notes_due` to the brief, for notes due within 7 days on symbols in any of the account's watchlists, or include them in `theses_due` with `held: false`.

### 3. The screener's stale-quarter rule silently drops 11% of mega-caps from every TTM screen (B-177, new evidence)
- kind: bug
- severity: medium
- evidence:
  - `POST /api/screener {market_cap: [5e10, null]}` returns 240 rows, 27 of them `quarter_stale: true` with `pe_ttm`, `revenue_ttm` and latest-quarter growth all null.
  - The 27 include AAPL (Q2 2026), V, MU, COST, PANW, QCOM, DIS, INTU, TDG and BDX (fiscal years ending August to October), and calendar-year CEG and WMB, whose SEC statements in Argus also stop at 2026-06-30 (`argus financials CEG`).
  - KLAC isn't stale (quarter_end 2026-09-30), but its `ttm_through` and `pe_ttm` are null. MSFT shows P/E TTM "–" on the page without a tag.
  - My GARP screen cannot see Apple, Visa, Micron or Microsoft at all, and nothing on the page says how many rows were excluded for missing TTM data.
- suggestion: the fiscal-Q4 derivation in B-177 is the real fix. Until it ships, show "N rows excluded: no current TTM" under the match count, with a toggle to include them using FY figures.

### 4. Stale rows still carry `revenue_q`, although the summary said quarter figures are nulled
- kind: bug
- severity: low
- evidence:
  - In the screener rows for PTC, INTU and ESE (`quarter_stale: true`), `revenue_growth_q_yoy_pct`, `revenue_ttm` and `pe_ttm` are null, but `revenue_q` is still 600,049,000 (PTC) and 8,558,000,000 (INTU).
  - A filter on a quarterly revenue field would still pass stale data.
- suggestion: null `revenue_q` and `revenue_q_prev` too for stale rows, or document that only growth and TTM are nulled.

### 5. The brief's watchlist "recent" earnings still lack the post-report reaction (B-110, new evidence)
- kind: feature
- severity: low
- evidence:
  - On the evening of 11-18, `watchlist_earnings.recent` still lists NVDA's 11-17 report (EPS 2.68, +6.1% surprise) with no price reaction.
  - The one fact I needed, that the stock fell 2.9% on a beat while its peers rose 4–5%, took `argus quotes` plus `/api/compare`.
- suggestion: add `reaction_pct` (first full session after the report, which Argus already computes for the stock page's Reported financials "Reaction" column) and `ext_change_pct` to `earnings_recent` and `watchlist_earnings.recent`.

### 6. NVDA's research news is mostly about other companies (B-059, new evidence)
- kind: bug
- severity: low
- evidence:
  - In `/api/research/NVDA` news, 8 of the latest 15 items aren't about NVDA: Alphabet vs Apple, the Sandisk price prediction, the Natera drop, the Coupang drop, GTA 6, Palo Alto, nVent and the Anthropic IPO.
  - `news_tone` (6 positive / 5 negative) counts them.
- suggestion: as B-059 says, keep only items whose headline or summary names the company or ticker, before counting tone.

### 7. "SPY, last session" changes after a same-day buy (B-174, new evidence)
- kind: bug
- severity: low
- evidence:
  - Before my NVDA buy, the brief's `benchmark.change_pct` was −0.3058%, which is SPY close to close (730.20 / 732.44).
  - After the buy, `/api/portfolios/bot0-sim` `totals.benchmark_day_pct` is −0.2853%, with `bought_in_session: true`. SPY didn't move; only my trade did.
- suggestion: as B-174 says, the benchmark's day move is SPY's own close-to-close change, whatever I trade.

## Summary for the round lead
- **Account:** $9,645.73, −3.54% since the start, vs SPY −2.98% from my fill (−0.56 pp). Cash is $250 (2.6%), across 7 positions.
- **Traded:** I bought 6.127 NVDA at $155.05 (11-18 mid, a post-report session), $950, about 10% of the account. The reason: a beat and estimate raises, at P/E TTM 19 and about 9.4x FY+1 EPS, after a governance-driven −2.9% day. The thesis note and a $130 exit alert are set.
- **Top finding:** the CLI's `argus fundamentals` returns `pe_ttm: null` for any symbol the server hasn't quoted yet (DE: CLI null vs API 35.8). The B-178, B-180, B-036 and B-164 re-checks all pass.
