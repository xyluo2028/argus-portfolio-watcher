# 06. No page waits on a provider

Roadmap items P1, P4, P5. Effort: medium. Backend only, plus small "updating" hints in the UI.

## Why

Measured on about 70 positions with the market closed, right after a restart:

| Call | Cold | Warm |
|---|---:|---:|
| `GET /api/brief/<portfolio>` | 105 s | 0.18 s |
| `GET /api/watchlists/Watchlist` (12 names) | 38 s | 0.03 s |

The warm numbers show the work is cheap. The cold ones are waiting for data providers. The loop's
backlog has reported this in 24 rounds (B-026).

The cause is a rule applied in the wrong places: **when a cached row is older than its time limit,
the request fetches a fresh one before answering.** Fundamentals expire after 24 hours
(`fundamentals_max_age_s`), events after 20 (`REFRESH_EVERY` in `services/events.py`). Caches are
warmed once after each market close (`live.py`, `_warm_loop`), so by Monday morning, or after any
restart, everything has expired. The first request then refreshes every holding one at a time,
through Finnhub's limiter of 55 calls a minute.

For a monitor, a fundamentals row from Friday is a fine answer on Monday while a fresh one loads.
P/E doesn't even depend on it: it is recomputed from the live price on every read (`with_pe`).

## What exists

Most of the machinery is already there; it just isn't used everywhere.

- `MarketService.cached_fundamentals(symbols)` (`services/market.py`): one query, never calls a
  provider, returns each row with `fresh` and `as_of`, P/E and 52-week range already adjusted.
- `MarketService.refresh_fundamentals(symbols)`: fetches many in parallel and stores them.
- `Argus.symbol_fundamentals(syms, wait=False)` (`app.py`): the right pattern. It answers from
  the cache, starts one background refresh for stale symbols (`run_background("fundamentals", …)`,
  single-flight by name), and returns `pending` so a client can poll. The portfolio's Financials
  tabs use it.
- `MarketService.get_fundamentals(symbol)`: the blocking path. It fetches when the row isn't fresh.
- Callers of the blocking path inside loops:
  - `Argus.watchlist()`: `get_fundamentals` per item.
  - `Argus.daily_brief()`: `get_fundamentals(symbol, ["high_52w", "low_52w"])` per position.
  - `Argus.evaluate_alerts()`: its `metrics()` helper, per alert symbol that needs fundamentals.
- `EventsService.refresh(symbols)`: sequential, per stale symbol, two provider calls each. Called
  on the request path by `Argus.upcoming_events(refresh=True)`, which `/api/events` and the brief
  use. The hub also calls it every six hours (`_events_loop`).
- `Argus.warm_caches()`: warms held symbols only. Watchlist symbols are never warmed, which is why
  a 12-name watchlist took 38 seconds.

## Decided

**The rule: a request never waits for a provider when Argus has any stored answer, however old.
It returns what it has, says how old it is, and starts a refresh in the background. A request
waits only when there is nothing stored at all (the first time a symbol is ever viewed), or when
the caller asks for a refresh explicitly.**

1. **Lists read the cache in one call.** `watchlist()`, `daily_brief()` and `evaluate_alerts()` use
   `cached_fundamentals` for all their symbols at once, then start one background refresh for the
   stale and missing ones through the same single-flight job `symbol_fundamentals` uses. Factor
   that "read cache, kick refresh, report pending" step into one helper so the four callers share it.
2. **The single-symbol call serves stale too.** `get_fundamentals(symbol)` returns a stored row
   immediately when one exists, adds `"stale": true` when it is past its time limit, and starts a
   background refresh. With no stored row it fetches, as today. `refresh=True` still forces a fetch.
3. **Events never refresh on the request path.** `upcoming_events` reads what is stored and starts
   a background refresh (single-flight, name `events`) for stale symbols. The hub's six-hour loop
   stays. A symbol that has never been refreshed shows no events until the background job lands,
   and the response says which symbols are pending.
4. **Warm what people look at, and on a clock.** `warm_caches` covers held and watched symbols
   (every account's: it runs as `SYSTEM`; `Argus.tracked_symbols()` already unions both). The warm
   loop also runs when the last run is more than 12 hours old, not only after a close, so a
   weekend never ends with everything expired.
5. **Tell the reader.** Responses that served stale rows include the oldest `as_of` among them and
   the pending symbols. The UI shows a quiet "updating…" on the affected card and refetches once
   after a few seconds, as the portfolio tabs already do with `pending`. No spinner that blocks.
6. **Smaller wins while here:**
   - P4: `Argus.risk()` recomputes everything on each call (0.34 s warm). Cache the result per
     portfolio, keyed by the trade revision (`portfolios.revision`), the last session and the
     account, the way the stream caches summaries in `api/server.py`.
   - P5: the hub's `tracked_symbols()` rebuilds every portfolio's positions every 30 seconds. Keep
     the last result and recompute only when `portfolios.revision` or `watchlists.revision` changed.

## Watch out

- **Accounts.** `run_background` threads don't carry the caller's account, and must not need one:
  pass them symbols, never portfolio names, and have them touch only shared market-data tables.
  The helper reads owned tables (the watchlist, positions) on the request thread first.
- **Single-flight drops, it doesn't queue.** `run_background("fundamentals", …)` returns false if a
  job with that name is running, and the new symbols are not added to it. `symbol_fundamentals`
  handles that by reporting them as pending so the next poll retries. Keep that behavior; don't
  start one thread per symbol.
- **The 15-minute retry guard** (`_fund_attempted`, `FUND_RETRY_S`) stops symbols no provider knows
  from being retried on every request. Reuse it in the shared helper.
- **Alerts.** `evaluate_alerts` runs every 30 seconds from the hub. With stale fundamentals it
  should evaluate on what is stored (a 52-week high from yesterday is fine) and never block the
  hub's tick.
- **Tests fake the providers.** A fake that counts calls is the way to prove "no provider call".

## Leave alone

- Quotes: `get_quotes` has its own freshness rules tied to market sessions.
- Research, peers and the DCF data: they are per-symbol pages with their own hour-long caches. A
  cold stock page taking two to four seconds is acceptable for now.
- The time limits themselves. With this rule they only decide when a background refresh starts.

## Done when

- Tests: with stored rows older than the limit and a provider fake that fails the test if called
  on the request thread, `watchlist()`, `daily_brief()`, `upcoming_events()` and
  `get_fundamentals()` return the stored data, flag it stale, and trigger exactly one background
  refresh. With no stored row, `get_fundamentals` still fetches.
- A test that `warm_caches` covers a watched symbol that isn't held.
- On a throwaway server with a copy of realistic data whose caches have expired (start it, then
  call before the warm run): the brief and the watchlist answer in under two seconds. Report the
  timings before and after.
- The watchlist page and the brief show data immediately and update once the refresh lands.
- `docs/deployment.md`: its "Should do" item 10 (warm caches) is done; update it.
