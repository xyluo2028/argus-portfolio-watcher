# Argus: review and roadmap

November 2026, at `main` after the v6 merge (`5307191`). Written from two seats: a programmer
reading the code, and an investor using the product.

## How this review was done

- Read the backend (12,200 lines of Python), the frontend (8,200 lines of TypeScript and CSS), the
  tests, the deployment files and the docs.
- Ran the test suite: 421 backend tests pass in 15 s. The phone UI suite passes on Chromium; two
  tests fail on WebKit (see B8).
- Ran Argus on realistic data (about 70 positions and a 12-name watchlist) and timed every main
  API call cold and warm.
- Opened every page at desktop (1400 px) and phone (390 px) width. No page threw an error and none
  scrolled sideways.
- Read the improvement loop's backlog on `claude-code-recursive-oncloud`: 168 findings from 16
  rounds, 48 fixed, 119 still open (48 bugs, 42 usability, 26 features, 2 performance, 1 removal).

Item IDs below (B = bug, S = security, O = operations, P = performance, C = code, I = investing,
F = feature) are used in the roadmap at the end, and in the implementation plans under
[`plans/`](plans/README.md), which say how to build each item. Effort is S (a day or less), M (a few days),
L (a week or more).

## Summary

Argus is in good shape for what it set out to be: a local-first monitor for one person's US stocks
and ETFs that an AI agent can operate as easily as a person. The portfolio math is careful, the
numbers carry their source and date, and the backend is well tested.

The v6 work turned it into a multi-account server, and that is where most of the new gaps are: the
product still assumes one person who has a terminal.

The six things most worth doing next:

1. **A new account can't start** (B1). Someone who signs up sees "No portfolios yet" and
   instructions that need a terminal. The web UI can't create a portfolio, and Markets, Screener,
   Watchlist and DCF are hidden until one exists.
2. **Sign-in travels in the clear off localhost** (S1, S2). The server listens on plain HTTP, and
   the token cookie holds the server's secret itself.
3. **Nothing restarts or backs up the server on a Mac** (O1, O2). It runs from a shell command, and
   backups run only when someone runs them.
4. **The first load after a weekend or restart can take over a minute** (P1). The daily brief took
   105 s cold and the watchlist 38 s; warm, both are under 0.2 s.
5. **Cash doesn't exist** (I1). Argus tracks positions only. That blocks true account returns,
   paper trading, cash-aware targets, and it is the reason the loop needs an outside script.
6. **Bond and multi-asset portfolios are second-class** (I2, B3). Bond funds show as
   "Unclassified" or, in one case, as 100% Technology; risk uses equity factors and beta to SPY.

## What is strong

- **Portfolio math.** FIFO lots, time-weighted return with flows handled explicitly, after-hours
  trades assigned to the right session, dividends accrued from ex-dates, splits re-based. Each rule
  is written down where it lives and covered by tests.
- **Honest numbers.** Quotes carry `as_of`, session and source; fundamentals say which provider
  supplied each field and flag stale SEC data; estimates are marked as estimates.
- **Agent-first design.** One facade (`Argus`) serves the API, CLI and MCP server. Writes default
  to a dry run, take an idempotency key and return before/after. Errors have stable codes and hints.
- **Account separation.** Every owned query goes through one filter (`access.py`), code with no
  account fails instead of guessing, and a test calls every API route and MCP tool as a second
  account and fails when a new one isn't covered.
- **Tests.** 421 backend tests, providers faked, no network, 15 seconds.
- **Breadth for its size.** Research, valuation bands, a DCF calculator, a screener on SEC data,
  risk with stress replays and factor exposures, a market-context page, dividends and an earnings
  calendar.

## Bugs

Confirmed in this review unless marked as from the backlog.

| ID | What happens | Evidence | Fix | Effort |
|---|---|---|---|---|
| B1 | A new account is stuck at "No portfolios yet". The text points to the terminal and to a server-side snapshot load. The UI has no "create portfolio", and with no portfolio only Data and Account are routed, so Markets, Screener, Watchlist and DCF are unreachable. | `App.tsx`: the zero-portfolio branch routes two pages; `api.ts` has no create call. Backlog B-004. | A "New portfolio" form (name, benchmark) on that screen and in the portfolio menu; route the market pages regardless of portfolios. | S |
| B2 | Opening Analysis on an empty portfolio blanks the whole page. | `GET /api/portfolios/<empty>/exposure` returns no `concentration`; `Analysis.tsx` reads `c.top1_pct`. There is no error boundary, so one render error takes the page down. Backlog B-155. | Return a zeroed `concentration`, guard the card, and add an error boundary around each route. | S |
| B3 | A bond fund is counted as 100% Technology in look-through sectors. | BNDX is 98.6% bonds, but its Yahoo sector weights (which describe its small equity sleeve) are applied to its whole weight. Bond funds with no fund profile fall into "Unclassified". | Scale sector weights by the fund's equity share; put the rest under its asset class. Part of I2. | S |
| B4 | The "Delete a portfolio" preview counts "days of performance history" that never exist. | The `nav_daily` table is never written; performance is recomputed on each request. | Drop the table and the count, or use the table as the cache proposed in P3. | S |
| B5 | Deleting any portfolio writes a snapshot of the whole instance to disk. | `Argus.delete_portfolio` calls the instance-wide `snapshots.dump`, which now includes every account's records and password hashes. | Save the deleting account's own snapshot instead. | S |
| B6 | The DCF calculator's defaults produce absurd answers for fast growers. | NVDA opens at "fair value 349% above today's price": 30% growth for five years with no decay, valued at the 5-year median multiple (54.9x against 29.3x today). | See I7: conservative defaults and a sensitivity grid. | M |
| B7 | Economic calendar rows with the same name can't be told apart (two "Core PPI", two "PPI"), and the yield curve's end labels overlap. | Markets page; backlog B-091. | Name month-on-month and year-on-year server-side; offset the labels. | S |
| B8 | Two phone tests fail on WebKit: tapping an autocomplete suggestion leaves the typed text, and tapping the comparison chart doesn't show values in the legend. | `frontend/tests/mobile.spec.ts`; both fail on older commits too. Likely real iPhone touch bugs. | Reproduce on WebKit, fix the touch handlers. | S–M |
| B9 | The stock page says "Not held in <portfolio>" when another of your portfolios holds it. For a portfolio shared with you it prints the portfolio's id ("Not held in 2"). | Backlog B-081; `PositionCard.tsx` prints its raw prop. | Say where it is held, by name. | S |
| B10 | The open backlog: 48 bugs. | Most are disagreements between two sources for one figure; see I5. | Triage first: many are duplicates or fixed since. | L |

## Security and multi-account hardening

Argus is now a server that strangers on the same network can reach and sign up to. These are
ordered by how much they matter.

| ID | Issue | Why it matters | Fix | Effort |
|---|---|---|---|---|
| S1 | The token cookie stores `ARGUS_TOKEN` itself. | A stolen cookie is the server's permanent secret, and signing out doesn't revoke it. Account sign-ins already use a random server-side session. | Give token sign-ins a server-side session too. | S |
| S2 | Plain HTTP off localhost. Cookies are marked Secure only when the request is HTTPS. | On a LAN address, passwords and cookies cross the network unencrypted. Tailscale encrypts its own traffic; a LAN IP doesn't. | Document and default to HTTPS in front (`tailscale serve`, Caddy); warn at startup when listening on a non-loopback address without it. | S |
| S3 | Open sign-up on a server bound to all interfaces. | Anyone who can reach it gets an account and can spend the shared provider quotas. `ARGUS_SIGNUP=off` exists but is not the default. | Consider invite codes (a one-time code made from the CLI), or default sign-up to off when the bind address isn't loopback. | S–M |
| S4 | Sign-in throttling is per username, in memory. | Ten wrong passwords lock a known username out for 15 minutes (anyone can lock you out); there is no per-address limit, and each attempt costs an scrypt hash. | Throttle per address as well as per name; back off instead of locking. | S |
| S5 | API keys are all-powerful and don't expire by default. | A key given to a bot or script can do everything but manage keys. | Read-only keys; per-key scopes later. | M |
| S6 | No per-account limits. | Any account can request unbounded symbol lists, trigger a screener rebuild, and grow the in-memory research and valuation caches without bound. Names and notes have no length limits; request bodies have no size limit. | Size limits on bodies and fields, a cap on symbols per call, bounded caches, a per-account request budget for provider-backed calls. | M |
| S7 | No security headers. | No Content-Security-Policy, `frame-ancestors`, `nosniff` or referrer policy. | One small middleware. | S |
| S8 | Sessions last 90 days, with no way to see or end them. | A lost phone stays signed in. | List sessions on the Account page with "sign out everywhere". | S |
| S9 | No account deletion. | An account can be disabled from the CLI, but its records stay forever. | `argus user delete` and a self-service delete that removes the account's records. | S |
| S10 | Small leaks between accounts. | The share form reveals whether a username exists. An import can set the shared name of an instrument. The hub streams live prices for the 48 largest positions across all accounts, so a bot's holdings compete with yours for slots. | Uniform errors; keep instrument metadata provider-sourced; allocate streaming slots per account. | S–M |
| S11 | The audit log has no reader. | Each change records who made it, but nothing shows it. | An activity view on the Account page; `argus audit`. | S |

## Reliability and operations

| ID | Issue | Fix | Effort |
|---|---|---|---|
| O1 | On macOS the server runs from a shell command: it doesn't start at boot, isn't restarted if it dies, and stops while the Mac sleeps. `deploy/` has systemd units only. | A launchd agent (`deploy/com.argus.serve.plist`) with keep-alive, plus a note on preventing sleep. | S |
| O2 | Backups aren't scheduled on macOS. `argus backup` works, but only the systemd timer runs it. | A launchd agent for the nightly backup; show the last backup's age on the Data page and in `/api/health`. | S |
| O3 | The log is hard to use. Lines have no timestamps, Argus's own INFO messages (cache warming, alerts fired) are dropped because logging is never configured, and the file grows without rotation. | Configure logging once: timestamps, the `argus` loggers at INFO, a rotating file. | S |
| O4 | Migrations run at startup with no automatic backup. | Take an online backup before applying a migration. | S |
| O5 | `/api/health` says only that the process is up. | Add provider status, the age of the last quote, the last warm run and the last backup. | S |
| O6 | Caches only grow. The SEC cache is 740 MB for about 330 companies; `price_bar` holds 458,000 rows. | A size or age limit for cache files; an occasional `VACUUM`. | S |
| O7 | No CI. Nothing checks a push except whoever made it. | A GitHub workflow: pytest, the frontend build, the Chromium phone tests. Backlog B-001. | S |
| O8 | A normal stop can hang on open live-stream connections (seen once: the server needed a forced kill). | Close streams on shutdown; set a graceful-shutdown timeout. | S |

## Performance

Measured on about 70 positions, market closed:

| Call | Cold | Warm |
|---|---:|---:|
| Daily brief | 105 s | 0.18 s |
| Watchlist (12 names) | 38 s | 0.03 s |
| Peers | 4.2 s | 0.03 s |
| Research | 2.1 s | 0.01 s |
| Performance, all time | 1.6 s | 0.05 s |
| Market context | 1.4 s | 0.02 s |
| Risk | 0.39 s | 0.34 s |
| Portfolio summary | 0.03 s | 0.03 s |

| ID | Issue | Fix | Effort |
|---|---|---|---|
| P1 | Reads block on providers when a cache has expired. Fundamentals live 24 hours, but caches are warmed only once after each close, so the first load after a weekend or a restart fetches every holding one at a time under Finnhub's 60-a-minute limit. Backlog B-026, reported in 24 rounds. | Serve what is stored and refresh in the background everywhere (the portfolio tabs already do); warm on expiry, not only on the close; fetch the brief's 52-week figures in one batch. | M |
| P2 | Nothing is compressed and hashed assets aren't cached. The main bundle is 305 KB and the fundamentals response 64 KB, both sent raw; hashed files carry no `Cache-Control`. | Gzip middleware; `immutable` on `/assets`. Matters most on a phone over a tunnel. | S |
| P3 | Performance is recomputed from the whole trade history on every request. Fine today, linear in history. | Cache the daily series per portfolio, keyed by the trade revision and the last session. | M |
| P4 | Risk does the same work warm as cold (0.34 s). | Cache by holdings and session. | S |
| P5 | The hub rebuilds every portfolio's positions from all transactions every 30 seconds. | Recompute only when the trade revision changes. | S |
| P6 | The frontend refetches on every page visit and never cancels a request it no longer needs (101 effects, no abort signals). | A small fetch layer: cache by URL, de-duplicate, cancel on unmount. | M |

## Code health

| ID | Issue | Fix | Effort |
|---|---|---|---|
| C1 | `app.py` is 1,932 lines: orchestration, caching and business rules for every domain in one class. | Keep `Argus` as the facade, and move each domain's logic into its service (research, dividends, events, valuation, peers). | L |
| C2 | The API has no typed contract. Routes return dicts, and `api.ts` re-declares every shape by hand in 633 lines that can drift. | Response models on the routes; generate the TypeScript types from the OpenAPI schema. | L |
| C3 | No linter, type checker or coverage. A basic lint run finds about 30 unreachable leftover lines in `app.py` (after the `return` in `_holding_quotes`), an unused variable and unused imports. | Ruff on the backend, run in CI (O7). Start with the checks that find real leftovers; widen later. | S–M |
| C4 | The frontend has no unit tests. The DCF projection math lives only in `dcf.ts`, untested, and can't be reached from the CLI or MCP. | Move the projection to the backend (one definition, testable, usable by agents), or add a unit-test runner for `dcf.ts`, `format.ts` and `metrics.ts`. | M |
| C5 | 33 broad `except Exception` blocks. Most are deliberate ("never block the summary on metadata"), but they hide real failures. | Log each with context (O3), and count them in health. | S |
| C6 | Adding an owned table takes several manual steps (the owner column, `OWNED`, both snapshot formats, the leak test). | A test that fails when a table has `account_id` but isn't registered in each place. | S |
| C7 | `numpy` is imported but not declared; it arrives through pandas. | Declare it. | S |
| C8 | Management actions are incomplete: no rename or benchmark change for a portfolio, no delete for a watchlist, alert or note, no CSV export. The MCP server lacks `list_watchlists`, the saved DCF models and peer lists. | Fill in the missing verbs across API, CLI, MCP and UI. | M |

## The investor's view

### What the model can't express

| ID | Gap | Why it matters | Sketch | Effort |
|---|---|---|---|---|
| I1 | **No cash.** Portfolios hold positions only. | Account value, deposits and withdrawals, a money-weighted return (what you actually earned), "can I afford this buy", and target weights that sum to less than 100% (backlog B-024) all need it. The loop's trader bot needs an outside script (`scripts/sim.py`) to keep a cash ledger. | An optional cash balance per portfolio: DEPOSIT and WITHDRAW transactions, cash moved by buys, sells, dividends and fees, a cash row in holdings and drift, and money-weighted return next to time-weighted. | L |
| I2 | **Everything is an equity.** Bond, TIPS, gold and commodity funds show as "Unclassified" or "ETF"; a bond portfolio is benchmarked to SPY, stress-tested with beta to SPY and described with equity factors (R² 0.26). | The most-reported gap in the backlog (B-017, 16 rounds). Anyone with a bond sleeve gets risk numbers that mean little. | An asset class per instrument (the fund profiles already carry asset mix and bond ratings); targets and drift by asset class; for bond funds, yield, duration and credit quality, and a rate-shock scenario instead of equity factors. | L |
| I3 | **No tax view.** Realized P&L is one FIFO total. | Tax-loss harvesting and year-end planning need gains by year, short and long term, and a choice of lots. | A realized-gains report by tax year; lot selection on a sell; a "harvestable losses" list. | M |
| I4 | **Corporate actions stop at splits.** | Mergers, spin-offs and ticker changes need manual sells and buys, which distorts realized P&L and performance. | MERGER, SPINOFF and SYMBOL_CHANGE transactions that carry cost basis across. | M |

### Trust in the numbers

- **I5. One figure, one definition.** The largest group of open bugs is two sources disagreeing on
  one page: two dividend yields (B-043), two betas (B-021), two EPS estimates for one quarter
  (B-119), a payout ratio that contradicts Argus's own rate and EPS (B-062), margins mixed from
  two providers (B-124). The codebase already states the rule ("a figure shown in two places comes
  from one definition"). It needs a pass that picks one owner per figure, labels the basis (TTM or
  latest quarter, GAAP or adjusted, price or total return) and removes the second copy. Effort: L.
- **I6. Returns are price-only and don't say so** (B-100). Volatility, drawdown, beta and the
  stock-page returns leave out dividends. For income holdings that understates return noticeably.
  Label it, then offer total return. Effort: M.
- **I7. The DCF calculator needs guard rails** (B6). Default to conservative inputs: growth capped
  and decaying, an exit multiple no higher than today's. Show a sensitivity grid (growth against
  multiple) and bear, base and bull cases. Show the saved fair value where decisions are made: on
  the stock page, and as a "price against my fair value" column on the watchlist. Effort: M.
- **I8. Performance measures.** Sharpe assumes a zero risk-free rate, though Argus already loads
  Treasury yields. There is no Sortino, no tracking error, and no attribution (which positions and
  sectors made or lost the excess return). The benchmark starts at the prior close while the
  portfolio starts at its fills (B-053). Effort: M.

### Daily workflow

- **I9. Alerts don't reach you.** They fire into the UI and the brief, by design. An investor wants
  the phone to buzz. Add delivery (ntfy, Telegram, email or web push) and more kinds: a portfolio
  drawdown, a moving-average cross, a position over its target weight, an index or yield level
  (B-078). Effort: M.
- **I10. The brief has blind spots.** It ignores named watchlists (B-106), macro events (B-038)
  and extended-hours moves in holdings that just reported (B-110). Effort: S–M.
- **I11. Notes are per symbol, not per position or decision** (B-018). A trade journal would link
  each buy and sell to its thesis and later ask "was I right?". Effort: M.
- **I12. Only one import format.** Investing.com CSV. Brokers' exports (IBKR, Schwab, Fidelity)
  and a generic CSV would remove the biggest barrier for a new user. Effort: M per format.

### Using it

- **I13. Phone.** The holdings table leads with quantity and cost, so Day %, value and P&L are
  off-screen. The stock page is 6,250 px long and Markets 6,300 px, with no section navigation.
  Backlog B-002 has been reported in 21 rounds. Reorder columns for narrow screens, add a section
  bar to long pages, make it installable as an app. Effort: M.
- **I14. A portfolio can't be opened by URL** (B-118). The selection lives in the browser, so links
  and bookmarks open whichever portfolio was last used. Effort: S.
- **I15. The stock page's proportions.** The revenue chart is far larger than the price chart's
  supporting cards; the page has no summary of your own position and thesis at the top. Effort: S.

## Feature ideas

Nice to have, roughly in order of value for the effort.

| ID | Feature | What it would give | Effort |
|---|---|---|---|
| F1 | **Paper portfolios** built on I1 | A portfolio with starting cash and rule-based fills, so the trader bot (and you) can simulate inside Argus and see it in the UI. Replaces `scripts/sim.py`. | M after I1 |
| F2 | **Rebalance planner** | From targets to a trade list: cash-aware, whole shares, smallest number of trades, optionally avoiding short-term gains. | M |
| F3 | **Screener upgrades** | Trailing-twelve-month and latest-quarter growth (B-019), sector and industry filters (B-060), saved screens, valuation against a company's own history (B-052). | M |
| F4 | **Research depth** | SEC filings list (B-121), earnings-call transcripts, segment revenue and guidance (B-090), a "why did it move" line on big moves (B-096). | M–L |
| F5 | **Macro additions** | Real yields, breakevens, credit spreads, the dollar index (B-037); futures and overnight moves (B-055). | M |
| F6 | **Ask Argus** | A question box in the UI that answers from Argus's own tools, since the MCP server already exposes them. | M |
| F7 | **Scheduled brief** | The daily brief delivered by the same channels as alerts (I9). | S after I9 |
| F8 | **Sharing beyond read-only** | Comments on a shared portfolio; a household view that combines chosen accounts. | M |
| F9 | **What-if history** | "What if I had bought the index instead", "what if I hadn't sold": the same engine as performance, on a hypothetical trade log. | M |
| F10 | **Beyond US long-only** | Options, shorts, other currencies and markets. A large change to lots, pricing and performance; only worth it with a concrete need. | L+ |
| F11 | **Postgres option** | Only if Argus ever runs as more than one process or hosts many active users. SQLite is the right choice today. | L |

## Roadmap

Each stage's items have an implementation plan in [`plans/`](plans/README.md).

### Now: make the multi-account server safe and usable (one to two weeks)

1. B1 new-account onboarding, B2 empty-portfolio crash and error boundaries.
2. S1 token session, S2 HTTPS guidance and startup warning, S7 headers, S4 throttling.
3. O1 and O2 launchd agents for the server and backups, O3 logging, O4 backup before migrating.
4. O7 CI, C3 lint and type check.
5. B3 bond fund as Technology, B5 per-account delete snapshot, B4 dead table.
6. P2 compression and asset caching.

All small. Together they close the gaps v6 opened.

### Next: the two model changes and trust in the numbers (one to two months)

1. **I1 cash**, then F1 paper portfolios. The loop's trader bot moves into Argus proper.
2. **I2 asset classes**, with cash as a class: targets and drift by asset class, bond metrics.
3. **P1** stale-while-revalidate, so no page waits on a provider.
4. **I5** the one-definition pass, starting with a triage of the 119 open backlog items (B10).
5. I7 DCF guard rails, with C4 moving the projection to the backend.
6. I9 alert delivery and I10 brief gaps.
7. C8 missing management actions, S5 read-only keys, S6 limits, S8 and S9 sessions and deletion.
8. I13 and I14 phone layout and portfolio URLs; B8 the WebKit touch bugs.

### Later: depth

1. I3 tax view, I4 corporate actions, I8 performance measures and attribution, I6 total return.
2. F2 rebalance planner, F3 screener, F4 research depth, F5 macro.
3. I11 trade journal, I12 broker imports, F6 to F9.
4. C1 splitting `app.py` and C2 a typed API contract, done alongside feature work in each domain
   rather than as one rewrite. P3 to P6 as data grows.

### How the improvement loop fits

The loop's trader bot will keep finding issues in the areas it touches: research, the screener,
fundamentals, the brief. It is unlikely to find what this review found, because it runs as the
only account on a fresh database inside a cloud session: onboarding (B1), security (S1 to S11),
operations (O1 to O8) and cold-load latency over a weekend (P1) are invisible to it. Those need a
person, or a second bot that signs up as a new user and tries to get started.
