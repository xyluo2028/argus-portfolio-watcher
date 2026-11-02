# Round 010 summary

Date: 2026-11-02, starting about 02:13 UTC. In New York that's Sunday 11-01 at about 21:13 ET, the first evening after daylight saving time ended. The market was closed, so all values are at the Fri 10-30 close.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 10-30 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** `uv run pytest -q` had 270 passing and 1 failing. The failure was `tests/test_speed.py::test_fundamentals_ask_providers_in_parallel_and_merge`, a wall-clock test (< 0.35 s) run while three investor agents loaded the machine. It passed 3 of 3 times on its own and in every later full run.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,662.43 | $99,128.07 | +$465.64 | $1,275.30 | +0.40% |
| loop-income | 17 | $99,618.80 | $101,709.19 | +$2,090.39 | $381.20 | +2.09% |
| loop-growth | 11 | $97,758.05 | $94,159.22 | −$3,598.83 | $2,241.95 | −3.60% |

loop-macro's realized P&L is −$62.27. Day P&L for 10-30 was −$60.62 (macro), +$376.79 (income) and −$1,936.84 (growth). Each matches its Performance step.

**Trades this round:** none in any portfolio.
- **loop-macro:** drift is within ±0.5 pp and payrolls are on Friday.
  - Note 56 is a conditional plan to switch the 12 GLD shares into IEF if GLD's correlation with SPY stays above 0.5 (now +0.76) or GLD closes below its 52-week low.
  - Note 57: hold DBC at 6%.
- **loop-income:** every position is within ±0.18 pp of target.
  - Turned off the spent earnings alerts #7 (MSFT) and #8 (ABBV).
  - Notes 59 (ABBV Q3, dividend +5.2%) and 60 (XOM Q3, dividend +3.9%).
  - Forward income is $3,354, a 3.30% yield.
- **loop-growth:** 9 of 11 holdings report 11-02 to 11-05, and each has a written exit line.
  - Added PAYS to the `growth-candidates` watchlist, with note 58: buy after the 11-09 report if growth is ≥35% and operating margin ≥20%.
  - IA and COLL failed research because their recent quarters slowed.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 24 findings: macro 8, multibagger 8, income 8.
- **Reopened:** B-006, reported by macro and income. After DST ended the calendar was a day late and an hour early: NFP showed on Sat 11-07 at 07:30.
- **New items:**
  - B-126: on weekends and Mondays the calendar starts on Saturday (macro, income).
  - B-127: theses stay "due" after a newer note, and the CLI can't change a review date (macro).
- **Existing items with new evidence:** r010 lines on B-016, B-017, B-019, B-026 (all three investors), B-027, B-036 (two), B-038, B-045, B-055, B-062, B-064, B-076, B-105, B-106, B-110, B-111, B-118 and B-119.
- **B-088:** raised to high, with two reporters.
- **Confirmed by investors:**
  - B-117 works: Day P&L equals the Performance step after an after-close sale.
  - B-116 couldn't be re-checked, because no PCE row was in the window.

**Picks:**
- **B-006:** wrong dates and times, high, two investors.
- **B-088:** past earnings reports vanish, high, two investors.
- **B-126:** Friday's releases missing on weekends, two investors.

## Shipped
- **B-006, calendar dated and timed by the feed's real clock after DST (e0ac58c).**
  - **Times:** Nasdaq's "gmt" field uses New York's offset at fetch time for every row. Argus assumed a fixed −4 h.
    - `nasdaq_offset` now infers the feed's offset from releases with fixed New York times (claims, NFP, ISM, EIA…).
    - `nasdaq_slot` converts each row with America/New_York for that row's date.
  - **Dates:** `_nasdaq_days` no longer treats a sparse Monday as its own day and carries the shift forward. That rule was what made a lone OPEC row shift the whole week.
  - **Store:** the release store is versioned (v2). The pre-fix store is dropped and rebuilt.
  - Live: NFP Fri 11-06 08:30, ISM Mon 11-02 10:00, claims Thu 11-05 08:30.
- **B-088, past earnings reports survive refreshes (04cd791).**
  - **Cause:** `EventsService.refresh` deleted every event kind in the ±100-day window. That included Yahoo's report dates and Finnhub's EPS history. A watchlist add or the brief triggers that refresh.
  - The refresh now replaces only the kinds it fills. Past reports with an actual are kept when a provider leaves them out, and a newer actual still updates them.
  - `/api/earnings` also lists a quarter whose report is out before the 10-Q is filed. That was why ABBV's and XOM's 10-30 Q3 rows were missing.
  - Live: ABBV Q3 (3.82 vs 3.823) and XOM Q3 (4.23 vs 4.12) are listed.
- **B-126, calendar starts on the last trading session (d6c9cba).**
  - New `session_before()` on the XNYS calendar, so holidays count too.
  - On Sat, Sun and Mon the window starts on Friday, and the release store keeps every day from that session through today.
  - Live at Sunday evening: Fri 10-30 ECI 0.8% and Chicago PMI 55.3 are listed.
  - Personal income was a Thursday release, with PCE, so it is correctly just before the window.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 279 passing and `npm run build` passes.

## Re-check next round
- **Macro and income, calendar (B-006, B-126):**
  - Every row should be on its real New York date and time, with NFP on Fri 11-06 at 08:30.
  - On Monday Friday's rows should still show, and on Tuesday the window should start on Monday.
  - On a release evening the day's actuals should stay listed.
  - Saturday's "Atlanta Fed GDPNow" and Sunday's "OPEC Meeting" rows now show between Friday and Monday, because Nasdaq lists them on those days. Decide whether they're noise.
  - B-116 (core PCE y/y, ECI) is still unchecked.
- **Multibagger and income, earnings history (B-088):**
  - After an events refresh or a watchlist add, past reports should stay in `/api/earnings` and on the stock page.
  - Recent reporters (TOST 11-03, MNTN 11-04, INOD 11-05) should get their new row right after the report.
  - PAYS's 08-05 report should come back in the main data dir once caches expire, about 22:18 UTC on 11-02.
- **Income:** XOM's SEC quarterly financials return only two periods, and the developer suggests a separate item. PG's dividend is 11-16, and XOM's announced amount is checked under B-064.
- **Multibagger:** PAYS reports 11-09.

## For a human
- **Flaky timing test:** `test_fundamentals_ask_providers_in_parallel_and_merge` failed once while three agents ran in parallel. It uses a 0.35 s wall-clock bound. Consider a looser bound or another way to show the two calls overlap. It isn't in the backlog yet.
- **B-115:** the month-end dividend-projection test will fail again around 11-26 to 11-28. It's still open and small, and a good pick for next round.
- **Schedule timing:** this is the tenth round in a row fired outside market hours (Sunday 21:13 ET this time). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer revert instruction (proposed again):** `developer.md` says `git checkout -- .`, which would wipe the lead's uncommitted backlog edits. Each developer was told to revert only its own files.
- **Throwaway data:** developers were told to use a separate data directory, and none was created in the main one this round. The old `dev-b117` rows from r009 stay in the snapshot's audit log. Proposal: put that instruction in `developer.md`.
- **Restart hazard:** `pkill -f "argus [s]erve"` killed a developer's own shell once. It recovered and Argus is running.
- **Open high-severity items:** B-017 (asset classes and bond duration). The multibagger also rated the weekend brief news gap (B-105/B-110) high this round.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead ignores it until wrap-up, as the procedure says.
