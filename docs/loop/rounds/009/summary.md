# Round 009 summary

Date: 2026-10-30, starting about 02:12 UTC. In New York that's Thu 10-29 at about 22:12 ET, the evening of the PCE and GDP releases, so the market was closed. All values are at the 10-29 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 10-29 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** `uv run pytest -q` had 265 passing. B-115's date-dependent test passes again, because today + 3 days no longer lands on the 29th–31st.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,662.43 | $99,188.69 | +$526.26 | $1,275.30 | +0.46% |
| loop-income | 17 | $99,618.80 | $101,352.77 | +$1,733.97 | $381.20 | +1.73% |
| loop-growth | 11 | $97,758.05 | $96,096.06 | −$1,661.99 | $2,241.95 | −1.66% |

loop-macro's realized P&L is −$62.27.

**Trades this round:**
- **loop-macro:** SELL 6 GLD @ 368.57 and BUY 24 IEF @ 91.25, executing note 51 after PCE. The stop needed the 10Y above 5.15%; it was 4.99%. Targets are now GLD 4.5 / IEF 7.5 (thesis note 54).
- **loop-income:** BUY 1 MSFT @ 529.05 post-market (note 53), closing a −0.32 pp gap to target. Forward income is $3,354, a 3.31% yield, and bonds are 34.7% of the book.
- **loop-growth:** no trades. Note 55 on TOST's FTC lawsuit: hold to the 11-03 report, exit if growth is under 18%. The screener's candidates (NUTX, CRMD, XZO) all failed research.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 25 findings: macro 8, income 9, multibagger 8.
- **Reopened:** B-034, reported by macro and income. The round-008 calendar fix held only in a fresh call: the running server lost the 10-29 PCE and GDP rows with their actuals.
- **New items:** B-116 to B-125.
- **Existing items with new evidence:** r009 lines on B-016, B-017, B-019, B-023, B-026, B-035, B-036, B-038, B-044, B-055, B-059, B-062, B-070, B-071, B-075, B-076, B-091, B-094, B-096, B-097, B-105, B-106, B-108, B-109 and B-110.
- **Confirmed by investors:**
  - B-104 works: HRMY and TOST show no FCF margin, and an SEC OCF margin of 37.0% and 9.3% instead. MSFT margins read 67.7 / 47.1 / 41.2%.
  - B-095 works: P/E is price ÷ EPS on fundamentals, the watchlist, compare and the valuation band.

**Picks** (all three produce wrong or missing numbers):
- **B-034:** reopened, high, two investors.
- **B-116:** high. The calendar reported core PCE as 2.5% when the Fed's measure is 3.1% y/y.
- **B-117:** medium. Day P&L was wrong after an after-close sale.

## Shipped
- **B-116, the calendar keeps PCE price index, ECI and the GDP price index (79928cf).**
  - The noise filter now has an allow-list. "Core PCE Price Index", "PCE price index", "GDP Price Index" and "Employment Cost Index" reach `all_events`.
  - ECI joins the curated list.
  - The GDP report's "Core PCE Prices", "PCE Prices" and "GDP Price Index" rows are labeled "(QoQ ann.)".
  - Live: core PCE 0.3% m/m and 3.1% y/y on 10-29, ECI on 10-30.
- **B-034, the calendar keeps rows it has seen (5a9da29).**
  - Release rows for yesterday and today (New York date) are stored in `data/cache/econ_releases.json` and merged on each fetch:
    - a later actual fills in a blank;
    - a later blank doesn't erase a value;
    - a missing row stays.
  - Rows are keyed by date, time, name and a repeat number, because Nasdaq gives two different rows the same name and time.
  - On a weekday, an answer with no rows for today is cached for 10 minutes, not 6 hours. The per-date queries are logged.
  - **Behavior change:** the calendar now starts on yesterday's New York date, so after midnight ET the previous day's actuals still show.
  - Live: 23 rows for 10-29 with actuals, kept even when every Nasdaq answer was empty.
- **B-117, shares sold after the close still count for that session (e883e3d).**
  - Shares sold after the close are rebuilt from their sale lots, using the same next-session rule as B-046.
  - Day P&L and Day % on rows, totals and the brief count them for that session. After-hours P&L leaves them out.
  - A position sold out after the close has no row, but its session P&L stays in the totals.
  - Live: loop-macro Day P&L is back to +$438.52, equal to the performance step for 10-29.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 271 passing and `npm run build` passes.

## Re-check next round
- **Macro and income, calendar (B-034, B-116):**
  - On a release evening after 8 pm ET, that day's rows and actuals should be listed.
  - Just after midnight ET, yesterday's rows should still show, because the calendar now starts on yesterday.
  - Core PCE y/y and ECI should be in the curated list, with the GDP-report rows labeled "(QoQ ann.)".
  - "Dallas Fed PCE" and "GDP Sales" are still curated (B-094).
- **Macro, Day P&L (B-117):**
  - After an after-close sell, Dashboard Day P&L should equal the Performance step.
  - Should a symbol sold out after the close appear in the brief's movers? It currently doesn't.
- **Income:** ABBV reports 10-30, so check its card and payout after the report. PG's dividend is 11-16.
- **Multibagger:** TOST 11-03, MNTN 11-04, INOD 11-05.

## For a human
- **B-034 storage:** the fix adds a persisted store, `data/cache/econ_releases.json`, pruned after 7 days. It's in `data/` and is not committed.
- **B-115:** the dividend-projection test passes now but will fail again when today + 3 days lands on the 29th–31st, next around 11-26 to 11-28. It's still open and small, and a good pick for next round.
- **Schedule timing:** this is the ninth round in a row fired outside market hours (about 22:12 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer revert instruction (proposed again):** `developer.md` says `git checkout -- .`, which would wipe the lead's uncommitted backlog edits. Each developer was told to revert only its own files.
- **Throwaway portfolios in the snapshot:** developers' throwaway test portfolios (`dev-b117` this round) leave create and delete rows in the audit log. Proposal: tell developers to test in a separate data directory.
- **Open high-severity items:** B-017 (asset classes and bond duration) and B-002 (phone width).
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead ignores it until wrap-up, as the procedure says.
