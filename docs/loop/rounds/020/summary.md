# Round 020 summary

**Trading day.** The session traded was Wednesday 2026-11-18. The round ran after the close (`market_session` `closed`, `can_trade` true).

## Data sources (preflight)

- **Quotes:** working (Yahoo). The Finnhub key reaches Finnhub: `/quote?symbol=AAPL` returned 200.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth`, which waits for the screener universe (B-027). It cleared once the universe was built.
- **Agents and tools:** as in r017–r019, the `trader` and `programmer` agent types and the `mcp__argus__*` tools weren't loaded. General-purpose agents read their `.claude/agents/` files and used the CLI and the API.

## The account (at the 11-18 close)

| | |
|---|---|
| Account value | **$9,645.73**, −3.54% since the start |
| SPY over the same sessions (`sim.py`, close to close) | −3.20% (account 0.34 pp behind) |
| SPY from the trader's 11-13 fill | −2.98% (account 0.56 pp behind) |
| Session change | −$150.06 (account −1.28% vs SPY −0.31%: XLV, TMUS, ADBE, LNG fell harder) |
| Cash | $250.11 (2.6%) |
| Positions | 7: SPY 35.2%, XLV 12.0%, ADBE 11.7%, META 10.1%, LNG 9.9%, NVDA 9.6%, TMUS 8.9% |

**Trades:**
- **BUY NVDA, 6.127 shares at $155.05** (the 11-18 mid: high 159.70, low 150.40), $949.99.
  - Why: 11-18 was the first session after NVDA's 11-17 after-close report, so the fill has no look-ahead (after hours NVDA was only +0.66%). It beat ($115.8B revenue vs $111.3B expected, EPS 2.68 vs 2.525), and next year's EPS consensus rose from 15.91 to 16.54. That puts it at P/E TTM about 19, the bottom of its 5-year range.
  - It fell 2.9% on the day while AMD rose 5.3% and AVGO 3.6%; the trader reads that as a discount for the CEO ouster, so it sized the buy at about 10%.
  - Thesis note id 8 (review 2027-02-25), exit alert at $130 (id 6); the old pre-entry alert was turned off.
- Nothing else: all theses hold, no exit alert fired, and cash is low.

**Account check:** `sim.py status` answers `"ok": true`. There are 7 transactions; the new NVDA fill equals its session mid ((159.70 + 150.40) / 2 = 155.05), and the 6 earlier ones were verified in earlier rounds.

**Re-checks from r019 (all pass):** FIX (all 8 quarters positive, TTM revenue $12.54B, net margin 13.0%; the screener row is flagged unreliable), the r019 screen (D gone, no stale rows pass, amber tags on PTC, INTU and ESE), fear & greed on a cold start (partial 5 of 7 with no rating, then 7 of 7 "Extreme fear"), and FOMC minutes in the calendar.

## Shipped

- **B-182: the CLI's `argus fundamentals` returned `pe_ttm: null` for symbols the server hadn't quoted (9c1c0c1).**
  - Cause: the CLI called `market.get_fundamentals()` directly, without fetching a quote, so the P/E only had the database's last prices to work with.
  - The CLI now goes through `app.fundamentals()`, like the API and MCP, and that path passes the quote it fetched straight into the P/E.
  - Live: CAT and EMR on a cold cache now give 21.92 and 33.82, matching the API.
- **B-184: stale screener rows still carried `revenue_q` (88bcbe0).**
  - `revenue_q`, `revenue_q_prev` and `ttm_through` are now nulled on stale rows.
  - `revenue_q` is now a screen field ("Revenue · latest qtr"). Before, the API rejected it, so the stale-data filter case couldn't even be tested.
  - Live: 0 of 53 stale rows carry a `revenue_q`, and a `revenue_q` filter excludes PTC and INTU.
- **B-177, partly: derive missing fiscal Q4s and anchor TTM on the newest closed fiscal year (5fc9385).**
  - A missing fiscal Q4 is now derived as the full year minus Q1–Q3, from SEC frames, for revenue, operating income and net income. It is derived only with a full-length year, three distinct quarters inside it, and B-178's negative guard. That costs about 50 more cached SEC frame requests per build.
  - TTM now starts from the newest closed fiscal year. That fixed MSFT and KLAC: their years end in June, and their TTM was empty.
  - Rows get a `quarter_derived` flag, and the Screener page shows "N more rows excluded: no current TTM or quarter figures" under the match count.
  - Live, among companies above $50B: stale rows went from 27 to 16, rows with no `revenue_ttm` from 51 to 24, and rows with no P/E TTM from 81 to 56. AAPL, V, MU, DIS, QCOM and INTU are now current.

Nothing was blocked. Tests: 447 pass, and `npm run build` passes.

**Backlog changes:**
- New items:
  - B-182 (done)
  - B-183 (watchlist notes missing from the brief's notes due; open)
  - B-184 (done)
- B-177 stays open for what's left:
  - COST and AZO: a 16-week fiscal quarter puts two quarters in one calendar frame, so Q4 can't be derived;
  - BDX, COR and APD: they wait for their 10-Ks;
  - V, MU, DIS and QCOM: they have a derived quarter and a P/E TTM, but `revenue_ttm` is still null;
  - TTM FCF and margins.
- New evidence added to B-110 (no post-report reaction in watchlist recent earnings), B-059 (NVDA news about other companies) and B-174 (the SPY day figure moved after the buy).

## For the trader to re-check next round

- **CLI P/E:** `argus fundamentals <a symbol not yet quoted> --json` should show `pe_ttm` whenever EPS is positive.
- **Screener:**
  - the GARP / TTM screen now includes AAPL, V, MU and MSFT;
  - an "excluded" line appears under the match count when a TTM filter is set;
  - the `revenue_q` column is blank on stale rows;
  - V, MU, DIS and QCOM have a null `revenue_ttm`: confirm, and say whether it matters.
- **B-183 (not picked):** whether the NVDA-style watchlist note still goes unseen.
- **NVDA:** the position after its first full post-entry session.

## For a human

- **B-179, sim look-ahead (still open):** this round the trader traded NVDA only after a full post-report session, which is fair. But nothing in `scripts/sim.py` enforces that; see r019's summary for the options.
- **SEC XBRL gap:** SEC's XBRL data for CEG, WMB and several utilities and REITs (NEE, SO, DUK, AEP, D, ETR, SRE, XEL, PLD, DLR) still stops at 2026-06-30. That is outside Argus.
