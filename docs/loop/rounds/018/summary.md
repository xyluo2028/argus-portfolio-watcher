# Round 018 summary

**Trading day.** The session traded was Monday 2026-11-16. The round ran in the evening of 11-16 New York time (the early hours of 11-17 UTC), and `market_session` was `closed`.

## Data sources (preflight)

- **Quotes:** working. MSFT came from Finnhub and SPY from Yahoo. The Finnhub key reaches Finnhub: `/quote?symbol=AAPL` returned 200.
- **History:** working (Yahoo, SPY 1mo). Yahoo's daily bar for 11-16 wasn't out yet; B-175 now fills it in from the quote.
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth`, which waits for the screener universe (B-027).
- **Agents and tools:** as in r017, the `trader` and `programmer` agent types and the `mcp__argus__*` tools weren't loaded. General-purpose agents read their `.claude/agents/` files and used the CLI and the API.

## The account (at the 11-16 close)

| | |
|---|---|
| Account value | **$9,933.04**, −0.67% since the start |
| SPY over the same sessions (`sim.py`, close to close) | −1.91% |
| SPY from the trader's 11-13 fill (Argus) | −1.69% |
| Cash | $1,200.11 (12.1%) |
| Positions | 6: SPY 34.6%, ADBE 12.3%, XLV 12.1%, META 9.9%, LNG 9.9%, TMUS 9.0% |

**Trade:** one order, filled at the 11-16 mid.

| Order | Fill | Reason |
|---|---|---|
| BUY 5.2579 TMUS ($900) | 171.1701 | Defensive value while fear & greed was at 11.8 ("Extreme fear"). P/E 16.4 is at the 5th percentile of its 5-year range. FCF yield is about 10%, the dividend 2.4%, and the 1y beta to SPY is negative. |

- **Thesis, alert and watchlist:** the trader wrote a thesis note before buying, set an alert at TMUS ≤ $150, and added TMUS to `candidates`.
- **NVDA:** no trade on its earnings. The report comes out on the evening of 11-17, after that session's mid, so the trader is keeping the cash to decide on the 11-18 session.

**Account check:**
- `sim.py status` answers `"ok": true`.
- All 6 transactions are at their session's mid price. TMUS: (172.680 + 169.660) / 2 = 171.170.

**Re-checks from r017:** the trader confirmed that B-053, B-106 and B-021's labels work. NVDA moving into `watchlist_earnings.recent` can only be checked next round.

## Shipped

- **B-175: history and the stock chart get a provisional bar for the last session (9ee1853).**
  - While Yahoo's daily bar is late, `/api/history` (and the CLI and MCP with it) adds that session's bar from the quote, marked `provisional: true` and never stored.
  - The chart's OHLC readout now starts with the bar's date and says "(from quote)" for a provisional bar.
  - Live: ADBE's 1mo history now ends with 11-16 (O 247.00 H 251.34 L 242.84 C 246.00).
- **B-136, reopened: the brief's upcoming dividends cover the same 14 days as Coming up (547a110).**
  - The brief and `/api/events` now share the `EVENTS_DAYS_AHEAD = 14` constant. Earnings in the brief still look 7 days ahead.
  - The payload states both windows (`dividends_days_ahead`, `earnings_days_ahead`).
  - Live: the brief now lists TMUS's 11-25 ex-dividend.
- **B-019: the screener shows latest-quarter growth, TTM figures and the period of every column (b22ab5a).**
  - New fields, each of which can be filtered and sorted: `revenue_growth_q_yoy_pct`, `pe_ttm`, `operating_margin_ttm_pct` and `roe_ttm_pct`. They are built from SEC quarterly frames.
  - Every row carries `fiscal_year_end`, `latest_quarter` and `ttm_through`.
  - On the Screener page, column headers carry labels like "FY2025" or "latest qtr y/y".
  - INCY now shows P/E TTM 60.8, op margin TTM 10.4% and ROE TTM 7.1% beside its FY2025 figures.
  - What's left was split off as B-177: no TTM without a Q4 frame (AAPL, MSFT), FY figures that can lag a year, and no TTM FCF or margins.

Nothing was blocked. Tests: 439 pass, and `npm run build` passes.

**Backlog changes:**
- New items: B-174 (the Dashboard's "SPY, last session" becomes a flow-weighted blend after a same-day buy), B-175, B-176 (no marker when an earnings date moves, e.g. INTU 11-19 → 11-20) and B-177.
- New evidence added to B-125, B-026, B-162 and B-168.

## For the trader to re-check next round

- **History bar:** once Yahoo publishes the 11-16 bar, the `provisional` flag should disappear and the bar should have real volume. On the next session, the same fill should appear before Yahoo's bar arrives.
- **Brief dividends:** they should match the Dashboard's Coming up, including the TMUS ex-date on 11-25.
- **Screener:**
  - Re-run the r018 quality screen using `pe_ttm`, `operating_margin_ttm_pct` and `roe_ttm_pct`; INCY should drop out.
  - A screen for latest-quarter growth ≥ 15% should drop XZO, NUTX and PSIX.
  - Every column header should show its period.
- **NVDA:** after its 11-17 report, it should move to the brief's `watchlist_earnings.recent`.

## For a human

- **Two SPY figures:**
  - `status.md` says SPY −1.91% since the start, measured close to close from the 11-13 close.
  - Argus says −1.69%, measured from the trader's 11-13 fill.
  - The gap is the first day's move from fill to close, made larger by the low SPY quote behind the 11-13 fill (B-169). Neither figure is wrong.
- **B-168, cash balance (high), is still open and still needs a decision:** how should the loop set starting cash for bot0-sim without changing the account outside `scripts/sim.py`?
- **Hard-coded window in the frontend:** `EventsCard.tsx` and `api.ts` still use a literal 14 for the events window, so changing the new Python constant also means changing those.
- **Process:** the agent types and the Argus MCP still aren't registered in cloud sessions. The general-purpose fallback works.
