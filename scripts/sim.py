"""The trader bot's paper account (docs/loop/README.md): $10,000 of play money, filled at the last
session's mid price.

Argus records trades and tracks positions, not cash, and it accepts any price and date. A simulation
needs both pinned down, so every order goes through here:
- cash = the starting $10,000 - buys + sells + recorded dividends - fees, from the portfolio's own
  transactions in Argus (nothing is stored here), and a buy that would overdraw it is refused;
- an order fills at the middle of the last completed session's range, (high + low) / 2, dated that
  session: a stock that traded 100 to 110 fills at 105, a price it really traded through. It is
  refused while the regular session is open (the range isn't final yet);
- one trading round per session: once `report` has recorded a session, further orders for it are
  refused. On a day off (weekend, holiday: no new session since the last round) the bot can't
  trade, and reviews its portfolio and Argus instead;
- positions are valued at the session's close.

It talks to the running Argus as the bot's account, with the API key scripts/cloud-session.sh puts in
data/bot0.key. Standard library only.

    python scripts/sim.py status                    # cash, positions, value, return; `day_off` says whether it can trade
    python scripts/sim.py price NVDA                # the fill price an order would get: high, low, mid, close
    python scripts/sim.py buy NVDA --amount 1500 --note "why"
    python scripts/sim.py buy VOO --qty 2 --note "why"
    python scripts/sim.py sell NVDA --all --note "why"       # or --qty 1.5
    python scripts/sim.py report                    # rewrite docs/loop/sim/status.md, append equity.csv
    python scripts/sim.py save                      # the account's records -> docs/loop/sim/bot0.json
    python scripts/sim.py load                      # ...and back into an empty account (a fresh session)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("ARGUS_URL", f"http://127.0.0.1:{os.environ.get('ARGUS_PORT') or 8787}")
KEY_FILE = ROOT / "data" / "bot0.key"
PORTFOLIO = "bot0-sim"
BENCHMARK = "SPY"
START_CASH = 10_000.0
SIM = ROOT / "docs" / "loop" / "sim"
EQUITY_CSV, STATUS_MD, RECORDS = SIM / "equity.csv", SIM / "status.md", SIM / "bot0.json"
CSV_FIELDS = ["session", "equity", "cash", "invested", "return_pct", "spy_close", "spy_return_pct"]


class SimError(Exception):
    pass


def api(method: str, path: str, body: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if KEY_FILE.exists():
        headers["Authorization"] = f"Bearer {KEY_FILE.read_text().strip()}"
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read()).get("error", {})
        except ValueError:
            err = {}
        raise SimError(f"{err.get('code', e.code)}: {err.get('message', e.reason)}"
                       + (f" (hint: {err['hint']})" if err.get("hint") else "")) from e
    except urllib.error.URLError as e:
        raise SimError(f"Argus isn't reachable at {BASE}: {e.reason}") from e


def ensure_portfolio() -> None:
    if not any(p["name"] == PORTFOLIO and not p.get("shared") for p in api("GET", "/api/portfolios")):
        api("POST", "/api/portfolios", {"name": PORTFOLIO, "benchmark": BENCHMARK})


def cash_from(txns: list[dict]) -> float:
    cash = START_CASH
    for t in txns:
        if t["type"] == "BUY":
            cash -= t["qty"] * t["price"] + t["fee"]
        elif t["type"] == "SELL":
            cash += t["qty"] * t["price"] - t["fee"]
        elif t["type"] == "DIVIDEND":
            cash += t["amount"]
        elif t["type"] == "FEE":
            cash -= t["amount"]
    return cash


def prices(symbol: str, session: str) -> dict:
    """`symbol`'s range and close for `session` (the last completed one), from Argus: the quote, or the
    daily bar when the quote has no range. `mid` is where an order fills."""
    got = api("GET", "/api/quotes?symbols=" + urllib.parse.quote(symbol))
    sym = symbol.upper().replace("-", ".")
    q = {x["symbol"]: x for x in got["quotes"]}.get(sym)
    if q is None:
        raise SimError(f"No quote for {symbol}: {got['errors'].get(symbol.upper(), 'unknown symbol')}")
    if q["session_date"] != session:
        raise SimError(f"{symbol}'s quote is for {q['session_date']}, not the last session {session}: "
                       "its prices aren't in yet. Try again later, or report it if it stays that way.")
    high, low, source = q.get("high"), q.get("low"), "quote"
    if not high or not low:
        bars = api("GET", f"/api/history/{urllib.parse.quote(sym)}?period=5d")["bars"]
        bar = next((b for b in reversed(bars) if b["ts"][:10] == session), None)
        if bar is None:
            raise SimError(f"Argus has no high and low for {symbol} on {session} (neither the quote nor the "
                           "daily history), so there is no mid price to fill at.")
        high, low, source = bar["h"], bar["l"], "history"
    if not low <= q["price"] * 1.001 or not q["price"] <= high * 1.001:
        raise SimError(f"{symbol}'s close {q['price']} is outside its {session} range {low} to {high}: "
                       "the figures disagree, so no fill. Report this as a bug.")
    return {"symbol": sym, "session": session, "high": high, "low": low, "mid": round((high + low) / 2, 4),
            "close": q["price"], "range_from": source}


def last_recorded_session() -> str | None:
    if not EQUITY_CSV.exists():
        return None
    rows = list(csv.DictReader(EQUITY_CSV.open()))
    return max((r["session"] for r in rows), default=None)


def state() -> dict:
    ensure_portfolio()
    market = api("GET", "/api/market-status")
    session = market["last_session"]
    txns = api("GET", f"/api/portfolios/{PORTFOLIO}/transactions")
    summary = api("GET", f"/api/portfolios/{PORTFOLIO}")
    cash = cash_from(txns)
    positions = [{"symbol": p["symbol"], "qty": p["qty"], "avg_cost": p["avg_cost"], "price": p.get("price"),
                  "value": p.get("market_value"), "unrealized_pnl": p.get("unrealized_pnl"),
                  "unrealized_pct": p.get("unrealized_pct")} for p in summary["positions"]]
    unpriced = [p["symbol"] for p in positions if p["value"] is None]
    invested = sum(p["value"] or 0.0 for p in positions)
    accrued = summary["totals"].get("dividends_accrued") or 0.0  # ex-dates held through, not yet recorded
    equity = cash + invested + accrued
    start = min((t["ts"][:10] for t in txns), default=None)
    # A session `report` has already recorded was traded in an earlier round: nothing new to trade on.
    day_off = last_recorded_session() == session
    return {"portfolio": PORTFOLIO, "session": session, "market_session": market["session"], "day_off": day_off,
            "can_trade": not day_off and market["session"] != "regular",
            "start_cash": START_CASH, "started": start, "cash": round(cash, 2), "invested": round(invested, 2),
            "dividends_accrued": round(accrued, 2), "equity": round(equity, 2),
            "return_pct": round((equity / START_CASH - 1) * 100, 2), "unpriced": unpriced,
            "realized_pnl": round(summary["totals"].get("realized_pnl") or 0.0, 2),
            "positions": positions, "trades": len([t for t in txns if t["type"] in ("BUY", "SELL")]),
            "trades_this_session": [t for t in txns if t["ts"][:10] == session and t["type"] in ("BUY", "SELL")]}


def order(side: str, args) -> dict:
    s = state()
    if s["market_session"] == "regular":
        raise SimError("The regular session is open, so today's range isn't final. Orders fill at the "
                       "session's mid price: run this after 16:00 New York time.")
    if s["day_off"]:
        raise SimError(f"Day off: the last session ({s['session']}) was already traded and recorded, and "
                       "there has been none since. No trades today; review the portfolio and Argus instead.")
    symbol = args.symbol.upper()
    px = prices(symbol, s["session"])
    price = px["mid"]
    held = next((p["qty"] for p in s["positions"] if p["symbol"] == symbol.replace("-", ".")), 0.0)
    if side == "SELL" and args.all:
        qty = held
    elif args.qty is not None:
        qty = args.qty
    elif args.amount is not None:
        qty = math.floor(args.amount / price * 10_000) / 10_000  # fractional shares, to 4 places
    else:
        raise SimError("Give --qty or --amount" + (" or --all." if side == "SELL" else "."))
    if qty <= 0:
        raise SimError("Nothing to trade: the quantity comes to zero.")
    cost = qty * price
    if side == "BUY" and cost > s["cash"] + 0.005:
        raise SimError(f"Not enough cash: {qty:g} {symbol} at {price:,.2f} costs {cost:,.2f}, cash is {s['cash']:,.2f}.")
    body = {"type": side, "symbol": symbol, "qty": qty, "price": price, "date": s["session"], "note": args.note,
            "idempotency_key": f"sim-{s['session']}-{side}-{symbol}-{qty:g}", "dry_run": args.dry_run}
    result = api("POST", f"/api/portfolios/{PORTFOLIO}/transactions", body)  # Argus refuses an oversell
    after = s["cash"] + (cost if side == "SELL" else -cost)
    return {"filled": not args.dry_run and bool(result["inserted_ids"]), "dry_run": args.dry_run,
            "already_recorded": bool(result["skipped_existing"]), "side": side, "symbol": symbol, "qty": qty,
            "price": price, "session_high": px["high"], "session_low": px["low"], "session_close": px["close"],
            "session": s["session"], "amount": round(cost, 2),
            "cash_before": s["cash"], "cash_after": round(after, 2)}


def report() -> dict:
    s = state()
    SIM.mkdir(parents=True, exist_ok=True)
    spy = prices(BENCHMARK, s["session"])["close"]
    rows = list(csv.DictReader(EQUITY_CSV.open())) if EQUITY_CSV.exists() else []
    rows = [r for r in rows if r["session"] != s["session"]]  # one row per session; a rerun replaces it
    base = float(rows[0]["spy_close"]) if rows else spy
    rows.append({"session": s["session"], "equity": f"{s['equity']:.2f}", "cash": f"{s['cash']:.2f}",
                 "invested": f"{s['invested']:.2f}", "return_pct": f"{s['return_pct']:.2f}",
                 "spy_close": f"{spy:.2f}", "spy_return_pct": f"{(spy / base - 1) * 100:.2f}"})
    rows.sort(key=lambda r: r["session"])
    with EQUITY_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)

    last = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None
    day = float(last["equity"]) - float(prev["equity"]) if prev else None
    money = lambda v: f"${v:,.2f}"  # noqa: E731
    signed = lambda v: f"{'+' if v >= 0 else '−'}${abs(v):,.2f}"  # noqa: E731
    pct = lambda v: f"{v:+.2f}%"  # noqa: E731
    out = [
        "# Trader bot: paper account",
        "",
        f"Play money, started with {money(START_CASH)}. Orders fill at the middle of the last US session's range, "
        "(high + low) / 2; positions are valued at its close. No trades on days without a new session. "
        "Rewritten by `scripts/sim.py report` at the end of every round; the history is in `equity.csv`.",
        "",
        f"**As of the {s['session']} close**",
        "",
        "| | |",
        "|---|---|",
        f"| Account value | **{money(s['equity'])}** ({pct(s['return_pct'])} since the start) |",
        f"| SPY over the same sessions | {pct(float(last['spy_return_pct']))} |",
        f"| Change since the previous session | {signed(day) if day is not None else 'first session'} |",
        f"| Cash | {money(s['cash'])} |",
        f"| Invested (market value) | {money(s['invested'])} |",
        f"| Realized P&L | {signed(s['realized_pnl'])} |",
        f"| Dividends accrued, not yet recorded | {money(s['dividends_accrued'])} |",
        f"| Trades so far | {s['trades']} |",
        "",
    ]
    if s["unpriced"]:
        out += [f"**No price for {', '.join(s['unpriced'])}**, so the account value above leaves them out.", ""]
    out += ["## Positions", ""]
    if s["positions"]:
        out += ["| Symbol | Shares | Avg cost | Close | Value | Weight | Unrealized |", "|---|---:|---:|---:|---:|---:|---:|"]
        for p in sorted(s["positions"], key=lambda p: -(p["value"] or 0)):
            priced = p["value"] is not None
            out.append(f"| {p['symbol']} | {p['qty']:g} | {p['avg_cost']:,.2f} | "
                       + (f"{p['price']:,.2f} | {money(p['value'])} | {p['value'] / s['equity'] * 100:.1f}% | "
                          f"{signed(p['unrealized_pnl'])} ({pct(p['unrealized_pct'])}) |" if priced else "– | – | – | – |"))
        out.append(f"| Cash | | | | {money(s['cash'])} | {s['cash'] / s['equity'] * 100:.1f}% | |")
    else:
        out.append("None: all cash.")
    out += ["", f"## Trades for the {s['session']} session", ""]
    if s["trades_this_session"]:
        out += ["| Side | Symbol | Shares | Mid price | Amount | Why |", "|---|---|---:|---:|---:|---|"]
        out += [f"| {t['type']} | {t['symbol']} | {t['qty']:g} | {t['price']:,.2f} | {money(t['qty'] * t['price'])} | "
                f"{(t.get('note') or '').replace('|', '/')} |" for t in s["trades_this_session"]]
    else:
        out.append("None.")
    out += ["", "## Last 30 sessions", "", "| Session | Account value | Return | SPY | Cash |", "|---|---:|---:|---:|---:|"]
    out += [f"| {r['session']} | {money(float(r['equity']))} | {pct(float(r['return_pct']))} | "
            f"{pct(float(r['spy_return_pct']))} | {money(float(r['cash']))} |" for r in reversed(rows[-30:])]
    out += ["", "To look at this account in your own Argus: sign in as the bot's account there, open **Data**, "
            "and restore `docs/loop/sim/bot0.json` (it replaces only that account's records).", ""]
    STATUS_MD.write_text("\n".join(out))
    return {"status_file": str(STATUS_MD.relative_to(ROOT)), "equity_file": str(EQUITY_CSV.relative_to(ROOT)),
            "session": s["session"], "equity": s["equity"], "return_pct": s["return_pct"],
            "spy_return_pct": float(last["spy_return_pct"]), "sessions": len(rows)}


def save() -> dict:
    """The account's own records (no accounts, keys or other accounts' data: safe in a public repository)."""
    doc = api("GET", "/api/snapshot")
    SIM.mkdir(parents=True, exist_ok=True)
    RECORDS.write_text(json.dumps(doc, indent=1) + "\n")
    return {"file": str(RECORDS.relative_to(ROOT)), "counts": {t: len(v) for t, v in doc["tables"].items() if v}}


def load() -> dict:
    if not RECORDS.exists():
        return {"loaded": False, "reason": f"no {RECORDS.relative_to(ROOT)} yet: the account starts empty"}
    r = api("POST", "/api/snapshot/restore?dry_run=false", json.loads(RECORDS.read_text()))
    return {"loaded": True, "counts": {t: n for t, n in r["counts"].items() if n}}


def main() -> None:
    p = argparse.ArgumentParser(description="The trader bot's $10,000 paper account in Argus.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Cash, positions, account value and return")
    sub.add_parser("report", help="Rewrite docs/loop/sim/status.md and add this session to equity.csv")
    sub.add_parser("save", help="Write the account's records to docs/loop/sim/bot0.json")
    sub.add_parser("load", help="Load docs/loop/sim/bot0.json into the (empty) account")
    sub.add_parser("price", help="A symbol's last-session high, low, mid (the fill price) and close").add_argument("symbol")
    for side in ("buy", "sell"):
        o = sub.add_parser(side, help=f"{side.title()} at the last session's mid price, (high + low) / 2")
        o.add_argument("symbol")
        o.add_argument("--qty", type=float, help="Shares (fractions allowed)")
        o.add_argument("--amount", type=float, help="Dollars; the share count is worked out from the mid price")
        if side == "sell":
            o.add_argument("--all", action="store_true", help="The whole position")
        o.add_argument("--note", help="Why: one line, kept on the transaction and shown in the status page")
        o.add_argument("--dry-run", action="store_true", help="Check and preview; record nothing")
    args = p.parse_args()
    try:
        simple = {"status": state, "report": report, "save": save, "load": load}
        if args.cmd == "price":
            out = prices(args.symbol, api("GET", "/api/market-status")["last_session"])
        else:
            out = simple[args.cmd]() if args.cmd in simple else order(args.cmd.upper(), args)
    except SimError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
    print(json.dumps({"ok": True, "data": out}, default=str))


if __name__ == "__main__":
    main()
