# Round 008 summary

Date: 2026-10-29, starting about 02:12 UTC. In New York that's Wed 10-28 at about 22:12 ET, the evening of the FOMC decision, so the market was closed. All values are at the 10-28 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 10-28 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,747.15 | $98,771.59 | +$24.44 | $1,253.87 | +0.03% |
| loop-income | 17 | $99,089.75 | $99,803.20 | +$713.45 | $910.25 | +0.71% |
| loop-growth | 11 | $97,758.05 | $95,184.29 | −$2,573.76 | $2,241.95 | −2.57% |

**Trades this round:** none.
- **loop-macro:** every position is within ±0.26 pp of target. The Fed held on 10-28, leaning hawkish. SELL 6 GLD / BUY 24 IEF stays staged for after PCE (10-29 08:30); it simulates to net cash +$60.66 (note 51).
- **loop-income:** within ±0.28 pp of target. MSFT, the only gap, is +2.9% after hours on its beat, and one share (~$546) would overshoot its 4% target by as much as the gap (note 52). KO alert #6 turned off. Bonds are 35.1% of the book.
- **loop-growth:** INOD bounced 6.5% and is held to its 11-05 report under note 49. The screener's three candidates (KVYO, PSIX, AUPH) all failed research.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 25 findings: macro 8, multibagger 8, income 9.
- **New items:** B-104 to B-114 from the investors, and B-115 from a developer (a date-dependent test, below).
- **Raised:** B-034 to high. On FOMC night the Fed decision vanished from the calendar.
- **Existing items with new evidence:** r008 lines on B-002, B-016, B-017, B-019, B-021, B-023, B-024, B-026 (first `/risk` load now 30.8 s), B-035, B-036, B-038, B-059, B-062, B-070, B-071, B-075, B-076, B-077, B-091, B-092, B-094, B-100 and B-103.
- **Confirmed by investors:**
  - B-083 (momentum) works on stocks and ETFs.
  - B-093 (dividends) works.
  - B-009/B-079 works for revenue and EPS. The margins and the no-capex FCF case were filed as B-104.

**Picks:**
- **B-034:** wrong or missing data, now high, reported in five rounds.
- **B-104:** wrong numbers, reported by two investors, a follow-up to last round's fix.
- **B-095:** wrong numbers, reported in two rounds.

## Shipped
- **B-034, calendar on the New York date (2476971).**
  - The calendar now starts on the America/New_York date, and the cache key includes that date.
  - Live at 22:24 ET on 10-28, `all_events` starts 10-28 with the FOMC statement, the rate decision (actual 4.00%) and the press conference.
- **B-104, valuation card from one window and one source (5572ff8).**
  - Gross, operating and net margin come from the same four SEC quarters as revenue and EPS.
  - FCF margin is never a cross-source ratio. Without SEC capex it is blank, and an SEC "operating cash flow margin (capex not reported)" shows instead.
  - Every FCF field shows its source.
  - Live:
    - MSFT: 67.66 / 47.10 / 41.17%, "SEC, 4Q to 09-30".
    - HRMY: FCF margin blank (it showed 19.05%), OCF margin 37.0%.
    - TOST: OCF margin 9.3%.
- **B-095, P/E = price ÷ the EPS shown (7795a74).**
  - P/E is computed at read time from the latest price and the card's EPS, labeled with the EPS's source. Loss-makers show "n/m".
  - The research valuation band re-rates its current value and percentile the same way.
  - Live: BLLN 162.9, RMBS 37.5, INOD 36.1.

Nothing was blocked.

**Checks:**
- `uv run pytest -q` has 264 passing and **1 failing**: `tests/test_p2.py::test_dividend_events_follow_ex_date_ownership_and_projection`. It fails the same way on the round 007 head, so this round didn't cause it.
  - It depends on the date. The fake monthly dividend history is built from `today + 3` = 10-31, which `add_months` clamps to 9-30, so the projection is 10-30 while the test expects 11-02.
  - It only fails when today + 3 days falls on the 29th to 31st, and should pass again from 10-29 ET.
  - It's logged as B-115 rather than edited outside this round's picks.
- `npm run build` passes.

## Re-check next round
- **Macro, calendar (B-034):** after 8 pm ET it should still show that day with its actuals, and the previous day should drop off after midnight ET. "FOMC Press Conference" is in `all_events` but filtered out of `events` (B-094).
- **Income:**
  - MSFT margins should read 67.7 / 47.1 / 41.2%, labeled SEC.
  - Check the card the night a holding reports, before its 10-Q is in SEC: the margins should switch to the provider's newer quarter, labeled Finnhub.
- **Multibagger:**
  - HRMY and TOST should show no FCF margin and an OCF margin labeled "capex not reported". The Profitability tab's FCF margin is blank for them on purpose.
  - P/E should equal price ÷ EPS on the stock page, the fundamentals tab, the watchlist, compare and the valuation band.
  - PEG (trailing) is still Finnhub's and can disagree with the new P/E.
  - P/E alerts may fire differently now.
- **Income:** PG's 11-16 dividend. **Multibagger:** INOD 11-05 and MNTN 11-04. **Macro:** PCE 10-29, then execute or drop note 51.

## For a human
- **Failing test (B-115):** the suite isn't fully green tonight. The cause is a date-dependent test that existed before this round, not a regression. It should be fixed early next round; a target day ≤ 28 is enough.
- **Schedule timing:** this is the eighth round in a row fired outside market hours (about 22:12 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer revert instruction:** proposed again. `developer.md` says `git checkout -- .`, which would wipe the lead's uncommitted backlog edits. Each developer was told to revert only its own files.
- **Open high-severity items:** B-017 (asset classes and bond duration; income now shows the N-PORT data needed for duration is already loaded). B-002 (phone width) has been reported in every round.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead ignores it until wrap-up, as the procedure says.
