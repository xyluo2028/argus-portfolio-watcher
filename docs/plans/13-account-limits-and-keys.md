# 13. Account limits, keys and deletion

Roadmap items S3, S5, S6, S9, S10, S11. Effort: medium; five independent parts. Do plan 02 first:
it changes the same sign-in code.

## Why

Plan 02 hardens how people sign in. This plan covers what an account can do once it is in, on a
server where anyone who can reach the sign-in page can create one:

- an API key can do everything its account can, forever (S5);
- nothing limits how much one account asks of the server or the shared data providers (S6);
- an account can't be deleted, only disabled, and its records stay (S9);
- changes are recorded with who made them, but nobody can read that record (S11);
- sign-up is all or nothing: open to everyone who can reach the page, or off (S3).

## Part A: read-only API keys (S5)

**Decided.** A key has a scope: `full` (today's behavior, the default) or `read`. A read key can
look at everything its account can and change nothing. That is the right key for a dashboard, a
reporting script, or an agent you want to watch but not trade.

- `ApiKey.scope` (new column, default `full`). `Principal` (`services/accounts.py`) gains
  `read_only`. Creating a key takes the scope: `argus key create <user> --name … --read-only`, the
  Account page's key form, `POST /api/account/keys`.
- **HTTP API:** enforce in `AuthMiddleware` (`api/auth.py`), which sees every protected request:
  a read-only principal may use GET and HEAD, plus the POST routes that only compute:
  `/api/screener` (a query) and `/api/portfolios/{ref}/simulate` (a what-if). Keep that allowlist
  next to the middleware with a comment, and add a test that fails when a new POST route is added
  without being classified as a read or a write.
- **MCP:** requests to `/mcp` are all POSTs, so the middleware can't tell reads from writes there.
  `_AccountMCP._handle_call_tool` (`mcp_server.py`) knows the tool name: refuse any tool not
  annotated read-only when the principal is read-only. The tools already carry `READ`, `WRITE` and
  `DELETE` annotations, and `tests/test_mcp.py` checks them. Careful: `list_alerts` is annotated as
  a read but calls `evaluate_alerts`, which records firings. That is fine (it changes nothing the
  user made), but name it in a comment so nobody "fixes" it.
- A refused call returns 403 with code `READ_ONLY_KEY` and a hint to use a full key.

## Part B: limits (S6)

**Decided.** Bound what a single request and a single account can cost. Pick limits generous
enough that no honest use hits them.

| What | Limit | Where |
|---|---|---|
| Request body | 2 MB; 10 MB for `/api/import/investing` and `/api/snapshot/restore` | a pure-ASGI middleware that counts `http.request` bytes and answers 413 |
| Symbols in one call | 100 | `Argus.quotes`, `compare` already caps at 10; check every route that splits a comma list |
| Names (portfolio, watchlist, key) | 80 characters | the services; SQLite doesn't enforce column lengths |
| Note and thesis text | 10,000 characters | `NoteService`, alert notes, transaction notes |
| Watchlists per account, items per list | 50, 500 | `WatchlistService` |
| In-memory research and valuation caches (`Argus._research`, `_valuation`, `_fund_attempted`) | 500 entries, oldest evicted | `app.py` |
| Requests per account | 600 a minute | the auth middleware, in memory, answering 429 |
| Screener rebuild | once per 10 minutes, whoever asks | `Argus.rebuild_screener` (it is already single-flight) |

Over-limit input gets `INVALID_ARG` with the limit in the message. Put the numbers in one place
(`config.py` or a `limits.py`) so they are easy to find and change.

## Part C: deleting an account (S9)

**Decided.**

- `AccountService.delete(ref)` removes the account, its sessions and keys, the shares it was
  given, and all its records. `AccountSnapshots._delete_mine` (`services/snapshot.py`) already
  deletes one account's records in foreign-key order: reuse it, acting as that account.
- Audit rows keep their `account_id`: history stays readable even though the name is gone. Write
  one audit row for the deletion with the username.
- **The oldest account can't be deleted while others exist.** The server token signs in as the
  oldest account (`AccountService.first`), so deleting it would silently hand the token to the next
  account. Refuse with an explanation. When it is the only account, deleting it returns the server
  to "no accounts": say what that means (sign-in turns off unless a token is set) and require the
  CLI for that case.
- CLI: `argus user delete <name>`, with a type-the-name confirmation like `portfolio delete`, and
  `--yes`. It prints what will be removed first.
- Self-service: "Delete my account" on the Account page, asking for the password, refused to API
  keys and token sign-ins. It offers the backup download first (the Data page's snapshot).

## Part D: an activity view (S11)

**Decided.** `AuditLog` rows carry `account_id` (set automatically: see `_audit_account` in
`models.py`). Expose the caller's own:

- `GET /api/account/activity?limit=100&before=<id>`: when, actor (`ui`, `cli`, `mcp`, `import`),
  action, entity, and a one-line summary built from `before` and `after`. Only rows whose
  `account_id` is the caller's.
- Account page: an "Activity" list, newest first, with "load more".
- CLI: `argus audit [--user NAME] [--limit N]` for the server operator, across accounts.

This is where a user sees "the MCP agent deleted a transaction at 14:02".

## Part E: invitations (S3)

**Ask the owner before building this.** Sign-up is open by design: the owner asked for accounts
anyone can create on the sign-in page. Today the choices are open or off (`ARGUS_SIGNUP`). A middle
setting would let the server stay closed to strangers while a friend or a bot's operator can still
join:

- `ARGUS_SIGNUP=open | invite | off`. In `invite` mode the Create account form asks for a code.
- A code is random, stored hashed, single-use, expiring after 7 days. Any signed-in account can
  make one from its Account page (all accounts are equals), and so can
  `argus invite create`.

If the owner says yes, also default sign-up to `invite` when the listen address isn't loopback.
If no, leave S3 as documented advice.

## Smaller items (S10)

- **Usernames are discoverable, and that is accepted.** The share form says whether an account
  exists, and so does the sign-up form (a taken name is refused). Hiding one without the other
  buys nothing; leave both.
- **Shared instrument names.** `Argus._upsert_instrument_names` lets an import fill a missing
  instrument name and exchange from the uploaded file, and `Instrument` is shared by all accounts.
  Let the providers own that metadata: use the file's name only for display in that import's
  report.
- **Live-price slots.** The hub streams the 48 symbols with the largest market value across all
  accounts (`live.py`, `tracked_symbols` and `STREAM_LIMIT`). One large account can take every
  slot. Fill the slots round-robin across accounts, each account's largest first.

## Done when

- Part A: a read key gets data everywhere and a 403 on every write route and write tool; the
  classification test catches an unclassified POST route.
- Part B: each limit has a test at the boundary; a 3 MB post to an ordinary route gets 413 without
  the server reading it all.
- Part C: deleting an account removes its records and nothing of anyone else's (extend the leak
  fixture: delete the second account, the first is intact); the oldest-account rule is tested.
- Part D: an account sees its own activity and none of another's.
- Every new route is in the leak test. `docs/deployment.md` documents scopes, limits, deletion and
  the audit command.
