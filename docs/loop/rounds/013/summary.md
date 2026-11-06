# Round 013 summary

Date: 2026-11-06, starting about 02:10 UTC. In New York that's Thursday 11-05 at about 21:10 ET, after the close. The latest close is Thu 11-05: SPY 733.00 (−4.41%), in a tech/AI selloff (Nasdaq 100 −6.4%, SMH −11.2%).

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 11-05 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working. At the start Yahoo had no 11-05 daily bar; the bars arrived during the round. B-134's quote fill covered the gap in performance. Risk now uses the same fill (B-142).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** 307 passing.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000. Values are at the 11-05 close, from `argus portfolio show` on the production server, which runs the round's starting code.

| Portfolio | Cost | Value | Unrealized | Cash | Return to date | Day P&L 11-05 | Accrued dividends |
|---|---|---|---|---|---|---|---|
| loop-macro | $98,404.56 | $88,394.12 * | −$10,010.44 * | $1,308.40 | −10.30% * (true about −1.59%) | −$1,335.99 * (true −$1,648) | $65.83 |
| loop-income | $99,950.30 | $102,570.21 | +$2,619.91 | $49.70 | +2.62% | −$1,046.11 | $185.64 |
| loop-growth | $98,287.80 | $94,704.33 | −$3,583.47 | $387.90 | −4.91% | −$4,278.62 | $0 |

\* **loop-macro's figures are wrong until the QUAL split is recorded.** QUAL split 4:1 on 11-05 (B-140). The book still holds 53 pre-split shares priced at the post-split 54.79. Argus now flags this, with the command to fix it (`split_warnings`). On a data copy with the SPLIT recorded, the developer got a value of $97,105.73, TWR −1.56% and Day P&L −$1,648.43. Those match the investor's hand count. **The SPLIT was not recorded in the model book this round:** the macro investor's call, next round.

**Trades this round:**
- **loop-growth:**
  - Sold all 205 HRMY at 32.47 (txn 51), realized −$1,324.30. Growth and margin both broke the thesis.
  - Bought 65 TMDX at 77.00 (txn 52) and 20 LOAR at 72.02 (txn 53), both at post-market quotes after strong Q3 reports.
  - Notes 70–77 hold the reasoning.
- **loop-income:** bought 2 XOM at 165.75 (txn 54), its most underweight position, ahead of the 11-16 ex-date. It also added a JPM 4% day-loss alert, which fired correctly. Note 78.
- **loop-macro:** no trades.
  - It staged a post-payrolls SGOV→SPY add (note 80); the XLE→RSP switch stays staged.
  - Note 79 records why the QUAL SPLIT wasn't recorded: performance would have shown +300% on the split day before B-140.

## Shipped
- **B-140: stock splits re-base cached history, unrecorded splits are flagged, performance stays continuous (b34d31c).**
  - **Re-basing:** when fresh Yahoo bars disagree with cached closes by a split-like factor, Argus replaces the symbol's whole cached history and expires its dividend history.
  - **Split events** are stored in a new `stock_split` table (migration 0002, the first since the baseline). For recent splits, the 52-week range comes from the adjusted bars.
  - **Warnings:** a held position whose split has no SPLIT transaction gets a `split_warnings` entry. It appears in the API, CLI, MCP, brief, drift warnings and a Dashboard banner, with the command to record it. Nothing is written to the ledger.
  - **Live check on a copy:**
    - QUAL's history is adjusted, its 52-week range is 46.47–57.03 and its yield 0.86% (it showed 3.45%).
    - With the SPLIT recorded: TWR −1.56%, drift says buy $37 of QUAL (not $7,703), and performance's last step equals Day P&L.
- **B-141: dividend projections follow a payer's own calendar where its history repeats (b19dbf0).**
  - **Bond ETFs:** BND, VCIT, VGIT and SCHP now project 12-01 and 12-18, with no January extra.
  - **loop-income** 2026 income rose from $655.76 to $788.33 (+$132.57).
  - **SCHD's December** moved from 12-23 to 12-09. O is unchanged.
  - **loop-macro:** IEF and SGOV gain a 12-21 payment, and VTIP's payment moves from 01-04 to 12-18.
  - **Day shifts:** a few other estimates move by days within the same month (VIG 12-28 → 12-21, NEE 11-30 → 11-23, HD March 03-03 → 03-12).
- **B-142: risk uses the quote-filled last session and flags a latest-day loss beyond the 99% VaR (79f5935).**
  - **Response:** risk now returns `closes_from_quotes` and a `last_day` field, and the card has a new "Last session" tile.
  - **Live check** (loop-income, on a copy with the 11-05 bars removed): `as_of` 11-05, 99% VaR $1,045. The last session was −$1,054.05, "exceeded 99% VaR". This matches the real-bar result to the cent.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 328 passing, and `npm run build` passes.

**New items:**
- B-143: an after-close reporter whose numbers aren't in yet drops off Coming up.
- B-144: no flag when operating cash flow reverses.
- B-145: VTIP's yield shows 5.58%.
- B-146: risk analysis crashes with a single holding (found by a developer).

## Re-check next round
- **Macro (B-140):**
  - Record `argus txn add loop-macro SPLIT QUAL --qty 4 --date 2026-11-05T09:30`. The warning should clear, the value should be about $97.1k and TWR about −1.6%, with no jump on 11-05.
  - Confirm QUAL's page shows normal 5D/1M returns and a 0.86% yield, and that the brief no longer says "near 52w low".
  - QUAL's dividend history re-bases to per-share amounts about a quarter of the old ones (expected after the split). Income is right only once the SPLIT is recorded.
- **Everyone (B-140):** watch for false "possible split" flags (source "quote") on symbols that didn't split. MTUM also split 4:1; nobody holds it.
- **Income and macro (B-141):**
  - The bond ETFs show two December payments and no January one.
  - The 2026 totals are up by about the amounts above.
  - Check the moved dates for VIG, NEE and HD.
- **Income (B-142):**
  - On the next evening Yahoo is late, check that risk's `as_of` equals performance's last date and that the "from quotes" note shows.
  - The Last session tile should match Day P&L, allowing for dividends.
- **Multibagger:**
  - B-143: GRND's Q3 numbers should show once Finnhub fills them.
  - B-119 (EPS basis), B-106 (brief watchlist movers) and B-109 (simulate at the close after hours) are still open.

## For a human
- **Production restart needed:** the running server is on the round's starting code. The next round's preflight restart picks up the three fixes and migration 0002.
  - The wrap-up `argus portfolio show` and `snapshot dump` CLI calls ran on the new code against `data/`, so that DB already has the migration. `data/` isn't committed.
- **Time bomb B-139 still open:** a test fails from 2026-11-27 on. It was deferred again this round for three wrong-number bugs. Pick it next round; there are about three weeks left.
- **Yahoo data quality, fourth case:** after a NaN close, a missing dividend row and a late bar, this round brought a split with no adjustment to the cached bars. Each is now handled defensively.
- **Schedule timing:** this is the thirteenth round in a row fired outside market hours (Thursday 21:10 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer instructions (proposed again):**
  - Developers are told to revert only their own files and to use a throwaway server and data copy instead of `pkill`. All three followed this.
  - Proposal: put both in `developer.md`.
- **Open high-severity items:** B-017 (asset classes and bond duration; raised again), B-016/B-055, and B-009.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead waits until wrap-up, as the procedure says.
