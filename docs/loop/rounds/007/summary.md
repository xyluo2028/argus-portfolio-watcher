# Round 007 summary

Date: 2026-10-28, starting about 02:12 UTC. In New York that's Tue 10-27 at about 22:12 ET, so the market was closed. All values are at the 10-27 close or a post-market quote.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 10-27 close and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote (HTTP 200).
- **History:** working (Yahoo, SPY 1mo).
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000.

| Portfolio | Positions | Cost | Value | Unrealized | Cash | Return to date |
|---|---|---|---|---|---|---|
| loop-macro | 11 | $98,747.15 | $98,654.91 | −$92.24 | $1,253.87 | −0.09% |
| loop-income | 17 | $99,089.75 | $99,872.34 | +$782.59 | $910.25 | +0.78% (+0.82% with the $33.76 PG dividend accrued) |
| loop-growth | 11 | $97,758.05 | $94,801.90 | −$2,956.15 | $2,241.95 | −2.96% |

**Trades this round:**
- **loop-income:**
  - Bought 1 KO @ $91.23 at the post-market price after its Q3 beat (thesis note 50, review 2027-02-20). KO is now 3.93% against a 4% target.
  - Bond ETFs are 35.2% of the book, and forward income is $3,350 a year.
- **loop-growth:**
  - No trades. INOD fell 25.3% on 10-27 on layoff reports tied to a customer "ramp-down". It's held until its 11-05 report, with exit rules in note 49.
  - DUOL, the screener's best new idea, failed research: latest quarter +18.3%, and the low P/E comes from a tax gain.
- **loop-macro:**
  - No trades: every position is within ±0.23 pp of target, and FOMC (10-28) and PCE (10-29) are imminent.
  - SELL 6 GLD / BUY 24 IEF stays parked in note 48.

The portfolios are saved in `docs/loop/sim/snapshot.json`.

## Triage
The investors filed 26 findings: macro 9, multibagger 9, income 8.
- **New items:** B-094 to B-101 from the investors, and B-102 and B-103, which the developers spotted.
- **Raised:** B-083 to high. INOD's momentum showed 1W +8.8% while the chart showed −18.7%.
- **Existing items with new evidence:** r007 lines on B-002, B-016 (oil and gold 1D show the overnight move with the opposite sign), B-017, B-019, B-023, B-026, B-036, B-038, B-045, B-049, B-059, B-067, B-071, B-075, B-077 and B-092.
- **Didn't reproduce:** B-088. MNTN's Q2 report is back, so the item stays open to watch around MNTN's 11-04 report.
- **Confirmed by investors:** B-046, B-013 and B-085, which shipped last round. They were already in Done.

**Picks:**
- **B-083:** wrong numbers, high, reported in three rounds by two investors.
- **B-009 + B-079:** wrong numbers, high, reported in six rounds. Both are the same card and the same window mismatch.
- **B-093:** wrong numbers. KO's December dividend showed twice, a regression from last round's B-013 slice.

## Shipped
- **B-083, momentum contradicts the chart (96f181a).**
  - 1W/1M/3M/6M/YTD/1Y now come from Argus's own daily closes, on the same starting closes as the chart's range buttons, through a shared `range_bases`. They replace Finnhub's stale values on the stock page, the Dashboard Momentum tab and MCP.
  - The stock page uses the live price.
  - Live: INOD reads 1W −18.7% and YTD −12.2%, matching the chart. RMBS and JPM match for every period.
- **B-009 + B-079, valuation card lags the SEC table (ce9d74f).**
  - When SEC's quarters are at least as recent as Yahoo's, revenue TTM, EPS TTM, latest-quarter growth and FCF margin come from SEC's four newest quarters. The card labels each one, e.g. "SEC, 4Q to 2026-09-30".
  - FCF margin is always SEC FCF ÷ SEC revenue.
  - Live:
    - RMBS: $796.11M / $2.43 / +22.3% / 39.3%. It showed $756M / +20.4% / 41.4% before.
    - BLLN: growth +64.4%. It showed −12.8% before.
    - KO FCF margin: 25.49%. It showed 25.06% before.
- **B-093, announced ex-dates and duplicates (8e14633).**
  - An announced ex-date replaces any estimate within half a payment period, so KO's December dividend shows once.
  - Announced ex-dates and pay events carry amounts: PG 11-16 shows $33.76, and KO 12-01 shows ≈ $22.79.
  - Projections now run past Dec 31: JPM ~2027-01-06, ABBV ~2027-01-15, PG ~2027-01-25.
  - The Dividends page uses the announced dates: KO 12-01, NEE 11-27.

Nothing was blocked. `uv run pytest -q` reports 260 passed, and `npm run build` passes.

## Re-check next round
- **Everyone, momentum (B-083):** during market hours the stock page should track the live price, and the Dashboard Momentum tab runs to the last close. "vs S&P 500, 1 year" is still Finnhub's and may lag a session.
- **Multibagger, valuation card (B-009):**
  - RMBS and BLLN card figures should match the SEC table.
  - BLLN EPS TTM is now $0.70, the sum of its quarters, against Yahoo's $0.63. The difference comes from the share count changing after its IPO.
  - P/E still uses Finnhub's EPS, so it won't equal price ÷ the EPS shown (B-095).
  - Check the card on the next stock that reports.
- **Income, dividends (B-093):**
  - KO should show one December payment everywhere, including once Yahoo records the 12-01 ex-date.
  - Announced amounts are the last payment until a raise is actually paid.
  - Check the January dates.
- **Income:** record PG's 11-16 dividend as a `DIVIDEND` when it's paid.
- **Multibagger:** INOD reports 11-05 and MNTN 11-04 (B-088).
- **Macro:** FOMC 10-28 and PCE 10-29. Execute or drop note 48.

## For a human
- **Schedule timing:** this is the seventh round in a row fired outside market hours, at about 22:12 ET. The README asks for weekdays during market hours. In-session behavior (live momentum, same-session lots) still can't be checked live.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer revert instruction:** proposed again. `developer.md` says to `git checkout -- .` when abandoning work, which would wipe the lead's uncommitted backlog edits. Each developer was told to revert only its own files.
- **Open high-severity items:** B-017 (asset-class view and duration). B-002, phone width, has now been reported by every investor across six rounds; it may need a dedicated round.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead ignores it until wrap-up, as the procedure says.
