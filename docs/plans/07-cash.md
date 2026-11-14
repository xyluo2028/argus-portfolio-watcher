# 07. Cash

Roadmap item I1, and the money-weighted return from I8. Effort: large, in three stages that ship
separately. Plan 08 (paper portfolios) builds on stage 1; plan 09 (asset classes) uses stage 3.

## Why

Argus tracks positions and nothing else. A portfolio has no cash balance, so Argus can't say:

- what the account is worth (positions plus cash);
- what the investor actually earned on their money, as opposed to how the positions performed;
- whether a buy is affordable, or how much dry powder is left;
- a target allocation with a cash share. Today targets that sum to under 100% show phantom sells
  (loop backlog B-024).

It is also why the improvement loop's trader bot needs an outside script to keep a cash ledger.

`services/performance.py` documents the current model at its top: with no cash, every buy is money
coming in and every sell or dividend is money going out. That stays true for portfolios that don't
track cash.

## Decided: the model

1. **Cash tracking is optional, per portfolio, with a start date.** A new nullable column
   `portfolio.cash_start` (a date). Null means "positions only": everything behaves exactly as
   today. Existing portfolios stay null. Nobody is forced to reconstruct years of deposits.
2. **Cash is derived from transactions, not stored.** From `cash_start` on:

   | Transaction | Effect on cash |
   |---|---|
   | DEPOSIT (new) | + amount |
   | WITHDRAW (new) | − amount |
   | INTEREST (new) | + amount (income, not a deposit) |
   | BUY | − (qty × price + fee) |
   | SELL | + (qty × price − fee) |
   | DIVIDEND | + amount |
   | FEE | − amount |
   | OPENING, SPLIT | none (shares arrive or change; no money moves) |

   A transaction counts when its New York trade date is on or after `cash_start`. Earlier ones
   never touch cash: that is what lets someone switch tracking on for a portfolio with history.
3. **The opening balance is a DEPOSIT dated `cash_start`**, created when tracking is switched on
   ("cash in the account at the start of that day"). No separate balance field.
4. **The three new types are ledger rows, not security trades.** They use the reserved symbol
   `$CASH` (not a valid ticker, so it can't collide; note that `CASH` is a real ticker), with
   `qty` and `price` 0 and a positive `amount`.
5. **Real-money portfolios are never blocked.** If a trade or withdrawal would take cash below
   zero, record it anyway and return a warning ("cash would be −$X: record a deposit, or check the
   start balance"). People forget to log deposits; refusing their real trades would make the
   record worse. Strict enforcement belongs to paper portfolios (plan 08).
6. **Estimated dividends count as a receivable.** Argus already estimates dividends from ex-dates
   held through that no DIVIDEND transaction records (`Argus.accrued_dividends`). Account value is
   positions + cash + those accrued dividends, shown as its own line. When the investor records the
   real DIVIDEND, the estimate drops out and cash rises by the same amount, so the total holds.
7. **Naming.** `services/portfolio.py` has `CASH_TYPES = {DIVIDEND, FEE}`, which means "types that
   carry an amount". Rename it `AMOUNT_TYPES` and extend it; call the new group `LEDGER_TYPES`.
   Put the cash arithmetic in a new pure module `services/cash.py` (no database), like `lots.py`.

## Decided: how to keep ledger rows out of everything else

This is the main risk. Dozens of places iterate a portfolio's transactions and assume every row is
a security: `build_positions` creates a position per symbol, performance and dividends fetch prices
for `{t.symbol for t in txns}`, the split check, the hub. A `$CASH` row reaching any of them means
a phantom position or a failed quote lookup.

**Contain it at the source: the accessors return security transactions unless asked.**

- `PortfolioService._active_txns(s, portfolio_id)` and `active_transactions(portfolio)` gain a
  parameter, default off, to include ledger rows. Every existing caller keeps getting securities
  only and needs no change.
- Only cash-aware code asks for ledger rows: the cash balance, the transaction log
  (`list_transactions`, which should show everything), performance from stage 2, snapshots (which
  copy tables directly and are unaffected).
- `_add_transactions` validates a batch with `build_positions([*existing, *new])`: filter ledger
  rows out of that call, and skip the ticker checks for them.
- After the change, grep for every use of `Transaction` and `.transactions` and confirm each one
  either goes through the accessors or handles ledger rows. `models.py` defines a
  `Portfolio.transactions` relationship; check whether anything reads it.

## Stage 1: the ledger and the balance

Schema and types:

- Migration: `portfolio.cash_start` (nullable date). `TxnType` gains `DEPOSIT`, `WITHDRAW`,
  `INTEREST`. Bump both snapshot versions (`VERSION` and `ACCOUNT_VERSION` in
  `services/snapshot.py`): an older Argus would crash on a `$CASH` row, so it must refuse the file.

Backend:

- `services/cash.py`: `balance(txns, cash_start, as_of=None)` and a per-day running balance (stage
  2 needs it).
- `PortfolioService`: `set_cash(ref, start, opening_balance, actor, dry_run)` switches tracking on
  (sets `cash_start`, inserts the opening DEPOSIT) or moves the start; `clear_cash(ref)` switches it
  off (sets null; ledger rows stay and are ignored). Both need `write=True` and an audit row.
- Adding a transaction returns `cash_before`, `cash_after` and any warning when the portfolio
  tracks cash. Editing and deleting work for ledger rows (amount, date, note).
- Summary (`PortfolioService.summary` and `Argus.portfolio`): `totals.cash` (null when not
  tracked), `totals.account_value` (market value + cash + accrued dividends; null when not tracked
  or not fully priced), `totals.cash_pct`. Leave `weight_pct` and every other existing field as is
  in this stage.
- The `all` view: `cash` is the sum over your portfolios that track it; `account_value` is given
  only when all of them do. Say which in a `cash_partial` flag.
- What-if (`Argus.simulate_trades`) already returns `net_cash`; add `cash_before` and `cash_after`
  when tracked.

Surfaces:

- API: `PUT /api/portfolios/{ref}/cash` (`start`, `opening_balance`, `dry_run`) and `DELETE` to
  switch off; the existing transaction routes accept the new types with no symbol.
- CLI: `argus portfolio cash <portfolio> --start YYYY-MM-DD --balance N` and `--off`;
  `argus txn add <portfolio> DEPOSIT --amount N`.
- MCP: `add_transaction` accepts the new types (update its description); a `set_portfolio_cash`
  tool; `get_portfolio`'s description mentions the cash fields.
- UI: Transactions page offers Deposit, Withdraw and Interest with an amount and date only; the
  dashboard shows a Cash tile and, when tracked, makes the headline number the account value with
  "of which cash" beneath; a "Track cash" control with start date and balance. If plan 12's
  portfolio settings card exists, put it there; otherwise on the Data page.

Tests: the balance table above, row by row; a trade before `cash_start` doesn't move cash; negative
cash warns and records; ledger rows never appear in positions, performance symbols, dividends or
the split check (assert no provider is asked for `$CASH`); snapshots round-trip a tracked
portfolio; the leak test lists the new routes and tool.

## Stage 2: returns that know about cash

Today's daily return in `compute_series` is `r = (V + Out) / (V_prev + In) − 1` with buys as `In`
and sells and dividends as `Out`. Keep that formula and change what the terms mean from
`cash_start` on:

| | Before `cash_start` (or never tracked) | From `cash_start` |
|---|---|---|
| `V` | positions | positions + cash |
| `In` | buys, OPENING at market value | DEPOSIT |
| `Out` | sells, dividends, less fees | WITHDRAW |

Trades, dividends, interest and fees become internal moves between cash and positions. On the
start day itself, `V_prev` is positions only and the opening DEPOSIT is that day's `In`, so the
series is continuous. Cash below zero is included as it is.

- **Restructure first.** Split `compute_series` into a function that produces per-day
  `(value, in, out)` for one portfolio, and a function that chains returns from such a series.
  The `all` view then sums the per-portfolio series day by day before chaining, which is the only
  correct way to combine portfolios with different `cash_start` dates. Today `all` feeds every
  transaction into one replay.
- **Money-weighted return.** Add `mwr_pct` to the performance summary for every portfolio, tracked
  or not: the internal rate of return of the day-by-day flows (`Out − In` dated each day), the
  starting value as an initial outlay for a sliced range, and the ending value as the final inflow.
  Solve by bisection on the daily rate; annualize when the range is a year or longer, otherwise
  report the period return it implies; return null when the flows have no sign change. Label it
  "your return on the money you put in" next to the time-weighted "how the portfolio performed".
- Update the docstring at the top of `services/performance.py`: it states the positions-only model.

Tests: a tracked portfolio that deposits 1,000, buys 500 of a stock that rises 10% shows +5% for
the account; a deposit on a later day doesn't move the return; switching tracking on mid-history
gives a continuous series; `all` with one tracked and one untracked portfolio; IRR against
hand-computed cases (one deposit; two deposits at different times; a withdrawal).

## Stage 3: weights of the whole account

For a portfolio that tracks cash, every percentage means "of the account":

- Summary: `weight_pct` per position becomes value ÷ account value.
- Exposure (`services/analysis.py`): a `Cash` row in the type and sector tables.
- Targets and drift: `Cash` is a valid target key at the symbol level, so targets can sum to 100
  with a cash share. Its "trade to target" is informational. This closes backlog B-024.
- Risk (`services/risk.py`, `analyze`): take the cash amount; weights are value ÷ (positions +
  cash), so beta and volatility shrink with the cash share while dollar VaR is unchanged.
- Concentration: positions' weights with the account as denominator.

Portfolios that don't track cash keep today's numbers exactly. Tests for each: with cash equal to
the positions' value, beta and volatility halve and dollar VaR doesn't move.

## Ask the owner

- Whether their existing portfolios should start tracking cash, from what date and balance. It is
  their data; the feature must not switch itself on.

## Leave alone

- Margin, interest on debit balances, multiple currencies.
- Automatic booking of dividends into cash: plan 08 does it for paper portfolios. For real ones,
  the receivable in decision 6 is enough for now.
- The importer (`importers/investing.py`): the export has no cash.

## Done when (each stage)

- Its tests pass, along with the whole suite and the frontend build.
- A portfolio that never switches tracking on returns byte-for-byte the same summary, performance,
  exposure, drift and risk as before the change. Prove it with a test that compares before and
  after on a fixture, not by inspection.
- The UI was checked on a throwaway server with one tracked and one untracked portfolio, at both
  widths.
- README and the MCP tool descriptions say what the cash fields mean.
