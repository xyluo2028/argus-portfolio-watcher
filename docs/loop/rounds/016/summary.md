# Round 016 summary

Date: 2026-11-13, starting about 02:12 UTC. In New York that's Thursday 11-12 at about 21:12 ET, so markets were closed. The latest close is Thu 11-12: SPY 757.12 (−0.35%). Tuesday's hot CPI turned into a bond sell-off: the 10y went from 4.98 to 5.10 and the 2y from 4.73 to 4.86.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 11-12 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo). Yahoo's 11-12 bar was still late during the investor reviews, which let the multibagger test B-157's late-bar case live.
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth`, "needs the screener's universe", while the universe built in the background (B-027).
- **Nasdaq calendar:** answered normally tonight with no 403s. 40 curated rows came back and `econ_releases.json` filled up (last round's 403s are in "For a human").
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** 360 passed.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000. Values are at the 11-12 close (`argus portfolio show` at wrap-up).

| Portfolio | Value | Cash | Return to date | Day P&L 11-12 |
|---|---|---|---|---|
| loop-macro | $97,988.11 | $1,367.79 | −0.64% | −$228.12 |
| loop-income | $102,702.18 | $13.19 | +2.72% | −$267.96 |
| loop-growth | $100,986.59 | $31.77 | +1.02% | −$1,963.42 |

Since 10-20, loop-income's time-weighted return is +2.93% and loop-macro's −0.60%, against SPY's −1.55%.

**Trades this round:**
- **loop-macro:** no trades.
  - Its IEF exit rule (10y above 5.15, or IEF's 20-day correlation to SPY turning positive) wasn't met: the 10y is 5.10 and the correlation is −0.24.
  - Note 89 holds the plan for after Friday's PPI, review 11-16: if core PPI is 0.4% or more and the 10y closes above 5.15, sell 44 IEF and buy 39 SGOV.
- **loop-income:** the 10y closed at 5.103%, above its 5.1% add trigger, and BND alert 10 (the 10y stand-in) fired.
  - Sold 1 HD @ 348.26 and 1 JNJ @ 283.52, realizing +$55.89.
  - Bought 5 BND @ 70.65 and 4 VCIT @ 78.76 (txns 60–63).
  - Bonds are now 34.5% against a 35% target. Note 88 records the trade, and new alert 11 (BND ≤ 69.30) stands in for the 10y at about 5.35%.
- **loop-growth:** no trades. LOAR −5.3% and RDDT −5.8% moved with their sectors, and every thesis is intact.
  - Added TGTX to growth-candidates (note 90). It wasn't bought: no cash, healthcare is already 46% of the book, and short interest is 28%.
  - Passed on NUTX, DUOL and ANIP.

## Shipped
- **B-163: the Watchlist page shows and switches between every named watchlist (9c57bef).**
  - The page used to read only the list named "Watchlist", so the multibagger's 14-name growth-candidates list was invisible in the UI.
  - Lists now appear as switchable buttons, with the selection kept in `?list=` and localStorage. Cold, the page opens the first non-empty list.
  - The Screener's "+ watch" now has a list picker and says which list it added to.
  - Frontend only: the API already handled named lists.
  - Side effect: the developer's live check left an empty "Watchlist" list in the database (and in the snapshot). It's harmless, but there's no API to delete a list.
- **B-164: the FOMC minutes are back in the curated calendar (a3f3dbd).**
  - The filter matched "FOMC Minutes", but Nasdaq names the release "FOMC Meeting Minutes".
  - Live, the curated rows went from 33 to 34; the only addition is the 11-18 14:00 minutes, and no other row was lost.
- **B-165: stock-page EPS growth comes from SEC's diluted EPS (72f49f1).**
  - This is the EPS version of what B-009 did for revenue. Finnhub's figure is used only when it's a quarter ahead of SEC or the stock isn't in EDGAR, and each figure is labeled with its source.
  - The figure shows "n/m" when the base EPS is zero or negative, or the growth is beyond ±1000%.
  - Live, TGTX reads −76.0% YoY and −85.6% for the latest quarter, where it showed +633.7% and −71.5%. The API, MCP and Dashboard tabs agree.
  - `FUNDAMENTALS_VERSION` went to 11, so cached fundamentals refresh.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 363 passing, and `npm run build` passes.

**New items:**
- B-163: Watchlist page shows only "Watchlist" (shipped).
- B-164: FOMC minutes missing from the curated calendar (shipped).
- B-165: EPS growth from Finnhub contradicts SEC (shipped).
- B-166: the "all 181 US releases" checkbox shows 154 rows.
- B-167: simulate shows concentration only by market value, not at cost.

**Confirmed fixed by investors:**
- B-152, by all three. Income checked the case after evening trades: −$268 vs Day P&L −$267.96.
- B-157, by the multibagger in the live late-bar case: RMBS 1W +21.9% matches everywhere.
- B-156 in the normal case. No day failed, so the partial-failure note is still unverified live.

## Re-check next round
- **Multibagger (B-163):** open /watchlist cold. Switch lists, reload, and share a `?list=` link. Use the Screener's "+ watch" with a non-default list. B-106 is still open: the brief reads only the default watchlist.
- **Macro (B-164):** the default calendar should list "FOMC Meeting Minutes" on 11-18 at 14:00 ET, with Fed speakers other than the Chair still hidden.
- **Multibagger (B-165):** check that EPS growth matches the SEC EPS table on more names, and look for "n/m" on a name that went from loss to profit.
  - Revenue growth YoY, the revenue and EPS CAGRs, and `peg_ttm` are still Finnhub-only and unlabeled, so they may disagree with SEC the same way. Report them if they do.
- **Macro and income (B-156):** if Nasdaq fails some days, check that the partial note "k of 24 days unavailable" appears.
- **Income:** B-017 (duration), B-026 (risk took 53.5 s cold), B-153/B-063 (forward income uses mixed annualization rules).

## For a human
- **B-026 is getting worse.** The first risk load took 53.5 s for income, up from 31.5 s last round. All three investors flagged cold-load times. It's the top perf candidate for a coming round.
- **High-severity items still open:** B-017 (asset classes and bond duration; income did its duration math by hand again) and B-016/B-055.
- **Nasdaq:** last round's 403s didn't recur tonight; the calendar loaded normally. A second calendar source (e.g. the BLS/BEA schedules) would still make Argus less dependent on one feed.
- **Schedule timing:** this is the sixteenth round in a row fired outside market hours (Thu 21:12 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer instructions (proposed again):**
  - `developer.md` says `git checkout -- .` when blocked, which would wipe the lead's uncommitted round files.
  - The lead added overrides to each brief again: no stash, checkout, reset or clean; stage only your own paths; never touch `docs/loop/`.
  - Proposal: put these rules in `developer.md` itself.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead waits until wrap-up, as the procedure says.
- **Production restart needed:** the developers restarted Argus on the new code, so the running server already has all three fixes.
