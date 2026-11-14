"""Stock splits: telling split bases apart, and finding held positions whose split isn't recorded.

Yahoo adjusts a symbol's whole price history when it splits, but only the bars Argus downloads
after that carry the new basis; a SPLIT transaction is how the ledger learns the share count changed.
Pure functions over plain values (no database), like lots.py.
"""

from __future__ import annotations

import math
from datetime import date
from fractions import Fraction
from typing import Iterable

from argus.market_calendar import NY, trade_session
from argus.models import TxnType
from argus.services.lots import TxnLike, build_positions

# Two closes for the same session this far apart are on different split bases: data corrections
# are cents, and the smallest common split (3:2) is a 50% gap.
SPLIT_GAP = 1.25
# A SPLIT transaction within this many days of the split date records it (brokers date it loosely).
MATCH_DAYS = 7


def rebased(stored: float, fresh: float) -> bool:
    """True when two prices for the same session differ by a split-like factor."""
    if not stored or not fresh or stored <= 0 or fresh <= 0:
        return False
    return abs(math.log(stored / fresh)) >= math.log(SPLIT_GAP)


def clean_ratio(r: float) -> float:
    """4.03 -> 4, 0.0998 -> 0.1, 1.49 -> 1.5: the split a price ratio most likely is."""
    f = Fraction(r).limit_denominator(10) if r >= 1 else 1 / Fraction(1 / r).limit_denominator(10)
    return round(float(f), 6)


def ratio_label(r: float) -> str:
    """4 -> "4:1", 0.1 -> "1:10", 1.5 -> "3:2"."""
    f = Fraction(r).limit_denominator(100)
    return f"{f.numerator}:{f.denominator}"


def unrecorded(txns: Iterable[TxnLike], splits: dict[str, list[tuple[date, float]]],
               portfolio: str, possible: dict[str, tuple[date, float]] | None = None) -> list[dict]:
    """Splits of held symbols that one portfolio's ledger doesn't record.

    `splits`: symbol -> [(split date, ratio)] as Yahoo reports them. `possible`: symbol -> (session,
    ratio) where the quote's previous close disagrees with the stored close by a split-like factor
    and Yahoo hasn't reported the split yet. A split counts when shares were held going into its
    date and no SPLIT transaction for that symbol is dated within MATCH_DAYS of it; the position is
    then valued at post-split prices with the pre-split share count. Nothing is written: the caller
    shows how to record it."""
    by_sym: dict[str, list[TxnLike]] = {}
    for t in txns:
        by_sym.setdefault(t.symbol, []).append(t)
    out = []
    for sym, rows in sorted(by_sym.items()):
        current = build_positions(rows).get(sym)
        if current is None or not current.is_open:
            continue
        recorded = [t.ts.astimezone(NY).date() for t in rows if t.type == TxnType.SPLIT]
        events = [(d, r, "yahoo") for d, r in splits.get(sym, [])]
        if possible and sym in possible and not any(abs((possible[sym][0] - d).days) <= MATCH_DAYS for d, _, _ in events):
            events.append((*possible[sym], "quote"))
        for d, ratio, source in sorted(events):
            if any(abs((d - r).days) <= MATCH_DAYS for r in recorded):
                continue
            before = build_positions([t for t in rows if trade_session(t.ts) < d]).get(sym)
            if before is None or not before.is_open:
                continue
            label = ratio_label(ratio)
            record = f"argus txn add {portfolio} SPLIT {sym} --qty {ratio:g} --date {d.isoformat()}T09:30"
            if source == "yahoo":
                message = (f"{sym} split {label} on {d.isoformat()}, but no SPLIT transaction records it: "
                           f"the {before.qty:g} shares held then are valued at post-split prices.")
            else:
                message = (f"{sym}'s previous close is {label} off the stored one on {d.isoformat()}: probably "
                           f"a {label} split Yahoo hasn't reported yet. Check it before recording a SPLIT.")
            out.append({"symbol": sym, "portfolio": portfolio, "date": d.isoformat(), "ratio": ratio,
                        "label": label, "source": source, "qty_before": before.qty,
                        "qty_after": round(before.qty * ratio, 6), "message": message,
                        "record": record, "hint": f"Record a SPLIT transaction with qty {ratio:g} (new shares "
                                                  f"per old) dated {d.isoformat()}: `{record}`"})
    return out


def unadjusted(series: dict[date, float], d: date, ratio: float) -> bool:
    """True when `series` (closes by date) still jumps by about `ratio` across `d`: the stored closes
    before the split are on the old basis (Yahoo hadn't adjusted them when they were downloaded)."""
    if not rebased(ratio, 1.0):
        return False
    before = [x for x in series if x < d]
    after = [x for x in series if x >= d]
    if not before or not after:
        return False
    jump = series[max(before)] / series[min(after)] if series[min(after)] else 0
    return jump > 0 and not rebased(jump, ratio)
