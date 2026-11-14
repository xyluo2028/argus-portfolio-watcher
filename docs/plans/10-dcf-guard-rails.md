# 10. DCF guard rails

Roadmap items I7, B6, C4. Effort: medium, in three parts.

## Why

The DCF calculator (`/dcf/<symbol>`) is a good tool with dangerous defaults. Open it on NVDA and,
before you touch anything, it says: "Undervalued. Fair value is 348.9% above today's price." The
defaults assumed 30% growth for five straight years with no slowdown, valued at the 5-year median
multiple of 54.9× when the stock trades at 29.3×. A first-time user reads that as a verdict.

Three further gaps:

- A single fair value hides how much it depends on two guesses. There is no sensitivity view.
- The saved model isn't shown where decisions are made (the stock page, the watchlist).
- The projection math lives only in the browser (`frontend/src/dcf.ts`, `project()`), with no
  tests, so the CLI and MCP agents can't use it, and the server can't compute a fair value.

## What exists

- `frontend/src/dcf.ts`: `project(inputs, price, shares)` (the model, 25 lines: read its header
  comment), `defaults(data, metric)`, `defaultMetric`, `historicalGrowth`.
- `frontend/src/pages/Dcf.tsx`: the page. The verdict is at "Undervalued / Overvalued / Fairly
  valued" with a ±5% band.
- `backend/argus/services/valuation.py`: `build()` gathers the inputs' sources (per metric: base
  value, history, growth rates, multiple history and its quartiles; shares, price, dividends).
  `clean_inputs()` validates a saved model. `INPUT_FIELDS` lists the inputs.
- `Argus.valuation`, `save_valuation`, `valuation_models` (`app.py`); routes under
  `/api/valuation`. A saved model is `ValuationModel(account_id, symbol, inputs, updated_at)`.
- No MCP tool or CLI command for any of it.

## Decided

### Part A: one definition of the math, on the server

- Port `project()` to Python as `valuation.project(inputs, price, shares)`, returning the same
  fields. Keep the browser's copy for instant feedback while typing.
- Two implementations must not drift, so pin them to shared cases: a JSON file of inputs and
  expected outputs (`tests/fixtures/dcf_cases.json`), checked by a pytest test against the Python
  function and by a unit test against the TypeScript one. Generate the expected values from the
  Python function once, then review a few by hand (a one-year case is easy to verify on paper).
  Include edge cases: zero growth, negative growth, decay, buybacks, a dividend, 30 years.
- The frontend has no unit-test runner. Add Vitest as a dev dependency with an `npm test` script,
  and run it in CI when plan 04's workflow exists.
- Fair value doesn't depend on today's price: it is the discounted future price plus dividends.
  So compute it when a model is saved and store it: add `fair_value` and the `shares` it used to
  the saved row (new columns, or inside the JSON; columns are easier to query). `valuation_models`
  then returns each saved symbol's fair value with no market-data fetch.
- MCP: `get_valuation(symbol)` returns the input sources, the saved model if any, and the
  projection of the saved or default inputs; `save_valuation(symbol, inputs, dry_run)`. CLI:
  `argus dcf <symbol>` printing the same. Both act on the caller's own saved models: list the
  tools in the leak test.

### Part B: defaults a cautious analyst would choose

Move `defaults()` to the server too (it belongs with the data it reads), expose them in the
`/api/valuation/<symbol>` response, and change them:

| Input | Today | New default | Reason |
|---|---|---|---|
| Growth | median of 5-year, 3-year and analysts, capped at 30% | the same median, capped at **15%**, floor −10% | Few companies hold 30% for five years; the user can raise it with one click on a suggestion. |
| Growth decay | 0 | **10%** a year | Growth fades. 15% becomes 13.5, 12.2, 10.9, 9.8. |
| Exit multiple | 5-year median | the **lower** of today's multiple and the 5-year median, capped at **25×** for cash flow and earnings, **8×** for sales | A mature company in five years won't hold a peak multiple. |
| Years, target return, dividends, share change | unchanged | unchanged | |

Keep every suggestion chip (5-year, 3-year, analysts, today, median, quartiles): the user's
judgment is the point of the tool. Add one line under the result: "Defaults are deliberately
conservative: adjust growth and the exit multiple to your own view."

Verdict wording: widen the "fairly valued" band from ±5% to ±15% (a five-year projection isn't
that precise), and when fair value is more than double or less than half the price, replace the
verdict with "Check your inputs" and name the two that matter (growth and exit multiple).

### Part C: show how fragile the answer is, and show it where it matters

- **Sensitivity grid** on the DCF page: five growth rates (the chosen one, ±5 and ±10 percentage
  points) by five exit multiples (the chosen one × 0.6, 0.8, 1, 1.2, 1.4). Each cell is the fair
  value, tinted by upside against today's price, with the chosen cell marked. It uses the same
  `project()`.
- **Stock page:** when you have a saved model for the symbol, a line near the price: "Your fair
  value $X (+Y% from here), saved <date>", linking to the DCF page.
- **Watchlist:** a "vs fair value" column for symbols with a saved model, sortable like the
  others; blank otherwise.

## Watch out

- Saved models are per account (`ValuationModel` has `account_id`): every query filters by owner.
- A model saved before this change has no stored fair value. Compute it lazily on first read, or
  in the migration from the stored inputs when shares are known; don't show a wrong number, show
  none.
- `shares` in the valuation data is market cap ÷ price. The page states that; keep it.
- The phone tests mock `/api/valuation` responses: extend the fixture if the page reads new fields.

## Leave alone

- The model itself (an exit-multiple DCF). No terminal-growth variant, no WACC.
- Analyst data sources.

## Done when

- The shared cases pass in both languages, and CI runs both.
- NVDA (or any fast grower) opens with a result inside ±100% of the price, not +349%. State the
  before and after numbers for three symbols in your report: one fast grower, one mature
  dividend payer, one with negative growth.
- The grid renders at 1400 px and 390 px (it can scroll inside its card on a phone).
- Stock page and watchlist show the saved fair value for the account that saved it, and nothing
  for another account.
- `get_valuation` and `save_valuation` work over MCP; the README's tool count is updated.
