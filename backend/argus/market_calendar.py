"""NYSE session state from the local exchange calendar (no network)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

from argus.errors import ArgusError

NY = ZoneInfo("America/New_York")
PRE_MARKET_OPEN = time(4, 0)
POST_MARKET_HOURS = timedelta(hours=4)


@lru_cache(maxsize=1)
def _cal():
    return xcals.get_calendar("XNYS")


def _py(ts: pd.Timestamp) -> datetime:
    return ts.to_pydatetime().astimezone(UTC)


def market_status(now: datetime | None = None) -> dict:
    """Return the session (pre | regular | post | closed) plus surrounding open/close times."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    ny_date = now.astimezone(NY).date()
    today = pd.Timestamp(ny_date)
    cal = _cal()

    session = "closed"
    is_trading_day = bool(cal.is_session(today))
    is_half_day = False
    if is_trading_day:
        open_, close = _py(cal.session_open(today)), _py(cal.session_close(today))
        is_half_day = close.astimezone(NY).time() < time(16, 0)
        pre = datetime.combine(ny_date, PRE_MARKET_OPEN, NY).astimezone(UTC)
        if pre <= now < open_:
            session = "pre"
        elif open_ <= now < close:
            session = "regular"
        elif close <= now < close + POST_MARKET_HOURS:
            session = "post"

    nxt = cal.date_to_session(today, "next")
    if _py(cal.session_open(nxt)) <= now:
        nxt = cal.next_session(nxt)
    prev = cal.date_to_session(today, "previous")
    if _py(cal.session_close(prev)) > now:
        prev = cal.previous_session(prev)

    return {
        "session": session,
        "is_trading_day": is_trading_day,
        "is_half_day": is_half_day,
        "now": now.isoformat(),
        "next_open": _py(cal.session_open(nxt)).isoformat(),
        # During pre-market or the regular session the next close is today's.
        "next_close": _py(cal.session_close(today if session in ("pre", "regular") else nxt)).isoformat(),
        "last_close": _py(cal.session_close(prev)).isoformat(),
        "last_session": prev.date().isoformat(),
    }



def session_date(ts: datetime) -> date:
    """The trading session a quote timestamp belongs to.

    During a trading day's pre/regular/post hours that is the day itself; otherwise
    (overnight, weekends, holidays) the price is the last completed session's close.
    """
    st = market_status(ts)
    if st["session"] != "closed":
        return ts.astimezone(NY).date()
    return date.fromisoformat(st["last_session"])


@lru_cache(maxsize=512)
def _trade_cutoff(d: date) -> datetime | None:
    """When trades stop counting toward session `d` (None if `d` isn't a session). A date entered without
    a time lands at 16:00 (parse_ny_datetime), so that's never after the close, even on a half day."""
    day = pd.Timestamp(d)
    if not _cal().is_session(day):
        return None
    return max(_py(_cal().session_close(day)), datetime.combine(d, time(16, 0), NY).astimezone(UTC))


def trade_session(ts: datetime) -> date:
    """The session a trade's money belongs to: its New York date if that's a session and the trade is
    by its close; otherwise (after the close, weekends, holidays) the next session."""
    ts = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    d = ts.astimezone(NY).date()
    if not _cal().first_session.date() <= d < _cal().last_session.date():
        return d  # outside the calendar's span: the NY date is the best we know
    cutoff = _trade_cutoff(d)
    if cutoff is not None and ts <= cutoff:
        return d
    return _cal().date_to_session(pd.Timestamp(d) + pd.Timedelta(days=1), "next").date()


def parse_ny_datetime(s: str | None) -> datetime:
    """Parse user input: None -> now; "YYYY-MM-DD" -> that day's 16:00 close; else ISO in New York time."""
    if not s:
        return datetime.now(UTC)
    try:
        if len(s) == 10:
            return datetime.combine(date.fromisoformat(s), time(16, 0), NY)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=NY)
    except ValueError as e:
        raise ArgusError("INVALID_ARG", f"Bad date '{s}'.",
                         hint="Use YYYY-MM-DD or YYYY-MM-DDTHH:MM (New York time).") from e


def sessions_between(start: date, end: date) -> list[date]:
    """Trading days in [start, end], ascending."""
    return [ts.date() for ts in _cal().sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))]
