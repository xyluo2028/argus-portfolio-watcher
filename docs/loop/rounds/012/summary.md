# Round 012 summary

Date: 2026-11-04, starting about 02:12 UTC. In New York that's Tuesday 11-03 at about 21:12 ET, after the close. The latest close is Tue 11-03.

## Data sources (preflight)
- **Quotes:** working. `argus quotes SPY MSFT` came from Yahoo with the 11-03 close (SPY 754.35) and post-market prices.
- **Finnhub key:** reaches Finnhub. `/api/v1/quote?symbol=AAPL` returned a quote.
- **History:** working, but at the start Yahoo had no 11-03 daily bar, so SPY's history ended at 11-02 (752.10, the bar B-128 was waiting for last round).
  - Yahoo published the 11-03 bars at about 02:30 UTC, during development.
  - The gap made performance and earnings reactions wrong for the evening. Filed and fixed this round as B-134.
- **SEC financials:** working (MSFT).
- **Market context:** the only error was `breadth` ("needs the screener's universe") while the universe built in the background (B-027).
- **Stream:** off on purpose (`ARGUS_STREAM=off`).
- **Tests at start:** 286 passing.

## Portfolios
Return to date is (value + cash − $100,000 starting capital) ÷ $100,000. Values are at the 11-03 close. Accrued dividends are reported separately (they now include B-133's recovered 11-02 payments).

| Portfolio | Cost | Value | Unrealized | Cash | Return to date | Day P&L 11-03 | Accrued dividends |
|---|---|---|---|---|---|---|---|
| loop-macro | $98,404.56 | $98,157.69 | −$246.87 | $1,308.40 | −0.53% | −$362.92 (before its trade) | $65.83 |
| loop-income | $99,618.80 | $101,126.84 | +$1,508.04 | $381.20 | +1.51% | −$651.48 | $185.64 |
| loop-growth | $99,823.05 | $97,941.31 | −$1,881.74 | $176.95 | −1.88% | +$1,509.93 | $0 |

**Trades this round:**
- **loop-macro:** sold 12 GLD at 360.39 (txn 49) and bought 47 IEF at 91.31 (txn 50), both at post-market quotes.
  - Realized −$224.76; net cash +$33.11.
  - This carries out note 56: GLD's 20-day correlation to SPY was 0.69, over the 0.5 trigger.
  - Notes 68 (IEF thesis, review 11-13) and 69 (XLE→RSP still staged for ISM services) record the reasoning.
- **loop-income:** no trades. Every position is within 0.28 pp of target. Note 67 is on BND (review 11-10).
- **loop-growth:** no trades. TOST's Q3 revenue grew +21.3%, above the 18% thesis-break line. Note 66 updates the thesis.

## Shipped
- **B-133: dividend history is merged, not replaced (a423c14).**
  - **Cause:** Yahoo dropped its 10-01 dividend rows for the bond ETFs overnight. Argus overwrote its stored history with that answer, which undid last round's B-129.
  - **Fix:** a refreshed history keeps previously seen ex-dates (within 400 days). Passed estimates are also walked month by month from the last known ex-date.
  - **Live results:**
    - loop-income received went from $53.07 to $185.64, and November from $105.86 to $238.43.
    - loop-macro's accrual went from $0 to $65.83.
- **B-134: the last session's close comes from the quote until Yahoo's bar arrives (63d2b8f).**
  - **Scope:** one shared helper, used by performance (benchmark included) and earnings reactions. The filled close is never stored.
  - **Live results:** checked on a copy of the data with the 11-03 bars removed.
    - loop-growth TWR went from −3.52% to −2.02%, with IWM now +1.45%.
    - loop-income went from +2.24% to +1.72%, with SPY now −1.91%.
    - For all three portfolios, performance's last step now equals Day P&L.
    - The DUOL reaction went from +5.93% to +11.95%, and TOST from −3.44% to −3.76%.
  - When Yahoo's real bars arrived, the results matched them to the cent.
- **B-115: dividend projections keep a month-end or first-day payer's day; the projection test passes on any date (14780f5).**
  - **Production was wrong too:**
    - O projected 12-30 instead of 12-31, then gave January no payment and February two.
    - The bond ETFs projected 12-02 instead of 12-01.
  - **Tests:**
    - A `freeze_today` fixture was added.
    - The target test passes on every day from 2026-01-01 to 2027-10-25.

Nothing was blocked.

**Checks:** `uv run pytest -q` has 307 passing and `npm run build` passes.

## Re-check next round
- **Income and macro (B-133):**
  - Received and accrued should stay near $185 and $66.
  - `dividend_history` should keep its rows across Yahoo's next refresh.
  - last_ex_date and trailing_12m stay low until Yahoo restores the 10-01 rows. That is expected; say so if it doesn't recover.
  - Confirm whether VTIP's 10-01 estimate should count for loop-macro.
- **Everyone (B-134):**
  - Performance's last step should equal Day P&L, and SPY/IWM shouldn't be null, on any evening when Yahoo's bar is late.
  - `closes_from_quotes` in the performance response says when the fill was used. It isn't shown in the UI yet.
- **Income (B-115):**
  - O's next dates should be 11-30, 12-31, 01-29 and 02-26.
  - The bond ETFs should show 12-01, 01-04 and 02-01.
- **Macro and income:** B-135, payrolls 11-06 dropping off the calendar. Check whether it's back.
- **Multibagger:**
  - B-119, the EPS basis mismatch behind TOST's "beat +44.3%".
  - B-137, the Reported financials table missing the just-reported quarter.

## For a human
- **New time bomb:** B-139. `test_speed.py::test_single_symbol_fundamentals_add_price_cagr_and_fcf_margin` fails from 2026-11-27 on, found with the new `freeze_today` fixture. Pick it within two rounds.
- **Yahoo data quality:** three rounds running, Yahoo has served wrong or missing data that Argus took at face value:
  - a NaN close (B-128)
  - a dividend list missing the latest row (B-129/B-133)
  - a late daily bar (B-134)
  Each is now handled defensively.
- **Schedule timing:** this is the twelfth round in a row fired outside market hours (Tuesday 21:12 ET). The README asks for weekdays during market hours.
- **Agents and tools:** as before, the `investor-*` and `developer` agent types and the `mcp__argus__*` tools weren't available. General-purpose agents read their `.claude/agents/` files and used the CLI and API.
- **Developer instructions (proposed again):** each developer was told to revert only its own files and to use a throwaway server and data copy instead of `pkill`. Proposal: put both in `developer.md`.
- **The running server is on the round's starting code.** It was not restarted after the fixes. The next round's preflight restart picks them up.
- **Open high-severity items:** B-017 (asset classes and bond duration; income re-raised it with bonds near 52-week lows), and B-016/B-055.
- **Cloud stop hook:** it asks for a commit and push whenever the tree is dirty mid-round. The lead ignores it until wrap-up, as the procedure says.
