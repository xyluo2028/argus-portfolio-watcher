# Round 015 summary

Date: 2026-11-12, starting about 02:11 UTC. In New York that's Wednesday 11-11 at about 21:11 ET, so markets were closed. 11-11 was Veterans Day: stocks traded, the cash bond market was closed. The latest close is Wed 11-11: SPY 759.81 (+1.32%).

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 11-11 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo), but the last bar was 11-10 at preflight. The 11-11 bar arrived later in the round.
- **SEC financials:** working (MSFT).
- **Market context:**
  - `events`: Nasdaq's economic calendar answered 403 for 2026-11-11. Before B-156, that one failure emptied the whole calendar.
  - `breadth`: "needs the screener's universe" while the universe built in the background (B-027).
  - By the B-156 live check, **all 24** of the server's Nasdaq day queries got 403, while a plain `curl` from the same machine got 200. See "For a human".
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** 353 passed.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000. Values are at the 11-11 close (`argus portfolio show` at wrap-up).

| Portfolio | Value | Cash | Return to date | Day P&L 11-11 |
|---|---|---|---|---|
| loop-macro | $98,216.23 | $1,367.79 | −0.42% | +$542.11 |
| loop-income | $102,933.63 | $49.70 | +2.98% (+3.17% with $183.50 accrued dividends) | +$66.56 |
| loop-growth | $102,950.01 | $31.77 | +2.98% | +$1,568.16 |

Since 10-20, loop-income's time-weighted return is +3.20% and loop-macro's −0.38%, against SPY's −1.20%.

**Trades this round:**
- **loop-macro:**
  - Read Tuesday's CPI as hot from the tape (IEF −0.86%, GLD −2.7%, 2Y +22 bp), because Argus's calendar was empty (B-156). Its plan says no SPY add on a hot print.
  - The oil leg broke (WTI 85.7, below its 90 trigger). Sold 50 XLE @ 63.51 (txn 58, realized −$196.00) and bought 31 SGOV @ 100.52 (txn 59).
  - Targets changed to XLE 6.5% and SGOV 17%. Thesis in note 85, review 11-19.
- **loop-growth:** no trades. PAYS passed the growth screen, but its affirmed FY sales guidance implies Q4 revenue below Q3, so it was passed over (note 86). LIF, XZO and LIFE were also passed.
- **loop-income:** no trades. The 10y is at 4.998%, below the 5.1% add trigger, and every position is within ±0.46 pp of target. Wrote note 87 and set alert 10 (BND ≤ 70.70) as a stand-in for the 10y, because ^TNX alerts are rejected (B-078).

## Shipped
- **B-156: one failed Nasdaq day no longer empties the economic calendar (2533339).**
  - Each day now fails on its own. Answered days and the kept releases are always merged.
  - If every day fails, the saved store is served.
  - `errors.events` now reads e.g. "Nasdaq calendar: 1 of 24 days unavailable (403)" instead of raw httpx text.
  - A partial fetch is retried after 10 minutes instead of being held for 6 hours.
  - **Live, the calendar still showed 0 rows.** Every server query got 403, and `econ_releases.json` was empty on this fresh data dir, so there was nothing to fall back on. The note read "24 of 24 days unavailable (403); showing saved releases".
- **B-157: momentum returns end at the quote's close while Yahoo's last bar is late (976d2c9).**
  - `price_stats` now uses the B-142 helper that fills the last session from the quote.
  - The API, MCP and Dashboard tabs therefore match the stock page. RMBS 1W was −2.58% vs +3.0%.
  - Yahoo's 11-11 bar had arrived by the live check, so the late-bar case is verified by tests only. Live, the figures agree (RMBS 1W +2.97%).
- **B-152: Risk's "Last session" is the book's Day P&L, unchanged by trades after the close (1e5ffaf).**
  - Live, loop-macro shows 542.11 = Day P&L after its evening XLE sell (it was 483.80).
  - New `last_day.basis` field. The tile says "held that session" or "today's holdings".
  - VaR and stress still use current holdings.
  - The Holdings "Day %" sub-issue is split out to B-162.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 360 passing, and `npm run build` passes.

**New items:**
- B-156: one failed day empties the calendar (shipped).
- B-157: momentum from a stale bar (shipped).
- B-158: the Markets error banner shows raw httpx text and overflows at 390 px.
- B-159: yield cards show a move on a bond-market holiday.
- B-160: the brief's 7-day earnings window misses a report 8 days out.
- B-161: the simulate side/type conflict message lists the values in reverse order.
- B-162: Holdings Day % follows two rules (split from B-152).

**Confirmed fixed by investors:** B-147 (all three), B-142 in the late-Yahoo case (income), B-136 (income; marked done), and B-117 still holds (macro).

## Re-check next round
- **Macro and income (B-156):** once Nasdaq answers the server again, check that a partial failure shows the other days with a "k of 24 days unavailable" note, and that `econ_releases.json` fills up.
- **Multibagger (B-157):** on an evening when Yahoo's bar is late, check that API/MCP/Dashboard momentum matches the `/t/<sym>` card.
- **Everyone (B-152):** after an evening trade, Analysis → Risk's Last session should match Dashboard Day P&L to the dollar. Before the open, check whether the tile says "today's holdings".
- **Multibagger:** B-149 (PAYS/GRND report timing), B-120 (RDDT forward P/E), B-106 and B-109.
- **Income:** B-148 (SCHP projected total).

## For a human
- **Nasdaq refuses the server's requests.** During the B-156 check, every economic-calendar query from Argus got 403, while a plain `curl` from the same machine got 200. It looks like request-level blocking by Nasdaq (headers or client fingerprint).
  - The developer did not try to work around it, and the loop shouldn't try to evade a provider's bot checks.
  - A human should decide whether Argus needs a different calendar source, such as official BLS/BEA release schedules. Until then the calendar depends on saved releases only.
- **Production restart needed:** the round restarted Argus on the new code during development, so the running server already has all three fixes.
- **Schedule timing:** this is the fifteenth round in a row fired outside market hours (Wed 21:11 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer instructions (proposed again):**
  - `developer.md` tells the developer to `git checkout -- .` when blocked. That would wipe the lead's uncommitted round files (backlog and reports).
  - This round the lead added overrides to each brief: no stash, checkout, reset or clean; stage only your own paths; never touch `docs/loop/`.
  - Proposal: put those rules in `developer.md` itself.
- **Open high-severity items:** B-017 (asset classes and bond duration; income estimated durations by hand again, and they held out of sample), B-016/B-055, and B-009.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead waits until wrap-up, as the procedure says.
