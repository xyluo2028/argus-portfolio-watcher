# 12. Missing management actions

Roadmap items C8 and I14. Effort: medium; many small, independent pieces. Group them into a few
commits by area (portfolios, watchlists, alerts and notes, export, MCP).

## Why

Argus grew by adding what was needed next, so several objects can be created but not fully
managed. None is hard; together they make the product feel unfinished:

| Object | Can do | Can't do |
|---|---|---|
| Portfolio | create, delete, share | rename, change the benchmark, open by link |
| Watchlist | add and remove symbols (a list appears on first add) | delete a list, rename it |
| Alert | create, switch on and off | delete, change the threshold or note |
| Note | create, edit, archive | delete |
| Transactions, positions | view | export |
| MCP | 38 tools | list watchlists, read or set peer lists (and DCF models: plan 10) |

## Decided

Every action below follows the ground rules: a method on `Argus` or a service, an audit row, an
API route listed in the leak test, and the write refused on a portfolio that is only shared with
you (`get_portfolio(..., write=True)`).

### Portfolios

- `PATCH /api/portfolios/{ref}` with optional `name` and `benchmark`. A name must be unique among
  your portfolios and not `all`. A benchmark must resolve to a quote (`market.get_quotes`), like a
  watchlist symbol does: today `create_portfolio` accepts any string, so validate there too.
- Renaming matters to the browser: the selected portfolio is stored by name in `localStorage`
  (`argus.portfolio`). After a rename, update the stored selection.
- CLI `argus portfolio rename <ref> <new name>` and `argus portfolio benchmark <ref> <symbol>`.
  MCP `update_portfolio`.
- UI: a "Portfolio settings" card on the Data page for the selected portfolio: name, benchmark,
  the existing Share link, and the existing delete control moved in. Plans 07 and 08 add cash
  tracking here.

### A portfolio in the address (I14)

Today the selection lives only in the browser, so a link opens whichever portfolio was used last
(backlog B-118).

- Read `?p=<key>` on load: when present and valid it selects that portfolio (`portfolioKey`: a name
  for yours, an id for a shared one) and is remembered. When the user changes the menu, update the
  parameter if the address has one. Don't add the parameter to addresses that didn't have it: most
  navigation stays clean, and a "Copy link to this portfolio" control in the settings card produces
  an address with it.
- An unknown or no-longer-shared key falls back to the usual default, silently.

### Watchlists

- `DELETE /api/watchlists/{name}` removes the list and its items. `PATCH` renames it. The default
  list (`Watchlist`) can be emptied but not renamed or deleted, because the app falls back to it.
- UI: rename and delete in the list switcher on the Watchlist page, with a confirm on delete.
- MCP: `list_watchlists` (names and counts: agents can't discover named lists today, which is
  behind backlog B-106) and `watchlist_delete`.

### Alerts and notes

- `DELETE /api/alerts/{id}` removes the alert and its firing history. `PATCH` already toggles
  `active`; extend it to `threshold` and `note`.
- `DELETE /api/notes/{id}`. Archive stays as the gentle option.
- UI: a delete control beside the existing ones, with a confirm. MCP: `delete_alert`,
  `delete_note`, marked destructive like `delete_transaction`.

### Export

- `GET /api/portfolios/{ref}/transactions.csv` and `/positions.csv`: `text/csv` with a download
  header. Transactions: date (New York), type, symbol, shares, price, fee, amount, note, source.
  Positions: symbol, name, shares, average cost, price, value, weight, unrealized gain.
- Works on a shared portfolio (it is a read).
- UI: "Export CSV" on the Transactions page and above the holdings table.
- Guard against formula injection: a note or name starting with `=`, `+`, `-` or `@` gets a
  leading apostrophe, because spreadsheets execute such cells.

### MCP parity

- `get_peers(symbol)` and `set_peers(symbol, peers)`, on the caller's own peer lists.
- Update `INSTRUCTIONS` in `mcp_server.py` and the README's tool count for everything added here.

## Watch out

- FastAPI matches routes in the order they are declared. `/api/portfolios/{ref}/transactions.csv`
  must not be swallowed by `/api/portfolios/{ref}/transactions`: they are different literal paths,
  but check with a test.
- The phone tests' fixtures throw on unexpected writes; new buttons that write need mocks only if
  a test clicks them.
- Deleting a watchlist or alert changes what the hub tracks; the watchlist service bumps a
  `revision` counter on changes (`WatchlistService.revision`): bump it on delete and rename too, so
  the per-account stream cache refreshes.

## Leave alone

- Bulk edits, undo, and a trash for deleted things.
- Merging two portfolios or moving transactions between them.

## Done when

- Each action works from the UI, the API, and (where listed) the CLI and MCP, for your own records,
  and is refused or "not found" for another account's: the leak test covers every new route and
  tool.
- A renamed portfolio keeps its transactions, targets, shares and saved selection.
- `?p=` opens the named portfolio in a fresh browser profile; a bad value doesn't break the page.
- A CSV with a note of `=1+1` opens in a spreadsheet as text.
- README and tool descriptions are current.
