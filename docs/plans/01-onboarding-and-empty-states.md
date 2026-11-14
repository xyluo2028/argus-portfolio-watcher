# 01. New-account onboarding and empty states

Roadmap items B1, B2, B9. Effort: small. Frontend only, except one backend line.

## Why

Since v6 anyone can create an account on the sign-in page. A new account has no portfolio, and for
that case the app shows one dead-end card: "No portfolios yet", with a link to a CSV import and
instructions that need a terminal on the server. A person who signed up from a browser can't
create a portfolio at all, and can't reach Markets, Screener, Watchlist, DCF or Alerts, which need
no portfolio. The same screen greets a bot's owner signing in as the bot.

Two related problems make an empty account worse: opening Analysis on a portfolio with no
positions blanks the page (B2), and nothing catches a render error, so one bad field takes down
the whole view.

## What exists

- `frontend/src/App.tsx`, `Main`: when `portfolios.length === 0` it routes only `/data` and
  `/account`; every other path shows the "No portfolios yet" card.
- `POST /api/portfolios` (`PortfolioBody`: `name`, `benchmark` default `SPY`) creates a portfolio
  for the signed-in account. The frontend's `api.ts` has no call for it.
- Pages that need a portfolio: Dashboard, Transactions, Analysis. Pages that only use it as a
  convenience: Ticker (reads your position with `api.portfolio(portfolio)`), Compare (suggests your
  holdings). Pages that don't use it: Watchlist, Markets, Screener, Dcf, Alerts, Data, Account.
- `services/analysis.py`, `exposure()`: returns `{"total_value": 0.0}` when nothing has value, so
  `concentration` is missing and `pages/Analysis.tsx` reads `c.top1_pct` of undefined.
- `components/PositionCard.tsx` prints "Not held in {portfolio}" with the raw prop. For a portfolio
  shared with you that prop is its id (`portfolioKey`), so it reads "Not held in 2".

## Decided

1. **Route every page whether or not a portfolio exists.** The market pages work without one. Pages
   that need one show an inline empty state instead of the app refusing to render.
2. **Create portfolios in the UI**, in two places: the empty state, and a "New portfolio…" entry at
   the end of the portfolio menu in the top bar. A portfolio needs a name and a benchmark (default
   SPY). After creating, select it and go to the dashboard.
3. **The empty state is one component**, used by Dashboard, Transactions and Analysis when there is
   no portfolio: a short welcome, the create form, and two secondary routes: "Import an
   Investing.com CSV" (links to Data) and "Restore a backup" (links to Data). No terminal commands:
   a signed-up user has no shell.
4. **A portfolio with no transactions is a normal state**, not an error. Dashboard says "No
   positions yet" with a link to Transactions ("Record your first trade"); Analysis says there is
   nothing to analyze yet. No card shows a spinner forever or prints `NaN`.
5. **An error boundary wraps each route's element.** A render error shows "Something went wrong on
   this page" with the error message and a reload button, and the top bar keeps working. This is a
   safety net; still fix B2 at the source.
6. **The server returns a full shape for an empty portfolio.** `exposure()` returns the same keys
   with zeros and empty lists, so no client has to special-case it (the MCP tool and CLI use it too).

## Do

Backend:

- `services/analysis.py`: when `total <= 0`, return every key the full result has: `total_value`
  0, the four tables as empty lists, `concentration` with `top1_pct`, `top5_pct`, `top10_pct` 0,
  `hhi` 0, `effective_positions` null and `positions` 0, `top_stock_exposure` and
  `funds_without_profile` empty. Check `concentration([])` callers for the same assumption
  (`simulate_trades` reads `concentration_before` and `_after`).

Frontend:

- `api.ts`: `createPortfolio(name, benchmark)`.
- `App.tsx`: remove the zero-portfolio branch of the router; add the "New portfolio…" menu entry
  (it is a `<select>`: use a sentinel value that opens the form and then restores the selection);
  wrap route elements in the error boundary; keep `loadPortfolios` as the way to refresh the menu
  after a create.
- A `NoPortfolio` component (the empty state) and a `NewPortfolioForm` (name, benchmark with the
  existing `TickerInput`, Create). Show the server's message on `ALREADY_EXISTS`.
- Dashboard, Transactions, Analysis: render `NoPortfolio` when there is no selected portfolio.
  Ticker and Compare: skip the portfolio calls when there is none, and hide the position card's
  trading controls (there is nowhere to record a trade).
- `PositionCard`: take the portfolio's display name for the "Not held in …" line (B9: for a shared
  portfolio the prop is an id). When the symbol is held in another of your portfolios, say which:
  the `all` view's transactions carry a `portfolio` name per row, so one call to
  `api.portfolio("all")` or the existing data can answer it. Keep it to one extra request at most.
- The Data page's "Delete a portfolio" card already handles an empty list.

## Leave alone

- Sign-up, sign-in and the Account page.
- Portfolio rename and benchmark change: plan 12.
- Any change to what an existing user with portfolios sees, apart from the new menu entry.

## Done when

- A new account can, from the browser only: create a portfolio, record a trade, see it on the
  dashboard; and can open Markets, Screener, Watchlist, DCF and Alerts before creating anything.
- Analysis on a portfolio with no transactions renders with zeros and an explanatory line.
- Throwing inside one page shows the boundary's message while the navigation still works.
- `GET /api/portfolios/<empty>/exposure` returns the full shape. Add a backend test for it and for
  `simulate_trades` on an empty portfolio.
- The phone tests cover the no-portfolio state: add a fixture variant where `/api/portfolios`
  returns `[]`, and assert the create form shows and the market pages open. Remember unexpected
  writes throw in the fixtures: mock the `POST`.
- Checked in a browser at 1400 px and 390 px, light and dark, as an account with no portfolios, one
  empty portfolio, and one portfolio shared with it and none of its own.
