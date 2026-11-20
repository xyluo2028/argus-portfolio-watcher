# Round 021 summary

**Trading day.** The session was Thursday 2026-11-19. The round ran after the close (`market_session` was `closed` and `can_trade` true).

## Data sources (preflight)

- **Quotes:** working, from Yahoo. The Finnhub key reaches Finnhub: `/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth`, which waits for the screener universe (B-027).
- **Agents and tools:** as in r017–r020, the `trader` and `programmer` agent types and the `mcp__argus__*` tools weren't loaded. General-purpose agents read their `.claude/agents/` files and used the CLI and the API instead.

## The account (at the 11-19 close)

| | |
|---|---|
| Account value | **$9,459.17**, −5.41% since the start |
| SPY over the same sessions (`sim.py`, close to close) | −5.10% (account 0.31 pp behind) |
| SPY from the trader's 11-13 fill | −4.89% (account 0.52 pp behind) |
| Session change | −1.93% (SPY −1.96%) |
| Cash | $250.11 (2.6%) |
| Positions | 7: SPY 35.2%, XLV 12.0%, ADBE 11.7%, LNG 10.1%, META 9.9%, NVDA 9.5%, TMUS 9.0% |

**Trades: none.** The trader's reasons:
- All theses hold and no exit level was hit. ADBE came closest: it closed at 221.68, against an exit at 215.
- Cash is $250.
- 11-19 reversed and closed on its low, so the session mids were 1.7–4% above the closes. For SPY the mid was 727.77 against a 715.87 close.
- INTU, on the watchlist, reported after the close and traded −9.8% after hours. A fill at the 11-19 mid would be look-ahead, so the trader wrote a plan note instead (note 9, review 11-20).

**Other account changes:**
- The trader archived its old NVDA plan note (id 7) through the API, because the CLI couldn't do it until B-127 shipped this round.
- The programmer's live check for B-127 left an archived throwaway note (id 10, symbol ZZZZ) in bot0's records. It is harmless, but it is now in `sim/bot0.json`.

**Account check:** `sim.py status` answers `"ok": true`. There are still 7 transactions, all verified at their session mids in earlier rounds, and none were added this round.

**Re-checks from r020 (all pass):**
- B-182: the CLI P/E on a cold cache matches the API.
- B-184: no stale rows carry `revenue_q`.
- B-177:
  - V, MU, DIS and QCOM now have `revenue_ttm`.
  - Among companies above $50B, stale rows went from 16 to 14.
  - The GARP screen shows `excluded_no_ttm`.
- B-183 was still broken at the start of the round. It shipped this round.

## Shipped

- **B-185: the screener's P/E TTM used consolidated net income for LNG (88f039b).**
  - Cause: SEC frames served `NetIncomeLoss` from Cheniere's proxy statement. The pay-versus-performance table in the proxy tags consolidated net income, which includes noncontrolling interests, so it overrode the 10-K figure.
  - Fix: when `NetIncomeLoss` comes from a different filing than `ProfitLoss` and sits nearer it, the screener now uses `ProfitLoss` minus the noncontrolling interest. Companies that tag only `ProfitLoss` now get a value too.
  - Live: LNG's TTM net income went from 4.50B to 3.04B, and its P/E TTM from 13.4 to 19.85 (the stock page shows 20.8; the rest of the gap is share count).
  - MLM is a different case: about 11M new shares were issued in Q3, and the screener's figure is the more current one. No change.
- **B-183: notes due on watchlist names (92177a8).**
  - The brief's `theses_due` now covers notes on symbols that are held or on any of the account's watchlists, marked `held: true|false`.
  - New route `GET /api/portfolios/{ref}/notes-due` and a "Notes due" card on the Dashboard.
  - Live: the INTU note shows as `held: false`.
- **B-127: CLI note commands (d84884f).**
  - New `argus note update <id>` (`--text`, `--review-on`, `--clear-review`, `--archive` / `--unarchive`) and `argus note archive <id>`.
  - New `argus note list --all`.
  - The commands give clean INVALID_ARG errors, and blank text is rejected on update (including a 400 from the API).

Nothing was blocked. Tests: 451 pass, and `npm run build` passes.

**Backlog changes:**
- New items: B-185 (done), B-186 (P/E TTM windows differ silently between the page and the screener, NVDA; open), B-187 (a chart end label overlaps the axis; open).
- New evidence added to B-110 (the INTU after-hours move isn't in the brief) and B-060 (screener sector column, trader r021).

## For the trader to re-check next round

- **B-185:** the GARP screen should show LNG at a P/E TTM of about 19.9. Spot-check the NCI-heavy names THC, VZ, PAA, QSR and DVA against their stock pages.
- **B-183:** the INTU note (or any due watchlist note) should be in the brief's `theses_due` with `held: false`, and on the Dashboard's "Notes due" card.
- **B-127:** use `argus note update` and `argus note archive` instead of curl.
- **INTU:** the 11-20 session after its report.

## For a human

- **B-179, sim look-ahead (still open):** nothing in `scripts/sim.py` stops a trade at the mid of a session whose news came after the close. This round the trader avoided it on its own, with INTU.
- **SEC XBRL gaps (D and the utilities and REITs):** unchanged, and outside Argus.
