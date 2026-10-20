# Argus

A local-first portfolio monitor for US stocks and ETFs: FastAPI + SQLite backend, React + Vite
frontend, a JSON CLI (`argus`) and an MCP server, built to be used by AI agents as easily as by hand.
Design notes: `docs/design.html`; deployment: `docs/deployment.md`.

**This repository is public.** Never commit `.env`, anything under `data/`, API keys, or personal
financial data. The improvement loop (`docs/loop/`) uses model portfolios only.

## Layout

- `backend/argus/app.py`: `Argus`, the facade every surface calls (API, CLI, MCP)
- `backend/argus/api/server.py`: FastAPI routes, auth, static UI; MCP is mounted at `/mcp/`
- `backend/argus/cli.py` (Typer), `backend/argus/mcp_server.py` (MCP tools)
- `backend/argus/services/`: portfolio math, dividends, risk, research, screener, market context...
- `backend/argus/providers/`: Finnhub, Yahoo (yfinance), SEC EDGAR, macro (Treasury, Fed, Nasdaq), French factors, OpenFIGI
- `backend/argus/live.py`: live price hub (Finnhub WebSocket + REST refresh, cache warming)
- `backend/argus/migrations/`: Alembic; every schema change needs a migration
- `frontend/src/`: `pages/`, `components/`, `api.ts` (types + client), `metrics.ts` (shared indicator definitions), `styles.css`
- `tests/`: pytest; providers are faked, no network

## Commands

```bash
uv sync                                  # Python deps
uv run pytest -q                         # all tests (must pass before every commit)
cd frontend && npm ci && npm run build   # type check + production build (must pass)
uv run argus serve                       # UI + API + MCP on http://127.0.0.1:8787
uv run argus --help                      # CLI; most commands take --json
```

## Conventions

- Match the surrounding code: its naming, comment density and idiom. Comments explain why, not what.
- Every surface goes through `Argus`; don't put business logic in routes, CLI commands or MCP tools.
- A figure shown in two places (dashboard and stock page, UI and MCP) comes from one definition.
- Tests for every behavior change; fake providers, never hit the network in tests.
- UI: colors come from the CSS tokens in `styles.css` (`--up`, `--down`, `--series-*`...), with
  light and dark themes; layouts must work at phone width (390 px) without horizontal page scroll.

## Data providers: be polite

- Finnhub free tier: 60 calls/min (a token bucket enforces it) and one WebSocket per key.
- SEC EDGAR: identify with `SEC_USER_AGENT`, stay under 10 requests/s; responses are cached.
- Yahoo is unofficial: batch where possible (`YahooProvider._quote_rows`, `yf.download`).
- SQLite: keep reads on the calling thread and in bulk; thread pools are for network calls only.
