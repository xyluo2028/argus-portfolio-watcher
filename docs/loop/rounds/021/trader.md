# Round 021: trader (trading day, session 2026-11-19)

## Account
From `python scripts/sim.py status`, valued at the 11-19 close. I made no trades this round.
- Account value **$9,459.17**, return since the start **−5.41%**.
- SPY from my 11-13 fill (752.66) to the 11-19 close (715.87) is **−4.89%**, so the account is **0.52 pp behind** SPY. Close to close from the 11-13 close (754.37), SPY is −5.10%.
- On 11-19 the account lost $186.56 (−1.93%) and SPY lost 1.96%, so I roughly matched the index on the day. The dashboard's time-weighted figures agree: return −5.72% (positions only, no cash), SPY −4.89%, excess −0.84%.
- Cash **$250.11** (2.6%), invested $9,209.06, no dividends accrued, realized P&L $0. There are 7 trades in all, none this session.

| Symbol | Qty | Avg cost | Close 11-19 | Day | Value | % of account |
|---|---|---|---|---|---|---|
| SPY | 4.6501 | 752.66 | 715.87 | −1.96% | $3,328.87 | 35.2% |
| XLV | 6.377 | 188.175 | 177.46 | −2.05% | $1,131.66 | 12.0% |
| ADBE | 4.9821 | 240.86 | 221.68 | −2.00% | $1,104.43 | 11.7% |
| LNG | 3.234 | 309.21 | 295.37 | −0.38% | $955.23 | 10.1% |
| META | 1.5764 | 634.35 | 596.22 | −3.27% | $939.88 | 9.9% |
| NVDA | 6.127 | 155.05 | 145.98 | −3.30% | $894.42 | 9.5% |
| TMUS | 5.2579 | 171.17 | 162.53 | −0.91% | $854.57 | 9.0% |

House rules: no single stock is above 25%, SPY is at 35% (the ETF limit is 50%), I hold 7 positions (4 to 10 allowed) and use no leverage. Every position has a thesis note.

## What I did
**Market (`/api/market-context`, as_of 11-19):**
- It was an ugly reversal day. SPY opened at 737.46, made a high of 739.90 and closed on its low (715.87, low 715.65), down 1.96%. The S&P 500 fell 2.02% (−5.5% over 1W, −6.7% over 1M) and the Nasdaq 100 2.21% (−10.2% over 1M). Headlines tie the drop to Anthropic's trading debut failing to lift the AI trade.
- All 11 sectors fell, from XLY −2.8% and XLC −2.7% to XLE −0.65%. XLK is −13.6% over 1M and below both its 50-day and 200-day averages. 5 of 11 sectors are above their 50-day.
- Breadth (500 largest US stocks): **45 advancers vs 455 decliners**, 47.6% above the 50-day, 0 new highs vs 19 new lows (NVDA, CAT, NFLX, BA, CMI…).
- Fear & greed **15.5, "Extreme fear"**, from all 7 components once breadth loaded (12.2 with 5 of 7, flagged partial, before that). VIX 28.4, with an inverted term structure (1.05). The 10-year yield is 5.04%, and 10y−2y is +0.28.
- Calendar: jobless claims came in at 203K vs 198K expected. Still ahead: Michigan sentiment (11-20), CB confidence (11-24), PCE and durable goods (11-25), and the FOMC on 12-09.

**Holdings** (from the brief, quotes, events and notes; no exit alert fired):
- **NVDA −3.3%** (145.98), now 0.19% above its 52-week low (`near_52w_extremes`). It is a market-wide tech selloff and nothing NVDA-specific. The thesis (beat, estimate raises, P/E in the bottom of its range) is intact, and my exit is at 130. After hours it was 144.65.
- **META −3.3%** (596.22; 587.65 after hours). The news is that it is "reevaluating" its 2030 net-zero goal because of the AI buildout, which is the same capex story already in my thesis. It is 6.5% above my 560 exit level.
- **ADBE −2.0%** (221.68). The low was 219.80, and my exit is at 215. The thesis (P/E TTM 12.4, forward about 8) is intact, but this is the position closest to its exit. The exit alert (id 1) is active.
- **XLV −2.05%.** It is still above its 50-day and 200-day averages, so the thesis is intact.
- **TMUS −0.9%.** One headline is a new risk to watch: "Why SpaceX's latest move has T-Mobile investors on edge" (a direct-to-phone service). The stock barely reacted. It goes ex-dividend on 11-25 ($1.02, about $5.36 for my shares). It is well above my 150 exit level.
- **LNG −0.4%**, the best holding today. RBC praised its contract wins. It is 13% above my 261 exit level.
- **SPY**: the core position, and its thesis is unchanged.
- I archived my old NVDA plan note (id 7, review date 11-18). It had been carried out last round but was still listed as due in the brief.

**Ideas:**
- I re-ran my GARP screen (cap > $2B, latest-quarter revenue growth ≥ 15%, P/E TTM 5–25, operating margin TTM ≥ 15%). It returned **63 matches** (54 last round), with `excluded_no_ttm: 182`. MU (P/E TTM 9.2, latest-quarter revenue +379%) and DIS now pass, because their fiscal Q4s are derived.
- **INTU** (on my watchlist) reported FQ1 after the 11-19 close: EPS 2.91 vs 2.75 expected, revenue $4.354B vs $4.392B (a small miss). After hours it was at 279.74 (**−9.8%**). The 11-19 mid (and so any fill today) predates the report, so I won't trade it. I wrote a plan note (id 9, review 2026-11-20).

**Decision: no trades.**
- With cash at $250 (2.6%), there is nothing to buy with unless I sell something, and every thesis is intact with no exit level hit.
- On a reversal day like this one, the fill rule works against buying. SPY's mid is 727.77, 1.7% above its close; NVDA's mid is 151.92 vs a close of 145.98, and META's 612.90 vs 596.22. Any buy today would show an instant 1.7–4% loss against the close.
- Rotating out of a holding into something else would mean selling at a mid that is also above the close, which is the better side of the fill. But I have no replacement idea that beats what I hold.
- Next session: re-check ADBE against 215, NVDA's 52-week low and INTU's settled reaction.

## Last round's changes
- **B-182 (CLI `pe_ttm` null for symbols the server hadn't quoted): works.**
  - On a cold cache, `uv run argus fundamentals ITW --json` gave `pe_ttm` 24.68 (EPS 11.22, sec) on the first call. GD gave 20.44 (yahoo) and ROK 30.55 (sec). The API returns the same figures.
- **B-184 (stale rows carry `revenue_q`): works.**
  - In `POST /api/screener {market_cap: [5e10, null]}` (236 rows), 0 of the 14 stale rows carry `revenue_q`. `revenue_q` is accepted as a filter field.
- **B-177 (derived fiscal Q4s): works and helped.** Among companies above $50B:
  - stale rows went from 16 to 14 (COST, AZO, BDX, COR, and the utilities, REITs and CEG/WMB waiting on SEC);
  - rows with no `revenue_ttm` went from 24 to 21;
  - rows with no P/E TTM went from 56 to 52.
  - **V, MU, DIS and QCOM now have a `revenue_ttm`** (45.9B, 133.2B, 102.3B and 43.1B), so the null last round's summary mentioned is gone.
  - AAPL (P/E TTM 38.4, growth 11.7%), V (31.9, 13.2%) and MSFT (25.9, 18.8%) now have current TTM figures. They miss my GARP screen on the numbers alone, which is correct: MSFT's P/E is just above my 25 limit.
  - MU's derived Q4 ($54.2B) looks extreme, so I checked it. It fits the quarterly series in `argus financials MU`: 13.6B → 23.9B → 41.5B → 54.2B, with operating margins of 45%, 68%, 80% and 81%. It is a real memory upcycle, not a derivation error.
- **The "excluded" line:** I checked it in the API only. The GARP screen returns `excluded_no_ttm: 182`, and a screen with no TTM filter returns 0. I didn't drive the Screener page UI with filters, so I haven't seen the line on the page.
- **B-183 (not picked): still open, confirmed again.** See finding 2.

## Findings

### 1. The screener's P/E TTM for LNG is 13.4, but the stock page says 20.8: the screener's TTM net income is 48% higher than the statements'
- kind: bug
- severity: medium (LNG is a holding of mine, and a P/E 35% too low makes it look like a deep-value pass in any GARP screen)
- evidence:
  - The LNG row from `POST /api/screener` has `pe_ttm: 13.40`, `net_income_ttm: 4,502,000,000`, `revenue_ttm: 23,942,000,000`, `revenue_q: 6,173,000,000` and `revenue_q_prev: 4,441,000,000`.
  - `/api/fundamentals/LNG` gives `pe_ttm: 20.82` from `eps_ttm: 14.19` (source sec).
  - `argus financials LNG` (quarterly) shows net income of 1,170M, 3,068M, −3,502M and 2,302M, which sums to **3,038M**, and EPS of 5.65 + 14.65 − 16.65 + 10.54 = 14.19. Quarterly revenue is 6,097M (latest) and 4,293M (a year earlier).
  - So the screener's quarters don't match the statements. Revenue is 1–3% off, and TTM net income is 1.46B higher, about the size of Cheniere's noncontrolling interest (Cheniere Partners). That suggests the frames picked up consolidated profit (or a different filing's fact) instead of net income attributable to Cheniere.
  - Across the first 22 rows of my GARP screen, the screener's P/E TTM is within ±7% of the stock page's for 19 of them. The exceptions are LNG (13.4 vs 20.8), MLM (15.7 vs 13.4) and NVDA (see finding 3).
- suggestion: for each row, compare the screener's TTM net income with the sum of the statement quarters (both come from SEC), and flag or prefer the statements when they differ by more than about 10%. Also check whether the CY frames for LNG serve `ProfitLoss` or a restated Q1 2026.

### 2. A plan note on a watchlist name still never reaches the brief (B-183, new evidence)
- kind: ux
- severity: medium
- evidence:
  - I added note 9 on INTU (on my `candidates` watchlist, not held), kind note, review date **2026-11-20**: "decide after the post-report session".
  - `GET /api/brief/bot0-sim` straight afterwards returned `theses_due: []`. `app.py:1226` filters notes due within 7 days down to `mine`, the held symbols.
  - Last round's NVDA note only appeared once I owned NVDA, by which point it was obsolete. It was still listed as due today, one day overdue, until I archived it by hand (finding 4).
- suggestion: as in B-183, add `watchlist_notes_due`, or include notes on watchlist symbols in `theses_due` with `held: false`.

### 3. NVDA's P/E TTM is 15.7 on the stock page and 18.3 in the screener, and the page's source switched from SEC to Yahoo with no visible cue
- kind: ux
- severity: low
- evidence:
  - `/api/fundamentals/NVDA` gives `pe_ttm: 15.68`, `eps_ttm: 9.31`, `sources.pe_ttm: "yahoo"`. Last round the same call gave 19.1 from SEC.
  - The screener row gives 18.28 (SEC TTM through the quarter ending 2026-07-26). `argus financials NVDA` also still ends at 2026-07-26 (EPS 2.46 + 2.39 + 1.76 + 1.30 = 7.91).
  - Yahoo's 9.31 evidently includes the quarter NVDA reported on 11-17 (2.68), whose 10-Q isn't in SEC yet. So the page is fresher, but two Argus screens disagree by 17% on one of my holdings, and nothing says which quarter each covers.
- suggestion: show which quarter each P/E TTM runs through (e.g. "TTM to Oct 2026, Yahoo" vs "TTM to Jul 2026, SEC") on both the stock page and the screener, or have the screener prefer the newer EPS when its source is fresher.

### 4. The CLI can't archive or update a note; I had to PATCH the API to retire an obsolete plan
- kind: ux
- severity: low
- evidence:
  - `uv run argus note --help` lists only `add` and `list`. MCP has `update_note`, and the API has `PATCH /api/notes/{id}`.
  - My NVDA plan note (id 7, review date 11-18) had been carried out last round, but the brief kept it in `theses_due` as overdue. Retiring it took `curl -X PATCH /api/notes/7 -d '{"archived":true}'`.
  - The brief also mixes kinds: a plain `note` is listed under "theses due".
- suggestion: add `argus note update <id> [--text] [--review-on] [--archive]`. In the brief, rename `theses_due` to `notes_due`, or carry `kind` into the UI label.

### 5. The brief's watchlist earnings still show no after-hours reaction: INTU −9.8% isn't visible (B-110, new evidence)
- kind: feature
- severity: low
- evidence:
  - `watchlist_earnings.recent` lists INTU's 11-19 report (EPS 2.91, +5.8% surprise; revenue 4.354B vs 4.392B est) with no price reaction.
  - `argus quotes INTU` shows `ext_price 279.74`, `ext_change_pct −9.77`. That is the fact that decides whether I look at INTU tomorrow.
- suggestion: add `ext_change_pct` (and, once the next session closes, `reaction_pct`) to `earnings_recent` and `watchlist_earnings.recent`.

### 6. The screener has no sector column or filter
- kind: feature
- severity: low
- evidence:
  - The rows from `POST /api/screener` carry no `sector` or `industry` field (keys: symbol, name, cik, revenue … quarter_stale), and the field list in `GET /api/screener` has no sector.
  - My book is already heavy in tech and communication (NVDA, META, ADBE, TMUS, plus SPY), and XLK and XLC are the two weakest sectors. To look for a replacement outside them, I have to open each match.
- suggestion: add the company profile's sector to the rows, with a sector include/exclude filter.

### 7. The performance chart's end label overlaps the axis label
- kind: ux
- severity: low
- evidence: dashboard `/` at desktop width (rendered in 0.67 s, no errors): the blue "bot0-sim −5.7%" end badge sits on top of the "−6.0%" axis tick, so the tick is unreadable. Phone width (390) has no horizontal overflow.
- suggestion: hide axis ticks that collide with an end badge, or nudge the badge.

## Summary for the round lead
- **Account:** $9,459.17, −5.41% since the start, vs SPY −4.89% from my fill (−0.52 pp). On the 11-19 session the account fell 1.93% vs SPY's −1.96%. Cash is $250 (2.6%), across 7 positions.
- **Traded:** nothing. All theses hold and no exit level was hit. On this reversal day the mids sat 1.7–4% above the closes, and INTU's report came after the close (its −9.8% after-hours move would be look-ahead).
- **Top finding:** the screener's LNG P/E TTM is 13.4 vs 20.8 on the stock page, because the screener's TTM net income (4.50B) is 1.46B above the SEC statement quarters (3.04B). The B-182, B-184 and B-177 re-checks pass, and V/MU/DIS/QCOM now have `revenue_ttm`.
