from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from argus.market_calendar import market_status, session_date
from argus.symbols import is_plausible_symbol, normalize_symbol, to_yahoo

NY = ZoneInfo("America/New_York")


@pytest.mark.parametrize("raw,expected", [
    ("NVDA.O", "NVDA"), ("UBER.K", "UBER"), ("be", "BE"), (" msft.oq ", "MSFT"), ("IBM.N", "IBM"),
    ("BRK.B", "BRK.B"), ("BRK-B", "BRK.B"), ("BF.A", "BF.A"),
])
def test_normalize_symbol(raw, expected):
    assert normalize_symbol(raw) == expected


def test_yahoo_form_and_plausibility():
    assert to_yahoo("BRK.B") == "BRK-B"
    assert is_plausible_symbol("GOOGL") and is_plausible_symbol("BRK.B")
    assert not is_plausible_symbol("") and not is_plausible_symbol("TOO-LONG-SYMBOL")


def ny(*args):
    return datetime(*args, tzinfo=NY)


@pytest.mark.parametrize("when,session", [
    (ny(2026, 9, 25, 3, 0), "closed"),     # before pre-market
    (ny(2026, 9, 25, 8, 0), "pre"),
    (ny(2026, 9, 25, 10, 0), "regular"),
    (ny(2026, 9, 25, 17, 0), "post"),
    (ny(2026, 9, 25, 21, 0), "closed"),
    (ny(2026, 9, 27, 12, 0), "closed"),    # Sunday
    (ny(2026, 12, 25, 12, 0), "closed"),   # Christmas
])
def test_sessions(when, session):
    assert market_status(when)["session"] == session


def test_weekend_points_to_friday_close_and_monday_open():
    st = market_status(ny(2026, 9, 27, 12, 0))
    assert st["last_session"] == "2026-09-25"
    assert datetime.fromisoformat(st["next_open"]).astimezone(NY) == ny(2026, 9, 28, 9, 30)


def test_day_after_thanksgiving_is_half_day():
    st = market_status(ny(2026, 11, 27, 12, 0))
    assert st["is_half_day"] and st["session"] == "regular"
    assert market_status(ny(2026, 11, 27, 13, 30))["session"] == "post"


def test_session_date_maps_off_hours_to_last_session():
    assert session_date(ny(2026, 9, 27, 12, 0)) == date(2026, 9, 25)   # Sunday -> Friday
    assert session_date(ny(2026, 9, 28, 2, 0)) == date(2026, 9, 25)    # Monday 2am -> Friday
    assert session_date(ny(2026, 9, 28, 11, 0)) == date(2026, 9, 28)   # Monday session
