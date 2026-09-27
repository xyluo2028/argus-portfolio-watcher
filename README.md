# Argus

*The hundred-eyed watchman for your portfolio.*

A local-first portfolio monitor for US stocks and ETFs, designed to be operated by AI agents as easily as by hand.

- Build portfolios from a trade log (multiple portfolios + watchlist)
- Near real-time prices on trading days, live P&L and day change
- Candlestick charts with indicators; performance vs SPY/QQQ
- Valuation and fundamentals: PE, forward PE, PB, PS, EV/EBITDA, revenue growth, margins
- MCP server and JSON CLI so Claude (Desktop / Code) can query and update your portfolio

> **Status:** design phase. See the [design doc](docs/design.html) (open it in a browser for the diagrams).

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
| P0 Foundation | Schema, data providers, trade log → FIFO lots/positions, `argus` CLI, Investing.com CSV import |
| P1 Monitor MVP | Live quote loop, dashboard, ticker detail, watchlist, benchmark compare, MCP tools |
| P2 Routines | Earnings/events, daily-brief data tool, alerts, thesis notes |
| P3 Analysis | Target weights and drift, what-if trades, more data providers |

## Setup (once code lands)

```bash
cp .env.example .env   # add FINNHUB_API_KEY and SEC_USER_AGENT
```

Secrets (`.env`) and local data (`data/`, including imported CSVs and the SQLite database) are gitignored.
