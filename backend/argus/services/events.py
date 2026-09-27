"""Earnings and dividend calendar for held/watched symbols, plus recent earnings results and news.

Refreshed at most once per day per symbol (cached in the `event` table); ETFs simply have
no earnings rows.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Engine, delete, select

from argus.db import session_scope
from argus.models import Event, RefreshLog
from argus.providers.base import ProviderError

log = logging.getLogger("argus.events")

REFRESH_EVERY = timedelta(hours=20)
LOOKBACK_DAYS = 14
HORIZON_DAYS = 60
NEWS_TTL = timedelta(hours=1)


def _to_date(v) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


class EventsService:
    def __init__(self, engine: Engine, finnhub=None, yahoo=None):
        self.engine = engine
        self.finnhub = finnhub
        self.yahoo = yahoo
        self._news: dict[str, tuple[datetime, list[dict]]] = {}

    # -- refresh --------------------------------------------------------------
    def _stale(self, symbols: list[str], force: bool) -> list[str]:
        if force:
            return symbols
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            fresh = {r.key.split(":", 1)[1] for r in s.scalars(select(RefreshLog).where(
                RefreshLog.key.in_([f"events:{x}" for x in symbols]))) if now - r.at < REFRESH_EVERY}
        return [x for x in symbols if x not in fresh]

    def refresh(self, symbols: list[str], force: bool = False, today: date | None = None) -> dict:
        today = today or datetime.now(UTC).date()
        start, end = today - timedelta(days=LOOKBACK_DAYS), today + timedelta(days=HORIZON_DAYS)
        todo = self._stale(symbols, force)
        failed: dict[str, str] = {}
        for sym in todo:
            rows: list[Event] = []
            try:
                rows += self._earnings(sym, start, end)
                rows += self._dividends(sym, start, end)
            except ProviderError as e:
                failed[sym] = str(e)
                continue
            with session_scope(self.engine) as s:
                # Replace this symbol's window so moved/cancelled dates don't linger.
                s.execute(delete(Event).where(Event.symbol == sym, Event.d >= start, Event.d <= end))
                for r in rows:
                    s.merge(r)
                s.merge(RefreshLog(key=f"events:{sym}", at=datetime.now(UTC)))
        return {"refreshed": [x for x in todo if x not in failed], "failed": failed}

    def _earnings(self, sym: str, start: date, end: date) -> list[Event]:
        out: dict[date, Event] = {}
        if self.finnhub is not None:
            for r in self.finnhub.earnings_calendar(sym, start, end):
                d = _to_date(r.get("date"))
                if d is None:
                    continue
                data = {k: r.get(k) for k in ("epsEstimate", "epsActual", "revenueEstimate", "revenueActual",
                                              "quarter", "year")}
                if data.get("epsActual") is not None and data.get("epsEstimate"):
                    data["epsSurprisePct"] = (data["epsActual"] / data["epsEstimate"] - 1) * 100 \
                        if data["epsEstimate"] > 0 else None
                out[d] = Event(symbol=sym, kind="earnings", d=d, hour=r.get("hour") or None, data=data,
                               source="finnhub")
        if not out and self.yahoo is not None:
            cal = self.yahoo.get_calendar(sym)
            for v in cal.get("Earnings Date") or []:
                d = _to_date(v)
                if d and start <= d <= end:
                    out[d] = Event(symbol=sym, kind="earnings", d=d, hour=None,
                                   data={"epsEstimate": cal.get("Earnings Average"),
                                         "revenueEstimate": cal.get("Revenue Average")}, source="yahoo")
        return list(out.values())

    def _dividends(self, sym: str, start: date, end: date) -> list[Event]:
        if self.yahoo is None:
            return []
        cal = self.yahoo.get_calendar(sym)
        out = []
        for key, kind in (("Ex-Dividend Date", "ex_dividend"), ("Dividend Date", "dividend_pay")):
            d = _to_date(cal.get(key))
            if d and start <= d <= end:
                out.append(Event(symbol=sym, kind=kind, d=d, hour=None, data={}, source="yahoo"))
        return out

    # -- queries --------------------------------------------------------------
    def between(self, symbols: list[str], start: date, end: date, kinds: list[str] | None = None) -> list[dict]:
        with session_scope(self.engine) as s:
            q = select(Event).where(Event.symbol.in_(symbols), Event.d >= start, Event.d <= end)
            if kinds:
                q = q.where(Event.kind.in_(kinds))
            return [{"symbol": e.symbol, "kind": e.kind, "date": e.d.isoformat(), "hour": e.hour,
                     **{k: v for k, v in (e.data or {}).items() if v is not None}, "source": e.source}
                    for e in s.scalars(q.order_by(Event.d, Event.symbol))]

    def next_earnings(self, symbols: list[str], today: date) -> dict[str, date]:
        out: dict[str, date] = {}
        for e in self.between(symbols, today, today + timedelta(days=HORIZON_DAYS), ["earnings"]):
            out.setdefault(e["symbol"], date.fromisoformat(e["date"]))
        return out

    def news(self, symbol: str, days: int = 3, limit: int = 5) -> list[dict]:
        """Recent headlines (Finnhub), cached for an hour per symbol."""
        if self.finnhub is None:
            return []
        now = datetime.now(UTC)
        hit = self._news.get(symbol)
        if hit and now - hit[0] < NEWS_TTL:
            items = hit[1]
        else:
            try:
                raw = self.finnhub.company_news(symbol, now.date() - timedelta(days=days), now.date())
            except ProviderError as e:
                log.warning("news %s: %s", symbol, e)
                return []
            items = [{"ts": datetime.fromtimestamp(n["datetime"], UTC).isoformat(), "headline": n.get("headline"),
                      "source": n.get("source"), "url": n.get("url")}
                     for n in sorted(raw, key=lambda n: -n.get("datetime", 0)) if n.get("headline")]
            self._news[symbol] = (now, items)
        return items[:limit]
