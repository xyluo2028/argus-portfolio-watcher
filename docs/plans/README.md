# Implementation plans

Each file here is a work package from [`../review-and-roadmap.md`](../review-and-roadmap.md),
written so that someone with no memory of the review can implement it. The design decisions are
already made and explained; the plan says what to build, where, how to prove it works, and what to
leave alone.

**To implement one:** read this file, then the plan, then the code the plan points at. Line numbers
and counts were right at commit `cc0105a` (November 2026); the code may have moved, so treat every
pointer as "start looking here" and verify before you edit.

## The plans

| # | Plan | Roadmap items | Effort | Needs first |
|---|---|---|---|---|
| 01 | [New-account onboarding and empty states](01-onboarding-and-empty-states.md) | B1, B2, B9 | S | – |
| 02 | [Sign-in hardening](02-sign-in-hardening.md) | S1, S2, S4, S7, S8 | M | – |
| 03 | [Running it on a Mac: supervision, backups, logs](03-operations.md) | O1–O5, O8 | M | – |
| 04 | [CI and lint](04-ci-and-lint.md) | O7, C3, C7 | S | – |
| 05 | [Small fixes](05-small-fixes.md) | B3, B4, B5, B7, P2, O6 | S each | – |
| 06 | [No page waits on a provider](06-no-page-waits-on-a-provider.md) | P1, P4, P5 | M | – |
| 07 | [Cash](07-cash.md) | I1, part of I8 | L (three stages) | 12 helps |
| 08 | [Paper portfolios](08-paper-portfolios.md) | F1 | M | 07 stage 1 |
| 09 | [Asset classes](09-asset-classes.md) | I2, B3 | L | 05 (B3) helps |
| 10 | [DCF guard rails](10-dcf-guard-rails.md) | I7, B6, C4 | M | – |
| 11 | [Alert delivery](11-alert-delivery.md) | I9 | M | – |
| 12 | [Missing management actions](12-management-actions.md) | C8, I14 | M | – |
| 13 | [Account limits, keys and deletion](13-account-limits-and-keys.md) | S3, S5, S6, S9–S11 | M | 02 |
| 14 | [Phone and navigation](14-phone-and-navigation.md) | I13, I15, B8 | M | – |
| 15 | [One figure, one definition](15-one-definition.md) | I5, I6, B10 | L | – |
| 90 | [Design notes for later items](90-later-design-notes.md) | I3, I4, I8, F2–F9, C1, C2, P3, P6 | – | – |

Suggested order: 01, 02, 03, 04, 05 (the roadmap's "Now"), then 06, 12, 07, 09, 10, 11, 13, 14, 15.
Plans 01 to 06 don't depend on each other and can be done in any order. Plan 90 holds design
decisions for later work; it is not ready to implement without a fuller plan.

When a plan is done, change its row here to say so, with the commit.

## Ground rules for every plan

### Scope

- Implement the plan as written. Where it says "Decided", don't reopen the question: the reasoning
  is given so you can apply it to cases the plan didn't foresee. Where it says "Ask the owner", stop
  and ask; don't guess.
- Keep each change the size the plan describes. Note other problems you find in your report; don't
  fix them in the same change.
- One commit per plan, or per stage for staged plans. Commit messages are plain text: no double
  quotes and no backticks. Start with the area, e.g. `Accounts: token sign-ins get a server session`,
  then a short body saying why.
- Work on a branch from `main`, never on `main` or `claude-code-recursive-oncloud`.

### This repository is public, and a real server runs from this checkout

- Never commit `.env`, anything under `data/`, keys, passwords or real portfolio data. Tests and
  docs use made-up symbols (AAA, BBB) or well-known public tickers.
- The owner's real Argus runs from this working directory on port 8787, with real data in `data/`.
  Don't restart it, don't run migrations against it, and don't write to `data/`, unless the owner
  asks. Running `argus` CLI commands without overriding the data directory reads and writes the
  real database.
- To try something on a live server, start a throwaway one:

  ```bash
  export ARGUS_DATA_DIR=/tmp/argus-try ARGUS_DB=/tmp/argus-try/argus.sqlite \
         ARGUS_HOST=127.0.0.1 ARGUS_STREAM=off ARGUS_TOKEN=
  uv run argus portfolio create growth
  uv run argus serve --port 8799
  ```

  `ARGUS_HOST=127.0.0.1` matters: the repo's `.env` may set a non-loopback host, and Argus refuses
  that when sign-in is off. `ARGUS_STREAM=off` matters: Finnhub allows one WebSocket per key, and a
  second server would knock the real one off. Leave `FINNHUB_API_KEY` set if you need symbol search
  or peers; set it empty to stay off Finnhub.
- For realistic data, copy the real database read-only into the throwaway directory
  (`sqlite3` online backup), make an API key there with `uv run argus key create <user> --name try`,
  and delete the copy when done. Nothing from it goes into a commit, a test or a doc.

### How Argus is put together

- `backend/argus/app.py`: `Argus`, the facade every surface calls. `api/server.py` (FastAPI routes),
  `cli.py` (Typer) and `mcp_server.py` (MCP tools) stay thin: business rules belong in `Argus` or a
  module under `services/`.
- A feature usually has four surfaces: API route, CLI command, MCP tool, UI. A plan says which ones
  it wants. Keep them consistent: one definition of each figure, the same names.
- Writes take an `actor` (`ui`, `cli`, `mcp`, `import`), add an `AuditLog` row, and where they
  change holdings, support `dry_run` and return before/after.
- Errors are `ArgusError(code, message, hint)`. The HTTP status for a code comes from `_STATUS` in
  `api/server.py`; anything not listed is 400.
- Settings come from environment variables in `config.py`. A new one needs a line in
  `.env.example` and in the table in `docs/deployment.md`.

### Accounts: the rule that is easiest to break

Every account sees only its own records. `backend/argus/access.py` explains the mechanism; read it.

- A query on an owned table (portfolio, watchlist, alert, note, peer list, DCF model) must filter
  with `access.owned(s, Model.account_id)`. New rows take `access.owner(s)`. Rows reached through a
  portfolio (transactions, targets) are protected by `PortfolioService.get_portfolio`, which takes
  `write=True` for anything that changes the portfolio.
- The account comes from a context variable. The web server sets it per request, tests run as
  `access.DEFAULT` (an autouse fixture in `tests/conftest.py`), and background work must opt in
  with `access.as_(access.SYSTEM, fn)`. Code running with no account raises on purpose.
- Threads don't inherit it. `asyncio.to_thread` copies the context; `ThreadPoolExecutor` workers
  and `Argus.run_background` threads don't. Keep owned-table reads on the calling thread and use
  pools for network calls only.
- **Every new API route and MCP tool must be listed in `tests/test_owners.py`**, which calls each
  one as a second account and fails when one is missing. Put shared market data in
  `NOT_PER_ACCOUNT` / `MCP_NOT_PER_ACCOUNT`; per-account ones in `denied` (must refuse) or `own`
  (must not show the other account's records).
- A new owned table needs: an `account_id` column (default 0, no foreign key), an entry in `OWNED`
  in `models.py` (the first account takes over rows with owner 0), handling in both snapshot
  formats in `services/snapshot.py`, and cases in the leak tests.

### Database changes

- Models are in `models.py`; migrations in `backend/argus/migrations/versions/NNNN_name.py`. Use the
  next free number when you implement: the numbers in these plans are not reservations.
- Write migrations idempotent per table, like `0004_owners.py`: inspect what exists and skip it.
  A database created from newer models already has the change.
- SQLite can't alter most things in place. Use Alembic batch mode, or create, copy and rename.
  `db.migrate` turns foreign keys off for the upgrade and runs a foreign-key check after it.
- `tests/test_migrations.py` fails when models and migrations disagree. Add a test that upgrades a
  database from the previous revision with rows in the affected tables, as
  `test_migration_gives_existing_records_to_the_oldest_account` in `tests/test_owners.py` does.
- If a change alters what a snapshot contains, bump the snapshot version so an older Argus refuses
  the file instead of misreading it.

### Frontend

- Types and the API client are in `frontend/src/api.ts`, written by hand: keep them in step with
  the backend response.
- Colors come from the CSS tokens in `styles.css`, in light and dark. Every page must work at
  390 px wide with no sideways page scroll.
- A portfolio shared with you is read-only: `useSharedBy()` (`portfolioAccess.ts`) is non-null
  then, and write controls hide. `portfolioKey` gives the reference to use in API calls.
- The phone tests (`frontend/tests/mobile.spec.ts`) run against mocked API responses in
  `frontend/tests/fixtures.ts`. A GET with no mock returns a 404 and any unexpected write throws,
  so a new call made on page load needs a mock there, and the page must survive that call failing.

### Before you call it done

```bash
uv run pytest -q                                   # all backend tests
cd frontend && npm run build                       # type check and production build
npx playwright test --project=chromium --trace off # phone UI tests (WebKit has two known failures)
```

- For anything visible, look at it in a browser on a throwaway server, at desktop and 390 px
  width, light and dark. A Playwright script can sign in by sending an API key header
  (`extraHTTPHeaders: { Authorization: "Bearer <key>" }`) and run from `frontend/` so it finds
  `node_modules`.
- Update `README.md`, `docs/deployment.md` and `.env.example` when behavior, settings or the MCP
  tool count change (the README states the count).
- Report what you verified and what you could not, plainly. If a step in the plan turned out to be
  wrong, say so and say what you did instead.
