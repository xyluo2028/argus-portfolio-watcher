"""FastAPI app: JSON API, server-sent events for live updates, and the built web UI.

Errors are returned as {"error": {"code", "message", "hint"}} with a matching HTTP status.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from argus.app import Argus
from argus.config import REPO_ROOT
from argus.errors import ArgusError
from argus.live import LiveHub
from argus.market_calendar import parse_ny_datetime
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


class PortfolioBody(BaseModel):
    name: str
    benchmark: str = "SPY"


def create_app(argus: Argus | None = None, start_hub: bool = True) -> FastAPI:
    argus = argus or Argus()
    hub = LiveHub(argus)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if start_hub:
            await hub.start()
        yield
        if start_hub:
            await hub.stop()

    app = FastAPI(title="Argus", lifespan=lifespan)
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
    async def history(symbol: str, period: str = "1y", interval: str = "1d"):
        return await run(argus.history, symbol, period, interval)

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

    # -- web UI ----------------------------------------------------------------------
    if UI_DIST.exists():
        app.mount("/assets", StaticFiles(directory=UI_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            f = UI_DIST / path
            return FileResponse(f if path and f.is_file() else UI_DIST / "index.html")
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

