# Round 001 summary

Date: 2026-10-20 (Tuesday, during the regular session). This was the loop's first round.

## Data sources (preflight)
- Quotes: working. `argus quotes SPY MSFT` came from Finnhub. Multi-symbol portfolio requests batch through Yahoo, which is by design.
- Finnhub key: reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned HTTP 200 with a quote, so the network secret is being attached.
- History: working (Yahoo, SPY 1mo).
- SEC financials: working (MSFT).
- Market context: the only error was `breadth` ("needs the screener's universe"). It cleared once the universe was built. B-027 tracks that the build only starts on the first screen.
- Stream: off on purpose (`ARGUS_STREAM=off`).

## Portfolios
All three were created and bought on 2026-10-20 at the live quote, each from $100,000 of starting capital. Values were taken around 11:48 ET.

| Portfolio | Benchmark | Positions | Cost | Value | Return to date | Cash |
|---|---|---|---|---|---|---|
| loop-macro | SPY | 10 ETFs | $98,757.78 | $98,752.98 | −$4.80 (−0.005%) | $1,242.22 |
| loop-income | SPY | 17 (35% bond ETFs) | $98,347.12 | $98,290.64 | −$56.48 (−0.06%) | $1,652.88 |
| loop-growth | IWM | 9 small/mid growth | $82,519.60 | $82,379.80 | −$139.80 (−0.17%) | $17,480.40 |

This round's trades:
- **loop-macro** (inflationary-slowdown book): SGOV 179, QUAL 53, XLV 67, XLE 148, SPY 13, XLP 91, USMV 78, VTIP 164, GLD 18, DBC 180. Symbol targets sum to 99%.
- **loop-income**: BND 169, VGIT 140, VCIT 126, SCHP 196, SCHD 288, VIG 20, JNJ 19, PG 31, PEP 37, JPM 14, HD 15, ABBV 17, KO 42, XOM 22, NEE 50, O 71, MSFT 7. Targets equal the intended weights. There are also four alerts.
- **loop-growth**: LOAR 174, PODD 76, KRYS 33, TOST 307, RMBS 96, TMDX 124, HRMY 205, ESE 32, BLLN 57. The watchlist `growth-candidates` holds 7 names that weren't bought.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The three investors filed 30 findings. They were merged into 27 new backlog items (B-005 to B-031), and the phone-width findings were folded into B-002, which was raised to medium. B-032 is a follow-up the developer found while working on B-005. The picks were the three bugs that produce wrong numbers. B-007 was reported by two investors.

## Shipped
- **B-005, the screener's net income could be 1000x too small (f459917).** SEC's frames API often serves the proxy statement's pay-versus-performance figure, tagged in thousands, so roughly 90 companies were affected. Net income is now set to null when it is under 0.1% of revenue, which removes absurd P/Es such as LOAR at 81,740 and ESTC's earnings growth of +99,900%. The trade-off: those companies now have no screener P/E at all. B-032 is the follow-up to get the real value.
- **B-006, the economic calendar dates and times were wrong (fcb780c).** Nasdaq's `date` buckets are usually one day ahead, but not consistently, and its clock is a fixed UTC-4. Days are now assigned from adjacent queries (copies and Monday releases are handled), and times are converted to America/New_York. Checked live, the Fed decision is on Wed 10-28 at 14:00, payrolls on Fri 11-06 at 08:30 and ISM on 11-02 at 10:00, with no weekend dates.
- **B-007, the first day's performance showed gain 0 and net invested 0 (5ff1aad).** A range that starts at inception now starts from 0, before the first day's buys. Gain now equals unrealized P&L, and TWR matches the chart's last point.

Nothing was blocked. `uv run pytest -q` reports 214 passed, and `npm run build` passes.

## Re-check next round
- **Macro:** check calendar dates and times against official schedules, especially Mon 10-26 and Thu 10-29 (GDP, PCE). No Nasdaq query returned those days this round, and an undetectable run of correctly bucketed mid-week dates is possible. Also check whether "Fed Interest Rate Decision" matches the FOMC end date.
- **Multibagger:** check that LOAR and ESTC no longer have absurd P/E or growth figures, and see how many large caps lost their screener P/E (B-032).
- **All:** on day two, check that Performance Gain still equals unrealized P&L. On day one the benchmark return is 0% because it is measured from that day's close.

## For a human
- B-006 relies on heuristics about Nasdaq's inconsistent date buckets, which look like caching on Nasdaq's side. A more stable calendar source would be better if one is free.
- Process: when a developer agent restarted Argus by running `bash scripts/cloud-session.sh` from its own shell, the script exited without starting Argus. Running it as `CLAUDE_CODE_REMOTE=true bash scripts/cloud-session.sh` worked. The script may need a manual-run flag, or the README could say to use `CLAUDE_CODE_REMOTE=true`. The loop doesn't edit that file itself.
- The `investor-*`, `developer` agent types and `mcp__argus__*` tools weren't available, because the session started from `main`. The round ran general-purpose agents that read their `.claude/agents/` files, and the investors used the CLI and API instead.
