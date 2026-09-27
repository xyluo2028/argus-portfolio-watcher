"""Live quote hub for the web server.

- Tracks every open position, watchlist item and portfolio benchmark.
- While the market is in a session (pre/regular/post), streams trade prints from the
  Finnhub WebSocket for the largest positions (free tier caps subscriptions at ~50) and
  refreshes everything over REST once a minute (this also supplies prev_close).
- While closed, it serves the settled close and does not poll.
- WebSocket prices are flushed to the quote cache so the CLI and MCP see them too.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select

from argus.app import Argus
from argus.db import session_scope
from argus.market_calendar import market_status
from argus.models import Portfolio, WatchlistItem
from argus.providers.base import Quote

log = logging.getLogger("argus.live")

FINNHUB_WS = "wss://ws.finnhub.io?token={key}"
STREAM_LIMIT = 48
REST_INTERVAL_S = 60
SESSION_CHECK_S = 30
FLUSH_INTERVAL_S = 10


class LiveHub:
    def __init__(self, argus: Argus, stream_limit: int = STREAM_LIMIT, rest_interval_s: int = REST_INTERVAL_S):
        self.argus = argus
        self.stream_limit = stream_limit
        self.rest_interval_s = rest_interval_s
        self.quotes: dict[str, Quote] = {}
        self.status: dict = market_status()
        self.streamed: list[str] = []
        self.ws_state = "disabled" if not argus.settings.finnhub_api_key else "idle"
        self.version = 0
        self._cond = asyncio.Condition()
        self._dirty: set[str] = set()
        self._tasks: list[asyncio.Task] = []
        self._ws_task: asyncio.Task | None = None
        self._resubscribe = asyncio.Event()

    # -- lifecycle ------------------------------------------------------------
    async def start(self) -> None:
        self._tasks = [asyncio.create_task(self._session_loop(), name="argus-session"),
                       asyncio.create_task(self._flush_loop(), name="argus-flush")]

    async def stop(self) -> None:
        for t in [*self._tasks, self._ws_task]:
            if t:
                t.cancel()
        await asyncio.gather(*[t for t in [*self._tasks, self._ws_task] if t], return_exceptions=True)
        await asyncio.to_thread(self._flush)

    # -- change notification --------------------------------------------------
    async def _bump(self) -> None:
        async with self._cond:
            self.version += 1
            self._cond.notify_all()

    async def wait_for_change(self, since: int, timeout: float) -> int:
        async with self._cond:
            try:
                await asyncio.wait_for(self._cond.wait_for(lambda: self.version != since), timeout)
            except TimeoutError:
                pass
            return self.version

    def snapshot(self) -> dict:
        return {
            "version": self.version,
            "market": self.status,
            "stream": {"state": self.ws_state, "symbols": len(self.streamed)},
            "quotes": {s: q.to_dict() for s, q in self.quotes.items()},
        }

    # -- what to track --------------------------------------------------------
    def tracked_symbols(self) -> list[str]:
        """Held symbols ordered by market value (largest first), then watchlist and benchmarks."""
        weights: dict[str, float] = {}
        extra: list[str] = []
        with session_scope(self.argus.engine) as s:
            portfolios = list(s.scalars(select(Portfolio)))
            extra += [w.symbol for w in s.scalars(select(WatchlistItem))]
            extra += [p.benchmark for p in portfolios]
        for p in portfolios:
            for sym, pos in self.argus.portfolios.positions(p.id).items():
                if pos.is_open:
                    q = self.quotes.get(sym)
                    weights[sym] = weights.get(sym, 0.0) + pos.qty * (q.price if q else pos.avg_cost or 0)
        held = sorted(weights, key=lambda s: -weights[s])
        return list(dict.fromkeys(held + extra))

    # -- loops ----------------------------------------------------------------
    async def _session_loop(self) -> None:
        last_rest = 0.0
        loop = asyncio.get_running_loop()
        while True:
            try:
                self.status = market_status()
                symbols = await asyncio.to_thread(self.tracked_symbols)
                in_session = self.status["session"] != "closed"
                due = loop.time() - last_rest >= self.rest_interval_s
                if symbols and (due or not self.quotes or set(symbols) - set(self.quotes)):
                    # Closed market: MarketService serves the settled close from cache.
                    await self._rest_refresh(symbols, max_age_s=self.rest_interval_s - 5 if in_session else None)
                    last_rest = loop.time()
                if in_session and self.ws_state != "disabled":
                    self._ensure_stream(symbols[: self.stream_limit])
                else:
                    await self._stop_stream()
                await self._bump()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - keep the hub alive; the next tick retries
                log.exception("session loop tick failed")
            await asyncio.sleep(SESSION_CHECK_S)

    async def _rest_refresh(self, symbols: list[str], max_age_s: int | None) -> None:
        quotes, errors = await asyncio.to_thread(self.argus.market.get_quotes, symbols, max_age_s)
        for sym, q in quotes.items():
            live = self.quotes.get(sym)
            # Never let a slower REST quote overwrite a newer streamed trade price.
            if live and live.source == "finnhub-ws" and live.as_of > q.as_of:
                self.quotes[sym] = replace(live, prev_close=q.prev_close, open=q.open)
            else:
                self.quotes[sym] = q
        if errors:
            log.warning("no quotes for %s", ", ".join(sorted(errors)))

    # -- websocket ------------------------------------------------------------
    def _ensure_stream(self, symbols: list[str]) -> None:
        if symbols != self.streamed:
            self.streamed = symbols
            self._resubscribe.set()
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._ws_loop(), name="argus-ws")

    async def _stop_stream(self) -> None:
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            await asyncio.gather(self._ws_task, return_exceptions=True)
        self._ws_task = None
        if self.ws_state != "disabled":
            self.ws_state = "idle"

    async def _ws_loop(self) -> None:
        import websockets

        url = FINNHUB_WS.format(key=self.argus.settings.finnhub_api_key)
        backoff = 1
        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    self.ws_state = "connected"
                    backoff = 1
                    subscribed: set[str] = set()
                    while True:
                        want = set(self.streamed)
                        for s in subscribed - want:
                            await ws.send(json.dumps({"type": "unsubscribe", "symbol": s}))
                        for s in want - subscribed:
                            await ws.send(json.dumps({"type": "subscribe", "symbol": s}))
                        subscribed = want
                        self._resubscribe.clear()
                        recv = asyncio.create_task(ws.recv())
                        resub = asyncio.create_task(self._resubscribe.wait())
                        try:
                            done, _ = await asyncio.wait({recv, resub}, return_when=asyncio.FIRST_COMPLETED)
                        finally:
                            # Also runs on cancellation, so no orphaned recv task outlives the socket.
                            for t in (recv, resub):
                                if not t.done():
                                    t.cancel()
                            await asyncio.gather(recv, resub, return_exceptions=True)
                        if recv in done and not recv.cancelled() and recv.exception() is None:
                            await self._on_ws_message(recv.result())
                        elif recv in done:
                            raise recv.exception() or ConnectionError("websocket receive cancelled")
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - network errors: reconnect with backoff
                self.ws_state = "reconnecting"
                log.warning("finnhub websocket: %s; retrying in %ss", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _on_ws_message(self, raw: str | bytes) -> None:
        msg = json.loads(raw)
        if msg.get("type") != "trade":
            return
        # Several prints per symbol can arrive in one message; keep the latest.
        latest: dict[str, dict] = {}
        for t in msg.get("data") or []:
            if t.get("s") and t.get("p") and (t["s"] not in latest or t["t"] >= latest[t["s"]]["t"]):
                latest[t["s"]] = t
        for sym, t in latest.items():
            self.apply_trade(sym, float(t["p"]), datetime.fromtimestamp(t["t"] / 1000, UTC))
        if latest:
            await self._bump()

    def apply_trade(self, symbol: str, price: float, ts: datetime) -> None:
        base = self.quotes.get(symbol)
        if base is None:
            self.quotes[symbol] = Quote(symbol, price, None, None, price, price, ts, "finnhub-ws")
        else:
            if ts < base.as_of:
                return
            self.quotes[symbol] = replace(
                base, price=price, as_of=ts, source="finnhub-ws", delayed=False,
                high=max(base.high or price, price) if self.status["session"] == "regular" else base.high,
                low=min(base.low or price, price) if self.status["session"] == "regular" else base.low,
            )
        self._dirty.add(symbol)

    # -- persistence ----------------------------------------------------------
    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_S)
            await asyncio.to_thread(self._flush)

    def _flush(self) -> None:
        dirty, self._dirty = self._dirty, set()
        if dirty:
            self.argus.market.store_quotes([self.quotes[s] for s in dirty if s in self.quotes])
