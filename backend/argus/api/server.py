"""FastAPI app: JSON API, server-sent events for live updates, and the built web UI.

Errors are returned as {"error": {"code", "message", "hint"}} with a matching HTTP status.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from argus.app import Argus
from argus.config import REPO_ROOT
from argus.errors import ArgusError
from argus.live import LiveHub
from argus.mcp_server import create_mcp
from argus.market_calendar import parse_ny_datetime
from argus.services.alerts import KINDS
from argus.services.portfolio import TxnInput
from argus.symbols import normalize_symbol

UI_DIST = REPO_ROOT / "frontend" / "dist"
STREAM_MIN_INTERVAL_S = 1.0
KEEPALIVE_S = 15.0

_STATUS = {"NOT_FOUND": 404, "ALREADY_EXISTS": 409, "PROVIDER_ERROR": 502, "NOT_CONFIGURED": 503}


class TxnBody(BaseModel):
    type: str
    symbol: str
    qty: float = 0.0
    price: float = 0.0
    fee: float = 0.0
    amount: float = 0.0
    date: str | None = None  # YYYY-MM-DD[THH:MM] New York time; default now
    note: str | None = None
    idempotency_key: str | None = None
    dry_run: bool = False


class WatchBody(BaseModel):
    symbols: list[str]
    note: str | None = None


class AlertBody(BaseModel):
    symbol: str
    kind: str
    threshold: float
    note: str | None = None


class NoteBody(BaseModel):
    symbol: str
    text: str
    kind: str = "note"
    review_on: str | None = None


class NotePatch(BaseModel):
    text: str | None = None
    review_on: str | None = None
    clear_review: bool = False
    archived: bool | None = None


class TargetsBody(BaseModel):
    level: str
    weights: dict[str, float]
    dry_run: bool = True


class SimBody(BaseModel):
    trades: list[dict]


class PortfolioBody(BaseModel):
    name: str
    benchmark: str = "SPY"


def create_app(argus: Argus | None = None, start_hub: bool = True) -> FastAPI:
    argus = argus or Argus()
    hub = LiveHub(argus)
    # MCP over streamable HTTP at /mcp/, reading the same live quotes as the UI.
    mcp = create_mcp(argus, live_quotes=lambda: dict(hub.quotes))
    mcp_app = mcp.streamable_http_app(streamable_http_path="/")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        async with mcp.session_manager.run():
            if start_hub:
                await hub.start()
            yield
            if start_hub:
                await hub.stop()

    app = FastAPI(title="Argus", lifespan=lifespan)
    # Only answer requests addressed to this machine: blocks DNS-rebinding pages in the browser
    # from reading or changing the portfolio through a hostile hostname that resolves to 127.0.0.1.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])
    app.state.argus = argus
    app.state.hub = hub

    @app.exception_handler(ArgusError)
    async def _argus_error(_: Request, e: ArgusError):
        return JSONResponse({"error": e.to_dict()}, status_code=_STATUS.get(e.code, 400))

    async def run(fn, *args, **kwargs):
        # Service calls hit SQLite and providers synchronously; keep the event loop free.
        return await asyncio.to_thread(fn, *args, **kwargs)

    # -- market ----------------------------------------------------------------
    @app.get("/api/market-status")
    async def market_status():
        return hub.status

    @app.get("/api/quotes")
    async def quotes(symbols: str = Query(..., description="Comma-separated")):
        return await run(argus.quotes, [s for s in symbols.split(",") if s.strip()])

    @app.get("/api/history/{symbol}")
    async def history(symbol: str, period: str = "1y", interval: str = "1d", indicators: str | None = None):
        specs = [x for x in indicators.split(",") if x.strip()] if indicators else None
        return await run(argus.history, symbol, period, interval, specs)

    @app.get("/api/fundamentals/{symbol}")
    async def fundamentals(symbol: str, fields: str | None = None, refresh: bool = False):
        f = [x.strip() for x in fields.split(",")] if fields else None
        return await run(argus.market.get_fundamentals, normalize_symbol(symbol), f, refresh)

    @app.get("/api/financials/{symbol}")
    async def financials(symbol: str, period: str = "quarterly", limit: int = 8):
        return await run(argus.market.get_financials, normalize_symbol(symbol), period, limit)

    @app.get("/api/search")
    async def search(q: str, limit: int = 10):
        return await run(argus.market.search, q, limit)

    # -- portfolios ------------------------------------------------------------
    @app.get("/api/portfolios")
    async def portfolios():
        return await run(argus.portfolios.list_portfolios)

    @app.post("/api/portfolios", status_code=201)
    async def create_portfolio(body: PortfolioBody):
        return await run(argus.portfolios.create_portfolio, body.name, body.benchmark, "ui")

    @app.get("/api/portfolios/{ref}")
    async def portfolio(ref: str, lots: bool = False):
        return await run(argus.portfolio, ref, True, lots, hub.quotes)

    @app.get("/api/portfolios/{ref}/performance")
    async def performance(ref: str, range: str = "all"):  # noqa: A002 - query param name
        return await run(argus.performance, ref, range, dict(hub.quotes))

    @app.get("/api/portfolios/{ref}/transactions")
    async def transactions(ref: str, symbol: str | None = None, include_deleted: bool = False):
        return await run(argus.portfolios.list_transactions, ref, symbol, include_deleted)

    @app.post("/api/portfolios/{ref}/transactions")
    async def add_transaction(ref: str, body: TxnBody):
        item = TxnInput(type=body.type, symbol=body.symbol, ts=parse_ny_datetime(body.date), qty=body.qty,
                        price=body.price, fee=body.fee, amount=body.amount, note=body.note,
                        external_id=body.idempotency_key)
        return await run(argus.portfolios.add_transactions, ref, [item], "ui", body.dry_run)

    @app.delete("/api/transactions/{txn_id}")
    async def delete_transaction(txn_id: int, dry_run: bool = False):
        return await run(argus.portfolios.delete_transaction, txn_id, "ui", dry_run)

    # -- watchlist & compare ------------------------------------------------------
    @app.get("/api/watchlists")
    async def watchlists():
        return await run(argus.watchlists.list_watchlists)

    @app.get("/api/watchlists/{name}")
    async def watchlist(name: str):
        return await run(argus.watchlist, name, dict(hub.quotes))

    @app.post("/api/watchlists/{name}")
    async def watchlist_add(name: str, body: WatchBody):
        return await run(argus.watchlists.add, body.symbols, body.note, name, "ui")

    @app.delete("/api/watchlists/{name}/{symbol}")
    async def watchlist_remove(name: str, symbol: str):
        return await run(argus.watchlists.remove, [symbol], name, "ui")

    @app.get("/api/compare")
    async def compare(symbols: str, fields: str | None = None):
        f = [x.strip() for x in fields.split(",")] if fields else None
        return await run(argus.compare, symbols.split(","), f)

    # -- routines: brief, events, alerts, notes ------------------------------------
    @app.get("/api/brief/{ref}")
    async def brief(ref: str, news: bool = True):
        return await run(argus.daily_brief, ref, dict(hub.quotes), news)

    @app.get("/api/events")
    async def events(days_ahead: int = 14, days_back: int = 7):
        return await run(argus.upcoming_events, days_ahead, days_back)

    @app.get("/api/alerts")
    async def alerts(include_inactive: bool = False):
        since = date.fromisoformat(hub.status["last_session"])
        return {"alerts": await run(argus.alerts.list, include_inactive),
                "fired": await run(argus.alerts.fired, since),
                "kinds": {k: {"label": v.label, "unit": v.unit} for k, v in KINDS.items()}}

    @app.post("/api/alerts", status_code=201)
    async def create_alert(body: AlertBody):
        return await run(argus.alerts.create, body.symbol, body.kind, body.threshold, body.note, "ui")

    @app.patch("/api/alerts/{alert_id}")
    async def toggle_alert(alert_id: int, active: bool):
        return await run(argus.alerts.set_active, alert_id, active, "ui")

    @app.get("/api/notes")
    async def notes(symbol: str | None = None, include_archived: bool = False):
        return await run(argus.notes.list, symbol, include_archived)

    @app.post("/api/notes", status_code=201)
    async def add_note(body: NoteBody):
        review = date.fromisoformat(body.review_on) if body.review_on else None
        return await run(argus.notes.add, body.symbol, body.text, body.kind, review, "ui")

    @app.patch("/api/notes/{note_id}")
    async def update_note(note_id: int, body: NotePatch):
        review = date.fromisoformat(body.review_on) if body.review_on else None
        return await run(argus.notes.update, note_id, body.text, review, body.clear_review, body.archived, "ui")

    # -- analysis -------------------------------------------------------------------
    @app.get("/api/portfolios/{ref}/exposure")
    async def get_exposure(ref: str):
        return await run(argus.exposure, ref, dict(hub.quotes))

    @app.get("/api/portfolios/{ref}/drift")
    async def get_drift(ref: str, level: str = "symbol", tolerance_pp: float = 2.0):
        return await run(argus.drift, ref, level, tolerance_pp, dict(hub.quotes))

    @app.put("/api/portfolios/{ref}/targets")
    async def put_targets(ref: str, body: TargetsBody):
        return await run(argus.set_targets, ref, body.level, body.weights, body.dry_run, "ui")

    @app.post("/api/portfolios/{ref}/simulate")
    async def simulate(ref: str, body: SimBody):
        return await run(argus.simulate_trades, ref, body.trades, dict(hub.quotes))

    # -- live stream -------------------------------------------------------------
    @app.get("/api/stream")
    async def stream(request: Request, portfolio: str | None = None):
        """SSE: an `update` event at most once per second while prices change."""
        async def events():
            seen = -1
            while not await request.is_disconnected():
                version = await hub.wait_for_change(seen, KEEPALIVE_S)
                if version == seen:
                    yield ": keepalive\n\n"
                    continue
                seen = version
                payload = hub.snapshot()
                if portfolio:
                    try:
                        payload["portfolio"] = await run(argus.portfolios.summary, portfolio, dict(hub.quotes))
                    except ArgusError as e:
                        payload["portfolio_error"] = e.to_dict()
                yield f"event: update\ndata: {json.dumps(payload, default=str)}\n\n"
                await asyncio.sleep(STREAM_MIN_INTERVAL_S)

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/health")
    async def health():
        return {"ok": True, "stream": hub.ws_state, "session": hub.status["session"]}

    app.mount("/mcp", mcp_app)

    # -- web UI ----------------------------------------------------------------------
    if UI_DIST.exists():
        app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            f = UI_DIST / path
            if path and f.is_file():
                return FileResponse(f)
            # index.html names the hashed bundles, so it must never be served stale after a rebuild.
            return FileResponse(UI_DIST / "index.html", headers={"Cache-Control": "no-cache"})
    else:
        @app.get("/", include_in_schema=False)
        async def no_ui():
            return JSONResponse({"message": "Argus API is running. The web UI isn't built yet: "
                                            "cd frontend && npm install && npm run build"})

    return app


def serve(port: int, host: str = "127.0.0.1") -> None:
    import socket

    import uvicorn

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex((host, port)) == 0:
            raise ArgusError("PORT_IN_USE", f"Port {port} is already in use.",
                             hint="Pass --port, or set ARGUS_PORT in .env.")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")

