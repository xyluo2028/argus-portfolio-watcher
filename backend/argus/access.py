"""Which account a call acts as, and so whose records it sees.

Portfolios (with their trades, targets and history), watchlists, alerts, notes, peer lists and saved
DCF models belong to one account; market data is shared. Every query of an owned table is filtered
by the account the current call acts as, held in a context variable:
- the web server and HTTP MCP set it per request from whoever signed in (argus.api.auth);
- the CLI and stdio MCP act as DEFAULT, the oldest account (`argus --as <user>` picks another). They
  open the database file directly, so they could read everything anyway;
- background work (the live hub's alerts, event refreshes and cache warming) runs as SYSTEM, which
  sees every account's records but can't create any.
Unset means a code path nobody gave an account: it fails rather than guess.

Account id 0 owns what was recorded before any account existed; the first account takes it over.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeVar

from sqlalchemy import func, select, true

SYSTEM = "system"
DEFAULT = "default"
NOBODY = 0  # owner of records made while no account existed

_current: ContextVar[int | str] = ContextVar("argus_account")
T = TypeVar("T")


def current() -> int | str:
    try:
        return _current.get()
    except LookupError:
        raise RuntimeError("No account for this call: wrap it in argus.access.acting_as(...)") from None


def enter(who: int | str | None) -> None:
    """Act as `who` from here on in this context (the CLI's process, a test). None means NOBODY."""
    _current.set(NOBODY if who is None else who)


@contextmanager
def acting_as(who: int | str | None) -> Iterator[None]:
    token = _current.set(NOBODY if who is None else who)
    try:
        yield
    finally:
        _current.reset(token)


def as_(who: int | str | None, fn: Callable[..., T]) -> Callable[..., T]:
    """`fn` run as `who`; for threads, which don't inherit the caller's context."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with acting_as(who):
            return fn(*args, **kwargs)
    return wrapper


def account_id(s) -> int | str:
    """The account id this call acts as (DEFAULT resolved with session `s`), or SYSTEM."""
    who = current()
    if who == DEFAULT:
        from argus.models import Account

        return s.scalar(select(func.min(Account.id))) or NOBODY
    return who


def owned(s, column):
    """Where-clause: rows of `column`'s table that belong to this call's account (all, for SYSTEM)."""
    who = account_id(s)
    return true() if who == SYSTEM else column == who


def owner(s) -> int:
    """The account that new records made by this call belong to."""
    who = account_id(s)
    if who == SYSTEM:
        raise RuntimeError("Background work can't create per-account records.")
    return who


def is_mine(s, owner_id: int) -> bool:
    who = account_id(s)
    return who == SYSTEM or owner_id == who
