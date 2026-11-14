# 90. Design notes for later items

These are the roadmap's "Later" items. Each note records the design direction and the traps worth
knowing, so the thinking isn't redone. **None is ready to implement as written.** Before building
one, turn its note into a full plan in the style of the numbered files: what exists, decisions,
done-when.

## I3. Tax view

- **What an investor needs:** realized gains and losses by tax year, split short term (held a year
  or less) and long term; losses available to harvest today; and the tax cost of a sale before
  making it.
- **The data is already there.** `services/lots.py` records every realization with the lot's open
  date, proceeds and cost (`Realization`). A report is a grouping of those by year and holding
  period. No schema change.
- **Lot selection.** Sales are FIFO. Tax-aware investors pick lots (highest cost first, or specific
  lots). That needs a `lot_method` per sale, or per portfolio, and `_apply_sell` to honor it. It
  changes realized P&L history, so make it opt-in per sale, never retroactive.
- **Wash sales** (a loss disallowed when the same security is bought within 30 days either side):
  flag them; don't try to adjust basis at first.
- **What-if:** `simulate_trades` already returns FIFO realized P&L; add the short and long split.
- Rules differ by country. Label everything "US federal rules, for planning; not tax advice", and
  keep the rules in one module.

## I4. Corporate actions beyond splits

- **Symbol change:** a transaction that renames a position from a date on, carrying lots and cost.
  Price history must be joined under the new symbol.
- **Merger for cash:** a SELL at the deal price. For stock: lots convert at a ratio to the
  acquirer's symbol, keeping open dates and cost. Mixed: both.
- **Spin-off:** new lots in the child with part of the parent's cost, by a stated allocation.
- All three are "transform lots" operations in `build_positions`, like SPLIT. Performance must
  treat them as no flow. Start with symbol change and stock merger: they cover most cases.
- Detecting them automatically is hard and error-prone. Record them by hand first; the split
  warning (`Argus.split_warnings`) is the pattern for prompting the user when data suggests one.

## I8. Performance measures and attribution

- **Risk-free rate.** Sharpe uses zero (`performance.summarize`, `risk_free_annual=0.0`). The macro
  provider already loads Treasury par yields; use the 3-month bill, averaged over the period, and
  say so in the label.
- **Sortino** (downside deviation only) and **tracking error / information ratio** against the
  benchmark come from the same daily series.
- **Benchmark start.** Backlog B-053: excess return starts the benchmark at the prior close and the
  portfolio at its fills. Fix it with the cash work (plan 07 stage 2), which restructures the
  series anyway.
- **Attribution.** "Which positions made or lost the excess return?" Per day, each position's
  contribution is its weight at the prior close × its return; summed over the range. Group by
  sector or asset class for a table: contribution, and allocation versus selection against the
  benchmark's sector weights (the sector ETFs on the Markets page can stand in for those). Build it
  on the per-portfolio daily series from plan 07.
- **Money-weighted return** is in plan 07.

## F2. Rebalance planner

- Input: targets (by position, sector or asset class), current holdings, cash, and constraints:
  whole shares or fractions, a minimum trade size, "don't sell at a short-term gain", a no-sell
  list.
- Output: a trade list that brings every weight inside its band with the fewest trades, and the
  cash left. `analysis.drift` already gives the dollar gap per target; the planner rounds, nets
  buys against sells and applies the constraints.
- Present it as a what-if (`simulate_trades` shows the after-state); recording the trades stays a
  separate, explicit step.
- Needs plan 07 (cash) and benefits from plan 09 (targets by asset class).

## F3. Screener

- **Fresher fundamentals.** The universe is built from SEC "frames" for the last calendar year
  (`services/screener.py`), so growth is a year old by autumn (backlog B-019). Trailing-twelve-month
  figures need per-company facts for thousands of companies: far heavier than one frame per
  metric. A middle path: frames for the latest two quarters, combined with the annual.
- **Sector and industry** (B-060): the universe rows have none. SEC supplies a SIC code per
  company; map it to sectors.
- **Saved screens**: an owned table, per account (all the owned-table steps apply).
- **Valuation against a company's own history** (B-052): needs the ratio history that only Finnhub
  provides per symbol, so it can't be a universe-wide filter; offer it as a column for the result
  page's top rows.

## F4. Research depth

- **SEC filings list** on the stock page (B-121): EDGAR's submissions endpoint lists recent
  filings with links. Cheap, and it removes a reason to leave Argus.
- **Segment revenue and guidance** (B-090): in XBRL for some filers, in press releases for most.
  Start with what XBRL gives; don't parse prose.
- **Earnings-call transcripts:** no free, reliable source. Link out instead.
- **"Why did it move"** (B-096): for a holding that moved more than a threshold, show the day's
  headlines and whether it reported. The pieces exist (`events.news`, the earnings calendar).

## F5. Macro

- Real yields, breakevens, credit spreads and a dollar index (B-037): FRED publishes all of them,
  but needs a free API key. Backlog items that need a new key were out of scope for the loop; this
  is the owner's call.
- Futures and overnight moves (B-055): Yahoo has index futures symbols (`ES=F`, `NQ=F`). The Markets
  page already shows instruments by Yahoo symbol.

## F6. Ask Argus

A question box in the UI answered with Argus's own tools. The MCP server already exposes the tools;
the missing parts are a model to call them and a place to run it. That means an API key for a
model provider on the server and a cost per question: the owner's decision. If built, it must act
as the signed-in account (the per-request account mechanism the MCP server uses) and be read-only
by default.

## F8, F9. Sharing and what-if history

- **Comments** on a shared portfolio: an owned table keyed by portfolio and author; readable by
  everyone the portfolio is shared with. A **household view** that combines chosen accounts needs
  consent from each account, so model it as mutual shares, not as a new role.
- **What-if history** ("if I had bought the index instead"): run the performance engine on a
  hypothetical transaction log derived from the real one (same dates and dollar amounts, a
  different symbol). No storage needed.

## F10, F11. Bigger bets

- **Options, shorts, other currencies:** each touches lots, pricing, performance and risk. Do none
  without a concrete need. Shorts are the smallest (negative lots; `_apply_sell` refuses them
  today).
- **Postgres:** only when Argus runs as more than one process or serves many active users. The
  SQLite-specific code is in `db.py` (pragmas, the migration runner), the upserts
  (`sqlite.insert … on_conflict`), batch-mode migrations, `services/backup.py` and the snapshot
  loader.

## C1, C2. Code structure

- **`app.py`** (1,932 lines). Don't rewrite it in one go. When a plan works in a domain (dividends,
  research, valuation, events), move that domain's logic into its service module and leave a thin
  method on `Argus`. The services that exist (`portfolio`, `alerts`, `watchlist`, `notes`) show the
  shape.
- **A typed API contract.** Routes return dicts and `frontend/src/api.ts` re-declares each shape by
  hand. Add response models route by route, starting with the routes a plan is already changing,
  then generate the TypeScript types from FastAPI's OpenAPI schema. Until then, a test that the
  mocked responses in `frontend/tests/fixtures.ts` match the real API's keys would catch drift.

## P3, P6. Performance as data grows

- **P3.** Performance replays the whole trade history on each request (1.6 s cold in the review,
  and it grows with history). Cache the per-portfolio daily series, keyed
  by `portfolios.revision` and the last session, in memory. Plan 07's split into "per-day value
  and flows" and "chain returns" makes the cached unit obvious.
- **P6.** The frontend refetches on every page visit and never cancels a request (101 effects, no
  abort signals). A small wrapper around `fetch` that caches GETs by URL for a few seconds,
  de-duplicates in-flight requests and cancels on unmount would remove most of it. Adopting a
  data-fetching library is the larger alternative; decide when the wrapper stops being enough.
