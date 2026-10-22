# Round 003 summary

Date: 2026-10-22, ~02:10–03:30 UTC. That's Wed 10-21, 22:10–23:30 ET, after the close, so every value is at the 10-21 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 10-21 close plus post-market prices. The market was closed.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe"), until the universe built (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 10 | $98,757.78 | $98,865.32 | +$107.54 | $1,242.22 | +0.11% |
| loop-income | 17 | $98,347.12 | $98,084.89 | −$262.23 | $1,652.88 | −0.26% |
| loop-growth | 11 | $95,500.05 | $95,147.40 | −$352.65 | $4,499.95 | −0.35% |

**No trades this round.**
- **loop-macro:**
  - The regime call is unchanged, and drift is within ±0.22 pp against a 2 pp band.
  - The macro investor simulated a pre-FOMC trim and didn't place it, because beta is already 0.25.
  - The next review is after the FOMC and GDP/PCE (10-28/29).
- **loop-income:**
  - Every position is within ±0.22 pp of target.
  - The income investor added alert #5 (PG down 4% or more in a day) and a note on O.
  - Forward income is $3,332 a year (3.40%).
- **loop-growth:**
  - All 11 theses still hold.
  - BELFA was added to `growth-candidates`.
  - RMBS reports on 10-26.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 25 findings: macro 9, multibagger 7, income 9.
- **13 new items, B-053 to B-065.** B-058 (fiscal-Q4 EPS null) came from two investors.
- **The rest went into existing items** as new evidence: B-002, B-009, B-013, B-015, B-021, B-022, B-023, B-024, B-025, B-034, B-036, B-040 and B-045.
- **Raised in severity:**
  - B-015 to high: even the first refresh stayed empty.
  - B-026 to medium: the cold `/risk` call took 33 s.
- **B-016 didn't reproduce.**
- **Re-checked and confirmed fixed:**
  - B-033: the brief is scoped to its portfolio.
  - B-008: RMBS and BCRX revenue.
  - B-010: SCHP and VTIP run rates.
  - B-007, day two: gain equals unrealized P&L, and the benchmark return is non-zero.

**Picks:**
- **B-040:** a high-severity wrong number, reported in two rounds.
- **B-058:** reported by two investors.
- **B-015:** high severity, reported in all three rounds.

## Shipped
- **B-040, fundamentals `fcf_ttm` was Yahoo's levered FCF (8eb7b29).**
  - `fcf_ttm` is now operating cash flow − capex over the last four SEC quarters, labeled `sec`. It falls back to the provider's figure, labeled `yahoo`, when SEC has no four usable quarters.
  - MSFT went from 16.5B to 67.0B and KO from 5.2B to 12.56B. Both match their SEC tables.
  - NEE still falls back to Yahoo, because its capex uses custom tags.
- **B-058, fiscal-Q4 diluted EPS was null (10a3bb7).**
  - Q4 EPS is derived from net income ÷ the Q4 share count, from full-year EPS − 9-month EPS, or from full-year EPS − the three reported quarters, and is flagged with `eps_diluted_derived`.
  - Checked live: KO, MSFT, LOAR, RMBS, ESE and PODD have no null EPS rows. KO 0.51, MSFT 3.65 and RMBS 0.57 match the reported figures.
- **B-015, research bands and reported growth were empty on first open (18613fa).**
  - Research now fetches cold fundamentals instead of reading a cold cache.
  - A result with failed inputs is marked `partial` and kept for 2 minutes instead of an hour.
  - Checked live: the first call for CRMD, AAON, IESC, POWL and CRDO had every band's current value and reported growth filled.

Nothing was blocked. `uv run pytest -q` reports 229 passed, and `npm run build` passes.

## Re-check next round
- **Income:**
  - Check that free cash flow (TTM) on stock pages matches the SEC table (KO 12.56B), and use it for payout safety.
  - NEE still shows Yahoo's FCF.
  - Check fiscal-Q4 EPS on KO, JNJ, PG and HD.
- **Multibagger:**
  - Check that first-open research on brand-new names has bands and reported growth.
  - Check fiscal-Q4 EPS on your holdings (it can be a cent off when the share count moves in the year).
  - BLLN's empty bands have a separate cause: too few Finnhub ratio points.
- **Macro:**
  - Check the excess-return start (B-053) and VTIP's December dividend (B-054).
  - Check whether the calendar still starts on the UTC date (B-034).

## For a human
- **Schedule timing:** this run again fired at about 22:10 ET, after the close, not during market hours. Check the routine's timezone. It keeps the calendar bug B-034 visible, and every trade is at a post-market quote.
- **Agents and tools:** as in earlier rounds, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Restart:** `bash scripts/cloud-session.sh` brought Argus up at preflight. Developers restarted it with `pkill` and `setsid nohup uv run argus serve` as separate commands.
- **Lint:** ruff already reports about 143 findings on the codebase. They predate this round, and the developers didn't fix them. That could be a backlog item, or B-001's CI could run ruff only on changed lines.
- **Open high-severity bugs for the next picks:** B-056 (RMBS statements stop at Q1 2026 with no gap flag), B-045 (earnings dates disagree) and B-009.
