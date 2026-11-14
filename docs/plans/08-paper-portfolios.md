# 08. Paper portfolios

Roadmap item F1. Effort: medium. Needs plan 07 stage 1 (cash); stage 2 makes its returns right.

## Why

The owner wants bots (and themselves) to practice investing with play money. Argus records
whatever price and date it is given, which is right for logging real trades and useless for a
simulation: a bot could "buy" at last month's low. The improvement loop works around this with a
script outside Argus, `scripts/sim.py` on the `claude-code-recursive-oncloud` branch, which keeps
a cash ledger and sets fill prices. That script is the specification for this plan: read it. Its
rules were chosen by the owner.

Moving the rules into Argus means a paper account shows up in the UI like any portfolio, any MCP
client can trade it, and the script can go.

## Decided

1. **A paper portfolio is a cash-tracked portfolio with rules.** New columns on `portfolio`:
   `paper` (boolean, default false) and `fill_rule` (`mid` or `close`, default `mid`). It is
   created with a starting cash amount: `cash_start` is the creation date and the opening DEPOSIT
   is the starting cash. A portfolio can't be converted between real and paper afterwards.
2. **Trades happen only through orders.** `place_order(portfolio, side, symbol, qty | amount, note,
   dry_run)`:
   - fills at the last completed US session, dated that session: `mid` is (high + low) ÷ 2 of that
     session (a stock that ranged 100 to 110 fills at 105), `close` is its regular close;
   - is refused while the regular session is open (the range isn't final), and when Argus has no
     high and low for that session, or the close lies outside them (bad data: fail, don't guess);
   - is refused when it would spend more cash than the portfolio has (unlike real portfolios, which
     only warn), or sell more than is held;
   - takes `amount` in dollars as an alternative to `qty`, giving fractional shares to four places;
   - builds its own idempotency key from session, side, symbol and quantity, so a retry can't
     double-fill.
   The session's high and low come from the quote when its `session_date` is the last session,
   else from the daily bar: the same order `sim.py` uses.
3. **History can't be rewritten.** On a paper portfolio, `add_transaction` for BUY, SELL, OPENING,
   SPLIT, and editing or deleting any trade, fail with a `PAPER_PORTFOLIO` error that points to
   `place_order`. DEPOSIT and WITHDRAW are allowed (a top-up is an outside flow and performance
   treats it as one).
4. **Dividends need no bookkeeping.** Plan 07 counts estimated dividends from ex-dates as a
   receivable in the account value. That is enough for a simulation.
5. **"Day off" stays in the loop.** Whether today's round may trade (has this session been traded
   already?) is the loop's rule, not Argus's. Argus will fill several orders against one session;
   they all get the same price. The response includes the session date so a caller can tell.

## Do

- Migration for the two columns. `services/` gets a small `paper.py` for the fill price and the
  order checks, pure where possible (`fill_price(rule, high, low, close)`).
- `Argus.place_order` and `Argus.create_paper_portfolio(name, starting_cash, fill_rule, benchmark)`.
- API: `POST /api/portfolios` accepts `paper`, `starting_cash`, `fill_rule`;
  `POST /api/portfolios/{ref}/orders`. CLI: `argus portfolio create --paper --cash 10000`,
  `argus order <portfolio> BUY NVDA --amount 1500`. MCP: `place_order` (a write tool, dry run by
  default like the others) and the two parameters on `create_portfolio`.
- UI: a "Paper" badge by the portfolio name; on a paper portfolio the trade forms (Transactions
  page, the stock page's position card) become an order ticket with side, symbol and shares or
  dollars, showing the fill price and the cash left before confirming. No price or date fields.
- The portfolio list (`list_portfolios`) carries `paper` so the menu can mark it.

## Afterwards, on the loop branch

When this reaches `claude-code-recursive-oncloud`, its `scripts/sim.py` should shrink to what
Argus doesn't do (writing `docs/loop/sim/status.md` and `equity.csv`, saving and loading the
account's records) and call `place_order` for trades, and `docs/loop/trader-guide.md` should say
so. That branch has its own instructions; change them there, not here.

## Done when

- Tests: fill price for both rules; refused during the regular session, on overdraw, on missing or
  inconsistent range data; a retried order doesn't double-fill; edits, deletes and direct trades
  are refused on a paper portfolio and still work on a real one; deposits are allowed.
- The leak test lists the new route and tool, and shows one account can't place orders in
  another's paper portfolio or in one shared with it.
- In the UI, a paper portfolio can be created, traded and watched from the browser alone.
- A paper portfolio with the same trades as a `sim.py` run reports the same cash and account value.
