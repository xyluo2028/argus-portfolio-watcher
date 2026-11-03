# Round 011 summary

Date: 2026-11-03, starting about 02:13 UTC. In New York that's Monday 11-02 at about 21:13 ET, after the close. The latest close is Mon 11-02.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 11-02 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned 200 with a quote.
- **History: broken at the start of the round.** `argus history SPY --period 1mo` and `/api/history/SPY` failed with `sqlite3.IntegrityError: NOT NULL constraint failed: price_bar.c`.
  - Yahoo serves the 11-02 daily bar with open, high and low but a NaN close.
  - The batch insert failed, so `price_bar` held 0 rows for every symbol.
  - Filed and fixed this round as B-128. History works now, but Yahoo still has no 11-02 daily close, so the last stored session is 10-30.
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** `uv run pytest -q` had 279 passing.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000. Values are at the 11-02 close. Accrued dividends are reported separately and aren't in this formula.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date | Day P&L 11-02 |
|---|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,662.43 | $98,547.21 | −$115.22 | $1,275.30 | −0.18% | −$513.81 |
| loop-income | 17 | $99,618.80 | $101,778.32 | +$2,159.52 | $381.20 | +2.16% | +$200.16 |
| loop-growth | 11 | $99,823.05 | $96,437.68 | −$3,385.37 | $176.95 | −3.39% | +$207.16 |

loop-macro's realized P&L is −$62.27.

After B-129, accrued dividends are $63.08 for loop-macro and $185.00 for loop-income. Each includes this round's estimated 11-02 ex-dates.

**Trades this round:**
- **loop-growth:** bought 7 KRYS at $295.00 (post-market, txn 48), with note 61 as the thesis update.
  - **Why:** Q3 revenue grew 30.2% and operating margin was 55.9%, plus a $400M buyback, yet the stock fell 11%.
  - KRYS is 12.9% at cost and healthcare is 47.5% of the portfolio. Cash is now $176.95.
- **loop-macro:** no trade.
  - Note 62 stages an XLE→RSP switch (SELL 30 XLE, BUY $2,000 RSP) for after Friday's payrolls if WTI stays under 98.
  - Note 63 says note 56's GLD correlation trigger couldn't be tested without history.
- **loop-income:** no trade.
  - Notes 64 (O, hold at 4%; ignore the "+162% beat") and 65 (XOM fell on oil; hold).
  - Archived note 39.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 22 findings: macro 8, multibagger 8, income 6.

**New items:**
- B-128: a NaN history bar empties the price history (all three investors).
- B-129: passed estimated ex-dates vanish (income, macro).
- B-130: endpoints 500 when the optional history part fails (all three).
- B-131: REIT EPS surprise compares AFFO with a GAAP estimate (income).
- B-132: "last report" rows have no report date (multibagger, income).

**Existing items with new r011 evidence:** B-009, B-012, B-013, B-016, B-018, B-022, B-026, B-037, B-046, B-055, B-063, B-064, B-077, B-091, B-094, B-097, B-102, B-105, B-106, B-110, B-118, B-119, B-125 and B-127.

**Confirmed by investors:**
- B-006 works (macro, income): NFP Fri 11-06 08:30, ISM Mon 10:00, claims Thu 08:30.
- B-126 works: on Monday evening the window starts on Fri 10-30.
- B-088 works for KRYS and for the portfolio earnings list. The per-symbol earnings check was blocked by B-128.

**Picks:**
- B-128: wrong numbers and errors everywhere, three investors.
- B-129: wrong income numbers and Day P&L that doesn't reconcile, two investors.
- B-130: whole endpoints and cards failing, three investors.

## Shipped
- **B-128: price bars without a close are dropped instead of failing the whole write (6cc8ca6).**
  - The Yahoo provider skips rows with a NaN or None OHLC. `_store_bars` stores only complete bars, so a bad bar never overwrites a good one.
  - If a fetch has no complete bar for the last session, that symbol is fetched again at most every 15 minutes.
  - Live: history, risk and performance return 200. Risk is as of 10-30 until Yahoo fills the 11-02 close.
- **B-129: a passed estimated ex-date counts until Yahoo's history shows it (89871c0).**
  - **Grace period:** half a pay period, marked as estimated. A real history row, a declared date or a manual DIVIDEND replaces it, with no double counting.
  - **Also accrued now:** declared ex-dates that passed before the history shows them.
  - **loop-income:** received went from $53.07 to $185.00 and November from $105.86 to $237.79.
  - **loop-macro:** November went from $0 to $63.08.
  - **Day P&L vs the 11-02 performance step:** the gaps are now $0.90 (income) and $3.97 (macro), down from the whole dividend.
- **B-130: history-derived figures fail soft in fundamentals, research and earnings (f54a1e8).**
  - **Cause:** the guards caught only `ArgusError`, so the SQLite error leaked through.
  - On failure the response includes `errors.price_history`, and the history fields are null.
  - A 5xx with no JSON body now shows a readable message in the UI instead of "Internal Server Error".
  - The stock page's fundamentals card has an error state instead of a permanent "Loading…".
  - Checked on a throwaway server with history forced to fail, with screenshots at desktop and phone width in light and dark.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 286 passing and `npm run build` passes.

## Re-check next round
- **Everyone (B-128, B-130):**
  - Risk, performance, correlations, returns, charts, research, fundamentals and per-stock earnings should load.
  - Check whether the 11-02 session (SPY close 752.10) is now in history and performance.
  - If 11-02 is still a hole after newer sessions arrive, filling the close from the quote is the follow-up.
- **Income and macro (B-129):**
  - When Yahoo lists the 11-02 payments, the estimates should switch to the real amounts and still be counted once.
  - Day P&L should match the performance step on ex-days.
  - The next estimates may move to 12-02, because they keep the last ex-date's day of the month.
- **Multibagger:**
  - B-088 on `/api/earnings/<sym>` (PAYS's report dates).
  - TOST reports 11-03, MNTN 11-04, INOD 11-05 and PAYS 11-09.
- **Macro:** test note 56's GLD correlation trigger now that history is back.
- **Income:** B-131 (REIT surprise) and B-064 (XOM declared $1.07) are still open.

## For a human
- **Yahoo data quality:** a single NaN close in Yahoo's daily bars took out about half of Argus.
  - It started on the first trading day after DST ended, when daily bar timestamps moved from 04:00 to 05:00 UTC.
  - It's fixed defensively now. If Yahoo keeps serving NaN closes for the latest day, filling it from the quote is worth an item.
- **Schedule timing:** this is the eleventh round in a row fired outside market hours (Monday 21:13 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer revert instruction (proposed again):** `developer.md` says `git checkout -- .`, which would wipe the lead's uncommitted backlog edits.
  - Each developer was told to revert only its own files and to use a throwaway data directory.
  - Proposal: put both instructions in `developer.md`.
- **Restart hazard (again):** `pkill -f "argus [s]erve"` matched a developer's own shell once. The developer recovered.
- **Open high-severity items:** B-017 (asset classes and bond duration), and B-016/B-055. The macro investor rated the after-hours Markets 1D (WTI −0.20% on a −7.4% day) medium-high.
- **Flaky timing test** from r010 (`test_fundamentals_ask_providers_in_parallel_and_merge`): it didn't fail this round.
- **B-115:** the month-end dividend-projection test is expected to fail around 11-26 to 11-28. Pick it before then.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead ignores it until wrap-up, as the procedure says.
