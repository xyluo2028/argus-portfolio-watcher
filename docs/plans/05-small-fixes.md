# 05. Small fixes

Roadmap items B3, B4, B5, B7, P2, O6. Each is small and independent: one commit each, any order.

## B3. A bond fund is counted as 100% Technology

**What happens.** In Analysis, the look-through sector table shows an international bond fund
(BNDX, 98.6% bonds) as Technology, and other bond funds as "Unclassified".

**Why.** `services/analysis.py`, `exposure()`, spreads a fund's whole value across
`profile["sectors"]`. Yahoo's sector weights describe only the fund's equity sleeve and sum to
about 1 even when that sleeve is 1% of the fund. The fund profile (from
`providers/yahoo.py`, `get_fund_profile`) also carries `asset_classes`: fractions keyed
`stockPosition`, `bondPosition`, `cashPosition`, `preferredPosition`, `convertiblePosition`,
`otherPosition`. `exposure()` ignores them.

**Decided.**
- For a fund with `asset_classes`, the equity share is `stockPosition` (clip to 0..1). Spread only
  that share across the sector weights, normalized to sum to 1. Put the rest in non-sector buckets
  named `Bonds` (bond, preferred and convertible positions), `Cash` and `Other assets`, in
  proportion to those positions. If the positions don't sum to 1 (funds report leverage and shorts
  as negatives), clip negatives to 0 and normalize.
- A fund with `asset_classes` but no sector weights (a pure bond fund) goes to those buckets, not
  to "Unclassified", and no longer appears in `funds_without_profile`.
- A fund with sector weights and no `asset_classes` keeps today's behavior.
- The same rule applies to the single-stock look-through: a top holding's weight is of the whole
  fund already, so leave that part as it is.

Plan 09 replaces these three buckets with a proper asset-class view. This fix removes the wrong
number now and uses the same data.

**Done when.** Tests in `tests/test_analysis.py`: a 99%-bond fund with `sectors: {Technology: 1.0}`
contributes about 1% to Technology and 99% to Bonds; a 60/40 fund splits its 60% across sectors;
a fund with negative cash normalizes; a fund with no `asset_classes` behaves as before. The
Analysis page shows the buckets without layout changes.

## B4. A table nothing writes

**What happens.** "Delete a portfolio" previews "N days of performance history". N is always 0:
`nav_daily` (`NavDaily` in `models.py`, "Filled in P1 by the performance engine") is never written.
Performance is computed on request.

**Decided.** Remove it. If performance is cached later (roadmap P3), that design will choose its own
storage.

**Do.** A migration dropping `nav_daily` (skip if absent); remove the model and its uses in
`services/portfolio.py` (`delete_portfolio` counts and deletes) and `services/snapshot.py`
(`_delete_mine`); remove `nav_days` from the deletion preview (`api.ts` `PortfolioDeletion`,
`pages/Data.tsx` `deletionSummary` and the card's wording about "performance history");
`tests/test_delete_portfolio.py` asserts on `nav_days` and inserts a `NavDaily` row: update it.

**Done when.** Migration tests pass, a database at the previous revision upgrades, and the delete
preview no longer mentions performance history.

## B5. Deleting a portfolio writes everyone's records to disk

**What happens.** `Argus.delete_portfolio` saves a safety copy first by calling
`self.snapshots.dump(...)`, the whole-instance snapshot. Since accounts exist, that file holds every
account's records plus password and key hashes, and any account can trigger it.

**Decided.** Save the deleting account's own snapshot instead:
`self.account_snapshots.export(username)`, written to
`data/snapshots/argus-<username>-before-delete-<portfolio>-<time>.json`. It contains the portfolio
being deleted and can be restored from the Data page, which is what the card promises.

**Do.** `Argus.delete_portfolio` needs the username for the file name and the `account` field:
resolve it from the acting account (there is no helper yet; `access.account_id(s)` gives the id,
`AccountService.get(id)` the name; account 0, before any account exists, has no name: use
`argus`). Keep the response's `backup` field.

**Done when.** A test with two accounts deletes one account's portfolio and asserts the backup file
is an account snapshot (`format` is `argus-account-snapshot`) with none of the other account's rows.
Existing tests in `tests/test_delete_portfolio.py` still pass.

## B7. Calendar rows with the same name, and overlapping curve labels

**Calendar.** Nasdaq's feed names month-on-month and year-on-year figures identically, so Markets
lists "Core PPI" twice and "PPI" twice with different numbers. `providers/macro.py` already knows
this: `_keep_releases` keys repeats by their order. Add a `basis` to each row where it can be told
apart, and show it in the name ("Core PPI (MoM)", "Core PPI (YoY)").

How to tell them apart is the open part, so investigate before coding. The order within a pair is
not reliable: at review time PPI listed the month-on-month figure first and Retail Sales the
year-on-year one first. Look at the raw feed rows (a live fetch, or a debugger on
`economic_calendar`) for a field that says which is which: Nasdaq rows carry more than the name,
for example a description. If a field does, use it. If nothing does, don't guess from magnitudes:
number the rows ("PPI (1 of 2)", "PPI (2 of 2)") so they can at least be told apart, and say in
your report that the basis couldn't be determined. Related backlog items for context: B-091 (units
and periods) and B-116.

**Yield curve.** `pages/Markets.tsx` draws an end label per curve at the last tenor
(`className="end-label"`). When today's and last month's 30-year yields are close, the labels
overlap. Nudge overlapping labels apart vertically (the DCF page's chart does the same for its
reference labels: see `pages/Dcf.tsx`), at 1400 px and 390 px.

**Done when.** A provider test with a faked Nasdaq pair yields two names a reader can tell apart
(labelled by basis if the feed allows, numbered otherwise); the Markets page shows no identical
names on one date and time; curve labels don't overlap when two curves end within 0.1 percentage
points.

## P2. Compress responses and cache hashed assets

**What happens.** Nothing is compressed: the main bundle is 305 KB, the chart library 169 KB, a
fundamentals response 64 KB. Hashed files under `/assets` carry no `Cache-Control`, so browsers
revalidate them on every load.

**Do.**
- Add Starlette's `GZipMiddleware` (minimum size about 1 KB) in `create_app`. The installed
  Starlette excludes `text/event-stream` from compression, which the live stream and MCP need.
  Confirm that rather than trust it: the stream test (`test_the_live_stream_is_per_account`) and
  the HTTP MCP test must still pass, and on a throwaway server `curl -N /api/stream` must deliver
  its first event at once.
- Serve `/assets` with `Cache-Control: public, max-age=31536000, immutable` (subclass
  `StaticFiles` or wrap its responses). The files are content-hashed by Vite. `index.html` already
  goes out with `no-cache`; keep that.

**Done when.** With `Accept-Encoding: gzip`, the bundle and a JSON response come back compressed;
assets carry the cache header; streams still flow. Add a test for the headers.

## O6. Caches that only grow

**What happens.** `data/cache/sec/` holds one companyfacts file per company ever looked at (740 MB
for about 330 companies at review time). Nothing removes old files.

**Decided.** Age out by last use, not by size: delete files under `data/cache/sec/` that haven't
been read in 90 days. Reads don't update modification time, so touch the file when the cache
serves it (`providers/sec_edgar.py`, `_fetch_json` and the N-PORT cache). Run the sweep from the
hub's warm step (`Argus.warm_caches`), where failures are already logged and tolerated. The
`price_bar` table is small in bytes; leave it.

**Done when.** A test with files of different ages keeps the recent ones; a served file's time is
refreshed; the sweep's result appears in the warm report.
