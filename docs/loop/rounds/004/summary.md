# Round 004 summary

Date: 2026-10-23, from about 02:10 UTC. That's Thu 10-22, about 22:10 ET, after the close, so every value is at the 10-22 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo, with the 10-22 close plus post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned HTTP 200 with a quote.
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe"), until the universe built (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,747.15 | $98,931.61 | +$184.46 | $1,253.87 | +0.19% |
| loop-income | 17 | $98,347.12 | $99,788.59 | +$1,441.47 | $1,652.88 | +1.44% |
| loop-growth | 11 | $95,500.05 | $94,644.67 | −$855.38 | $4,499.95 | −0.86% |

**Trades this round:**
- **loop-macro:** sold 50 SGOV @ 100.63 (realized +$1.03) and bought 55 IEF @ 91.27 ($5,019.85), both at post-market quotes. The idea: on 10-22 the 10-year yield fell 19 bp and bonds have started to hedge stocks again. Targets are now SGOV 13% and IEF 5%. IEF has a thesis note with a review date of 10-30.
- **loop-income:** no trades. Every position is within ±0.34 pp of target. Alert #5 (PG) was turned off and alert #6 (KO down 4% or more in a day, before its 10-27 report) added.
- **loop-growth:** no trades. All 11 theses still hold. TMDX got a watch note (review 11-06) and LIF went onto `growth-candidates`.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 24 findings: macro 9, multibagger 7, income 8.
- **New items:** B-066 to B-072, plus B-073 as a developer follow-up.
- **B-066 was found by two investors:** income saw it in index 1D, macro in futures, FX and crypto 1D.
- **B-048 raised to high** and widened: the headline consensus contradicts the counts beside it.
- **B-056** confirmed by a second investor (income: KO, NEE).
- **The rest went into existing items** as new evidence: B-002, B-012, B-013, B-017, B-019, B-022, B-023, B-024, B-025, B-026, B-027, B-029, B-034, B-036, B-039, B-045, B-046, B-049, B-051, B-053, B-054, B-059, B-061, B-062 and B-063.
- **Re-checked and confirmed fixed:**
  - B-015, for COLL, GEN, LIF and HIMS.
  - B-058, for all growth holdings and KO, JNJ, PG and HD. PEP's 16-week Q4 is still missing; that's B-069.
  - B-040, for KO, ABBV, PG, JNJ, MSFT and LIF. HD, NEE, PEP and O still use Yahoo's figure (B-069).

**Picks:**
- **B-066:** wrong numbers, high severity, reported by two investors.
- **B-056:** high severity, reported by two investors.
- **B-048:** high severity, reported in three rounds.

## Shipped
- **B-066, Markets 1D used the wrong prior close (0f70d37).**
  - The cause is in Yahoo's daily bars: past closes randomly come back null, and after 6 pm ET futures, FX and crypto "today" bars already hold the overnight price.
  - Every series is now anchored on the batch quote's previous close and live price, worked out on each asset's own session calendar.
  - Checked live at 22:26 ET:

    | Gauge | Before | After | Should be |
    |---|---|---|---|
    | S&P 500 | −0.64% | −1.21% | −1.21% |
    | Nasdaq 100 | −1.80% | −2.90% | −2.90% |
    | XLU | +2.36% | +2.07% | +2.07% |
    | WTI | +3.72% | +1.06% | |
    | Bitcoin | −3.18% | +0.23% | |

- **B-056, statements silently stopped at Q1 2026 (eba0140).**
  - The cause isn't in Argus. SEC's companyfacts feed itself ends at Q1 2026 for KO, NEE and RMBS, although their 10-Qs, with XBRL, are filed.
  - Statements and fundamentals now carry `latest_period`, its age and `stale` (more than 135 days old). The stock page warns about stale SEC data, and FCF TTM says which quarters it covers (for example "SEC, 4Q to 2026-04-03").
  - Filling the missing rows from each filing's own XBRL is the new item B-073.
- **B-048, analyst consensus contradicted its counts (5ec782e).**
  - Both feeds were Yahoo: the headline key and mean, and the monthly counts.
  - The label, mean and count are now derived from the counts shown on the page. Yahoo's headline is used only as a labeled fallback, and the price-target count is shown separately.
  - Checked live:
    - INOD: was "none", now Buy 1.75, 4 analysts.
    - KRYS: was "Strong Buy 1.25", now Buy 2.00, 12 analysts.
    - LIF: now Buy 2.10, 10 analysts.

Nothing was blocked. `uv run pytest -q` reports 235 passed, and `npm run build` passes.

## Re-check next round
- **Macro:**
  - Check Markets 1D during regular hours and again over a weekend.
  - Futures now show the next session's date after 6 pm ET.
  - USD/JPY's previous point is now the quote's previous close.
  - B-034 (calendar on the UTC date) is still open.
- **Income:**
  - Check the stale-SEC warning on KO and NEE. After KO reports on 10-27 it will be two quarters behind.
  - Check that the FCF TTM coverage line matches the quarters in the table.
- **Multibagger:**
  - Check that consensus labels agree with the count bars. Labels will often read "Buy" where Yahoo said "Strong Buy".
  - Check the warning on RMBS.
  - B-045 (earnings dates) is the top remaining high-severity bug.

## For a human
- **Schedule timing:** this round again fired at about 22:10 ET, after the close (fourth round in a row). Check the routine's timezone. Trades are at post-market quotes and the UTC-date bugs (B-034, B-049) stay visible.
- **Shared scratchpad:** the investor agents share one scratchpad directory. The macro investor's `drift.json` was overwritten by another investor's file of the same name. Proposed: the investor guide should tell each investor to use its own subfolder. I didn't change it, because the loop's instructions are off-limits to the loop.
- **Preflight restart:** the classifier refused the combined `pkill …; rm -rf data; bash scripts/cloud-session.sh` command. There was no `data/` and nothing running, so I ran `scripts/cloud-session.sh` alone. Consider rewording the README step as separate commands.
- **Agents and tools:** as in earlier rounds, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **SEC lag:** companyfacts lagging filings by months (B-056, B-073) affects many holdings. B-073 is a bigger change than one round's item usually is.
- **Open high-severity bugs for the next picks:** B-045 (earnings dates), B-009 (Finnhub vs SEC quarterly growth) and B-017 (asset-class view).
