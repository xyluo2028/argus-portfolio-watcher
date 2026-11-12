# Round 015: income investor

## What I did
- **Market (Argus market context, reviewed Wed 11-11 ~21:30 ET, latest close Wed 11-11; Veterans Day, so stocks traded and the cash bond market was closed):**
  - CPI week. The S&P 500 rose 1.31% to 7619.38 and the Nasdaq 100 2.28% (XLK +3.23%). VIX fell to 17.49 from 25.6 last Friday.
  - Rates rose: ^TNX went 4.859 (11-06) → 4.864 → 4.983 (11-10, CPI day) → 4.998. On the Treasury curve (as of 11-10) the 10-year is 4.98% and the 2-year 4.73%, up 22 bp from 4.51% last round. The 10y–2y spread narrowed to +25 bp.
  - Fear & Greed reads 20.8, "Extreme fear", on five components (breadth isn't built tonight).
  - Argus's economic calendar is **empty** tonight, so I couldn't see the CPI actual or Thursday's PPI in Argus (finding 1). FOMC is 12-09. HD reports 11-17 before the open.
- **Portfolio `loop-income` (11-11 close, `argus portfolio show --json`):**
  - **Value and P&L:** value $102,933.63, cost $99,950.30, unrealized +$2,983.33 (+2.98%). Day P&L +$66.56 (+0.06%) against SPY +1.32%. MSFT (−2.26%, −$96) and PG (−0.59%) offset XOM, SCHD and VIG.
  - **Since last round:** 11-09 +$913.98, 11-10 −$242.81 (CPI), 11-11 +$66.56, so +$737.73 (+0.72%) against SPY +3.33% (735.29 → 759.81). That's what a 0.16-beta book should do in a relief rally.
  - **Performance:** TWR +3.20% since 10-20, SPY −1.20%, excess +4.40%. Gain $3,166.83 equals unrealized plus accrued dividends ($2,983.33 + $183.50), to the cent. I also checked the SPY leg by hand from the 11-06 base.
- **Risk:** beta 0.165, volatility 7.98%, VaR 95% $680 / 99% $1,052, max drawdown −5.74%. The "SPY −10%" scenario gives −1.6% (0.165 × 10). The 2022 rate-shock replay gives −14.2%.
- **Income:** forward income $3,344.27. The yield is 3.25% (= 3,344.27 ÷ 102,933.63) and 3.35% on cost (÷ 99,950.30). I checked both by hand.
  - 2026 total $781.91, of which $183.50 received (est.) and $598.41 projected; December is $490.49.
  - Next up: O pays 11-13, PG pays 11-16, XOM goes ex 11-16, MSFT ex 11-19, JNJ ex 11-24, NEE ex 11-27.
- **Payout check before HD's report:** HD's payout is 64.8% with 5-year dividend growth of 8.96%. It is my largest risk contributor (13.5% of risk on a 5.5% weight). Nothing to act on before 11-17.
- **Bond sleeve, by hand (Argus still has no duration):** I re-ran my regression of daily returns on ^TNX changes over one year of Argus history. Effective duration is BND 5.42, VCIT 5.74, VGIT 4.80 and SCHP 4.06, which gives −$906 per +50 bp on the $34,991 sleeve.
  - **Test of that number:** the 10-year rose 13.9 bp from 11-06 to 11-10. The model predicts −$252, and the sleeve actually lost −$260 (11-06 closes against the latest prices). The estimate works.
- **Drift:** everything is within ±0.46 pp of target on a ±2 pp band. The biggest drifts are HD +0.46, BND −0.33 and VCIT −0.29. The bond sleeve is at 34.0% against a 35% target.
  - I simulated a trim (SELL $474 HD, BUY $300 BND, BUY $220 VCIT). It works, and `type: "sell"` is accepted.
  - I didn't place it, because a 0.46 pp drift isn't worth trading.
- **Decision: no trade.**
  - The 10-year at 4.998% is still below my 5.1% add trigger.
  - Drift is less than a quarter of the band.
  - With only $49.70 in cash, any bond add would have to be funded by trimming HD, JNJ or PEP, and that isn't justified before HD's report.
  - Wrote note 87 (BND, review 11-18).
  - Alerts on ^TNX are still rejected (B-078), so I set alert 10, `BND price_below 70.70`, as a proxy for the 10-year at about 5.1% (5.4 duration × ~10 bp).
- **Cash: $49.70** (invested at cost $99,950.30, realized gains $0, no trades).
  - Return to date: (102,933.63 + 49.70 − 100,000) ÷ 100,000 = **+2.98%**.
  - With Argus's $183.50 of accrued dividends it is +3.17%. Argus doesn't book those as cash, so I don't count them as spendable.

## Last round's changes
- **B-142 (risk fills the last session from quotes): works, and tonight was the late-Yahoo case I couldn't test last round.**
  - The Yahoo history for the holdings ends at 11-10. For example, the BND, VCIT, VGIT and SCHP `/api/history` bars stop at 11-10.
  - Risk has `closes_from_quotes.date = 2026-11-11` for all 17 holdings plus SPY, `as_of` 2026-11-11, and the card header says "(last close from quotes)".
  - The Last session (11-11) tile shows +$67 / +0.06% (`last_day.value` 66.559). That matches header Day P&L of +$66.56, and performance's 11-10→11-11 step (102,867.07 → 102,933.63).
- **B-147 (simulate needs a side): works.** `{"symbol":"HD","type":"sell","amount":474}` simulated as a SELL of 1.349 shares at 351.31. A trade with no side returns 400 "Trade 1 (HD): give side (or type) BUY or SELL."
- **B-146 (one-holding risk):** doesn't apply to my book. My 17-holding risk is unchanged in shape and the card renders.
- **B-139:** tests only. No effect on me.
- **Re-seen, still open:**
  - **B-136: fixed for a weekday run.** The brief's `dividends_upcoming` is O pay 11-13, PG pay 11-16 and XOM ex 11-16, the same as Coming up.
  - **B-148:** unchanged. SCHP still has 11 projected ex-dates priced at 0.09717 (= 1.166 ÷ 12) each, totalling $209.49 against $228.54 annual income. The book's next 12 months sum to $3,325.23 against $3,344.27.
  - **B-153:** the 11-02 bond-ETF dividends are still estimated 10 days later; $130.43 of the $183.50 "received" is estimated.
  - **B-044:** "Where the risk comes from" still lists 15 of 17 holdings (SCHP and XOM are missing), at desktop and 390 px.
  - **B-063:** the footnote still says "Annual rate = latest payment × payments per year", but SCHP's $1.17 is its trailing 12 months.
  - **B-022:** Targets & drift still opens on "By sector" with "Targets sum to 0.0%".
  - **B-132:** HD's 11-17 earnings row still says `quarter 3, year 2027`.
  - **B-043:** KO yields 2.69% on fundamentals against 2.17% on Dividends (2.12 ÷ 97.57); XOM 2.60% against 2.47%.
  - **B-118:** `/analysis?portfolio=loop-income` opened loop-growth. I had to set `localStorage['argus.portfolio']` in a Playwright script to screenshot my own book.

## Findings

### 1. One failed day empties the whole economic calendar, including CPI actuals and the next PPI
- kind: bug
- severity: medium (in CPI week, the one week I most need it)
- evidence:
  - `GET /api/market-context` returns `calendar.events: []` and `all_count: 0`, with the error `econ:21:2026-11-11: Client error '403 Forbidden' ... date=2026-11...`. It was still empty when I re-fetched later.
  - Only FOMC rows remain. Tue 11-10's CPI (with its actual) and Thu 11-13's PPI are gone, even though they appeared last round.
  - The other days answer: `curl https://api.nasdaq.com/api/calendar/economicevents?date=2026-11-10` and `?date=2026-11-13` both returned 200 from this machine a minute later.
  - Cause, in `backend/argus/providers/macro.py` `economic_events()`: `pool.map(day, queries)` runs about 24 day queries. The first `raise_for_status()` failure propagates out of `fetch()`, so `_keep_releases()` never runs. As a result, neither the days that answered nor the stored rows for the last session are returned.
  - This is broader than B-135, where a day Nasdaq drops loses only that day's rows.
- suggestion: catch errors per day (treat a failed day as "no answer", as `_nasdaq_days` already handles) and still merge and return the rest, plus the kept store. Report "1 of 24 days failed" in `errors`.

### 2. Bond rate sensitivity is still missing (B-017), and my by-hand estimate held up out of sample
- kind: feature
- severity: medium (34% of the book; rates are this week's main risk)
- evidence:
  - `/exposure` still shows the four bond ETFs as "Unclassified 34.0%". Stress scenarios have no rate shock other than the 2022 replay.
  - From `/api/history/{BND,VCIT,VGIT,SCHP}` and `/api/history/^TNX` (1y, 251 days), the regression slope gives durations of 5.42, 5.74, 4.80 and 4.06, which is −$906 per +50 bp.
  - From 11-06 to 11-10 the 10-year rose 13.9 bp. The model predicted −$252 and the sleeve lost −$260.
  - The brief flags BND, VCIT, VGIT and SCHP as "near 52w low" (1.3–2.2% away) with no rate context.
- suggestion: add an "Est. rate sensitivity (1y regression)" column for bond funds, and "10y +50 / +100 bp" rows in Stress scenarios, labelled as estimated. It is about 25 lines on data Argus already caches.

### 3. At phone width, Stress scenarios hide every loss number
- kind: ux
- severity: medium (the one table a client asks about in a selloff)
- evidence:
  - I screenshotted `/analysis` at 390 px with loop-income selected. There are no page errors and no page overflow.
  - The Stress scenarios table shows only "Scenario" and a cut-off "Window" column. SPY, "Your portfolio (est.)" and "Change in value" (−25.0% / −$25,690 etc.) are off the right edge, with no scroll hint.
  - The Dividends table still stops after Yield (B-002).
- suggestion: on phones, drop the Window column (or move it under the scenario name) and show Scenario, Your portfolio and Change in value.

### 4. I still can't alert on the 10-year yield, so a key trigger has to go through a proxy (B-078)
- kind: feature
- severity: medium (my bond-add rule is written on ^TNX)
- evidence:
  - `argus alert add ^TNX price_above 5.1` returns `INVALID_SYMBOL: '^TNX' doesn't look like a US ticker.`, while `/api/quotes?symbols=^TNX` returns 4.998.
  - I set `BND price_below 70.70` instead (alert 10). That only works through my own duration estimate.
- suggestion: allow `^`-prefixed index and yield symbols for `price_above`/`price_below` (the quote path already handles them).

### 5. The 10-year gauge shows a move on a bond-market holiday without saying so
- kind: ux
- severity: low
- evidence:
  - On Veterans Day (cash Treasuries closed), `/api/quotes?symbols=^TNX` returned price 4.998 with open = high = low = 4.998, `as_of` 19:59:54Z and change +0.015. Market context shows "10-year yield 4.998, 1D +0.30%" for 11-11, and ^TNX history has an 11-11 bar.
  - The Treasury curve correctly stays on 11-10.
  - An income client sees a "rate move" on a day bonds didn't trade.
- suggestion: when the date is a SIFMA bond holiday, mark ^TNX (and the curve) "bond market closed" and show the change as 0 or a dash.

### 6. First risk load is 31.5 s (B-026, getting worse)
- kind: perf
- severity: low (known)
- evidence: the first `GET /api/portfolios/loop-income/risk` of the evening took 31.46 s (25.6 s last round). Performance took 0.06 s, dividends 0.07 s, drift 0.04 s, exposure 0.57 s and the brief 2.6 s. Analysis rendered its shell in 0.65 s, and Risk said "Loading risk…" until then.
- suggestion: as in B-026, warm risk in the background after startup and after Yahoo's daily bars land.

### 7. Two yields for the same holding on two pages, still (B-043)
- kind: ux
- severity: low
- evidence:
  - `/api/portfolios/loop-income/fundamentals` vs `/dividends`: KO 2.69% vs 2.17%, XOM 2.60% vs 2.47%, SCHP 4.89% vs 4.60%, VCIT 5.01% vs 5.15%.
  - KO's 2.69% implies a price of about $79 against the $97.57 quote, so it looks stale.
- suggestion: compute the fundamentals yield from Argus's own dividend rate ÷ live price, or label it with its source and date.

## Summary for the lead
- No trade. The 10-year is at 4.998%, below my 5.1% trigger, drift is within ±0.46 pp, cash is $49.70, and HD reports 11-17. I wrote note 87 and set alert 10 (BND ≤ 70.70 as a 10-year proxy, since ^TNX alerts are rejected). Value $102,933.63, return to date +2.98% (+3.17% with accrued dividends), TWR +3.20% against SPY −1.20% since 10-20.
- Confirmed: B-142 works in the late-Yahoo case. Risk filled 11-11 from quotes, and the Last session tile (+$66.56) matches Day P&L. B-147 works (`type: "sell"` is accepted, and a trade without a side gets a 400). B-136 is fixed on a weekday run.
- Top new bug: one 403 from Nasdaq empties the whole economic calendar (CPI actual, PPI and every stored row) because `pool.map` raises out of `fetch()` before the kept rows are merged. Also: Stress scenarios at 390 px hide every loss number. My by-hand bond duration (−$906 per +50 bp) predicted the CPI-week move within $8 (−$252 against −$260), which strengthens the case for B-017.
