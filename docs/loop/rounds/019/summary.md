# Round 019 summary

**Trading day.** The session traded was Tuesday 2026-11-17. The round ran on the evening of 11-17 New York time (11-18 UTC), with `market_session` `closed`.

## Data sources (preflight)

- **Quotes:** working (Yahoo/Finnhub). The Finnhub key reaches Finnhub: `/quote?symbol=AAPL` returned 200.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth`, which waits for the screener universe (B-027). It cleared once the universe was built.
- **Agents and tools:** as in r017–r018, the `trader` and `programmer` agent types and the `mcp__argus__*` tools weren't loaded. General-purpose agents read their `.claude/agents/` files and used the CLI and the API.

## The account (at the 11-17 close)

| | |
|---|---|
| Account value | **$9,795.79**, −2.04% since the start |
| SPY over the same sessions (`sim.py`, close to close) | −2.91% |
| SPY from the trader's 11-13 fill | −2.69% (account +0.65 pp ahead) |
| Cash | $1,200.11 (12.3%) |
| Positions | 6: SPY 34.8%, XLV 12.1%, ADBE 12.0%, LNG 10.0%, META 10.0%, TMUS 9.0% |

**Trades: none.**
- **NVDA:** it beat after the 11-17 close and traded at 162.94 after hours (+4.8%), while a fill would be at the 11-17 mid of 154.26. The trader passed, because buying at a pre-report price with the reaction already visible is look-ahead. It wrote a plan note to decide at the 11-18 session, up to about $1,000.
- **Everything else:** no adds in the broad sell-off (fear & greed in extreme fear, breadth 81 up / 418 down, software leading the declines). All theses are intact and no exit alert fired.

**Account check:** `sim.py status` answers `"ok": true`. There are still 6 transactions, all verified at their session mid in earlier rounds; none were added this round.

**Re-checks from r018:** the trader confirmed that B-175 (provisional history bar), B-136 (the brief lists TMUS's 11-25 ex-dividend) and B-019 (screener TTM and latest-quarter fields) work, and that NVDA moved into `watchlist_earnings.recent`.

## Shipped

- **B-178: FIX's Q4 2025 revenue was derived as −$4.62B (ef97ee8).**
  - Cause: FIX's Q1 2026 10-Q tagged Q1 2025's figures as the whole of 2025, and the newest filing always won the dedupe.
  - A full-year figure from a 10-K, 20-F or 40-F now beats a 10-Q's copy of the same period.
  - For revenue, gross profit and operating income, two cases are now withheld and listed in a new `withheld` field:
    - a full year that is smaller than a quarter inside it;
    - a negative derived Q4 when the year and year-to-date figures are positive.
  - The screener drops a bad FY figure and sets `revenue_unreliable` when TTM revenue is below the largest quarter in its window.
  - Live: FIX Q4 2025 revenue is now $2.65B and TTM is $12.54B (it was $5.27B), with net margin 13.0% (was 30.9%).
  - The screener's FIX revenue is now empty and flagged, because SEC's CY2025 frame serves the bad figure.
  - 14 of 5,326 screener rows are newly flagged unreliable.
- **B-180: a stale latest quarter in the screener (3651f0d).**
  - Every row now carries `quarter_end`, and `quarter_stale: true` once that quarter ended more than 135 days ago.
  - For stale rows, the quarter and TTM figures are null, so they can't pass filters. The FY figures stay.
  - On the Screener page, a stale row gets an amber tag showing its quarter.
  - D's missing Q2/Q3 2026 data is SEC's, not Argus's: SEC's XBRL data stops at Q1 2026 for D, NEE, SO, DUK, AEP, ETR, SRE, EXC, PLD and DLR.
  - 490 rows are now stale. About 194 of them are August–October fiscal years (AAPL, V, COST…) with no Q4 derivation; that evidence was added to B-177.
- **B-036: fear & greed flags a partial reading (ad8fa6d).**
  - `/api/market-context` now carries `components_used`, `components_total`, `partial` and `missing`. `rating` is null while the reading is partial.
  - The Markets gauge reads "Partial (5 of 7)" and names the missing readings.
  - Not done: the brief part. The brief has no market section at all, so there was nothing to flag there (that would go with B-038).

Nothing was blocked. Tests: 443 pass, and `npm run build` passes.

**Backlog changes:**
- New items:
  - B-178 (done)
  - B-179 (sim look-ahead, for a human)
  - B-180 (done)
  - B-181 (events say `held: false` for a held stock bought after the ex-date)
- New evidence added to B-176 (INTU's date flipped back to 11-19), B-110 (NVDA's after-hours move is missing from the brief), B-059 (the CEO-ouster headline scored positive) and B-177.

## For the trader to re-check next round

- **FIX stock page:** no negative quarter, TTM revenue at least the latest quarter's, and sensible P/S and margins. The stock page's ROE of 55.2% comes from Finnhub and wasn't touched.
- **Screener:** re-run the r019 screen (latest-quarter growth ≥ 15). D should be gone and no stale rows should pass. Check the stale tags on the Screener page (e.g. INTU, PTC).
- **Fear & greed on a cold start:** `partial: true`, 5 of 7, `rating: null`; then `partial: false` with a rating once breadth loads.
- **NVDA:** the decision planned for the 11-18 session.

## For a human

- **B-179, sim look-ahead.** The round runs after the close, so after-hours earnings reactions are visible while fills use the pre-report session mid; NVDA's +4.8% would have been free. The trader declined, but nothing enforces it. Two options:
  - `scripts/sim.py` refuses or warns on a buy when `|ext_change_pct|` is large or the symbol reported after that session's close;
  - the round trades the next session instead.
  
  The loop may not edit `sim.py` or the schedule, so this needs a human.
- **SEC XBRL gap:** SEC's XBRL data is missing the Q2/Q3 2026 10-Qs for several utilities and REITs (D, NEE, SO, DUK…). That is outside Argus. Those rows now show as stale rather than wrong.
