# The improvement loop

Argus improves itself in rounds that run as a Claude Code cloud scheduled task. Each round:

1. **Three investor agents** (`.claude/agents/investor-*.md`) do their real jobs with Argus (a macro
   allocator, a multi-bagger hunter, an income and risk manager), each running a model portfolio,
   and report bugs, friction and missing features with evidence.
2. **The round lead** (the scheduled session itself) merges the findings into the backlog and picks
   at most three items.
3. **The developer agent** (`.claude/agents/developer.md`) ships each item: code, tests, build,
   a visual check, one commit.
4. The lead saves the model portfolios, writes the round summary and pushes to
   `claude-code-recursive-oncloud`. The next round starts from there.

A human reviews the branch from time to time and merges what's good into `main`. The loop never
pushes to `main`.

```
docs/loop/
  README.md            this file: the round procedure (the scheduled task follows it)
  investor-guide.md    the investors' shared brief and report format
  backlog.md           every finding, deduplicated, with its status
  sim/snapshot.json    the model portfolios (written by the loop; loaded by scripts/cloud-session.sh)
  rounds/NNN/          one folder per round: investor reports and summary.md
```

## Round procedure (for the round lead)

You run unattended: there's no one to answer questions. Work through these steps in order.

### 0. Preflight

The session was cloned from the default branch (`main`), not the loop branch, so switch first and
check everything after the switch.

- **Switch branches first:** `git fetch origin && git checkout claude-code-recursive-oncloud && git pull`.
  Never push to `main` or any other branch, and never force-push.
- **Kill switch:** if `docs/loop/PAUSE` exists on the loop branch now checked out, write nothing,
  push nothing, and end the session with "Paused".
- **Restart Argus on this branch's code and portfolios.** Anything already running was started from
  `main`: `pkill -f "argus [s]erve"; rm -rf data; bash scripts/cloud-session.sh`. The script prints
  whether Argus is up; confirm with `curl -s http://127.0.0.1:8787/api/health`.
- **Agents and tools:** the agent files and `.mcp.json` load when a session starts, from `main`. If
  the `investor-*` and `developer` agent types aren't available, run general-purpose agents and tell
  each to read its file in `.claude/agents/` first and follow it as its instructions. If the
  `mcp__argus__*` tools aren't available, tell the investors to use the CLI (`uv run argus ... --json`)
  and the API instead: they cover the same ground.
- Round number `NNN`: one more than the highest folder in `docs/loop/rounds/` (first round: `001`).
  Create `docs/loop/rounds/NNN/`.
- **Check the data sources** and record the results for the summary:
  `uv run argus quotes SPY MSFT --json` (Finnhub or Yahoo), `uv run argus history SPY --period 1mo --json`
  (Yahoo history), `curl -s http://127.0.0.1:8787/api/market-context` (look at `errors`),
  `uv run argus financials MSFT --json` (SEC). If prices and history both fail, the round can't do
  useful work: write `summary.md` saying which sources failed and how, commit it, push, and stop.

### 1. Investor reviews

Run the three investor agents **in parallel** (`investor-macro`, `investor-multibagger`,
`investor-income`). Give each one: the round number, the report path
`docs/loop/rounds/NNN/investor-<style>.md`, the path of the previous round's `summary.md` (if any),
and the data-source status from preflight (so they don't report an outage as a bug). Wait for all
three.

### 2. Triage

Update `docs/loop/backlog.md` (format at the top of that file):

- Merge each finding into an existing item when it's the same issue (add the reporter, raise the
  severity if warranted), otherwise add a new item with the next ID.
- Mark items an investor confirmed fixed as `done`; reopen ones they found still broken.
- Don't add items that need a paid data source, a new API key, real personal data, or that would
  expose Argus beyond localhost.

Then **pick at most three open items** for this round, in this order: bugs that produce wrong numbers
or errors; then items reported by more than one investor; then usability and performance; then
features; removals count as usability. Prefer items that can ship in one focused change. For each
pick, write acceptance criteria into the backlog item.

### 3. Development

**Kill switch, second check:** `git fetch origin` and look for `docs/loop/PAUSE` on
`origin/claude-code-recursive-oncloud` (`git cat-file -e origin/claude-code-recursive-oncloud:docs/loop/PAUSE`).
If it's there, stop: no development, no commit, no push.

For each picked item, **one at a time** (they share the working tree), run the `developer` agent
with the item's ID, its evidence and its acceptance criteria. After each one returns:

- **shipped**: check `git log -1` is that item's commit and that `uv run pytest -q` passes; mark the
  item `done (rNNN, <hash>)`.
- **blocked**: make sure the tree is clean (`git status`), and mark the item `blocked: <reason>`.

### 4. Wrap up

1. Save the model portfolios: `uv run argus snapshot dump docs/loop/sim/snapshot.json`.
2. Write `docs/loop/rounds/NNN/summary.md`:
   - data-source status
   - each portfolio's value and return to date (`uv run argus portfolio show <name> --json`) and this
     round's trades
   - shipped items (ID, title, commit), blocked items and why
   - what the investors should re-check next round
   - anything a human should look at (a recurring outage, an item that keeps failing, a process
     problem with this loop)
3. Run the full checks one last time: `uv run pytest -q` and `cd frontend && npm run build`.
4. Commit the reports, backlog, snapshot and summary: `Loop round NNN: <shipped item titles>`.
5. `git fetch origin`; if `docs/loop/PAUSE` now exists on `origin/claude-code-recursive-oncloud`,
   don't push and end with "Paused before push" (the round's commits stay in this session only).
   Otherwise `git push origin claude-code-recursive-oncloud`. If the push is rejected because the
   branch moved, `git pull --rebase` and push again; never force.

## Hard rules

- **This repository is public.** No secrets, no `.env`, no `data/`, no real personal or portfolio
  data in any commit, report or summary.
- Don't edit this loop's own instructions (`docs/loop/README.md`, `docs/loop/investor-guide.md`,
  `.claude/`, `CLAUDE.md`, `scripts/cloud-session.sh`). Propose process changes in the summary instead.
- Don't weaken or delete tests to make them pass.
- At most three items per round, each one commit.
- Respect provider limits: Finnhub 60 calls/min, SEC under 10 requests/s.

## Scheduled task prompt

Paste this as the task's prompt at claude.ai/code/routines:

> You are the round lead of Argus's improvement loop. Check out the branch
> `claude-code-recursive-oncloud` (not a `claude/` branch) and pull it. Then run one round exactly
> as `docs/loop/README.md` describes, from preflight to push. You run unattended: don't ask
> questions; when a step can't be done, record why in the round summary and continue or stop as
> the procedure says. Push only to `claude-code-recursive-oncloud`.

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
   - **Setup script**: `uvx --from playwright playwright install --with-deps chromium || true`
2. **Scheduled task** at claude.ai/code/routines: this repository, the `argus-loop` environment, no
   connectors, a weekday schedule during market hours a few minutes past the hour (e.g. 10:37 ET),
   and the prompt above. **Run now** once and read the transcript before enabling the schedule.
3. **Protect `main`** on GitHub (a ruleset requiring pull requests) so no run can push to it.
4. **Kill switches**, from gentlest to hardest:
   - commit an empty `docs/loop/PAUSE` to `claude-code-recursive-oncloud`: the next round ends at
     preflight, and a running round stops before development and before its push;
   - switch the scheduled task off at claude.ai/code/routines: no new rounds start;
   - stop or archive a running round's session at claude.ai/code: it ends now;
   - a GitHub ruleset that blocks pushes to the loop branch, or removing the Claude GitHub App
     from the repository: nothing more lands, whatever a session does.
