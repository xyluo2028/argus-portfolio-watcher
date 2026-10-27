# Round 006 summary

Date: 2026-10-27, starting about 02:13 UTC. In New York that's Mon 10-26 at about 22:13 ET, so the market was closed. All values are at the 10-26 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 10-26 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,747.15 | $98,889.95 | +$142.80 | $1,253.87 | +0.14% |
| loop-income | 17 | $98,998.52 | $100,020.33 | +$1,021.81 | $1,001.48 | +1.02% (+1.06% with the $33.76 PG dividend accrued) |
| loop-growth | 11 | $97,758.05 | $96,461.18 | −$1,296.87 | $2,241.95 | −1.30% |

**Trades this round:**
- **loop-income:**
  - Bought 1 JPM @ $334.40 and 1 HD @ $317.00, both at post-market prices (thesis notes 44 and 45).
  - Added alert #8: ABBV down 5% or more in a day (ABBV reports 10-30).
  - Forward income is $3,348 a year (3.35%). Bond ETFs are 35.1% of the book, above the 30% floor.
- **loop-growth:**
  - Bought 25 RMBS @ $90.32 after its Q3 beat: revenue +22.3%, operating margin 38.3%. The position is now 121 shares at an average of $92.98, 11.25% of capital.
  - Thesis note 46 replaces the pre-earnings note 43.
  - MNTN went on the watchlist (note 47) ahead of its 11-04 report.
- **loop-macro:**
  - No trades: every position is within ±0.42 pp of target, and FOMC (10-28) and PCE (10-29) are close.
  - SELL 6 GLD / BUY 24 IEF is simulated and parked in note 48, to review on 10-29 after PCE.

The portfolios are saved in `docs/loop/sim/snapshot.json`. The snapshot's audit log also shows a scratch portfolio (`scratch-b046`) that a developer created for a live check and then deleted.

## Triage
The investors filed 25 findings: macro 9, multibagger 9, income 7.
- **New items:** B-085 to B-092, plus B-093, the part of B-013 not fixed this round.
- **Found by two investors:**
  - B-013 (macro and income).
  - B-046 (income and multibagger; severity raised to high).
  - B-083 (income and multibagger; it covers every momentum period now, not just 1 week).
  - B-076 (macro and income).
- **Existing items with new evidence:** r006 lines on 30 items, among them B-002, B-009 (raised to high), B-017, B-019, B-023, B-036, B-059, B-067 and B-075.
- **Moved to Done:** B-025, B-068 and B-074 shipped last round and were confirmed by the investors this round.

**Picks:**
- **B-085:** errors (500s).
- **B-046:** wrong numbers, two investors.
- **B-013:** wrong numbers, two investors, sixth round reported.

## Shipped
- **B-085, stock page 500s on first open (7a9d693).**
  - A new `upsert()` in `db.py` writes in one statement: insert, or update if the row exists. The cache tables filled on read paths use it: company and fund profiles, dividend history, the security map, fundamentals and the bars refresh log.
  - The instrument refresh no longer holds a transaction open across its Yahoo calls.
  - A test reproduces the race. Live, simultaneous `/profile` and `/holdings` requests on three uncached symbols all returned 200.
- **B-046, trades after the close (0cdd051).**
  - A trade after the regular close of its New York day counts from the next session, through the new `trade_session()` in `market_calendar.py`. It no longer changes that session's Day P&L, Day %, performance-series flow or TWR. Its move from the fill price shows in after-hours P&L only.
  - Live results:
    - loop-income Day P&L is back to +$205.82, and `flow_in` on 10-26 is 0.
    - loop-growth "last session" is +0.92% again.
    - The brief now shows RMBS +5.45%, the stock's own move.
- **B-013, upcoming dividends disagree (f76fbf4), this round's slice.**
  - A dividend pay counts as held only if the portfolio held shares on its ex-date. The unentitled JPM 10-31 pay is gone from Coming up and the brief; /t/JPM shows it as "not owed".
  - Coming up, the brief and stock-page Events now include the Dividends projection's estimated ex-dates, marked "est.". For loop-income, BND, VCIT, VGIT and SCHP add up to $131.93.
  - Estimated ex-dates move off weekends and holidays to the next trading day: Sun 11-01 → Mon 11-02, NEE → 11-30.
  - The rest is now **B-093**: the Dividends page ignores announced ex-dates (KO ~12-15 vs 12-01, NEE ~11-30 vs 11-27), and projections stop at Dec 31. VTIP's December dividend (B-054) is still open.

Nothing was blocked. `uv run pytest -q` reports 252 passed, and `npm run build` passes.

## Re-check next round
- **All three: after-close trades (B-046).**
  - On the next session, a lot bought after the close should run its Day P&L from the fill, and the series change should equal Day P&L.
  - Overnight, `/performance` leaves out the evening's after-close buys until the next session's point exists. Tonight loop-growth's `end_value` is $94,203 while the dashboard shows $96,461. Confirm the two line up once 10-27 is in the series.
  - loop-growth's history was restated: GRND and INOD, bought 10-20 at 22:18 ET, now count from 10-21.
  - After-close **sells** weren't covered by this change.
- **Income and macro (B-013):**
  - Coming up and the brief should show no JPM pay and should show the 11-02 estimates (BND, VCIT, VGIT, SCHP; IEF, SGOV).
  - When those ex-dates pass, check the accruals.
- **Everyone: first opens (B-085).** Opening stock pages not visited yet should give no 500s.
- **Newly added holdings:** sector and type should still fill in, because the instrument refresh was restructured for B-085.
- **Income:** when PG's dividend is paid in mid-November, record it as a `DIVIDEND`.
- **Multibagger:** MNTN reports 11-04. Watch B-088, the vanished past report.

## For a human
- **Schedule timing:** this is the sixth round in a row fired outside market hours, at about 22:13 ET. The README asks for weekdays during market hours. Same-session behavior (B-046's next-session lot, B-025) still can't be checked live.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer revert instruction:** `developer.md` says to `git checkout -- .` when abandoning work. That would also wipe the lead's uncommitted backlog edits. This round each developer was told to revert only its own files. Proposed: change `developer.md` to say so.
- **Scratchpad:** proposed again: put each investor's own scratch subfolder in the investor guide.
- **Open high-severity items:** B-009 (the valuation card lags the SEC table after a print), B-017 (asset-class view and duration) and B-046's follow-up on after-close sells.
