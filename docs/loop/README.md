# The improvement loop

Argus improves itself in rounds that run as a Claude Code cloud scheduled task, once a day after the
US market has closed. Two bots do the work:

1. **The trader bot** (`.claude/agents/trader.md`) runs a $10,000 paper account in Argus, signed in
   as the account `bot0`. On a trading day it researches, decides and trades at the last session's
   mid price; on a day off (weekend, holiday) it doesn't trade, and reviews its portfolio and Argus
   itself. Either way it reports bugs, friction and missing features with evidence.
2. **The round lead** (the scheduled session itself) merges the findings into the backlog and picks
   at most three items.
3. **The programmer bot** (`.claude/agents/programmer.md`) ships each item: code, tests, build,
   a visual check, one commit.
4. The lead saves the trader's account, updates its status page, writes the round summary and pushes
   to `claude-code-recursive-oncloud`. The next round starts from there.

A human reviews the branch from time to time and merges what's good into `main`. The loop never
pushes to `main`.

**To see how the trader is doing**, open [`sim/status.md`](sim/status.md): account value, return
against SPY, cash, positions, the latest trades and the last 30 sessions. It is rewritten every
round; `sim/equity.csv` has the full history, and each round's `rounds/NNN/trader.md` has the
reasoning. To look at the account in your own Argus, restore `sim/bot0.json` into an account there
from the Data page (it replaces only that account's records).

```
docs/loop/
  README.md            this file: the round procedure (the scheduled task follows it)
  trader-guide.md      the trader's brief, the paper-account rules and the report format
  backlog.md           every finding, deduplicated, with its status
  sim/status.md        the paper account today (written by scripts/sim.py report)
  sim/equity.csv       one row per session: account value, cash, return, SPY
  sim/bot0.json        the trader's records in Argus (saved by the loop; loaded by scripts/cloud-session.sh)
  rounds/NNN/          one folder per round: trader.md and summary.md
scripts/
  cloud-session.sh     session start: install, build, create the bot0 account and key, start Argus, load sim/bot0.json
  sim.py               the paper account: cash, fills at the session's mid price, one trading round per session
  screenshot.py        page screenshots, signed in as bot0
```

Rounds 001 to 016 ran three investor agents (macro, multi-bagger, income) with $100,000 model
portfolios each; their reports are still under `rounds/`, and their findings are in the backlog.

## How the paper account works

Argus records trades and tracks positions; it has no cash balance and accepts any price and date.
`scripts/sim.py` pins both down, and is the only way the trader trades:

- **$10,000 to start.** Cash is that, minus buys, plus sells and recorded dividends, worked out from
  the portfolio's own transactions in Argus. A buy that would overdraw it is refused.
- **Fills at the session's mid price:** (high + low) / 2 of the last completed US session, dated that
  session. A stock that traded between 100 and 110 fills at 105. No orders while the regular session
  is open.
- **Valued at the close.**
- **One trading round per session.** Once `sim.py report` has recorded a session, more orders for it
  are refused. That is also how a **day off** is recognized: no new session since the last round.
- The account lives in Argus as portfolio `bot0-sim` of the account `bot0`. Each session starts a
  fresh Argus, so the round saves the account's records to `sim/bot0.json` and the next one loads them.

## Round procedure (for the round lead)

You run unattended: there's no one to answer questions. Work through these steps in order.

### 0. Preflight

The session was cloned from the default branch (`main`), not the loop branch, so switch first and
check everything after the switch.

- **Switch branches first:** `git fetch origin && git checkout claude-code-recursive-oncloud && git pull`.
  Never push to `main` or any other branch, and never force-push.
- **Kill switch:** if `docs/loop/PAUSE` exists on the loop branch now checked out, write nothing,
  push nothing, and end the session with "Paused".
- **Restart Argus on this branch's code and the trader's account.** Anything already running was
  started from `main`: `pkill -f "argus [s]erve"; rm -rf data; bash scripts/cloud-session.sh`. The
  script creates the account `bot0` and its API key (`data/bot0.key`), starts Argus and loads
  `docs/loop/sim/bot0.json`. Confirm with `curl -s http://127.0.0.1:8787/api/health` and
  `python scripts/sim.py status` (it must answer `"ok": true`; on the first round the account is
  empty, with $10,000 cash). Sign-in is on from here: the CLI and MCP act as `bot0`; `curl` to
  `/api/...` needs `-H "Authorization: Bearer $(cat data/bot0.key)"`.
- **Agents and tools:** the agent files and `.mcp.json` load when a session starts, from `main`. If
  the `trader` and `programmer` agent types aren't available, run general-purpose agents and tell
  each to read its file in `.claude/agents/` first and follow it as its instructions. If the
  `mcp__argus__*` tools aren't available, tell the trader to use the CLI (`uv run argus ... --json`)
  and the API instead: they cover the same ground.
- Round number `NNN`: one more than the highest folder in `docs/loop/rounds/` (first round: `001`).
  Create `docs/loop/rounds/NNN/`.
- **Trading day or day off?** `python scripts/sim.py status` gives `session` (the last completed US
  session), `day_off` (true when that session was already traded and recorded: a weekend or holiday)
  and `can_trade`. If `market_session` is `regular`, the task ran during US market hours: treat the
  round as a day off and say so in the summary, for a human to fix the schedule.
- **Check the data sources** and record the results for the summary:
  `uv run argus quotes SPY MSFT --json` (Finnhub or Yahoo), `uv run argus history SPY --period 1mo --json`
  (Yahoo history), `curl -s -H "Authorization: Bearer $(cat data/bot0.key)" http://127.0.0.1:8787/api/market-context` (look at `errors`),
  `uv run argus financials MSFT --json` (SEC), and the Finnhub key itself:
  `curl -s "https://finnhub.io/api/v1/quote?symbol=AAPL" -H "X-Finnhub-Token: $FINNHUB_API_KEY"`
  should return a quote (`{"c":...}`); a 401 means the network secret isn't reaching Finnhub, so
  say so in the summary for a human (quotes fall back to Yahoo). If prices and history both fail, the round can't do
  useful work: write `summary.md` saying which sources failed and how, commit it, push, and stop.

### 1. The trader's round

Run the `trader` agent. Give it: the round number, whether this is a **trading day** or a **day off**
and the session date (from preflight), the report path `docs/loop/rounds/NNN/trader.md`, the path of
the previous round's `summary.md` (if any), and the data-source status from preflight (so it doesn't
report an outage as a bug). Wait for it to finish.

Then check its work: `python scripts/sim.py status` must still answer `"ok": true`, and
`uv run argus txn list bot0-sim --json` must show no transaction whose price isn't the mid price of
its session (the trader may only trade through `scripts/sim.py`). If something is off, say so in the
summary under "for a human"; don't repair the account yourself.

### 2. Triage

Update `docs/loop/backlog.md` (format at the top of that file):

- Merge each finding into an existing item when it's the same issue (add the reporter, raise the
  severity if warranted), otherwise add a new item with the next ID.
- Mark items the trader confirmed fixed as `done`; reopen ones it found still broken.
- Don't add items that need a paid data source, a new API key, real personal data, or that would
  expose Argus beyond localhost.

Then **pick at most three open items** for this round, in this order: bugs that produce wrong numbers
or errors; then what blocks the trader's daily work or was reported in more than one round; then
usability and performance; then features (on a day off, weigh the trader's recommendations first);
removals count as usability. Prefer items that can ship in one focused change. For each
pick, write acceptance criteria into the backlog item.

### 3. Development

**Kill switch, second check:** `git fetch origin` and look for `docs/loop/PAUSE` on
`origin/claude-code-recursive-oncloud` (`git cat-file -e origin/claude-code-recursive-oncloud:docs/loop/PAUSE`).
If it's there, stop: no development, no commit, no push.

For each picked item, **one at a time** (they share the working tree), run the `programmer` agent
with the item's ID, its evidence and its acceptance criteria. After each one returns:

- **shipped**: check `git log -1` is that item's commit and that `uv run pytest -q` passes; mark the
  item `done (rNNN, <hash>)`.
- **blocked**: make sure the tree is clean (`git status`), and mark the item `blocked: <reason>`.

### 4. Wrap up

1. If the programmer restarted Argus with a rebuilt database, make sure the trader's account is
   still there (`python scripts/sim.py status`). Then record the session and save the account:
   `python scripts/sim.py report` (rewrites `docs/loop/sim/status.md`, adds the session to
   `equity.csv`) and `python scripts/sim.py save` (writes `docs/loop/sim/bot0.json`).
2. Write `docs/loop/rounds/NNN/summary.md`:
   - trading day or day off, the session date, and the data-source status
   - the account: value, return since the start and against SPY, cash, and this round's trades with
     their fill prices and reasons (from `sim.py report` and the trader's report)
   - shipped items (ID, title, commit), blocked items and why
   - what the trader should re-check next round
   - anything a human should look at (a recurring outage, an item that keeps failing, an account
     that looks wrong, a process problem with this loop)
3. Run the full checks one last time: `uv run pytest -q` and `cd frontend && npm run build`.
4. Commit the report, backlog, `docs/loop/sim/` and summary: `Loop round NNN: <shipped item titles>`
   (on a round that shipped nothing: `Loop round NNN: <trading day | day off>, no changes shipped`).
5. `git fetch origin`; if `docs/loop/PAUSE` now exists on `origin/claude-code-recursive-oncloud`,
   don't push and end with "Paused before push" (the round's commits stay in this session only).
   Otherwise `git push origin claude-code-recursive-oncloud`. If the push is rejected because the
   branch moved, `git pull --rebase` and push again; never force.
6. **End with a short final message** for the person following along (it becomes the notification):
   the account value and its return against SPY's, what was traded (or "day off"), what shipped, and
   `docs/loop/sim/status.md` as the place to look.

## Hard rules

- **This repository is public.** No secrets, no `.env`, no `data/` (the bot's API key lives there),
  no passwords, no real personal or portfolio data in any commit, report or summary.
- Don't edit this loop's own instructions or its referee (`docs/loop/README.md`,
  `docs/loop/trader-guide.md`, `.claude/`, `CLAUDE.md`, `scripts/cloud-session.sh`, `scripts/sim.py`).
  Propose process changes in the summary instead.
- The trader's account changes only through `scripts/sim.py`, and only the trader trades. Nobody
  edits or deletes its past trades, or `docs/loop/sim/equity.csv`.
- Don't weaken or delete tests to make them pass.
- At most three items per round, each one commit.
- Respect provider limits: Finnhub 60 calls/min, SEC under 10 requests/s.

## Scheduled task prompt

Paste this as the task's prompt at claude.ai/code/routines:

> You are the round lead of Argus's improvement loop. Check out the branch
> `claude-code-recursive-oncloud` (not a `claude/` branch) and pull it. Then run one round exactly
> as `docs/loop/README.md` describes, from preflight to push: the trader bot (account bot0, a
> $10,000 paper account) reviews and trades at the last US session's mid price, or on a day off
> reviews its portfolio and Argus instead; you triage what it reports; the programmer bot ships up
> to three items. You run unattended: don't ask questions; when a step can't be done, record why in
> the round summary and continue or stop as the procedure says. Push only to
> `claude-code-recursive-oncloud`. End with a short final message: the account's value and return
> against SPY, what was traded or that it was a day off, and what shipped.

## Setup (once, by a human)

1. **Cloud environment** `argus-loop` at claude.ai/code:
   - **Network: Custom**, with the default package managers included, plus `*.yahoo.com`,
     `finnhub.io`, `www.sec.gov`, `data.sec.gov`, `home.treasury.gov`, `www.federalreserve.gov`,
     `api.nasdaq.com`, `mba.tuck.dartmouth.edu`, `api.openfigi.com`, `cdn.playwright.dev`,
     `playwright.download.prss.microsoft.com`.
   - **Network secret** for a dedicated Finnhub key: host `finnhub.io`, header `X-Finnhub-Token`,
     no prefix.
   - **Environment variables**: `FINNHUB_API_KEY=via-network-secret` (any non-empty value turns
     Finnhub on; if the network secret turns out not to apply, put the key itself here),
     `SEC_USER_AGENT=argus-loop you@example.com`, `ARGUS_STREAM=off`, `BASH_DEFAULT_TIMEOUT_MS=600000`.
     Optional: `ARGUS_BOT_PASSWORD=<a password>` gives the session's `bot0` account a password, so
     a person can sign in to that session's web UI as the bot. Without it the bot signs in with its
     API key only. Never put the password in the repository.
   - **Setup script**: `uvx --from playwright playwright install --with-deps chromium || true`
2. **Scheduled task** at claude.ai/code/routines: this repository, the `argus-loop` environment, no
   connectors, and the prompt above. Schedule it **every day, after the US close and before the next
   open**: around 10:00 Asia/Tokyo is 20:00 or 21:00 in New York. Tuesday to Saturday (Tokyo) are
   trading days; Sunday, Monday and US holidays are days off. It must not run between 9:30 and 16:00
   New York time: the trader can't trade then. **Run now** once and read the transcript before
   enabling the schedule.
3. **Protect `main`** on GitHub (a ruleset requiring pull requests) so no run can push to it.
4. **Kill switches**, from gentlest to hardest:
   - commit an empty `docs/loop/PAUSE` to `claude-code-recursive-oncloud`: the next round ends at
     preflight, and a running round stops before development and before its push;
   - switch the scheduled task off at claude.ai/code/routines: no new rounds start;
   - stop or archive a running round's session at claude.ai/code: it ends now;
   - a GitHub ruleset that blocks pushes to the loop branch, or removing the Claude GitHub App
     from the repository: nothing more lands, whatever a session does.
