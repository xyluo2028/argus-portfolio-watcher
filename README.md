# Argus

*The hundred-eyed watchman for your portfolio.*

A local-first portfolio monitor for US stocks and ETFs, designed to be operated by AI agents as easily as by hand.

- Build portfolios from a trade log (multiple portfolios + watchlist)
- Near real-time prices on trading days, live P&L and day change
- Candlestick charts with indicators; performance vs SPY/QQQ
- Valuation and fundamentals: PE, forward PE, PB, PS, EV/EBITDA, revenue growth, margins
- MCP server and JSON CLI so Claude (Desktop / Code) can query and update your portfolio

> **Status:** P0 foundation, P1 monitor MVP and P2 routines are done: dashboard, ticker charts, live prices, performance vs benchmark, watchlist, transactions, compare, events calendar, alerts, thesis notes, daily-brief data, and a 25-tool MCP server. P3 (target weights, drift, what-if) is next. See the [design doc](docs/design.html) (open it in a browser for the diagrams).

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
| P3 Analysis | Target weights and drift, what-if trades, more data providers |

## Setup

```bash
brew install uv
uv sync
cp .env.example .env   # add FINNHUB_API_KEY and SEC_USER_AGENT
```

Without `FINNHUB_API_KEY`, quotes and metrics fall back to Yahoo (slower, unofficial).
`SEC_USER_AGENT` is only needed for `argus financials`.

## Web UI

```bash
(cd frontend && npm install && npm run build)   # once, and after UI changes
uv run argus serve                               # http://localhost:8787
```

During market hours prices stream live (Finnhub WebSocket for the largest ~48 positions, REST
refresh for the rest each minute). Set `ARGUS_PORT` in `.env` to use another port. For UI
development, run `npm run dev` in `frontend/` alongside `argus serve` (Vite proxies `/api`).

## Use it from Claude (MCP)

Argus exposes 25 tools: portfolio, quotes, history with indicators, fundamentals, SEC
financials, compare, performance, transactions, watchlist, events, alerts, notes, and
`get_daily_brief_data`, which gathers everything for a brief in one call. Write tools default
to `dry_run=true` and accept an `idempotency_key`. The prompts `daily_brief` and
`position_review` package common routines.

```bash
# Claude Code, stdio (works whether or not `argus serve` is running)
claude mcp add argus -- uv run --directory ~/Documents/github/project-hatching/argus-portfolio-watcher argus mcp

# or over HTTP while `argus serve` is running (uses the live price stream)
claude mcp add --transport http argus http://localhost:8787/mcp/
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
uv run argus portfolio performance growth --range ytd
uv run argus txn add growth BUY NVDA --qty 5 --price 225 --dry-run
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

## Development

```bash
uv run pytest
```

Secrets (`.env`) and local data (`data/`, including imported CSVs and the SQLite database) are gitignored.
