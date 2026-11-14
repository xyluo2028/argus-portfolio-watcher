# 15. One figure, one definition

Roadmap items I5, I6, B10. Effort: large, but made of small batches. Unlike the other plans this
one is a method plus a set of decisions; the code changes follow from applying them figure by
figure.

## Why

An investor stops trusting a tool the first time it shows two different numbers for the same
thing. The loop's investors hit that again and again. Of 48 open bugs in its backlog, the largest
group is one figure with two values:

| Figure | What they saw | Backlog |
|---|---|---|
| Dividend yield | KO 2.74% (Finnhub) beside 2.27% (Argus's own) | B-043, B-145 |
| Payout ratio | 77.2% (Finnhub) against Argus's own rate ÷ EPS of 63.7% | B-062 |
| Beta | two unlabeled betas on one page | B-021 |
| EPS estimate | two consensus figures for one quarter (0.17 and 0.27) | B-119 |
| Margins | gross from Finnhub beside operating and net from SEC | B-124 |
| Revenue growth | labeled TTM, showing the latest quarter | B-102, B-151 |
| Returns | a dated month-end "YTD total return" beside a live YTD price return | B-107, B-100 |
| Next earnings date | different dates on one stock page | B-045, B-149 |

The codebase already states the rule (`frontend/src/metrics.ts`, top comment: "One definition per
indicator"; the loop's `CLAUDE.md`: "A figure shown in two places comes from one definition"). It
holds for the figures that were moved to SEC data in earlier rounds (P/E, EPS, margins when SEC is
current). It doesn't yet hold where Argus computes a figure itself and also passes a provider's
version through.

## Where figures come from

- `services/market.py`: `METRIC_FIELDS` is the list of fundamentals fields. Each provider maps its
  own names onto them (`providers/finnhub.py`, `providers/yahoo.py` `metrics_from_info`), the SEC
  quarters override some, and `sources` records who supplied each field.
- Argus computes others itself: dividend rate and yield (`services/dividends.py`), beta and
  volatility (`services/risk.py`), price returns (`Argus.price_stats`), P/E from the live price
  (`with_pe`).
- `frontend/src/metrics.ts` defines each indicator's label and format once for the dashboard tabs
  and the stock page. Research, the dividends card and the risk card format their own.

## Step 1: triage the backlog (B10)

The backlog is `docs/loop/backlog.md` on the `claude-code-recursive-oncloud` branch
(`git show origin/claude-code-recursive-oncloud:docs/loop/backlog.md`). It has 119 open items from
16 rounds. Before fixing anything:

- For each open bug, check whether it still reproduces on a throwaway server with realistic data.
  Several were likely fixed by later work without being closed.
- Merge duplicates, and group what remains by figure family: dividends, valuation, earnings,
  returns and risk, calendar, everything else.
- Write the result as a table in your report: item, still reproduces (yes, no, couldn't check),
  family, proposed action.

The loop's round lead owns that file. Don't edit it from a branch off `main`; hand the table to
the owner, who can apply the status changes on the loop branch.

## Step 2: apply these decisions, one family per commit

Each decision names the single owner of a figure. Wherever the other version is shown, remove it,
or label it with its source when Argus has no figure of its own.

**Dividends**
- **Yield** is Argus's forward yield: its forward annual rate per share (from its own payment
  history, `services/dividends.py`) ÷ the current price. Label "Dividend yield (forward)". Show a
  provider's yield only when Argus has no payment history for the symbol, labeled with the source.
- **Payout ratio** is that forward annual rate ÷ diluted EPS over the last four SEC quarters,
  labeled "Payout (of earnings)". Add "Payout (of free cash flow)" where FCF is known (B-070).
  Don't show a provider's payout ratio beside it.
- **Yield on cost** and **income** already come from Argus; keep them.

**Valuation**
- **P/E** is the current price ÷ the EPS shown beside it (done in B-095). **Forward P/E** keeps the
  provider's figure and says what it is: "next fiscal year, analysts' adjusted EPS" (B-120).
- **PEG**: one, computed from the P/E shown and the growth rate named in its label; drop the second
  (B-123).
- **Margins**: gross, operating and net come from the same source and the same four quarters. If
  SEC can't supply all three, show all three from one provider. Never mix (B-124).
- **Growth rates** state their period in the label: "Revenue growth, last 4 quarters" or
  "…, latest quarter" (B-102, B-151).

**Earnings**
- **One consensus per quarter per page.** Pick the source in a fixed order (Finnhub, then Yahoo),
  show its basis ("adjusted" or "reported"), and use that same row in the events card, the
  estimates tab and the reported-financials table (B-119, B-131).
- **One next-report date per symbol**, from one function, used by every card (B-045, B-149).

**Returns and risk** (this is I6)
- **Beta** is Argus's own: one year of daily returns against the portfolio's benchmark, labeled
  "Beta (1 year, daily, vs SPY)". Don't show a provider's beta beside it; providers usually compute
  five years of monthly returns, which is a different number for a good reason, so it only
  confuses (B-021).
- **Returns, volatility and drawdown are price-only.** Say so wherever they appear: "price return,
  dividends excluded" (B-100). Remove the provider's month-end "YTD total return" from the stock
  page, or label it with its date and that it includes dividends (B-107).
- A true total-return series (price plus dividends from Argus's own history) is worth adding after
  the labels are right; treat it as a follow-up with its own tests.

## Step 3: keep it that way

- Write the decisions down in `docs/figures.md`: one row per figure with its definition, owner,
  label and period. It is the reference for anyone adding a card.
- Move the formatting and labels that Research, the dividends card and the risk card do on their
  own into `metrics.ts`, so a label is written once.
- Add a test per decision that would fail if the second version came back: for example, that the
  fundamentals response's `dividend_yield_pct` equals the dividends module's yield for a symbol
  with history.

## Watch out

- Provider fields are also inputs to alerts (`near_52w_high`, `pe_above`), the screener and the
  MCP tools. Changing which value a field carries changes what agents and alerts see: update the
  MCP tool descriptions (`get_fundamentals` documents each field's source at length) and check the
  alert kinds that read fundamentals.
- `FUNDAMENTALS_VERSION` in `services/market.py` invalidates stored rows when the field logic
  changes. Bump it when a field's meaning changes.
- This is where a change can make a number worse. For each family, compare before and after on
  ten real symbols (a large cap, a dividend payer, a REIT, a bank, a loss-maker, a foreign ADR, an
  ETF, a recent IPO, a stock that split, a fiscal-year-end oddity) and put the table in your report.

## Done when

- The triage table exists and the owner has it.
- Each family's decisions are applied, with the before-and-after table for that family.
- `docs/figures.md` lists every figure a page shows, and no page shows a figure that isn't in it.
- The tests from step 3 pass.
