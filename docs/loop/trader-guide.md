# The trader bot's brief

You run a $10,000 paper account in Argus as the account `bot0` (your agent file,
`.claude/agents/trader.md`, says who you are and your house rules). Each round you **do your real job
with Argus**, then report what helped, what got in the way and what you wished it did. Your report is
the programmer bot's only input, so make it concrete and backed by evidence.

## Ground rules

- **Use Argus, not your memory.** Prices, fundamentals, news and dates come from Argus. If Argus
  can't tell you something you need for a decision, that is a finding, not a reason to guess.
- **You are signed in as `bot0`.** The MCP tools (`mcp__argus__*`) and the CLI
  (`uv run argus ... --json`) act as your account already. The JSON API needs your key:
  `curl -s -H "Authorization: Bearer $(cat data/bot0.key)" http://127.0.0.1:8787/api/...`. For the
  web UI, `uvx --from playwright python scripts/screenshot.py <path> <out.png>` signs in with the same
  key, takes a screenshot and reports load time, page errors and horizontal overflow; then read the
  PNG. Real users live in the UI, so look at the pages that matter to your job, at desktop and phone
  width (`--width 390`).
- **Only your own account.** Your portfolio is `bot0-sim`; your watchlists, notes and alerts are
  yours too. Don't create other accounts or touch anything else.
- **Don't edit code or docs.** Your only file output is your report.
- **Never put keys, passwords or real people's data in a report.** This repository is public.
- Data providers are rate limited (Finnhub: 60 calls/min). Don't loop over hundreds of symbols one by one.

## The paper account

Argus records trades and tracks positions; it has no cash balance and accepts any price. So your
money and your fills go through one helper, `scripts/sim.py` (JSON out; `"ok": false` carries the reason):

```bash
python scripts/sim.py status                               # cash, positions, account value, return; day_off, can_trade
python scripts/sim.py price NVDA                           # last session's high, low, mid (your fill price) and close
python scripts/sim.py buy NVDA --amount 1500 --note "why"  # or --qty 3 (fractions allowed); add --dry-run to preview
python scripts/sim.py sell NVDA --all --note "why"         # or --qty 1.5
```

- **Starting money:** $10,000. Cash = that, minus buys, plus sells and recorded dividends. A buy you
  can't afford is refused; so is selling more than you hold.
- **Fills:** every order fills at the **middle of the last completed session's range**,
  (high + low) / 2, dated that session. A stock that traded between 100 and 110 fills at 105. You
  can't choose the price or the date, and you can't trade while the regular session is open.
- **Valuation:** positions are valued at the session's close, so a fill above the close shows a
  small loss on day one. That's expected.
- **One trading round per session.** Decide, then place all of the round's orders. Never record a
  trade any other way (not `add_transaction`, not `argus txn add`, not the API): it would bypass the
  cash and price rules. Editing or deleting past trades is off limits too.
- **Dividends:** when a holding pays one, `status` shows it under `dividends_accrued` and it already
  counts in your account value. Leave it there.

## Each round

1. Read `docs/loop/backlog.md` (so you don't re-report known items) and the previous round's
   `summary.md` (what shipped, what to re-check).
2. **Verify what shipped last round** that touches your work: does it work, does it help?
3. Run `python scripts/sim.py status` and do the round it calls for.

### Trading day (`day_off: false`)

1. **Market:** the backdrop (`get_market_context`, the Markets page): regime, breadth, sectors, what's
   on the calendar.
2. **Holdings:** for each position, what happened (price, news, earnings, events coming up) and
   whether its thesis still holds (`get_portfolio`, `get_daily_brief_data`, `get_events`, `list_notes`).
3. **Ideas:** hunt with the screener and dig into candidates: fundamentals, statements, research,
   peers, the DCF calculator (`screen_stocks`, `get_fundamentals`, `get_financials`, `get_research`,
   `compare_symbols`, the stock page). Keep candidates on a watchlist (`watchlist_add`).
4. **Decide and trade:** check `python scripts/sim.py price <symbol>` first, write your thesis as a
   note (`add_note`, kind `thesis`, with a review date), then place the orders. Check the house rules
   in your agent file before each buy. Set alerts for the prices or events that would change your mind.
5. Run `python scripts/sim.py status` again and put the result in your report.

### Day off (`day_off: true`: weekend or holiday, no new session)

No trades; the helper refuses them. Use the time for the two reviews a busy trading day crowds out:

1. **Portfolio review.** Performance since the start and against SPY (`get_performance`, the
   dashboard); what worked, what didn't and why; each thesis re-read against the latest numbers; risk
   and concentration (`get_risk`, `get_exposure`); earnings and dividends in the next two weeks; what
   you intend to do at the next session and what would change that plan.
2. **Argus review: features and experience.** Walk through Argus as a user, especially parts you
   haven't used lately: every page at desktop and phone width, the tools you skip, the account pages
   (sign-in, Account, sharing, backup and restore on Data). For each: is it correct, is it clear, is
   it fast, what is missing? Then **recommend**: the three to five changes that would most improve
   your daily work, each with the decision it would make easier.

### What counts as a finding (both kinds of round)

- **bug**: a wrong number, an error, something broken. Cross-check figures: the same number on two
  pages, in the UI vs the API vs MCP, or against a value you can compute from Argus's own data
  (e.g. a return from its price history). Inconsistencies are the most valuable finds.
- **ux**: confusing, too many clicks, unclear labels, bad phone layout, hard-to-read charts.
- **perf**: slow pages or tools (give the timing).
- **feature**: something your job needs that Argus doesn't do. Say what decision it would change.
- **removal**: something that adds clutter or complexity for little value.

Things the helper does for you because Argus can't (a cash balance, fills at a rule-based price)
are fair game: report what Argus would need for you to do without it.

## Report

Write `docs/loop/rounds/<NNN>/trader.md` (the round lead gives you the path), in this shape:

```markdown
# Round NNN: trader (<trading day | day off>, session YYYY-MM-DD)

## Account
Value, return since the start and vs SPY, cash, positions (from `sim.py status`).

## What I did
Trading day: market view, research, decisions, and each trade with its fill price and reason
(or why none). Day off: the portfolio review, and the plan for the next session.

## Last round's changes
Each shipped item that touches my work: works / partly / broken, and whether it helped.

## Findings
### <short title>
- kind: bug | ux | perf | feature | removal
- severity: high (wrong numbers, blocks my job) | medium | low
- evidence: the exact tool call / page / command, what it returned, what I expected
- suggestion: what would fix it, as small as possible

## Recommendations (day off only)
The three to five changes that would help most, in order, each with the decision it would improve.
```

Five to ten findings, most important first. Quality over quantity: one confirmed wrong number beats
five wishes. End by returning a 3-line summary to the round lead: account value and return, what you
traded (or that it was a day off), and your top finding.
