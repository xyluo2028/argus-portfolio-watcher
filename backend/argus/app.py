"""Service facade shared by the CLI and (from P1) the MCP server and web API.

Every public method returns plain JSON-serializable data or raises ArgusError.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Callable

from sqlalchemy import Engine, select

from argus.config import Settings, load_settings
from argus.db import make_engine, session_scope
from argus.errors import ArgusError
from argus import indicators as indicators_mod
from argus.importers import investing
from argus.market_calendar import NY, market_status, session_date, sessions_between
from argus.models import AuditLog, FundProfile, Instrument, Target
from argus.providers.base import Quote
from argus.providers.finnhub import FinnhubProvider
from argus.providers.sec_edgar import SecEdgarProvider
from argus.providers.yahoo import YahooProvider
from argus.services import analysis
from argus.services.alerts import AlertService
from argus.services.events import EventsService
from argus.services.lots import build_positions
from argus.services import performance as performance_mod
from argus.services.market import MarketService
from argus.services.notes import NoteService
from argus.services.portfolio import PortfolioService, TxnInput, position_to_dict
from argus.services.watchlist import DEFAULT as DEFAULT_WATCHLIST, WatchlistService
from argus.symbols import normalize_symbol


class Argus:
    def __init__(self, settings: Settings | None = None,
                 market_factory: Callable[[Engine, Settings], MarketService] | None = None):
        self.settings = settings or load_settings()
        self.engine = make_engine(self.settings.db_path)
        self.portfolios = PortfolioService(self.engine)
        self.watchlists = WatchlistService(self.engine)
        self.market = (market_factory or self._default_market)(self.engine, self.settings)
        self.events = EventsService(self.engine, self.market.directory, self.market.profile_provider)
        self.alerts = AlertService(self.engine)
        self.notes = NoteService(self.engine)

    @staticmethod
    def _default_market(engine: Engine, s: Settings) -> MarketService:
        yahoo = YahooProvider()
        finnhub = FinnhubProvider(s.finnhub_api_key, cache_dir=s.cache_dir) if s.finnhub_api_key else None
        return MarketService(
            engine, s,
            quote_providers=[p for p in (finnhub, yahoo) if p],
            history_provider=yahoo,
            fundamentals_providers=[p for p in (finnhub, yahoo) if p],
            sec=SecEdgarProvider(s.sec_user_agent, cache_dir=s.cache_dir),
            directory=finnhub,
            profile_provider=yahoo,
        )

    # -- read -----------------------------------------------------------------
    def market_status(self) -> dict:
        return market_status()

    def quotes(self, symbols: list[str]) -> dict:
        syms = [normalize_symbol(s) for s in symbols]
        quotes, errors = self.market.get_quotes(syms)
        return {"quotes": [quotes[s].to_dict() for s in syms if s in quotes], "errors": errors,
                "market": market_status()}

    def portfolio(self, ref: str, with_quotes: bool = True, include_lots: bool = False,
                  live_quotes: dict[str, Quote] | None = None) -> dict:
        """Portfolio summary. `live_quotes` (from the web server's hub) are preferred over the cache."""
        state = self.portfolios.positions(ref)
        open_syms = [s for s, p in state.items() if p.is_open]
        quotes = {s: live_quotes[s] for s in open_syms if live_quotes and s in live_quotes}
        missing = [s for s in open_syms if s not in quotes]
        errors: dict[str, str] = {}
        if with_quotes and missing:
            got, errors = self.market.get_quotes(missing)
            quotes |= got
        out = self.portfolios.summary(ref, quotes if with_quotes else {}, include_lots=include_lots)
        out["quote_errors"] = errors
        return out

    def history(self, symbol: str, period: str = "1y", interval: str = "1d",
                indicators: list[str] | None = None) -> dict:
        """OHLCV bars, optionally with indicators computed over a warm-up window.

        Indicators need earlier bars (a 200-day SMA needs 200 days), so they are computed
        on the full cached daily history and then trimmed to the requested period.
        """
        sym = normalize_symbol(symbol)
        bars = self.market.get_history(sym, period, interval)
        out = {"symbol": sym, "interval": interval, "period": period, "source": "yahoo",
               "bars": [{"ts": b.ts.isoformat(), "o": b.o, "h": b.h, "l": b.l, "c": b.c, "v": b.v} for b in bars]}
        if indicators:
            full = self.market.get_history(sym, "max" if interval == "1d" else period, interval) if bars else []
            offset = len(full) - len(bars)
            computed = indicators_mod.compute(full, indicators)
            out["indicators"] = {
                k: ({kk: vv[offset:] for kk, vv in v.items()} if isinstance(v, dict) else v[offset:])
                for k, v in computed.items()
            }
        return out

    COMPARE_FIELDS = ("pe_ttm", "pe_forward", "peg", "pb", "ps_ttm", "ev_ebitda", "market_cap",
                      "revenue_growth_yoy_pct", "gross_margin_pct", "net_margin_pct", "roe_pct", "dividend_yield_pct",
                      "beta")

    def watchlist(self, name: str = DEFAULT_WATCHLIST, live_quotes: dict[str, Quote] | None = None,
                  with_fundamentals: bool = True) -> dict:
        """Watchlist items with quotes and (cached daily) valuation metrics."""
        items = self.watchlists.items(name)
        syms = [i["symbol"] for i in items]
        quotes = {s: live_quotes[s] for s in syms if live_quotes and s in live_quotes}
        missing = [s for s in syms if s not in quotes]
        errors: dict[str, str] = {}
        if missing:
            got, errors = self.market.get_quotes(missing)
            quotes |= got
        for i in items:
            q = quotes.get(i["symbol"])
            i["quote"] = q.to_dict() if q else None
            if with_fundamentals:
                try:
                    i["metrics"] = self.market.get_fundamentals(i["symbol"], list(self.COMPARE_FIELDS))["metrics"]
                except ArgusError as e:
                    i["metrics"] = None
                    errors.setdefault(i["symbol"], e.message)
        return {"watchlist": name, "items": items, "errors": errors}

    def compare(self, symbols: list[str], fields: list[str] | None = None) -> dict:
        """Side-by-side quote + metrics for 2-10 symbols."""
        syms = list(dict.fromkeys(normalize_symbol(s) for s in symbols if s.strip()))
        if not 1 <= len(syms) <= 10:
            raise ArgusError("INVALID_ARG", "Compare 1 to 10 symbols.")
        wanted = fields or list(self.COMPARE_FIELDS)
        quotes, errors = self.market.get_quotes(syms)
        rows = []
        for sym in syms:
            row: dict = {"symbol": sym}
            q = quotes.get(sym)
            row |= {"price": q.price, "change_pct": q.change_pct} if q else {"price": None, "change_pct": None}
            try:
                row |= self.market.get_fundamentals(sym, wanted)["metrics"]
            except ArgusError as e:
                errors.setdefault(sym, e.message)
            rows.append(row)
        return {"fields": wanted, "rows": rows, "errors": errors}

    # -- tracked symbols, events, alerts, brief ----------------------------------
    def held_positions(self) -> dict[str, tuple[float, float]]:
        """symbol -> (total shares, weighted average cost) across all portfolios."""
        agg: dict[str, list[float]] = {}
        for p in self.portfolios.list_portfolios():
            for sym, pos in self.portfolios.positions(p["id"]).items():
                if pos.is_open:
                    a = agg.setdefault(sym, [0.0, 0.0])
                    a[0] += pos.qty
                    a[1] += pos.cost_basis
        return {s: (q, c / q) for s, (q, c) in agg.items() if q}

    def tracked_symbols(self) -> list[str]:
        watched = [i["symbol"] for w in self.watchlists.list_watchlists() for i in self.watchlists.items(w["name"])]
        return sorted(set(self.held_positions()) | set(watched))

    def upcoming_events(self, days_ahead: int = 14, days_back: int = 7, refresh: bool = True,
                        symbols: list[str] | None = None) -> dict:
        syms = [normalize_symbol(x) for x in symbols] if symbols else self.tracked_symbols()
        refreshed = self.events.refresh(syms) if refresh else {"refreshed": [], "failed": {}}
        today = datetime.now(NY).date()
        held = set(self.held_positions())
        rows = self.events.between(syms, today - timedelta(days=days_back), today + timedelta(days=days_ahead))
        for r in rows:
            r["held"] = r["symbol"] in held
        return {
            "as_of": today.isoformat(),
            "upcoming": [r for r in rows if r["date"] >= today.isoformat()],
            "recent": [r for r in rows if r["date"] < today.isoformat()],
            "refresh_failed": refreshed["failed"],
        }

    def evaluate_alerts(self, live_quotes: dict[str, Quote] | None = None) -> list[dict]:
        """Check active alerts now; returns the ones that newly fired this session."""
        active = self.alerts.list()
        if not active:
            return []
        syms = sorted({a["symbol"] for a in active})
        quotes = {s: live_quotes[s] for s in syms if live_quotes and s in live_quotes}
        missing = [s for s in syms if s not in quotes]
        if missing:
            quotes |= self.market.get_quotes(missing)[0]
        costs = {s: c for s, (_, c) in self.held_positions().items()}
        today = datetime.now(NY).date()

        def metrics(sym: str) -> dict:
            try:
                return self.market.get_fundamentals(sym)["metrics"]
            except ArgusError:
                return {}

        return self.alerts.evaluate(quotes, metrics, costs, self.events.next_earnings(syms, today),
                                    session_date(datetime.now(UTC)))

    def daily_brief(self, ref: str, live_quotes: dict[str, Quote] | None = None, news: bool = True) -> dict:
        """Structured facts for a pre-market / post-close brief. The agent writes the prose."""
        status = market_status()
        summ = self.portfolio(ref, True, False, live_quotes)
        positions = summ["positions"]
        bench_sym = summ["portfolio"]["benchmark"]
        bench = (live_quotes or {}).get(bench_sym) or self.market.get_quotes([bench_sym])[0].get(bench_sym)
        priced = [p for p in positions if p.get("change_pct") is not None]
        by_pct = sorted(priced, key=lambda p: p["change_pct"])
        by_dollar = sorted(priced, key=lambda p: -abs(p.get("day_pnl") or 0))

        def pick(p: dict) -> dict:
            return {k: p.get(k) for k in ("symbol", "change_pct", "day_pnl", "price", "weight_pct", "unrealized_pct")}

        near = []
        for p in positions:
            try:
                m = self.market.get_fundamentals(p["symbol"], ["high_52w", "low_52w"])["metrics"]
            except ArgusError:
                continue
            price, hi, lo = p.get("price"), m.get("high_52w"), m.get("low_52w")
            if not (price and hi and lo) or not lo * 0.9 <= price <= hi * 1.1:
                continue  # missing or inconsistent range (e.g. a different listing's currency)
            if price >= hi * 0.97:
                near.append({"symbol": p["symbol"], "near": "52w_high", "gap_pct": (price / hi - 1) * 100})
            elif price <= lo * 1.03:
                near.append({"symbol": p["symbol"], "near": "52w_low", "gap_pct": (price / lo - 1) * 100})

        events = self.upcoming_events(days_ahead=7, days_back=3)
        self.evaluate_alerts(live_quotes)
        last_session = date.fromisoformat(status["last_session"])
        today = datetime.now(NY).date()
        movers = [*by_pct[:3], *by_pct[-3:]] if len(by_pct) > 6 else by_pct
        out = {
            "portfolio": summ["portfolio"]["name"],
            "market": {k: status[k] for k in ("session", "is_trading_day", "last_session", "next_open")},
            "totals": {k: summ["totals"].get(k) for k in ("market_value", "day_pnl", "day_pnl_pct", "unrealized_pnl",
                                                         "unrealized_pct", "position_count")},
            "benchmark": {"symbol": bench_sym, "change_pct": bench.change_pct if bench else None},
            "top_gainers": [pick(p) for p in reversed(by_pct[-5:])],
            "top_losers": [pick(p) for p in by_pct[:5]],
            "largest_dollar_moves": [pick(p) for p in by_dollar[:5]],
            "near_52w_extremes": near,
            "earnings_upcoming": [e for e in events["upcoming"] if e["kind"] == "earnings"],
            "earnings_recent": [e for e in events["recent"] if e["kind"] == "earnings"],
            "dividends_upcoming": [e for e in events["upcoming"] if e["kind"] != "earnings"],
            "alerts_fired": self.alerts.fired(since=min(last_session, today)),
            "theses_due": self.notes.list(due_by=today + timedelta(days=7)),
            "watchlist_movers": [
                {"symbol": i["symbol"], "change_pct": i["quote"]["change_pct"], "price": i["quote"]["price"]}
                for i in self.watchlist(live_quotes=live_quotes, with_fundamentals=False)["items"]
                if i["quote"] and i["quote"]["change_pct"] is not None and abs(i["quote"]["change_pct"]) >= 3
            ],
        }
        if news:
            out["headlines"] = {}
            for p in movers:  # headlines only for the biggest movers, to keep the brief short
                if items := self.events.news(p["symbol"], days=2, limit=3):
                    out["headlines"][p["symbol"]] = items
        return out

    # -- analysis: exposure, targets, drift, what-if -------------------------------
    FUND_PROFILE_MAX_AGE = timedelta(days=7)

    def fund_profiles(self, symbols: list[str]) -> dict[str, dict]:
        """ETF look-through data, cached a week; non-funds are cached as empty profiles."""
        now = datetime.now(UTC)
        out: dict[str, dict] = {}
        with session_scope(self.engine) as s:
            for fp in s.scalars(select(FundProfile).where(FundProfile.symbol.in_(symbols))):
                if now - fp.as_of < self.FUND_PROFILE_MAX_AGE:
                    out[fp.symbol] = fp.data
        yahoo = self.market.profile_provider
        todo = [x for x in symbols if x not in out]
        if yahoo is not None and todo:
            with ThreadPoolExecutor(max_workers=8) as pool:
                fetched = dict(zip(todo, pool.map(yahoo.get_fund_profile, todo)))
            with session_scope(self.engine) as s:
                for sym, data in fetched.items():
                    s.merge(FundProfile(symbol=sym, as_of=now, data=data))
            out |= fetched
        return {k: v for k, v in out.items() if v}

    def exposure(self, ref: str, live_quotes: dict[str, Quote] | None = None) -> dict:
        summ = self.portfolio(ref, True, False, live_quotes)
        rows = summ["positions"]
        return {"portfolio": summ["portfolio"]["name"],
                **analysis.exposure(rows, self.fund_profiles([r["symbol"] for r in rows]))}

    def targets(self, ref: str, level: str) -> dict[str, float]:
        p = self.portfolios.get_portfolio(ref)
        with session_scope(self.engine) as s:
            return {t.key: t.weight_pct for t in s.scalars(select(Target).where(Target.portfolio_id == p.id,
                                                                                 Target.level == level))}

    def set_targets(self, ref: str, level: str, weights: dict[str, float], dry_run: bool = True,
                    actor: str = "cli") -> dict:
        """Replace all targets at `level` (symbol | sector). Weights are percents."""
        if level not in ("symbol", "sector"):
            raise ArgusError("INVALID_ARG", "level must be 'symbol' or 'sector'.")
        if any(w < 0 or w > 100 for w in weights.values()):
            raise ArgusError("INVALID_ARG", "Each target must be between 0 and 100 (percent).")
        clean = {(normalize_symbol(k) if level == "symbol" else k.strip()): float(w) for k, w in weights.items()}
        p = self.portfolios.get_portfolio(ref)
        preview = self.drift(ref, level, targets=clean)
        preview["dry_run"] = dry_run
        if not dry_run:
            with session_scope(self.engine) as s:
                for t in s.scalars(select(Target).where(Target.portfolio_id == p.id, Target.level == level)):
                    s.delete(t)
                for k, w in clean.items():
                    s.add(Target(portfolio_id=p.id, level=level, key=k, weight_pct=w))
                s.add(AuditLog(actor=actor, action="set_targets", entity="portfolio", entity_id=str(p.id),
                               after={"level": level, "weights": clean}))
        return preview

    def drift(self, ref: str, level: str = "symbol", tolerance_pp: float = 2.0,
              live_quotes: dict[str, Quote] | None = None, targets: dict[str, float] | None = None) -> dict:
        summ = self.portfolio(ref, True, False, live_quotes)
        tg = targets if targets is not None else self.targets(ref, level)
        return {"portfolio": summ["portfolio"]["name"], **analysis.drift(summ["positions"], tg, level, tolerance_pp)}

    def simulate_trades(self, ref: str, trades: list[dict], live_quotes: dict[str, Quote] | None = None) -> dict:
        """What-if: apply hypothetical BUY/SELL trades (qty, or dollar `amount`) at `price` or the
        current quote; nothing is saved. Returns before/after weights, exposure and realized P&L."""
        p = self.portfolios.get_portfolio(ref)
        before = self.portfolio(ref, True, False, live_quotes)
        now = datetime.now(UTC)
        syms = sorted({normalize_symbol(t["symbol"]) for t in trades})
        quotes = dict(live_quotes or {})
        missing = [s for s in syms if s not in quotes]
        if missing:
            quotes |= self.market.get_quotes(missing)[0]
        items: list[TxnInput] = []
        cash = 0.0
        for i, t in enumerate(trades):
            sym = normalize_symbol(t["symbol"])
            side = str(t.get("side", "BUY")).upper()
            if side not in ("BUY", "SELL"):
                raise ArgusError("INVALID_ARG", f"Trade {i + 1}: side must be BUY or SELL.")
            price = t.get("price") or (quotes[sym].price if sym in quotes else None)
            if not price:
                raise ArgusError("NO_PRICE", f"No price for {sym}; pass price explicitly.")
            qty = t.get("qty") or (t["amount"] / price if t.get("amount") else None)
            if not qty or qty <= 0:
                raise ArgusError("INVALID_ARG", f"Trade {i + 1}: give qty or amount > 0.")
            items.append(TxnInput(side, sym, now, qty, price, float(t.get("fee") or 0.0), id=10**9 + i))
            cash += (-1 if side == "BUY" else 1) * qty * price
        state = build_positions([*self.portfolios.active_transactions(p.id), *items])  # validates oversells
        sim_quotes = dict(quotes)
        for s in syms:
            if s not in sim_quotes:
                last = next(x for x in reversed(items) if x.symbol == s)
                sim_quotes[s] = Quote(s, last.price, None, None, None, None, now, "simulated")
        after_rows = []
        by_symbol = {r["symbol"]: r for r in before["positions"]}
        for sym, pos in state.items():
            if not pos.is_open:
                continue
            base = dict(by_symbol.get(sym, {"symbol": sym, "sector": None, "type": None, "name": None}))
            q = sim_quotes.get(sym)
            px = q.price if q else base.get("price") or pos.avg_cost
            base |= {"qty": pos.qty, "avg_cost": pos.avg_cost, "cost_basis": pos.cost_basis, "price": px,
                     "market_value": pos.qty * px}
            after_rows.append(base)
        total_after = sum(r["market_value"] for r in after_rows)
        for r in after_rows:
            r["weight_pct"] = r["market_value"] / total_after * 100 if total_after else None
        realized_after = sum(ps.realized_pnl for ps in state.values())
        changed = {normalize_symbol(t["symbol"]) for t in trades}
        profiles = self.fund_profiles([r["symbol"] for r in after_rows])
        return {
            "portfolio": p.name,
            "trades": [{"symbol": x.symbol, "side": x.type, "qty": x.qty, "price": x.price} for x in items],
            "net_cash": cash,  # + frees cash (sells), - needs cash (buys)
            "realized_pnl_from_trades": realized_after - before["totals"]["realized_pnl"],
            "value_before": before["totals"]["market_value"],
            "value_after": total_after,
            "positions_changed": [
                {"symbol": s, "weight_before": (by_symbol.get(s) or {}).get("weight_pct"),
                 "weight_after": next((r["weight_pct"] for r in after_rows if r["symbol"] == s), 0.0),
                 "qty_after": next((r["qty"] for r in after_rows if r["symbol"] == s), 0.0)} for s in sorted(changed)],
            "concentration_before": analysis.concentration([analysis.value(r) for r in before["positions"]]),
            "concentration_after": analysis.concentration([r["market_value"] for r in after_rows]),
            "sector_lookthrough_after": analysis.exposure(after_rows, profiles).get("by_sector_lookthrough", []),
            "saved": False,
        }

    PERF_RANGES = ("1mo", "3mo", "ytd", "1y", "all")

    def performance(self, ref: str, range_: str = "all", live_quotes: dict[str, Quote] | None = None) -> dict:
        """Daily value and TWR vs the portfolio's benchmark; `range_` slices and rebases the series."""
        if range_ not in self.PERF_RANGES:
            raise ArgusError("INVALID_ARG", f"Unknown range '{range_}'.", hint=f"Use one of {', '.join(self.PERF_RANGES)}.")
        p = self.portfolios.get_portfolio(ref)
        txns = self.portfolios.active_transactions(p.id)
        if not txns:
            return {"portfolio": p.name, "range": range_, "benchmark": p.benchmark, "summary": {}, "series": []}
        start = min(t.ts for t in txns).astimezone(NY).date()
        status = market_status()
        end = date.fromisoformat(status["last_session"])
        sessions = sessions_between(start, end)
        symbols = sorted({t.symbol for t in txns} | {p.benchmark})
        with ThreadPoolExecutor(max_workers=8) as pool:  # first run fetches ~all symbols from Yahoo
            closes = dict(zip(symbols, pool.map(lambda s: self.market.daily_closes(s, start), symbols)))

        # While a session is open, add today as a provisional point priced from live quotes.
        today = datetime.now(NY).date()
        if status["session"] != "closed" and status["is_trading_day"] and live_quotes and today not in sessions:
            sessions.append(today)
            for sym, q in live_quotes.items():
                if sym in closes:
                    closes[sym][today] = q.price

        bench = closes.pop(p.benchmark, {}) if p.benchmark not in {t.symbol for t in txns} else closes.get(p.benchmark, {})
        points = performance_mod.compute_series(txns, sessions, closes, bench)
        cutoff = {"1mo": today - timedelta(days=31), "3mo": today - timedelta(days=92),
                  "ytd": date(today.year, 1, 1) - timedelta(days=1), "1y": today - timedelta(days=366)}.get(range_)
        if cutoff:
            # Base the slice on the last close at or before the cutoff.
            base = max((i for i, pt in enumerate(points) if pt.d <= cutoff), default=0)
            points = points[base:]
        base_idx = points[0].index if points else 1.0
        base_bench = points[0].bench_index if points else None
        return {
            "portfolio": p.name,
            "range": range_,
            "benchmark": p.benchmark,
            "provisional_today": bool(points) and points[-1].d == today and status["session"] != "closed",
            "summary": performance_mod.summarize(points),
            "series": [{
                "d": pt.d.isoformat(), "value": pt.value, "flow_in": pt.flow_in, "flow_out": pt.flow_out,
                "twr_pct": (pt.index / base_idx - 1) * 100,
                "bench_pct": (pt.bench_index / base_bench - 1) * 100 if pt.bench_index and base_bench else None,
            } for pt in points],
        }

    # -- import ---------------------------------------------------------------
    def import_investing(self, path: Path, portfolio: str | None = None, opening_through: date | None = None,
                         dry_run: bool = True, validate_symbols: bool = True) -> dict:
        parsed = investing.parse_investing_csv(path)
        name = portfolio or parsed.portfolio_name
        if not name:
            raise ArgusError("INVALID_ARG", "Can't infer the portfolio name from the file name.",
                             hint="Pass --portfolio NAME.")
        checks = investing.reconcile(parsed)
        planned = investing.plan_transactions(parsed, opening_through)

        invalid: dict[str, str] = {}
        if validate_symbols:
            _, invalid = self.market.get_quotes(sorted({t.symbol for t in planned}))
            checks.append({"check": "symbols_resolve", "ok": not invalid,
                           "detail": "all symbols have live quotes" if not invalid
                           else f"unresolved: {', '.join(sorted(invalid))}"})

        kinds = {"OPENING": 0, "BUY": 0}
        for t in planned:
            kinds[t.type] += 1
        report = {
            "file": str(path),
            "portfolio": name,
            "dry_run": dry_run,
            "lots": len(planned),
            "symbols": len({t.symbol for t in planned}),
            "by_type": kinds,
            "opening_through": opening_through.isoformat() if opening_through else None,
            "checks": checks,
            "lot_preview": [{"symbol": t.symbol, "type": t.type, "date": t.ts.date().isoformat(), "qty": t.qty,
                             "price": t.price} for t in planned],
        }
        if opening_through is None:
            report["warning"] = ("No --opening-through date: every lot is imported as a BUY on its date. "
                                 "Holdings you already owned should be OPENING lots.")
        if not all(c["ok"] for c in checks):
            report["status"] = "blocked"
            if not dry_run:
                raise ArgusError("CHECKS_FAILED", "Import blocked by failed checks.",
                                 hint="; ".join(c["detail"] for c in checks if not c["ok"]))
            return report

        existing = {p["name"] for p in self.portfolios.list_portfolios()}
        if name not in existing:
            report["creates_portfolio"] = True
            if dry_run:
                after = build_positions(planned)
                report["positions_after"] = [position_to_dict(p, s) for s, p in sorted(after.items())]
                report["status"] = "ok"
                return report
            self.portfolios.create_portfolio(name, actor="import")

        result = self.portfolios.add_transactions(name, planned, source="import", dry_run=dry_run)
        report["inserted"] = len(result["inserted_ids"])
        report["skipped_existing"] = len(result["skipped_existing"])
        report["positions_after"] = [x["after"] for x in result["positions"]]
        report["status"] = "ok"
        if not dry_run:
            self._upsert_instrument_names(parsed)
            self.market.refresh_instruments(sorted({t.symbol for t in planned}))
        return report

    def _upsert_instrument_names(self, parsed: investing.ParsedExport) -> None:
        with session_scope(self.engine) as s:
            for lot in parsed.lots:
                inst = s.get(Instrument, lot.symbol) or Instrument(symbol=lot.symbol)
                inst.name = inst.name or lot.name
                inst.exchange = inst.exchange or lot.exchange
                s.merge(inst)
