"""Ticker normalization."""

from __future__ import annotations

import re

# Reuters (RIC) exchange suffixes used by Investing.com exports: NVDA.O, UBER.K, ...
# ".A"/".P" are omitted on purpose: they collide with share classes like BF.A.
_RIC_SUFFIXES = {"O", "OQ", "N", "K"}
_VALID = re.compile(r"^[A-Z][A-Z0-9]{0,5}(\.[A-Z]{1,2})?$")


def normalize_symbol(raw: str) -> str:
    """Upper-case, trim, and strip a RIC exchange suffix.

    The canonical form keeps share classes with a dot ("BRK.B"), as Finnhub does;
    the Yahoo adapter converts to its dash form itself.
    """
    s = raw.strip().upper().replace("-", ".")
    if "." in s:
        base, suffix = s.rsplit(".", 1)
        if suffix in _RIC_SUFFIXES:
            s = base
    return s


def to_yahoo(symbol: str) -> str:
    return symbol.replace(".", "-")


def is_plausible_symbol(s: str) -> bool:
    return bool(_VALID.match(s))
