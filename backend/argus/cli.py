"""`argus` command line. Human tables by default; `--json` gives a stable envelope for agents:

    {"ok": true, "data": ...}   or   {"ok": false, "error": {"code", "message", "hint"}}
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Callable

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from argus.errors import ArgusError
from argus.market_calendar import NY, parse_ny_datetime
from argus.symbols import normalize_symbol

app = typer.Typer(help="Argus: portfolio monitor for US stocks & ETFs.", no_args_is_help=True,
                  pretty_exceptions_enable=False)
portfolio_app = typer.Typer(help="Create, list and show portfolios.", no_args_is_help=True)
txn_app = typer.Typer(help="Record and inspect transactions.", no_args_is_help=True)
import_app = typer.Typer(help="Import holdings from other tools.", no_args_is_help=True)
alert_app = typer.Typer(help="Price, move, valuation, cost and earnings alerts.", no_args_is_help=True)
note_app = typer.Typer(help="Thesis and notes per symbol, with review dates.", no_args_is_help=True)
app.add_typer(portfolio_app, name="portfolio")
app.add_typer(txn_app, name="txn")
app.add_typer(import_app, name="import")
app.add_typer(alert_app, name="alert")
app.add_typer(note_app, name="note")

console = Console()
JsonOpt = Annotated[bool, typer.Option("--json", help="Machine-readable JSON output.")]
DryRunOpt = Annotated[bool, typer.Option("--dry-run", help="Validate and preview; write nothing.")]


def _argus():
    from argus.app import Argus  # deferred: keeps `--help` fast

    return Argus()


def _run(as_json: bool, fn: Callable[[], dict | list], render: Callable[[dict | list], None] | None = None):
    try:
        data = fn()
    except ArgusError as e:
        if as_json:
            print(json.dumps({"ok": False, "error": e.to_dict()}))
        else:
            console.print(f"[red]Error ({e.code}):[/red] {e.message}")
            if e.hint:
                console.print(f"[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)
    if as_json:
        print(json.dumps({"ok": True, "data": data}, default=str))
    elif render:
        render(data)
    else:
        console.print_json(json.dumps(data, default=str))


# -- formatting helpers --------------------------------------------------------
def _money(v, signed=False) -> str:
    if v is None:
        return "-"
    return f"{v:+,.2f}" if signed else f"{v:,.2f}"


def _pct(v) -> str:
    return "-" if v is None else f"{v:+.2f}%"


def _color(v) -> str:
    if v is None:
        return "white"
    return "green" if v > 0 else "red" if v < 0 else "white"


def _cell(v, text: str) -> str:
    return f"[{_color(v)}]{text}[/{_color(v)}]"


@app.command()
def serve(port: Annotated[int | None, typer.Option(help="Default: ARGUS_PORT or 8787")] = None,
          host: str = "127.0.0.1"):
    """Run the web UI, JSON API and live price stream (http://localhost:8787)."""
    from argus.api.server import serve as run_server
    from argus.config import load_settings

    try:
        run_server(port or load_settings().port, host)
    except ArgusError as e:
        console.print(f"[red]Error ({e.code}):[/red] {e.message}")
        if e.hint:
            console.print(f"[dim]Hint: {e.hint}[/dim]")
        raise typer.Exit(1)


@app.command("mcp")
def mcp_cmd():
    """Run the MCP server over stdio (for Claude Desktop / Claude Code)."""
    from argus.mcp_server import run_stdio

    run_stdio()


# -- market ---------------------------------------------------------------------
@app.command("market-status")
def market_status_cmd(as_json: JsonOpt = False):
    """Current NYSE session (pre / regular / post / closed) and next open/close."""
    def render(d):
        console.print(f"Session: [bold]{d['session']}[/bold]  (trading day: {d['is_trading_day']}, "
                      f"half day: {d['is_half_day']})")
        console.print(f"Last close: {_ny(d['last_close'])}   Next open: {_ny(d['next_open'])}")
    _run(as_json, lambda: _argus().market_status(), render)


def _ny(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(NY).strftime("%a %b %d %H:%M ET")


@app.command()
def quotes(symbols: Annotated[list[str], typer.Argument(help="Tickers, e.g. NVDA MSFT")], as_json: JsonOpt = False):
    """Latest quotes (cached for 15s; settled closes are reused while the market is closed)."""
    def render(d):
        t = Table("Symbol", "Price", "Chg", "Chg %", "As of (ET)", "Source")
        for q in d["quotes"]:
            t.add_row(q["symbol"], _money(q["price"]), _cell(q["change"], _money(q["change"], True)),
                      _cell(q["change_pct"], _pct(q["change_pct"])), _ny(q["as_of"]), q["source"])
        console.print(t)
        for sym, err in d["errors"].items():
            console.print(f"[yellow]{sym}: {err}[/yellow]")
    _run(as_json, lambda: _argus().quotes(symbols), render)


@app.command()
def history(symbol: str, period: str = "1y", interval: str = "1d",
            indicators: Annotated[str | None, typer.Option(help="e.g. sma50,sma200,rsi14,macd,bb20")] = None,
            as_json: JsonOpt = False):
    """OHLCV bars (daily bars are cached locally)."""
    def render(d):
        bars = d["bars"]
        console.print(f"{d['symbol']} {d['period']} {d['interval']}: {len(bars)} bars")
        t = Table("Date", "Open", "High", "Low", "Close", "Volume")
        for b in bars[-10:]:
            t.add_row(b["ts"][:10], _money(b["o"]), _money(b["h"]), _money(b["l"]), _money(b["c"]), f"{b['v']:,.0f}")
        console.print(t)
    specs = [x for x in indicators.split(",") if x.strip()] if indicators else None
    _run(as_json, lambda: _argus().history(symbol, period, interval, specs), render)


@app.command()
def fundamentals(symbol: str,
                 fields: Annotated[str | None, typer.Option(help="Comma-separated subset, e.g. pe_ttm,pb")] = None,
                 refresh: Annotated[bool, typer.Option(help="Ignore the 24h cache.")] = False,
                 as_json: JsonOpt = False):
    """Valuation and profitability metrics (Finnhub first, Yahoo fills gaps)."""
    def render(d):
        t = Table("Metric", "Value", "Source", title=f"{d['symbol']} (as of {d['as_of'][:16]})")
        for k, v in d["metrics"].items():
            t.add_row(k, "-" if v is None else f"{v:,.4g}" if abs(v) < 1e6 else f"{v:,.0f}", d["sources"].get(k, ""))
        console.print(t)
    field_list = [f.strip() for f in fields.split(",")] if fields else None
    _run(as_json, lambda: _argus().market.get_fundamentals(normalize_symbol(symbol), field_list, refresh), render)


@app.command()
def financials(symbol: str, period: str = "quarterly", limit: int = 8, as_json: JsonOpt = False):
    """Reported financials from SEC EDGAR (revenue, margins, EPS, cash flow)."""
    def render(d):
        cols = ["revenue", "gross_margin_pct", "operating_margin_pct", "net_income", "eps_diluted", "free_cash_flow"]
        t = Table("Period end", *cols, title=f"{d.get('company')} ({d['period']}, {d['units'].get('revenue', '')})")
        for p in d["periods"]:
            t.add_row(p["period_end"], *[_fmt_big(p.get(c)) for c in cols])
        console.print(t)
    _run(as_json, lambda: _argus().market.get_financials(normalize_symbol(symbol), period, limit), render)


def _fmt_big(v) -> str:
    if v is None:
        return "-"
    if abs(v) >= 1e9:
        return f"{v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:,.1f}M"
    return f"{v:,.2f}"


@app.command()
def search(query: str, limit: int = 10, as_json: JsonOpt = False):
    """Find US symbols by ticker or name."""
    def render(rows):
        t = Table("Symbol", "Name", "Type")
        for r in rows:
            t.add_row(r["symbol"], r["name"] or "", r["type"] or "")
        console.print(t)
    _run(as_json, lambda: _argus().market.search(query, limit), render)


# -- portfolios -------------------------------------------------------------------
@portfolio_app.command("list")
def portfolio_list(as_json: JsonOpt = False):
    def render(rows):
        t = Table("ID", "Name", "Benchmark")
        for r in rows:
            t.add_row(str(r["id"]), r["name"], r["benchmark"])
        console.print(t)
    _run(as_json, lambda: _argus().portfolios.list_portfolios(), render)


@portfolio_app.command("create")
def portfolio_create(name: str, benchmark: str = "SPY", as_json: JsonOpt = False):
    _run(as_json, lambda: _argus().portfolios.create_portfolio(name, benchmark),
         lambda d: console.print(f"Created portfolio [bold]{d['name']}[/bold] (id {d['id']}, benchmark {d['benchmark']})"))


@portfolio_app.command("show")
def portfolio_show(ref: Annotated[str, typer.Argument(help="Portfolio name or id")],
                   no_quotes: Annotated[bool, typer.Option("--no-quotes", help="Skip market data.")] = False,
                   lots: Annotated[bool, typer.Option("--lots", help="Include open lots.")] = False,
                   as_json: JsonOpt = False):
    """Positions with live price, weight, day and unrealized P&L."""
    _run(as_json, lambda: _argus().portfolio(ref, with_quotes=not no_quotes, include_lots=lots), _render_portfolio)


def _short(v, signed=False) -> str:
    """Compact money: cents below 100, whole dollars above (fits 80 columns)."""
    if v is None:
        return "-"
    fmt = ("{:+,.2f}" if signed else "{:,.2f}") if abs(v) < 100 else ("{:+,.0f}" if signed else "{:,.0f}")
    return fmt.format(v)


def _short_pct(v) -> str:
    return "-" if v is None else f"{v:+.1f}%"


def _render_portfolio(d):
    tot, mkt = d["totals"], d["market"]
    t = Table(title=f"{d['portfolio']['name']}  ·  market {mkt['session']}", box=box.SIMPLE_HEAD,
              pad_edge=False, padding=(0, 1), collapse_padding=True)
    for name in ("Sym", "Qty", "Avg", "Price", "Day%", "Day$", "Value", "Wt", "P&L", "P&L%"):
        t.add_column(name, justify="left" if name == "Sym" else "right", no_wrap=True)
    for r in d["positions"]:
        t.add_row(r["symbol"], f"{r['qty']:g}", _short(r["avg_cost"]), _short(r.get("price")),
                  _cell(r.get("change_pct"), _short_pct(r.get("change_pct"))),
                  _cell(r.get("day_pnl"), _short(r.get("day_pnl"), True)), _short(r.get("market_value")),
                  "-" if r.get("weight_pct") is None else f"{r['weight_pct']:.1f}%",
                  _cell(r.get("unrealized_pnl"), _short(r.get("unrealized_pnl"), True)),
                  _cell(r.get("unrealized_pct"), _short_pct(r.get("unrealized_pct"))))
    console.print(t)
    console.print(f"Value [bold]{_money(tot['market_value'])}[/bold]  Cost {_money(tot['cost_basis'])}")
    console.print(f"Unrealized {_cell(tot['unrealized_pnl'], _money(tot['unrealized_pnl'], True))} "
                  f"({_pct(tot['unrealized_pct'])})  Day {_cell(tot['day_pnl'], _money(tot['day_pnl'], True))} "
                  f"({_pct(tot['day_pnl_pct'])})  Realized {_money(tot['realized_pnl'], True)}")
    if d.get("quote_errors"):
        console.print(f"[yellow]No quote for: {', '.join(d['quote_errors'])}[/yellow]")


@portfolio_app.command("performance")
def portfolio_performance(ref: str, range_: Annotated[str, typer.Option("--range", help="1mo | 3mo | ytd | 1y | all")] = "all",
                          as_json: JsonOpt = False):
    """Time-weighted return vs the benchmark, drawdown and volatility."""
    def render(d):
        s = d["summary"]
        if not s:
            console.print("No transactions yet.")
            return
        console.print(f"[bold]{d['portfolio']}[/bold] {s['start']} → {s['end']} ({s['sessions']} sessions)")
        console.print(f"Return (TWR) {_cell(s['twr_pct'], _pct(s['twr_pct']))}   {d['benchmark']} "
                      f"{_cell(s['benchmark_pct'], _pct(s['benchmark_pct']))}   Excess "
                      f"{_cell(s['excess_pct'], _pct(s['excess_pct']))}")
        vol = "-" if s["volatility_pct"] is None else f"{s['volatility_pct']:.1f}%"
        sharpe = "-" if s["sharpe"] is None else f"{s['sharpe']:.2f}"
        console.print(f"Max drawdown {_pct(s['max_drawdown_pct'])}   Volatility (ann.) {vol}   Sharpe (rf=0) {sharpe}")
    _run(as_json, lambda: _argus().performance(ref, range_), render)


@app.command()
def brief(portfolio: str, no_news: Annotated[bool, typer.Option("--no-news")] = False, as_json: JsonOpt = False):
    """Facts for a daily brief: movers, events, fired alerts, theses due (JSON is the useful form)."""
    def render(b):
        t = b["totals"]
        console.print(f"[bold]{b['portfolio']}[/bold] {_money(t['market_value'])}  day "
                      f"{_cell(t['day_pnl'], _money(t['day_pnl'], True))} ({_pct(t['day_pnl_pct'])})  "
                      f"{b['benchmark']['symbol']} {_pct(b['benchmark']['change_pct'])}")
        movers = ", ".join(f"{m['symbol']} {_pct(m['change_pct'])}" for m in b["top_gainers"][:3] + b["top_losers"][:3])
        console.print(f"Movers: {movers}")
        for e in b["earnings_upcoming"]:
            console.print(f"Earnings {e['date']} {e.get('hour') or ''} {e['symbol']}")
        for a in b["alerts_fired"]:
            console.print(f"[yellow]Alert[/yellow] {a['message']}")
        for n in b["theses_due"]:
            console.print(f"Review {n['symbol']} ({n['review_on']}): {n['text'][:80]}")
    _run(as_json, lambda: _argus().daily_brief(portfolio, news=not no_news), render)


@app.command()
def events(days: int = 14, as_json: JsonOpt = False):
    """Upcoming earnings and dividend dates for holdings and watchlist."""
    def render(d):
        t = Table("Date", "Symbol", "Event", "When", "EPS est.", "Held")
        for e in d["upcoming"]:
            t.add_row(e["date"], e["symbol"], e["kind"].replace("_", " "), e.get("hour") or "",
                      "-" if e.get("epsEstimate") is None else f"{e['epsEstimate']:.2f}", "yes" if e["held"] else "")
        console.print(t)
    _run(as_json, lambda: _argus().upcoming_events(days_ahead=days), render)


@alert_app.command("add")
def alert_add(symbol: str, kind: str, threshold: float, note: str | None = None, as_json: JsonOpt = False):
    """e.g. `argus alert add NVDA day_move_pct 5` or `argus alert add AMD below_cost_pct 15`."""
    _run(as_json, lambda: _argus().alerts.create(symbol, kind, threshold, note),
         lambda a: console.print(f"Alert {a['id']}: {a['symbol']} — {a['label']}"))


@alert_app.command("list")
def alert_list(all_: Annotated[bool, typer.Option("--all")] = False, as_json: JsonOpt = False):
    def render(rows):
        t = Table("ID", "Symbol", "Rule", "Last fired", "Note")
        for a in rows:
            t.add_row(str(a["id"]), a["symbol"], a["label"] + ("" if a["active"] else " (off)"),
                      (a.get("last_fired") or {}).get("session_date", ""), a["note"] or "")
        console.print(t)
    _run(as_json, lambda: _argus().alerts.list(all_), render)


@alert_app.command("off")
def alert_off(alert_id: int, as_json: JsonOpt = False):
    _run(as_json, lambda: _argus().alerts.set_active(alert_id, False), lambda a: console.print(f"Alert {a['id']} off"))


@note_app.command("add")
def note_add(symbol: str, text: str, thesis: Annotated[bool, typer.Option("--thesis")] = False,
             review_on: Annotated[str | None, typer.Option(help="YYYY-MM-DD")] = None, as_json: JsonOpt = False):
    _run(as_json, lambda: _argus().notes.add(symbol, text, "thesis" if thesis else "note",
                                             date.fromisoformat(review_on) if review_on else None),
         lambda n: console.print(f"Saved {n['kind']} {n['id']} on {n['symbol']}"))


@note_app.command("list")
def note_list(symbol: str | None = None, as_json: JsonOpt = False):
    def render(rows):
        for n in rows:
            console.print(f"[bold]{n['symbol']}[/bold] #{n['id']} {n['kind']}"
                          + (f" (review {n['review_on']})" if n["review_on"] else "") + f": {n['text']}")
    _run(as_json, lambda: _argus().notes.list(symbol), render)


# -- transactions -----------------------------------------------------------------
@txn_app.command("add")
def txn_add(portfolio: str,
            type: Annotated[str, typer.Argument(help="BUY | SELL | OPENING | DIVIDEND | SPLIT | FEE")],
            symbol: str,
            qty: Annotated[float, typer.Option(help="Shares (SPLIT: new shares per old share)")] = 0.0,
            price: Annotated[float, typer.Option(help="Per-share price")] = 0.0,
            fee: float = 0.0,
            amount: Annotated[float, typer.Option(help="Cash amount for DIVIDEND / FEE")] = 0.0,
            when: Annotated[str | None, typer.Option("--date", help="YYYY-MM-DD[THH:MM] New York time; default now")] = None,
            note: str | None = None,
            idempotency_key: Annotated[str | None, typer.Option("--id", help="Idempotency key; retries are no-ops")] = None,
            dry_run: DryRunOpt = False,
            as_json: JsonOpt = False):
    """Record a transaction. Positions are re-derived and checked (e.g. you can't sell more than you hold)."""
    from argus.services.portfolio import TxnInput

    def go():
        item = TxnInput(type=type, symbol=symbol, ts=parse_ny_datetime(when), qty=qty, price=price, fee=fee,
                        amount=amount, note=note, external_id=idempotency_key)
        return _argus().portfolios.add_transactions(portfolio, [item], source="cli", dry_run=dry_run)

    def render(d):
        for p in d["positions"]:
            b, a = p["before"], p["after"]
            console.print(f"{a['symbol']}: {b['qty']:g} → {a['qty']:g} sh, avg cost {_money(b['avg_cost'])} → "
                          f"{_money(a['avg_cost'])}, realized {_money(a['realized_pnl'], True)}")
        if d["skipped_existing"]:
            console.print("[yellow]Already recorded (same --id); nothing written.[/yellow]")
        elif d["dry_run"]:
            console.print("[cyan]Dry run: nothing written.[/cyan]")
        else:
            console.print(f"[green]Saved txn {', '.join(map(str, d['inserted_ids']))}[/green]")
    _run(as_json, go, render)


@txn_app.command("list")
def txn_list(portfolio: str, symbol: str | None = None,
             all_: Annotated[bool, typer.Option("--all", help="Include deleted")] = False, as_json: JsonOpt = False):
    def render(rows):
        t = Table("ID", "Date", "Type", "Symbol", "Qty", "Price", "Fee/Amt", "Source", "Note")
        for r in rows:
            style = "strike dim" if r["deleted"] else ""
            t.add_row(str(r["id"]), r["ts"][:10], r["type"], r["symbol"], f"{r['qty']:g}", _money(r["price"]),
                      _money(r["amount"] or r["fee"]), r["source"], r["note"] or "", style=style)
        console.print(t)
    _run(as_json, lambda: _argus().portfolios.list_transactions(portfolio, symbol, all_), render)


@txn_app.command("delete")
def txn_delete(txn_id: int, dry_run: DryRunOpt = False, as_json: JsonOpt = False):
    """Soft-delete a transaction (kept in the audit log)."""
    _run(as_json, lambda: _argus().portfolios.delete_transaction(txn_id, dry_run=dry_run),
         lambda d: console.print(("Would delete" if d["dry_run"] else "Deleted") + f" txn {d['deleted']['id']}"))


# -- import -------------------------------------------------------------------------
@import_app.command("investing")
def import_investing(file: Path,
                     portfolio: Annotated[str | None, typer.Option(help="Default: name from the file name")] = None,
                     opening_through: Annotated[str | None, typer.Option(
                         help="Lots dated on/before this YYYY-MM-DD are OPENING (owned before import)")] = None,
                     no_validate: Annotated[bool, typer.Option("--no-validate", help="Skip symbol checks (offline)")] = False,
                     dry_run: DryRunOpt = False,
                     as_json: JsonOpt = False):
    """Import an Investing.com Holdings CSV export (reads only lot fields)."""
    def go():
        cutoff = date.fromisoformat(opening_through) if opening_through else None
        return _argus().import_investing(file, portfolio, cutoff, dry_run=dry_run, validate_symbols=not no_validate)

    def render(d):
        console.print(f"[bold]{d['file']}[/bold] → portfolio [bold]{d['portfolio']}[/bold]"
                      + (" (new)" if d.get("creates_portfolio") else ""))
        console.print(f"{d['lots']} lots, {d['symbols']} symbols: {d['by_type']['OPENING']} OPENING, "
                      f"{d['by_type']['BUY']} BUY")
        for c in d["checks"]:
            mark = "[green]✓[/green]" if c["ok"] else "[red]✗[/red]"
            console.print(f"  {mark} {c['check']}: {c['detail']}")
        if d.get("warning"):
            console.print(f"[yellow]{d['warning']}[/yellow]")
        if d["status"] == "blocked":
            console.print("[red]Blocked: fix the failed checks first.[/red]")
        elif d["dry_run"]:
            console.print("[cyan]Dry run: nothing written. Re-run without --dry-run to import.[/cyan]")
        else:
            console.print(f"[green]Imported {d['inserted']} lots[/green]"
                          + (f", skipped {d['skipped_existing']} already imported" if d["skipped_existing"] else ""))
    _run(as_json, go, render)
