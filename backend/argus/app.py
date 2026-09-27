"""Service facade shared by the CLI and (from P1) the MCP server and web API.

Every public method returns plain JSON-serializable data or raises ArgusError.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from sqlalchemy import Engine

from argus.config import Settings, load_settings
from argus.db import make_engine, session_scope
from argus.errors import ArgusError
from argus import indicators as indicators_mod
from argus.importers import investing
from argus.market_calendar import NY, market_status, sessions_between
from argus.models import Instrument
from argus.providers.base import Quote
from argus.providers.finnhub import FinnhubProvider
from argus.providers.sec_edgar import SecEdgarProvider
from argus.providers.yahoo import YahooProvider
from argus.services.lots import build_positions
from argus.services import performance as performance_mod
from argus.services.market import MarketService
from argus.services.portfolio import PortfolioService, position_to_dict
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
