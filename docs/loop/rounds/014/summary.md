# Round 014 summary

Date: 2026-11-09, starting about 02:10 UTC. In New York that's Sunday 11-08 at about 21:10 ET, so markets were closed. The latest close is Fri 11-06: SPY 735.29 (+0.31%).

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 11-06 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo). The 11-06 bars were on time.
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** 327 passed, 1 failed.
  - The failure was `test_splits.py::test_52_week_range_comes_from_adjusted_bars_after_a_recent_split`, a test that fails on weekends and mornings. It was folded into B-139 and fixed.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000. Values are at the 11-06 close, as the investors measured them on the production server (the round's starting code). `argus portfolio show` at wrap-up gave the same market values.

| Portfolio | Value | Cash | Return to date | Day P&L 11-06 |
|---|---|---|---|---|
| loop-macro | $96,993.64 | $1,308.41 | −1.70% | −$112.09 |
| loop-income | $102,195.90 | $49.70 | +2.25% (+2.43% with $183.50 accrued dividends) | −$375.21 |
| loop-growth | $98,794.45 | $31.77 | −1.17% | +$3,335.00 |

Since 10-20, loop-income's time-weighted return is +2.46% and loop-macro's −1.67%, against SPY's −4.39%.

**Trades this round:**
- **loop-macro:**
  - Recorded the QUAL 4:1 split (txn 55): 53 shares became 212, average cost 56.42. The split warning cleared, and the book's value is now right.
  - No market trades. The post-payrolls SPY add failed its VIX/VIX3M condition (1.04). The XLE→RSP switch is held through Tuesday's CPI (note 82).
- **loop-growth:**
  - Sold all 487 GRND @ 13.41 (txn 56), realized −$457.78. The Q3 operating margin collapsed to 2.9%, there was a shelf filing and insider selling (note 83).
  - Bought 72 RDDT @ 95.65 (txn 57), a starter position (note 84).
  - Both trades were priced at Friday's post-market prices.
- **loop-income:** no trades. Every position is within ±0.38 pp of target, and it is waiting for CPI (note 81).

## Shipped
- **B-147: simulate requires `side` (or `type`) on every trade instead of defaulting to BUY (e4f2d4a).**
  - Two investors independently had a SELL sent with `type` simulated as a buy, with no error.
  - `type` is now accepted as an alias, case-insensitive. A trade that is missing its side, has an unknown side, sends conflicting `side`/`type`, or has no symbol gets a 400 naming the trade.
  - The API and MCP share the same code path. There is no CLI simulate command.
  - **Breaking on purpose:** callers that left out `side` to mean a buy now get a 400.
- **B-139: the time-bomb tests derive their dates from today (257dc16).** Tests only; no production bug.
  - The CAGR test used `date.today()`, which `freeze_today` doesn't freeze.
  - The 52-week test counted its bars back from the last close, while the code's window counts back from now. That made it fail on weekends and mornings.
  - The full suite passed with today frozen at seven dates from 2026-11-09 to 2027-06-30.
- **B-146: risk analyzes a one-holding portfolio, and says so plainly when there are none (ff58856).**
  - `np.cov` returned a 0-d array for one holding; it is now wrapped in `np.atleast_2d`.
  - An empty book now returns "No holdings with a market value to analyze."
  - Live check on a data copy: one holding gives 100% risk share and the API returns 200. The Risk card renders at desktop and phone width.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 353 passing, and `npm run build` passes.

**New items:**
- B-147: simulate defaults to BUY (picked and shipped this round).
- B-148: SCHP's projected payments don't add up to its annual income.
- B-149: GRND's report is dated a day late after an after-close release.
- B-150: the split warning is missing from the first summary after a restart.
- B-151: the stock page hides a latest-quarter margin collapse.
- B-152: two different "last session" P&L figures, and two rules in the Day % column.
- B-153: estimated income is unmarked in "2026 so far".
- B-154: garbled characters in Finnhub news summaries.
- B-155: an empty portfolio blanks the Analysis page (found by a developer).

## Re-check next round
- **Macro and multibagger (B-147):** re-run a sell through simulate with `type: "SELL"` and check it shows as a sale with positive `net_cash`. A trade with no side should be rejected.
- **Everyone (B-146):** risk for every book is unchanged; only the one-holding and zero-holding cases are new.
- **Macro (B-150):** after the next restart, check whether the first portfolio summary has every expected warning.
- **Income:**
  - On the next evening Yahoo is late, check that risk fills the last session from quotes (B-142).
  - Check SCHP's projected total (B-148).
- **Multibagger:** B-149 (GRND's report date), B-119 and B-120 (EPS basis and forward P/E), B-106 (brief watchlist movers), and B-109 (simulate at the post-market price after hours).
- **Income (B-131):** O's surprise looks fixed by new data; confirm.

## For a human
- **Production restart needed:** the running server is on the round's starting code. The next round's preflight restart picks up the three fixes.
- **B-147 is a deliberate API change:** simulate rejects trades with no side. The web UI always sends `side`.
- **`freeze_today` limit:** freezing past about a year from the real date fails with `exchange_calendars` DateOutOfBounds. This is a limit of the test fixture, not a date bomb.
- **Schedule timing:** this is the fourteenth round in a row fired outside market hours (Sunday 21:10 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer instructions (proposed again):**
  - The B-147 developer briefly ran `git stash`/`git stash pop`, which also stashed the lead's uncommitted round files. They came back intact.
  - Proposal: `developer.md` should forbid `git stash`, should say to stage only the developer's own paths, and should say to use a throwaway server and data copy instead of `pkill`.
- **Open high-severity items:** B-017 (asset classes and bond duration; income estimated durations by hand again), B-016/B-055, and B-009.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead waits until wrap-up, as the procedure says.
