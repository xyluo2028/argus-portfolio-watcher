"""Service facade shared by the CLI and (from P1) the MCP server and web API.

Every public method returns plain JSON-serializable data or raises ArgusError.
"""

from __future__ import annotations

import logging
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
from argus.models import (AuditLog, CompanyProfile, DividendHistory, FundProfile, Instrument, PeerList, SecurityMap,
                          Target)
from argus.providers.base import ProviderError, Quote
from argus.providers.finnhub import FinnhubProvider
from argus.providers.openfigi import OpenFigiProvider, yahoo_symbol
from argus.providers.sec_edgar import SecEdgarProvider
from argus.providers.yahoo import YahooProvider
from argus.services import analysis
from argus.services import dividends as dividends_mod
from argus.services.alerts import AlertService
from argus.services.events import EventsService
from argus.services.lots import build_positions
from argus.services import performance as performance_mod
from argus.services.market import MarketService
from argus.services.notes import NoteService
from argus.services.portfolio import ALL, PortfolioService, TxnInput, position_to_dict
from argus.services.snapshot import SnapshotService
from argus.services.watchlist import DEFAULT as DEFAULT_WATCHLIST, WatchlistService
from argus.symbols import is_plausible_symbol, normalize_symbol


log = logging.getLogger("argus.app")


class Argus:
    def __init__(self, settings: Settings | None = None,
                 market_factory: Callable[[Engine, Settings], MarketService] | None = None):
        self.settings = settings or load_settings()
        self.engine = make_engine(self.settings.db_path)
        self.portfolios = PortfolioService(self.engine, on_new_symbols=self.describe_instruments)
        self.watchlists = WatchlistService(self.engine, resolve=lambda syms: self.market.get_quotes(syms)[1])
        self.market = (market_factory or self._default_market)(self.engine, self.settings)
        self.events = EventsService(self.engine, self.market.directory, self.market.profile_provider)
        self.alerts = AlertService(self.engine)
        self.notes = NoteService(self.engine)
        self.snapshots = SnapshotService(self.engine)

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
            figi=OpenFigiProvider(s.openfigi_api_key),
        )

    # -- read -----------------------------------------------------------------
    def market_status(self) -> dict:
        return market_status()

    def quotes(self, symbols: list[str]) -> dict:
        syms = [normalize_symbol(s) for s in symbols]
        quotes, errors = self.market.get_quotes(syms)
        return {"quotes": [quotes[s].to_dict() for s in syms if s in quotes], "errors": errors,
                "market": market_status()}

    def describe_instruments(self, symbols: list[str]) -> None:
        """Fill type/sector for symbols that lack a sector (e.g. first recorded from the UI), so funds
        aren't mistaken for stocks. Symbols that already have one cost nothing."""
        with session_scope(self.engine) as s:
            known = {i.symbol: i for i in s.scalars(select(Instrument).where(Instrument.symbol.in_(symbols)))}
            missing = [x for x in symbols if x not in known or not known[x].sector]
        if missing:
            self.market.refresh_instruments(missing)

    def portfolio(self, ref: str, with_quotes: bool = True, include_lots: bool = False,
                  live_quotes: dict[str, Quote] | None = None) -> dict:
        """Portfolio summary. `live_quotes` (from the web server's hub) are preferred over the cache."""
        state = self.portfolios.positions(ref)
        open_syms = [s for s, p in state.items() if p.is_open]
        try:
            self.describe_instruments(open_syms)
        except Exception as e:  # never block the summary on metadata
            log.warning("instrument metadata: %s", e)
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
    # -- company profile & peers ---------------------------------------------------
    PROFILE_MAX_AGE = timedelta(days=7)
    PROFILE_VERSION = 2  # bump to refetch cached profiles (2: fund peers from the same category)
    MAX_PEERS = 9  # plus the symbol itself = compare()'s limit of 10
    FUND_TYPES = ("ETF", "MUTUALFUND")
    FUND_COMPARE_FIELDS = ("net_assets", "expense_ratio_pct", "dividend_yield_pct", "ytd_return_pct", "return_3y_pct")

    def company_profile(self, symbol: str, refresh: bool = False) -> dict:
        """What the company does and where it is (Yahoo), IPO date and suggested peers (Finnhub).
        Cached a week; missing providers just leave fields empty."""
        sym = normalize_symbol(symbol)
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            row = s.get(CompanyProfile, sym)
            if row and not refresh and now - row.as_of < self.PROFILE_MAX_AGE and row.data.get("v") == self.PROFILE_VERSION:
                return {"symbol": sym, "as_of": row.as_of.isoformat(), **{k: v for k, v in row.data.items() if k != "v"}}

        data: dict = {}
        if self.market.profile_provider is not None:
            try:
                info = self.market.profile_provider.get_info(sym)
            except ProviderError:
                info = {}
            officers = [{"name": o.get("name"), "title": o.get("title")} for o in (info.get("companyOfficers") or [])[:3]]
            data |= {
                "name": info.get("longName") or info.get("shortName"),
                "summary": info.get("longBusinessSummary"),
                "quote_type": info.get("quoteType"),
                "sector": info.get("sector"), "industry": info.get("industry"),
                "country": info.get("country"), "city": info.get("city"), "state": info.get("state"),
                "address": info.get("address1"), "zip": info.get("zip"),
                "website": info.get("website"), "employees": info.get("fullTimeEmployees"),
                "officers": officers,
                "fund_family": info.get("fundFamily"), "category": info.get("category"),
            }
        fund = data.get("quote_type") in self.FUND_TYPES
        if self.market.directory is not None:
            try:
                fh = self.market.directory.get_profile(sym)
                data |= {"ipo": fh.get("ipo"), "logo": fh.get("logo") or None,
                         "website": data.get("website") or fh.get("weburl"), "name": data.get("name") or fh.get("name"),
                         "country": data.get("country") or fh.get("country")}
                if not fund:
                    data["suggested_peers"] = self._us_listed([p for p in self.market.directory.get_peers(sym) if p != sym])
            except ProviderError:
                pass
        if fund:  # Finnhub has no fund peers; use the same Morningstar category instead
            data["suggested_peers"] = self._similar_funds(sym, data.get("category"))
        data = {k: v for k, v in data.items() if v not in (None, "", [])} | {"suggested_peers": data.get("suggested_peers", [])}
        with session_scope(self.engine) as s:
            s.merge(CompanyProfile(symbol=sym, as_of=now, data=data | {"v": self.PROFILE_VERSION}))
        return {"symbol": sym, "as_of": now.isoformat(), **data}

    @staticmethod
    def holdings_overlap(a: dict, b: dict) -> float | None:
        """Percent of weight two funds share among their listed top holdings (sum of the smaller weight
        per common holding). None when either lists no holdings, e.g. bond funds."""
        wa = {normalize_symbol(h["symbol"]): h["weight"] for h in a.get("top_holdings", [])}
        wb = {normalize_symbol(h["symbol"]): h["weight"] for h in b.get("top_holdings", [])}
        if not wa or not wb:
            return None
        return round(sum(min(w, wb[k]) for k, w in wa.items() if k in wb) * 100, 1)

    def _similar_funds(self, sym: str, category: str | None) -> list[str]:
        """The biggest US ETFs in the same category, those sharing the most top holdings first."""
        yahoo = self.market.profile_provider
        if not category or yahoo is None:
            return []
        try:
            found = [normalize_symbol(x) for x in yahoo.similar_etfs(category, 2 * self.MAX_PEERS + 2)]
        except ProviderError as e:
            log.warning("similar funds for %s: %s", sym, e)
            return []
        candidates = self._us_listed([x for x in dict.fromkeys(found) if x != sym], limit=None)
        profiles = self.fund_profiles([sym, *candidates])
        own = profiles.get(sym, {})
        size_rank = {x: i for i, x in enumerate(candidates)}
        overlap = {x: self.holdings_overlap(own, profiles.get(x, {})) or 0.0 for x in candidates}
        return sorted(candidates, key=lambda x: (-overlap[x], size_rank[x]))[:self.MAX_PEERS]

    def _us_listed(self, symbols: list[str], limit: int | None = MAX_PEERS) -> list[str]:
        """Keep symbols listed on a US exchange (not OTC); Finnhub suggests home-market peers for
        foreign companies (e.g. IGM.TO for BN), which have no US quotes."""
        try:
            directory = self.market.directory.symbol_directory() if self.market.directory else {}
        except ProviderError:
            directory = {}
        if not directory:
            return [x for x in symbols if "." not in x][:limit]
        return [x for x in symbols if x in directory and directory[x].exchange != "OOTC"][:limit]

    def peers(self, symbol: str, with_metrics: bool = True) -> dict:
        """Your peer list for `symbol` (or the suggested one) with a side-by-side comparison."""
        sym = normalize_symbol(symbol)
        with session_scope(self.engine) as s:
            row = s.get(PeerList, sym)
            custom = list(row.peers) if row else None
        profile = self.company_profile(sym)
        fund = profile.get("quote_type") in self.FUND_TYPES
        peers = custom if custom is not None else profile.get("suggested_peers", [])
        out = {"symbol": sym, "peers": peers, "custom": custom is not None,
               "kind": "fund" if fund else "stock", "category": profile.get("category") if fund else None}
        if with_metrics:
            syms = [sym, *peers][:self.MAX_PEERS + 1]
            out |= self.compare(syms, list(self.FUND_COMPARE_FIELDS) if fund else None)
            if fund:
                profiles = self.fund_profiles(syms)
                own = profiles.get(sym, {})
                for row in out["rows"]:
                    row["overlap_pct"] = None if row["symbol"] == sym else \
                        self.holdings_overlap(own, profiles.get(row["symbol"], {}))
        return out

    HOLDINGS_NAMED = 100  # largest stock holdings given tickers (OpenFIGI, cached for good)
    HOLDINGS_QUOTED = 50  # of those, quoted for the heatmap
    SECURITY_MAP_RETRY = timedelta(days=30)  # retry ids OpenFIGI couldn't map

    def fund_holdings(self, symbol: str, limit: int | None = None) -> dict:
        """A fund's holdings, largest first: every one from its latest SEC N-PORT filing (months old;
        `as_of` says when), else Yahoo's current top 10. The largest stock holdings carry today's move.
        Plus sector weights, countries, asset mix and bond ratings (all percent). `fund` is false (and
        the rest empty) for anything that isn't a fund. `limit` caps the holdings returned."""
        sym = normalize_symbol(symbol)
        out: dict = {"symbol": sym, "fund": self.company_profile(sym).get("quote_type") in self.FUND_TYPES,
                     "source": None, "as_of": None, "filed": None, "count": 0, "holdings": [], "sectors": [],
                     "countries": [], "asset_classes": {}, "bond_ratings": {}, "notes": [], "errors": {}}
        if not out["fund"]:
            return out
        prof = self.fund_profiles([sym]).get(sym, {})
        nport = None
        if self.market.sec is not None:
            try:
                nport = self.market.sec.fund_holdings(sym)
            except ProviderError as e:
                log.warning("N-PORT %s: %s", sym, e)
                out["notes"].append("SEC_USER_AGENT" in str(e) and "Set SEC_USER_AGENT in .env to see every holding "
                                    "(from SEC filings); showing Yahoo's top 10." or f"SEC filing unavailable: {e}")
        if nport and nport["holdings"]:
            rows = [{"symbol": None, "us_listed": False, "name": h["name"] or h["title"],
                     "weight_pct": round(h["weight_pct"], 3), "value_usd": h["value_usd"], "country": h["country"],
                     "kind": "stock" if h["asset_cat"] in ("EC", "EP")
                     else "bond" if h["asset_cat"] in ("DBT", "ABS-MBS", "ABS-O", "ABS-CBDO", "ABS-APCP") else "other",
                     "maturity": h.get("maturity"), "coupon_pct": h.get("coupon_pct"),
                     "_ids": (h["isin"], h["cusip"], h["ticker"], h["currency"])} for h in nport["holdings"]]
            self._name_holdings(rows, out["notes"])
            rows = self._merge_lines(rows)
            countries = list(nport["countries"].items())
            out |= {"source": "sec", "as_of": nport["as_of"], "filed": nport["filed"], "count": nport["count"],
                    "countries": [{"country": c, "weight_pct": round(w, 2)} for c, w in countries[:12]]
                    + ([{"country": "Other", "weight_pct": round(sum(w for _, w in countries[12:]), 2)}]
                       if len(countries) > 12 else [])}
        else:
            # US listings go through the normal symbol form; foreign ones (2330.TW) stay in Yahoo's.
            try:
                directory = self.market.directory.symbol_directory() if self.market.directory else {}
            except ProviderError:
                directory = {}
            rows = []
            for h in prof.get("top_holdings", []):
                n = normalize_symbol(h["symbol"])
                us = n in directory if directory else "." not in n
                rows.append({"symbol": n if us else h["symbol"], "us_listed": us, "name": h.get("name"),
                             "weight_pct": round(h["weight"] * 100, 3), "value_usd": None, "country": None,
                             "kind": "stock"})
            out |= {"source": "yahoo" if rows else None, "count": len(rows)}
        quoted = [r for r in rows if r["symbol"]][:self.HOLDINGS_QUOTED]
        quotes = self._holding_quotes([r["symbol"] for r in quoted if r["us_listed"]],
                                      [r["symbol"] for r in quoted if not r["us_listed"]])
        for r in rows:
            r.pop("_ids", None)
            q = quotes.get(r["symbol"]) if r["symbol"] else None
            r["price"], r["change_pct"] = (q.price, q.change_pct) if q else (None, None)
        out["errors"] = {r["symbol"]: "no quote" for r in quoted if r["symbol"] not in quotes}
        out["holdings"] = rows[:limit] if limit else rows
        out["sectors"] = [{"sector": k, "weight_pct": round(v * 100, 2)}
                          for k, v in sorted(prof.get("sectors", {}).items(), key=lambda kv: -kv[1])]
        for key in ("asset_classes", "bond_ratings"):
            out[key] = {k: round(v * 100, 2) for k, v in prof.get(key, {}).items()}
        return out

    def _name_holdings(self, rows: list[dict], notes: list[str]) -> None:
        """Give the largest stock holdings a quotable symbol: the filing's own ticker for US lines,
        else OpenFIGI's listing in the currency the fund holds (cached, so each id is asked once)."""
        todo = [r for r in rows if r["kind"] == "stock"][:self.HOLDINGS_NAMED]
        keyed: dict[str, tuple[list[dict], dict]] = {}  # id -> (rows holding it, OpenFIGI job)
        for r in todo:
            isin, cusip, ticker, currency = r["_ids"]
            country = r["country"]
            if ticker and currency == "USD" and is_plausible_symbol(normalize_symbol(ticker)):
                r["symbol"], r["us_listed"] = normalize_symbol(ticker), True
                continue
            # A USD line with a CUSIP is a US listing (incl. ADRs); without one (e.g. a GDR) prefer home.
            us_line = currency == "USD" and bool(cusip)
            key = cusip if us_line else isin or cusip
            if key in keyed:  # e.g. local shares and a GDR of the same company: the first (largest) decides
                keyed[key][0].append(r)
            elif key:
                id_type = "ID_ISIN" if key == isin else "ID_CINS" if key[0].isalpha() else "ID_CUSIP"
                keyed[key] = ([r], {"id_type": id_type, "id": key, "isin": isin, "country": country,
                                    "currency": currency if us_line or currency != "USD" else None})
        if not keyed:
            return
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            known = {m.id: (m.symbol, m.exchange) for m in s.scalars(select(SecurityMap).where(SecurityMap.id.in_(keyed)))
                     if m.symbol or now - m.as_of < self.SECURITY_MAP_RETRY}
        missing = [k for k in keyed if k not in known]
        figi = self.market.figi
        if missing and figi is not None:
            for i in range(0, len(missing), figi.batch):
                chunk = missing[i:i + figi.batch]
                try:
                    got = figi.map([keyed[k][1] for k in chunk])
                except ProviderError as e:  # rate limited: the rest get names on a later load
                    log.warning("holdings tickers: %s", e)
                    notes.append("Some holdings are still being matched to tickers; reload in a minute.")
                    break
                with session_scope(self.engine) as s:
                    for k in chunk:
                        listing = got.get(k)
                        ys = yahoo_symbol(*listing) if listing else None
                        if ys and listing[1] == "US":
                            ys = normalize_symbol(ys)
                        s.merge(SecurityMap(id=k, ticker=listing[0] if listing else None,
                                            exchange=listing[1] if listing else None, symbol=ys, as_of=now))
                        known[k] = (ys, listing[1] if listing else None)
        for k, (rs, _) in keyed.items():
            ys, exch = known.get(k, (None, None))
            for r in rs if ys else []:
                r["symbol"], r["us_listed"] = ys, exch == "US"

    @staticmethod
    def _merge_lines(rows: list[dict]) -> list[dict]:
        """One row per symbol: funds can hold a company twice (local shares and a GDR, e.g. Samsung)."""
        merged: dict[str, dict] = {}
        out = []
        for r in rows:
            if r["symbol"] and r["symbol"] in merged:
                m = merged[r["symbol"]]
                m["weight_pct"] = round(m["weight_pct"] + r["weight_pct"], 3)
                m["value_usd"] = (m["value_usd"] or 0) + (r["value_usd"] or 0) or None
                if not m["us_listed"] and r["country"] not in (None, "US"):  # a GDR may be filed as US
                    m["country"] = r["country"]
                continue
            if r["symbol"]:
                merged[r["symbol"]] = r
            out.append(r)
        return sorted(out, key=lambda r: -r["weight_pct"])

    def _holding_quotes(self, us: list[str], foreign: list[str]) -> dict[str, Quote]:
        """Quotes for fund holdings from the cache or Yahoo (in parallel), keeping Finnhub's per-minute
        budget for the portfolio. Foreign symbols are Yahoo's own (7203.T)."""
        quotes = self.market.cached_quotes(us + foreign, max_age_s=60)
        yahoo = self.market.profile_provider
        need = [(s, s in foreign) for s in us + foreign if s not in quotes]
        if yahoo is None or not need:
            return quotes
        chunks = [need[i::8] for i in range(8)]

        def fetch(chunk):
            got = {}
            for native in (False, True):
                syms = [s for s, n in chunk if n == native]
                if syms:
                    try:
                        got |= yahoo.get_quotes(syms, native=native)
                    except ProviderError:
                        pass
            return got

        with ThreadPoolExecutor(max_workers=8) as pool:
            for got in pool.map(fetch, [c for c in chunks if c]):
                quotes |= got
                self.market.store_quotes(got.values())
        return quotes
        prof = self.fund_profiles([sym]).get(sym, {})
        raw = prof.get("top_holdings", [])
        # US listings go through the normal quote path (cache, live providers); foreign ones (2330.TW,
        # ASML.AS) only Yahoo knows, under its own symbol.
        try:
            directory = self.market.directory.symbol_directory() if self.market.directory else {}
        except ProviderError:
            directory = {}
        us = {h["symbol"]: normalize_symbol(h["symbol"]) for h in raw
              if (normalize_symbol(h["symbol"]) in directory if directory else "." not in normalize_symbol(h["symbol"]))}
        quotes, errors = self.market.get_quotes(list(us.values())) if us else ({}, {})
        foreign = [h["symbol"] for h in raw if h["symbol"] not in us]
        native: dict[str, Quote] = {}
        if foreign and self.market.profile_provider is not None:
            try:
                native = self.market.profile_provider.get_quotes(foreign, native=True)
            except ProviderError:
                pass
        for h in raw:
            q = quotes.get(us[h["symbol"]]) if h["symbol"] in us else native.get(h["symbol"])
            out["holdings"].append({"symbol": us.get(h["symbol"], h["symbol"]), "name": h.get("name"),
                                    "weight_pct": round(h["weight"] * 100, 2), "us_listed": h["symbol"] in us,
                                    "price": q.price if q else None, "change_pct": q.change_pct if q else None})
            if not q:
                out["errors"][h["symbol"]] = errors.get(us.get(h["symbol"], ""), "no quote")
        out["sectors"] = [{"sector": k, "weight_pct": round(v * 100, 2)}
                          for k, v in sorted(prof.get("sectors", {}).items(), key=lambda kv: -kv[1])]
        for key in ("asset_classes", "bond_ratings"):
            out[key] = {k: round(v * 100, 2) for k, v in prof.get(key, {}).items()}
        return out

    def set_peers(self, symbol: str, peers: list[str] | None, actor: str = "cli") -> dict:
        """Save your peer list (unknown tickers are refused); None goes back to the suggestions."""
        sym = normalize_symbol(symbol)
        with session_scope(self.engine) as s:
            before = s.get(PeerList, sym)
            before_peers = list(before.peers) if before else None
        if peers is None:
            with session_scope(self.engine) as s:
                if (row := s.get(PeerList, sym)) is not None:
                    s.delete(row)
                    s.add(AuditLog(actor=actor, action="reset_peers", entity="peers", entity_id=sym,
                                   before={"peers": before_peers}))
            return self.peers(sym, with_metrics=False)
        clean = [p for p in dict.fromkeys(normalize_symbol(x) for x in peers if x.strip()) if p != sym]
        if len(clean) > self.MAX_PEERS:
            raise ArgusError("INVALID_ARG", f"At most {self.MAX_PEERS} peers.")
        new = [p for p in clean if p not in (before_peers or []) and is_plausible_symbol(p)]
        bad = [p for p in clean if not is_plausible_symbol(p)]
        unknown = self.market.get_quotes(new)[1] if new else {}
        if bad or unknown:
            raise ArgusError("UNKNOWN_SYMBOL", f"No quote found for: {', '.join(sorted({*bad, *unknown}))}",
                             hint="Check the ticker; only US-listed stocks and ETFs are supported.")
        with session_scope(self.engine) as s:
            s.merge(PeerList(symbol=sym, peers=clean))
            s.add(AuditLog(actor=actor, action="set_peers", entity="peers", entity_id=sym,
                           before={"peers": before_peers}, after={"peers": clean}))
        return self.peers(sym, with_metrics=False)

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

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Symbol search that ranks your holdings and watchlist first."""
        return self.market.search(query, limit, prefer=set(self.tracked_symbols()))

    def tracked_symbols(self) -> list[str]:
        watched = [i["symbol"] for w in self.watchlists.list_watchlists() for i in self.watchlists.items(w["name"])]
        return sorted(set(self.held_positions()) | set(watched))

    def upcoming_events(self, days_ahead: int = 14, days_back: int = 7, refresh: bool = True,
                        symbols: list[str] | None = None, portfolio: str | None = None) -> dict:
        """Events for `symbols`, else one portfolio's holdings, else (or for ALL) holdings + watchlist."""
        if symbols:
            syms = [normalize_symbol(x) for x in symbols]
        elif portfolio and str(portfolio).lower() != ALL:
            syms = sorted(s for s, p in self.portfolios.positions(portfolio).items() if p.is_open)
        else:
            syms = self.tracked_symbols()
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
                # Fund rows cached before asset classes were collected are refetched.
                if now - fp.as_of < self.FUND_PROFILE_MAX_AGE and (not fp.data or "asset_classes" in fp.data):
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

    DIVIDEND_MAX_AGE = timedelta(hours=24)

    def dividend_histories(self, symbols: list[str]) -> dict[str, list[tuple[str, float]]]:
        """Ex-date dividend history per symbol (Yahoo), cached a day; a failed fetch keeps the old copy."""
        now = datetime.now(UTC)
        fresh: dict[str, list] = {}
        stale: dict[str, list] = {}
        with session_scope(self.engine) as s:
            for row in s.scalars(select(DividendHistory).where(DividendHistory.symbol.in_(symbols))):
                (fresh if now - row.as_of < self.DIVIDEND_MAX_AGE else stale)[row.symbol] = [tuple(x) for x in row.data]
        yahoo = self.market.profile_provider
        todo = [x for x in symbols if x not in fresh]
        if yahoo is not None and todo:
            def fetch(sym):
                try:
                    return yahoo.get_dividends(sym)
                except ProviderError:
                    return None
            with ThreadPoolExecutor(max_workers=8) as pool:
                fetched = dict(zip(todo, pool.map(fetch, todo)))
            with session_scope(self.engine) as s:
                for sym, rows in fetched.items():
                    if rows is not None:
                        s.merge(DividendHistory(symbol=sym, as_of=now, data=[list(x) for x in rows]))
                        fresh[sym] = rows
        return {sym: fresh.get(sym) or stale.get(sym, []) for sym in symbols}

    def dividends(self, ref: str, live_quotes: dict[str, Quote] | None = None) -> dict:
        """Forward dividend income and yield per holding, plus this year's dividends: estimated
        received so far (shares held at each ex-date) and projected for the rest of the year."""
        summ = self.portfolio(ref, True, False, live_quotes)
        rows = summ["positions"]
        p = self.portfolios.view(ref)
        by_sym: dict[str, list] = {}
        for t in self.portfolios.active_transactions(p.id if p.id is not None else ALL):
            by_sym.setdefault(t.symbol, []).append(t)

        def qty_at(sym: str, d: date) -> float:
            cutoff = datetime.combine(d, datetime.min.time(), NY)
            pos = build_positions([t for t in by_sym.get(sym, []) if t.ts < cutoff]).get(sym)
            return pos.qty if pos else 0.0

        histories = self.dividend_histories([r["symbol"] for r in rows])
        return {"portfolio": summ["portfolio"]["name"],
                **dividends_mod.analyze(rows, histories, qty_at, datetime.now(NY).date())}

    def earnings_overview(self, ref: str) -> dict:
        """Per holding: the last reported quarter (EPS/revenue vs estimate) and the next report date."""
        p = self.portfolios.view(ref)
        state = self.portfolios.positions(p.id if p.id is not None else ALL)
        syms = sorted(s for s, pos in state.items() if pos.is_open)
        failed = self.events.refresh(syms)["failed"]
        today = datetime.now(NY).date()
        rows = self.events.between(syms, today - timedelta(days=120), today + timedelta(days=120), ["earnings"])
        out: dict[str, dict] = {s: {"symbol": s, "last": None, "next": None} for s in syms}
        for e in rows:  # ordered by date
            o = out[e["symbol"]]
            if e["date"] <= today.isoformat() and e.get("epsActual") is not None:
                o["last"] = e
            elif e["date"] >= today.isoformat() and o["next"] is None:
                o["next"] = e
        # The free calendar only reaches a few weeks back; fill older last reports from EPS history.
        with session_scope(self.engine) as s:
            funds = {i.symbol for i in s.scalars(select(Instrument).where(Instrument.symbol.in_(syms)))
                     if i.type == "ETP" or i.sector == "ETF"}
        missing = [x for x in syms if out[x]["last"] is None and x not in funds]
        for sym, r in self.events.latest_results(missing).items():
            out[sym]["last"] = {"symbol": sym, "kind": "earnings", "date": None, **r, "source": "finnhub"}
        return {"portfolio": p.name, "as_of": today.isoformat(), "rows": list(out.values()), "refresh_failed": failed}

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
        p = self.portfolios.view(ref)
        txns = self.portfolios.active_transactions(p.id if p.id is not None else ALL)
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
                         dry_run: bool = True, validate_symbols: bool = True, text: str | None = None) -> dict:
        """Import an Investing.com export from `path`, or from `text` (an upload; `path` then only names it)."""
        parsed = investing.parse_investing_text(text, path.name) if text is not None else investing.parse_investing_csv(path)
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
