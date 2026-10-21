# Round 002 summary

Date: 2026-10-21, ~02:10–03:30 UTC. That's Tue 10-20, 22:10–23:30 ET, after the close, so every trade and value is at the 10-20 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo this time, with the 10-20 close plus post-market prices. The market was closed.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned HTTP 200 with a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe"). It cleared once an investor's first screen built the universe (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 10 | $98,757.78 | $98,862.66 | +$104.88 | $1,242.22 | +0.10% |
| loop-income | 17 | $98,347.12 | $98,375.25 | +$28.13 | $1,652.88 | +0.03% |
| loop-growth | 11 | $95,500.05 | $95,063.43 | −$436.62 | $4,499.95 | −0.44% |

This round's trades:
- **loop-macro:** none. The regime call is unchanged, and drift is within ±0.22 pp against a 2 pp band. The next review is after the FOMC (10-28) and GDP/PCE (10-29).
- **loop-income:** none. Every position is within ±0.25 pp of target, rates are flat and no dividends changed. After B-010, forward income reads $3,332 a year (3.39%), up from $3,218.
- **loop-growth:** two buys at the post-market quote, each with a thesis note and a review date of 2026-11-20: GRND 487 @ 14.35 ($6,988.45) and INOD 107 @ 56.00 ($5,992.00). BCRX and PTCT were added to the `growth-candidates` watchlist.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 23 findings: macro 8, income 7, multibagger 8. Twenty became new items, B-033 to B-052. The rest went into existing items: the phone-width calendar rows into B-002, the Dividends page dates into B-013, and the BCRX revenue evidence into B-008. B-014 (XOM listed twice) no longer reproduces, because the provider's data changed, so it moved to Won't do.

**Picks:** B-033 was reported by two investors and puts other portfolios' events in the wrong brief. B-008 and B-010 are high-severity wrong numbers, and both were reported in two rounds.

## Shipped
- **B-033, a portfolio's brief listed other portfolios' events, alerts and theses (8bb750b).**
  - `daily_brief` now scopes its events to the brief's portfolio, and `held` means held in that portfolio.
  - Alerts and theses are filtered to the portfolio's symbols.
  - Earnings that have already reported, whether they have actuals or their time has passed, now go under recent instead of upcoming. This also fixes `/api/events` and "Coming up".
  - Checked live: the loop-macro brief no longer lists other portfolios' names, and RMBS appears only in loop-growth's brief.
- **B-008, statements missed revenue tagged including assessed tax (1d4ad3f).**
  - The statements and the screener now share one revenue tag list.
  - The including-tax tag only fills periods where no net-revenue tag has a value.
  - RMBS and BCRX now have revenue for all 8 quarters, and research growth and margins are filled.
  - BANR, a bank, isn't fixed by this; see B-047.
- **B-010, TIPS ETF income was understated (bd921a1).**
  - A payer whose last-12-month payments vary a lot in both directions now uses its trailing 12 months as the run rate.
  - SCHP's rate went from 0.672 to 1.258, and loop-income's forward income rose $115.
  - Steady payers are unchanged.
  - VTIP now also uses its trailing 12 months, about 2.35 instead of 0.933 × 4.

Nothing was blocked. `uv run pytest -q` reports 225 passed, and `npm run build` passes.

## Re-check next round
- **Macro:** the loop-macro brief should show no other portfolios' events. Check that VTIP's dividend rate looks right. Do the day-two performance check: gain should equal unrealized P&L, and the benchmark return should be non-zero.
- **Income:** check SCHP's rate and the forward income on the Dividends page. Check that the brief lists only your holdings and that already-reported earnings sit under recent. Do the day-two performance check.
- **Multibagger:** check RMBS and BCRX statements and research growth. BCRX's Q4 2025 revenue of $406.6M is what the filings say, and BCRX has no gross margin because it files no GrossProfit. Check the GRND and INOD theses after their first full session.

## For a human
- **Schedule timing:** this run fired at about 22:10 ET, after the close, not during market hours as the setup intends. Investors traded at post-market quotes, and the macro investor found a UTC-date calendar bug (B-034) only because of the hour. Check the routine's timezone.
- **Restart process:**
  - `rm -rf data` at preflight was refused by this session's permission classifier. There was no `data/` and no running Argus, so it didn't matter this time.
  - A developer found that running `pkill -f "argus [s]erve"` and the start in the same shell command kills that shell, because the command text matches the pattern. Run them as separate calls.
  - `bash scripts/cloud-session.sh` run by hand again left no server running after a restart, and the developer started it with `setsid nohup uv run argus serve`.
  - The README's restart line could split these steps. The loop doesn't edit that file itself.
- **Agents and tools:** as in round 001, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files, and the investors used the CLI and API.
- **New high-severity bugs:** B-040 (fundamentals FCF is Yahoo's levered FCF, 4x too small for MSFT) and B-045 (inconsistent earnings dates) are open for the next round's picks.
