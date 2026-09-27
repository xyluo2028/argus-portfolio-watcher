"""Service facade shared by the CLI and (from P1) the MCP server and web API.

Every public method returns plain JSON-serializable data or raises ArgusError.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

from sqlalchemy import Engine

from argus.config import Settings, load_settings
from argus.db import make_engine, session_scope
from argus.errors import ArgusError
from argus.importers import investing
from argus.market_calendar import market_status
from argus.models import Instrument
from argus.providers.base import Quote
from argus.providers.finnhub import FinnhubProvider
from argus.providers.sec_edgar import SecEdgarProvider
from argus.providers.yahoo import YahooProvider
from argus.services.lots import build_positions
from argus.services.market import MarketService
from argus.services.portfolio import PortfolioService, position_to_dict
from argus.symbols import normalize_symbol


class Argus:
    def __init__(self, settings: Settings | None = None,
                 market_factory: Callable[[Engine, Settings], MarketService] | None = None):
        self.settings = settings or load_settings()
        self.engine = make_engine(self.settings.db_path)
        self.portfolios = PortfolioService(self.engine)
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

    def history(self, symbol: str, period: str = "1y", interval: str = "1d") -> dict:
        sym = normalize_symbol(symbol)
        bars = self.market.get_history(sym, period, interval)
        return {"symbol": sym, "interval": interval, "period": period, "source": "yahoo",
                "bars": [{"ts": b.ts.isoformat(), "o": b.o, "h": b.h, "l": b.l, "c": b.c, "v": b.v} for b in bars]}

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
