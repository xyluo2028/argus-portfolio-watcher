"""Import an Investing.com "Holdings" CSV export.

Only the per-lot fields are read (see docs/design.html section 12a). The summary
section and the totals rows are used purely as reconciliation checks.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from argus.errors import ArgusError
from argus.market_calendar import NY
from argus.models import TxnType
from argus.services.portfolio import TxnInput
from argus.symbols import normalize_symbol

LOTS_SECTION = "Open Positions"
SUMMARY_SECTION = "Open Positions Summary"
COST_TOLERANCE = 0.05  # dollars; Investing.com rounds its totals
AVG_TOLERANCE = 0.01
FILENAME_RE = re.compile(r"^(?P<name>.+?)_Holdings_\d{8}$", re.IGNORECASE)


@dataclass
class ParsedLot:
    row: int
    raw_symbol: str
    symbol: str
    name: str | None
    exchange: str | None
    open_date: date
    side: str
    qty: float
    price: float
    commission: float


@dataclass
class ParsedExport:
    portfolio_name: str | None
    lots: list[ParsedLot]
    summary: dict[str, tuple[float, float]] = field(default_factory=dict)  # symbol -> (amount, avg price)
    totals: dict[str, float] = field(default_factory=dict)  # market_value, open_pl


def _money(s: str) -> float:
    s = s.strip()
    if s in ("", "-", "--"):
        raise ValueError("empty number")
    return float(s.replace("$", "").replace(",", ""))


def _section(rows: list[list[str]], title: str) -> tuple[int, list[dict]] | None:
    for i, r in enumerate(rows):
        if len(r) >= 1 and r[0].strip() == title and not any(c.strip() for c in r[1:]):
            header = rows[i + 1]
            out = []
            for j in range(i + 2, len(rows)):
                if not rows[j] or not any(c.strip() for c in rows[j]):
                    break
                out.append((j + 1, dict(zip(header, rows[j]))))
            return i, out
    return None


def parse_investing_csv(path: Path) -> ParsedExport:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as e:
        raise ArgusError("NOT_FOUND", f"No such file: {path}") from e
    rows = list(csv.reader(text.splitlines()))

    lots_sec = _section(rows, LOTS_SECTION)
    if lots_sec is None:
        raise ArgusError("BAD_FORMAT", f"'{LOTS_SECTION}' section not found.",
                         hint="Export from Investing.com > Portfolio > Holdings > Export (CSV).")
    lots = []
    for line, r in lots_sec[1]:
        try:
            lots.append(ParsedLot(
                row=line,
                raw_symbol=r["Symbol"],
                symbol=normalize_symbol(r["Symbol"]),
                name=(r.get("Name") or "").strip() or None,
                exchange=(r.get("Exchange") or "").strip() or None,
                open_date=datetime.strptime(r["Open Date"].strip(), "%m/%d/%Y").date(),
                side=r["Type"].strip().upper(),
                qty=_money(r["Amount"]),
                price=_money(r["Open Price"]),
                commission=_money(r.get("Commission") or "0"),
            ))
        except (KeyError, ValueError) as e:
            raise ArgusError("BAD_FORMAT", f"Line {line}: can't read lot ({e}).") from e

    summary = {}
    sum_sec = _section(rows, SUMMARY_SECTION)
    if sum_sec:
        for _, r in sum_sec[1]:
            try:
                summary[normalize_symbol(r["Symbol"])] = (_money(r["Amount"]), _money(r["Avg Price"]))
            except (KeyError, ValueError):
                continue

    totals = {}
    for r in rows:
        if len(r) >= 2 and r[0].strip() in ("Market Value", "Open P/L"):
            try:
                totals[r[0].strip()] = _money(r[1].split("/")[0])
            except ValueError:
                pass

    m = FILENAME_RE.match(path.stem)
    return ParsedExport(m.group("name") if m else None, lots, summary, totals)


def reconcile(parsed: ParsedExport) -> list[dict]:
    checks = []
    agg: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for lot in parsed.lots:
        agg[lot.symbol][0] += lot.qty
        agg[lot.symbol][1] += lot.qty * lot.price

    non_long = [f"line {l.row} {l.raw_symbol} ({l.side})" for l in parsed.lots if l.side != "BUY"]
    checks.append({"check": "long_only", "ok": not non_long,
                   "detail": "all lots are BUY" if not non_long else f"not supported: {', '.join(non_long)}"})

    if parsed.summary:
        bad = []
        for sym, (amount, avg) in parsed.summary.items():
            q, cost = agg.get(sym, (0.0, 0.0))
            if abs(q - amount) > 1e-6 or (q and abs(cost / q - avg) > AVG_TOLERANCE):
                bad.append(sym)
        extra = sorted(set(agg) - set(parsed.summary))
        ok = not bad and not extra
        checks.append({"check": "lots_match_summary", "ok": ok,
                       "detail": f"{len(parsed.summary)} symbols: shares and average price match" if ok
                       else f"mismatch: {', '.join(bad + extra)}"})

    if "Market Value" in parsed.totals and "Open P/L" in parsed.totals:
        expected = parsed.totals["Market Value"] - parsed.totals["Open P/L"]
        cost = sum(lot.qty * lot.price for lot in parsed.lots)
        diff = cost - expected
        checks.append({"check": "total_cost", "ok": abs(diff) <= COST_TOLERANCE,
                       "detail": f"lot cost {cost:,.2f} vs export {expected:,.2f} (diff {diff:+.2f})"})
    return checks


def plan_transactions(parsed: ParsedExport, opening_through: date | None) -> list[TxnInput]:
    """Turn lots into transactions with stable idempotency keys."""
    seen: Counter[str] = Counter()
    out = []
    for lot in parsed.lots:
        kind = TxnType.OPENING if opening_through and lot.open_date <= opening_through else TxnType.BUY
        base = f"investing:{lot.symbol}:{lot.open_date.isoformat()}:{lot.qty:g}:{lot.price:g}"
        seen[base] += 1
        # Two identical lots on the same day are legitimate; number them.
        ext = base if seen[base] == 1 else f"{base}:{seen[base]}"
        out.append(TxnInput(
            type=kind.value,
            symbol=lot.symbol,
            ts=datetime.combine(lot.open_date, time(16, 0), NY),
            qty=lot.qty,
            price=lot.price,
            fee=lot.commission,
            note=f"Imported from Investing.com ({lot.raw_symbol})",
            external_id=ext,
        ))
    return out
