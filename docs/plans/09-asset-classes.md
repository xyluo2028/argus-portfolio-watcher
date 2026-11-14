# 09. Asset classes

Roadmap items I2 and B3. Effort: large; three stages that ship separately.

## Why

Argus treats every holding as an equity with a sector. That fails anyone who holds bonds, gold,
commodities or cash:

- Exposure shows bond funds as "ETF" or "Unclassified", and one as 100% Technology (B3; plan 05
  has the stop-gap fix).
- Targets and drift offer two levels, by position and by sector. A portfolio of bond funds gets one
  row, "ETF 100%". An investor who thinks "60% stocks, 30% bonds, 10% cash" can't say so.
- Risk describes a bond portfolio with its beta to SPY, equity factors (Fama-French, R² 0.26 on the
  review's bond portfolio) and stress replays that proxy missing history with beta. For bonds the
  questions are yield, duration and credit quality.
- A bond portfolio is benchmarked to SPY by default.

This is the most-reported gap in the loop's backlog (B-017, 16 rounds).

## What exists

- `Instrument` (`models.py`): `type` ("Common Stock", "ETP", "ADR"…) and `sector`. No asset class.
- Fund profiles (`Argus.fund_profiles`, cached a week in `fund_profile`; fetched by
  `providers/yahoo.py`, `get_fund_profile`): `sectors` (fractions of the equity sleeve),
  `top_holdings`, `asset_classes` (fractions keyed `stockPosition`, `bondPosition`, `cashPosition`,
  `preferredPosition`, `convertiblePosition`, `otherPosition`), `bond_ratings`.
- yfinance's fund data also offers `fund_overview` (category name, family) and `bond_holdings`
  (duration and maturity). Argus doesn't read those two yet.
- Company profiles (`Argus.company_profile`) carry `quote_type` and, for funds, `category`.
- `services/analysis.py`: `exposure()` and `drift()`. `Argus.set_targets` accepts level `symbol` or
  `sector`; `Target.level` is an 8-character column.
- `services/risk.py`, `analyze()`: equity-style risk from daily closes.

## Decided

### The classes

Six, in this display order: **Equity, Fixed income, Cash, Commodities, Crypto, Other.** Keep the
list short and fixed. Real estate funds stay Equity (they are equities with a sector).

### How a holding gets its classes

A holding maps to a split across classes that sums to 1, so a 60/40 fund counts 60% Equity and 40%
Fixed income. One pure function, in a new `services/asset_class.py`, decides:

1. Not a fund: `{Equity: 1}`.
2. A fund whose category names a commodity or crypto exposure: all of it in that class. Match the
   category text: "Commodit" or "Precious Metals" → Commodities; "Digital Assets" → Crypto. These
   funds usually report their holdings as "other" or as nothing, so the category is the only signal.
3. A fund with `asset_classes`: stock → Equity; bond, preferred and convertible → Fixed income;
   cash → Cash; other → Other. Clip negatives to 0 (leverage and shorts) and normalize.
4. A fund with neither: `{Other: 1}`, and list it so the UI can say it couldn't be classified.

The category comes from the fund profile: extend `get_fund_profile` to store
`fund_overview`'s category name, so classification needs no second lookup. The profile cache has no
version field; today it refetches rows that lack `asset_classes`. Add a version key the way
`CompanyProfile` does (`PROFILE_VERSION`), and bump it.

Don't add a per-account override table yet. If the automatic class is wrong for a ticker, fix the
rule. Revisit if real cases can't be covered by rules.

### Stage 1: see it

- `exposure()` returns `by_asset_class` (look-through, using the splits) and the sector
  look-through covers only the equity share of each holding, which is the full fix for B3. Sector
  percentages stay "of the portfolio", so they no longer sum to 100 for a mixed portfolio; say so
  in the table's caption ("equity share: 62%").
- UI: Analysis opens with an "Asset classes" bar list above Sectors. The dashboard's "By sector"
  card shows asset classes instead when Equity is under 90% of the portfolio.
- MCP `get_exposure` and the CLI's exposure output include the new table.

### Stage 2: target it

- A third target level, `class`. Keys are the six class names. `drift()` computes each class's
  current weight from the splits.
- The Targets & drift card gets a "By asset class" tab and opens on the level that has saved
  targets (today it always opens on "By sector": backlog B-022).
- With cash tracking (plan 07 stage 3), the portfolio's own cash counts in the Cash class.

### Stage 3: bond-aware risk

- Extend the fund profile with duration and average maturity from `bond_holdings`, when present.
  Check what the data looks like for three or four real bond funds before designing around it
  (BND, BNDX, VCIT, a TIPS fund): the review saw `bond_ratings` for one fund sum to 178% because a
  "US government" share overlaps the letter grades. Normalize what you show, and don't show what
  you can't make sense of.
- Portfolio level: the fixed-income share's weighted duration and yield (Argus already computes a
  forward dividend yield per holding), and a credit-quality mix.
- A rate-shock row in the stress table: "+1 percentage point in yields" ≈ −duration × 1% of the
  fixed-income value. Label it an estimate.
- When Equity is under half the portfolio, the factor-exposure table is misleading: show it folded
  with a line saying equity factors explain little of this portfolio, and show the R².
- Benchmark: when a portfolio is mostly Fixed income and its benchmark is SPY, suggest a bond
  benchmark (AGG) in the UI. Changing a benchmark needs plan 12.

## Watch out

- Fund profiles come from Yahoo through yfinance and are fetched in a thread pool. Keep network
  work in the provider and the pool; classification is pure.
- `funds_without_profile` in `exposure()` drives a UI note. After this change it should mean
  "couldn't classify", which is rule 4.
- Target keys for sectors are free text today (the sector names from exposure). Class keys are a
  fixed list: validate them in `set_targets`.
- The loop's trader bot holds ETFs too; anything that changes `get_exposure`'s shape needs the MCP
  tool description updated.

## Leave alone

- Per-security bond analytics (individual bonds aren't supported at all).
- A full fixed-income risk model: key-rate durations, spread duration, convexity.
- Currency exposure.

## Done when

- Stage 1: tests for each classification rule and for mixed portfolios; the 99%-bond fund from
  plan 05's test lands in Fixed income; a gold fund lands in Commodities; a 60/40 fund splits. In
  the browser, a portfolio of bond funds shows "Fixed income" on Analysis and the dashboard.
- Stage 2: targets by class save, drift computes, the card opens on the right level; `set_targets`
  refuses an unknown class.
- Stage 3: duration and the rate-shock row appear for a bond portfolio and not for an equity one;
  an all-equity portfolio's risk output is unchanged (compare before and after in a test).
- README, MCP tool descriptions and `docs/deployment.md` (if settings changed) are current.
