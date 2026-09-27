"""Alert rules evaluated against live quotes, cached fundamentals, events and cost basis.

Each alert fires at most once per trading session (unique alert_id + session_date), and
fired alerts show up in the UI, the MCP daily brief and `list_alerts`. There are no push
notifications by design.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError

from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import Alert, AlertEvent, AuditLog
from argus.providers.base import Quote
from argus.symbols import is_plausible_symbol, normalize_symbol


@dataclass(frozen=True)
class Kind:
    label: str  # template; {t} is the formatted threshold
    unit: str  # how `threshold` reads: "$", "%", "x", "days"
    needs: str  # quote | fundamentals | events | cost


KINDS: dict[str, Kind] = {
    "price_above": Kind("Price at or above {t}", "$", "quote"),
    "price_below": Kind("Price at or below {t}", "$", "quote"),
    "day_move_pct": Kind("Moves {t} or more in a day", "%", "quote"),
    "day_gain_pct": Kind("Up {t} or more in a day", "%", "quote"),
    "day_loss_pct": Kind("Down {t} or more in a day", "%", "quote"),
    "near_52w_high": Kind("Within {t} of the 52-week high", "%", "fundamentals"),
    "near_52w_low": Kind("Within {t} of the 52-week low", "%", "fundamentals"),
    "pe_above": Kind("P/E (TTM) at or above {t}", "x", "fundamentals"),
    "pe_below": Kind("P/E (TTM) at or below {t}", "x", "fundamentals"),
    "below_cost_pct": Kind("{t} or more below your average cost", "%", "cost"),
    "above_cost_pct": Kind("{t} or more above your average cost", "%", "cost"),
    "earnings_within_days": Kind("Earnings within {t}", "days", "events"),
}


def check(kind: str, t: float, q: Quote | None, m: dict, cost: float | None,
          next_earnings: date | None, today: date) -> tuple[bool, float | None, str] | None:
    """Return (fired, observed value, message) or None if the data isn't available."""
    if kind not in KINDS:
        raise ArgusError("INVALID_ARG", f"Unknown alert kind '{kind}'.")
    needs_price = kind not in ("pe_above", "pe_below", "earnings_within_days")
    if needs_price and q is None:
        return None
    p = q.price if q else None
    chg = q.change_pct if q else None
    if kind == "price_above":
        return p >= t, p, f"price {p:,.2f} ≥ {t:,.2f}"
    if kind == "price_below":
        return p <= t, p, f"price {p:,.2f} ≤ {t:,.2f}"
    if kind in ("day_move_pct", "day_gain_pct", "day_loss_pct"):
        if chg is None:
            return None
        fired = abs(chg) >= t if kind == "day_move_pct" else chg >= t if kind == "day_gain_pct" else chg <= -t
        return fired, chg, f"{chg:+.2f}% on the day"
    if kind in ("near_52w_high", "near_52w_low"):
        ref = m.get("high_52w") if kind == "near_52w_high" else m.get("low_52w")
        if not ref:
            return None
        gap = (p / ref - 1) * 100
        fired = p >= ref * (1 - t / 100) if kind == "near_52w_high" else p <= ref * (1 + t / 100)
        which = "high" if kind == "near_52w_high" else "low"
        return fired, gap, f"{gap:+.1f}% from 52-week {which} {ref:,.2f}"
    if kind in ("pe_above", "pe_below"):
        pe = m.get("pe_ttm")
        if pe is None:
            return None
        return (pe >= t if kind == "pe_above" else pe <= t), pe, f"P/E {pe:.1f}"
    if kind in ("below_cost_pct", "above_cost_pct"):
        if not cost:
            return None
        diff = (p / cost - 1) * 100
        return (diff <= -t if kind == "below_cost_pct" else diff >= t), diff, f"{diff:+.1f}% vs your cost {cost:,.2f}"
    if kind == "earnings_within_days":
        if next_earnings is None:
            return None
        days = (next_earnings - today).days
        return 0 <= days <= t, float(days), f"earnings {next_earnings.isoformat()} (in {days} days)"
    raise AssertionError(kind)  # every KINDS entry is handled above


class AlertService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def create(self, symbol: str, kind: str, threshold: float, note: str | None = None, actor: str = "cli") -> dict:
        if kind not in KINDS:
            raise ArgusError("INVALID_ARG", f"Unknown alert kind '{kind}'.", hint=f"Use one of: {', '.join(KINDS)}")
        sym = normalize_symbol(symbol)
        if not is_plausible_symbol(sym):
            raise ArgusError("INVALID_SYMBOL", f"'{sym}' doesn't look like a US ticker.")
        if threshold < 0:
            raise ArgusError("INVALID_ARG", "Threshold must be >= 0 (direction is part of the kind).")
        with session_scope(self.engine) as s:
            a = Alert(symbol=sym, kind=kind, threshold=threshold, note=note, created_by=actor)
            s.add(a)
            s.flush()
            s.add(AuditLog(actor=actor, action="create", entity="alert", entity_id=str(a.id),
                           after={"symbol": sym, "kind": kind, "threshold": threshold}))
            return self._row(a)

    def set_active(self, alert_id: int, active: bool, actor: str = "cli") -> dict:
        with session_scope(self.engine) as s:
            a = s.get(Alert, alert_id)
            if a is None:
                raise ArgusError("NOT_FOUND", f"No alert {alert_id}.")
            a.active = active
            s.add(AuditLog(actor=actor, action="enable" if active else "disable", entity="alert", entity_id=str(a.id)))
            return self._row(a)

    def list(self, include_inactive: bool = False) -> list[dict]:
        with session_scope(self.engine) as s:
            q = select(Alert).order_by(Alert.symbol, Alert.id)
            if not include_inactive:
                q = q.where(Alert.active.is_(True))
            alerts = list(s.scalars(q))
            last = {}
            for ev in s.scalars(select(AlertEvent).where(AlertEvent.alert_id.in_([a.id for a in alerts]))
                                .order_by(AlertEvent.ts)):
                last[ev.alert_id] = ev
            return [self._row(a) | ({"last_fired": {"session_date": last[a.id].session_date.isoformat(),
                                                    "message": last[a.id].message}} if a.id in last else {})
                    for a in alerts]

    def fired(self, since: date) -> list[dict]:
        with session_scope(self.engine) as s:
            rows = s.execute(select(AlertEvent, Alert).join(Alert, Alert.id == AlertEvent.alert_id)
                             .where(AlertEvent.session_date >= since).order_by(AlertEvent.ts.desc()))
            return [{"alert_id": a.id, "symbol": a.symbol, "kind": a.kind, "threshold": a.threshold,
                     "session_date": ev.session_date.isoformat(), "ts": ev.ts.isoformat(), "value": ev.value,
                     "message": ev.message, "note": a.note} for ev, a in rows]

    def evaluate(self, quotes: dict[str, Quote], metrics: Callable[[str], dict], costs: dict[str, float],
                 next_earnings: dict[str, date], session_date: date) -> list[dict]:
        """Check every active alert; record and return the ones that newly fired this session."""
        new = []
        with session_scope(self.engine) as s:
            alerts = list(s.scalars(select(Alert).where(Alert.active.is_(True))))
            done = {ev.alert_id for ev in s.scalars(select(AlertEvent).where(AlertEvent.session_date == session_date))}
        for a in alerts:
            if a.id in done:
                continue
            m = metrics(a.symbol) if KINDS[a.kind].needs == "fundamentals" else {}
            res = check(a.kind, a.threshold, quotes.get(a.symbol), m, costs.get(a.symbol),
                        next_earnings.get(a.symbol), session_date)
            if not res or not res[0]:
                continue
            _, value, msg = res
            message = f"{a.symbol}: {msg}"
            try:
                with session_scope(self.engine) as s:
                    s.add(AlertEvent(alert_id=a.id, session_date=session_date, value=value, message=message))
            except IntegrityError:
                continue  # another process recorded it first
            new.append({"alert_id": a.id, "symbol": a.symbol, "kind": a.kind, "message": message, "note": a.note})
        return new

    @staticmethod
    def _row(a: Alert) -> dict:
        k = KINDS[a.kind]
        t = a.threshold
        shown = {"$": f"${t:,.2f}", "%": f"{t:g}%", "x": f"{t:g}x", "days": f"{t:g} days"}[k.unit]
        return {"id": a.id, "symbol": a.symbol, "kind": a.kind, "threshold": t, "unit": k.unit,
                "label": k.label.format(t=shown), "note": a.note, "active": a.active, "created_by": a.created_by}
