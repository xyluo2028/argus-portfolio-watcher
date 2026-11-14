# Argus

*The hundred-eyed watchman for your portfolio.*

A local-first portfolio monitor for US stocks and ETFs, designed to be operated by AI agents as easily as by hand.

- Build portfolios from a trade log (multiple portfolios + watchlist)
- Near real-time prices on trading days, live P&L and day change
- Candlestick charts with indicators; performance vs SPY/QQQ
- Valuation and fundamentals: PE, forward PE, PB, PS, EV/EBITDA, revenue growth, margins
- MCP server and JSON CLI so Claude (Desktop / Code) can query and update your portfolio

> **Status:** P0 foundation, P1 monitor MVP, P2 routines and P3 analysis are done: dashboard, ticker charts, live prices, performance vs benchmark, watchlist, transactions, compare, events calendar, alerts, thesis notes, daily-brief data, exposure with ETF look-through, targets & drift, what-if trades, and a 37-tool MCP server. See the [design doc](docs/design.html) (open it in a browser for the diagrams).

## Planned stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, SQLite (WAL), APScheduler, uv |
| Market data | Finnhub (free tier) for live quotes, yfinance for history, SEC EDGAR for financials |
| Frontend | React + Vite + TypeScript, TradingView Lightweight Charts |
| Agent interface | MCP server (stdio + streamable HTTP), `argus` CLI with `--json` |

## Roadmap

| Phase | Scope |
|---|---|
| P0 Foundation ✓ | Schema, data providers, trade log → FIFO lots/positions, `argus` CLI, Investing.com CSV import |
| P1 Monitor MVP ✓ | Live quote loop, dashboard, ticker detail, watchlist, benchmark compare, MCP tools |
| P2 Routines ✓ | Earnings/events, daily-brief data tool, alerts, thesis notes |
| P3 Analysis ✓ | Exposure (ETF look-through), target weights and drift, what-if trades |

## Setup

```bash
brew install uv                                     # Linux/WSL: curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
cp .env.example .env && chmod 600 .env              # add FINNHUB_API_KEY and SEC_USER_AGENT
```

Building the web UI needs Node 20.19+ (`nvm install 22` on Linux).

Without `FINNHUB_API_KEY`, quotes and metrics fall back to Yahoo (slower, unofficial).
`SEC_USER_AGENT` (an app name and your email, as SEC asks of automated clients) is needed for
reported financials and for an ETF's full holdings list, which comes from its quarterly SEC N-PORT
filing (2-5 months old); without it the stock page shows Yahoo's current top 10. Holdings are matched
to tickers through OpenFIGI; an optional free `OPENFIGI_API_KEY` raises its rate limit.

## Web UI

```bash
(cd frontend && npm install && npm run build)   # once, and after UI changes
uv run argus serve                               # http://localhost:8787
```

During market hours prices stream live (Finnhub WebSocket for the largest ~48 positions, REST
refresh for the rest each minute). Set `ARGUS_PORT` in `.env` to use another port. For UI
development, run `npm run dev` in `frontend/` alongside `argus serve` (Vite proxies `/api`).

## Accounts and bots

Argus starts without sign-in, for use on your own machine. Create an account to turn sign-in on for
every request: the web UI asks for a username and password (or the server token), and bots, scripts
and MCP clients send an account's API key.

Every account is the same kind, whether a person or a bot uses it; none manages another. In the web UI:

- **The first account:** sign in with `ARGUS_TOKEN` (without one, the UI is open anyway) and create it
  on the **Account** page. It takes over everything recorded so far, so make it yours.
- **Any later account:** **Create an account** on the sign-in page, with a username and password. It
  starts empty. For a bot, create its account there, then make an API key on its Account page.
  `ARGUS_SIGNUP=off` removes that button; accounts then come from the CLI only.
- **Your own account:** the Account page changes your password, manages your API keys and shares
  your portfolios.

Or from the terminal (also where an account is disabled or its password reset):

```bash
uv run argus user add me                                  # asks for a password
uv run argus user add trader-bot --no-password            # a bot is just another account
uv run argus key create trader-bot --name "sim routine"   # shown once: Authorization: Bearer <key>
```

Each account has its own portfolios, watchlists, alerts, notes, peer lists and saved DCF models;
market data is shared. The first account takes over everything recorded before it, so make it
yours. To watch a bot's portfolio, have it share the portfolio with you, read-only:

```bash
uv run argus --as trader-bot portfolio share "Bot sim" --with me   # or the bot's share_portfolio MCP tool
```

The CLI and `argus mcp` act as the oldest account; `argus --as <user> ...` acts as another.
`ARGUS_TOKEN`, if set, keeps working and acts as the oldest account. More in
[docs/deployment.md](docs/deployment.md#accounts-and-api-keys).

## Use it from Claude (MCP)

Argus exposes 38 tools: portfolio, quotes, history with indicators, fundamentals, company profile & peers, ETF holdings, dividends, risk, research, market context, a stock screener, SEC
financials, compare, performance, transactions (add, edit, delete), watchlist, events, alerts, notes, exposure,
drift/targets, what-if (`simulate_trades`), sharing a portfolio, and
`get_daily_brief_data`, which gathers everything for a brief in one call. Write tools default
to `dry_run=true` and accept an `idempotency_key`. The prompts `daily_brief` and
`position_review` package common routines.

```bash
# Claude Code, stdio (works whether or not `argus serve` is running)
claude mcp add argus -- uv run --directory ~/Documents/github/project-hatching/argus-portfolio-watcher argus mcp

# or over HTTP while `argus serve` is running (uses the live price stream)
claude mcp add --transport http argus http://localhost:8787/mcp/
# with accounts: add --header "Authorization: Bearer <API key>"
```

For Claude Desktop, add the same stdio command under `mcpServers` in
`claude_desktop_config.json` (command `uv`, args `["run", "--directory", "<repo path>", "argus", "mcp"]`).

## Usage

```bash
# Import an Investing.com holdings export (Portfolio > Holdings > Export).
# Lots dated on/before --opening-through are holdings you already owned (OPENING).
uv run argus import investing data/growth_Holdings_09272026.csv --opening-through 2026-08-27 --dry-run
uv run argus import investing data/growth_Holdings_09272026.csv --opening-through 2026-08-27

uv run argus portfolio show growth            # live positions, day & unrealized P&L
uv run argus portfolio show all               # every portfolio combined (read-only view)
uv run argus portfolio performance growth --range ytd
uv run argus txn add growth BUY NVDA --qty 5 --price 225 --dry-run
uv run argus txn edit 42 --price 221.50 --dry-run   # fix a recorded trade (id from `txn list`)
uv run argus quotes NVDA MSFT
uv run argus fundamentals NVDA --fields pe_ttm,pe_forward,pb,ps_ttm
uv run argus financials NVDA --period quarterly
uv run argus history NVDA --period 6mo --indicators sma50,rsi14
uv run argus brief growth --json               # facts for a daily brief
uv run argus events                              # earnings & dividends, next 14 days
uv run argus alert add NVDA day_move_pct 5       # fires once per session
uv run argus note add NVDA "AI capex cycle" --thesis --review-on 2026-11-20
uv run argus market-status
```

Every command accepts `--json` and returns `{"ok": true, "data": ...}` or
`{"ok": false, "error": {"code", "message", "hint"}}`, which is the format agents use.

The web UI's **Data** page does the same: choose a CSV, pick the "already owned through" date from
the lot dates, check the preview, then import. It also backs up and restores your own account's
records (below).

## Back up and move your data

```bash
uv run argus snapshot dump                       # data/snapshots/argus-snapshot-<time>.json
uv run argus snapshot load backup.json --dry-run # on the new machine: preview
uv run argus snapshot load backup.json           # restore into an empty instance
uv run argus snapshot load backup.json --replace # wipe existing records first (backed up automatically)
```

That snapshot is the whole server: every account's portfolios, transactions (including deleted
ones), watchlists, notes, alerts, targets, shares and the audit log, plus the accounts and API keys
(as hashes). That's why it's CLI only. A snapshot from before accounts existed loads into the oldest
account.

The web UI's **Data** page backs up and restores only your own account: your portfolios,
transactions, targets, watchlists, notes, alerts, peer lists and DCF models. Restoring replaces only
your records (saved to `data/snapshots/` first) and never touches another account; the file loads
into any account on any instance. Market data caches are in neither; they refill on use.

## Running it always-on

To run Argus on a server, a home box or your PC and reach it from other devices (Tailscale,
Cloudflare Tunnel), see **[docs/deployment.md](docs/deployment.md)**: accounts, API keys
and the access token (`ARGUS_TOKEN`), allowed hostnames, systemd units and Docker (`deploy/`, `compose.yaml`),
nightly `argus backup`, schema migrations, and moving your data.

## Development

```bash
uv run pytest
```

Secrets (`.env`) and local data (`data/`, including imported CSVs and the SQLite database) are gitignored.
