"""Database schema.

Transactions are the source of truth; lots and positions are derived from them
(see `argus.services.lots`). Market data tables are caches and can be dropped.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Stores UTC; always returns aware datetimes (SQLite itself keeps no timezone)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime; pass an aware datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    type_annotation_map = {datetime: UTCDateTime}


class TxnType(StrEnum):
    OPENING = "OPENING"  # holding owned before import: cost kept, performance starts at that day's value
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"  # cash amount in `amount`
    SPLIT = "SPLIT"  # ratio (new shares per old share) in `qty`
    FEE = "FEE"  # cash amount in `amount`


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    benchmark: Mapped[str] = mapped_column(String(16), default="SPY")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="portfolio")


class Instrument(Base):
    __tablename__ = "instrument"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(200))
    exchange: Mapped[str | None] = mapped_column(String(32))
    type: Mapped[str | None] = mapped_column(String(32))  # e.g. "Common Stock", "ETP", "ADR"
    sector: Mapped[str | None] = mapped_column(String(80))
    industry: Mapped[str | None] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Transaction(Base):
    __tablename__ = "txn"
    __table_args__ = (UniqueConstraint("portfolio_id", "external_id", name="uq_txn_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"), index=True)
    type: Mapped[str] = mapped_column(String(12))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    ts: Mapped[datetime] = mapped_column(index=True)
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="cli")  # ui | cli | mcp | import
    # Idempotency key: a retried write with the same key is a no-op.
    external_id: Mapped[str | None] = mapped_column(String(200))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    portfolio: Mapped[Portfolio] = relationship(back_populates="transactions")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(default=utcnow)
    actor: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)


class QuoteCache(Base):
    __tablename__ = "quote"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    price: Mapped[float] = mapped_column(Float)
    prev_close: Mapped[float | None] = mapped_column(Float)
    open: Mapped[float | None] = mapped_column(Float)
    high: Mapped[float | None] = mapped_column(Float)
    low: Mapped[float | None] = mapped_column(Float)
    as_of: Mapped[datetime] = mapped_column()
    source: Mapped[str] = mapped_column(String(16))
    delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(default=utcnow)


class PriceBar(Base):
    __tablename__ = "price_bar"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    interval: Mapped[str] = mapped_column(String(8), primary_key=True)
    ts: Mapped[datetime] = mapped_column(primary_key=True)
    o: Mapped[float] = mapped_column(Float)
    h: Mapped[float] = mapped_column(Float)
    l: Mapped[float] = mapped_column(Float)  # noqa: E741
    c: Mapped[float] = mapped_column(Float)
    v: Mapped[float] = mapped_column(Float)


class Fundamental(Base):
    __tablename__ = "fundamental"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    as_of: Mapped[datetime] = mapped_column()
    metrics: Mapped[dict] = mapped_column(JSON)
    sources: Mapped[dict] = mapped_column(JSON)  # metric name -> provider


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)


class WatchlistItem(Base):
    __tablename__ = "watchlist_item"

    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlist.id"), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    note: Mapped[str | None] = mapped_column(Text)
    added_at: Mapped[datetime] = mapped_column(default=utcnow)


class Event(Base):
    """Scheduled or reported corporate events (earnings, dividends), cached from providers."""

    __tablename__ = "event"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)  # earnings | ex_dividend | dividend_pay
    d: Mapped[date] = mapped_column(Date, primary_key=True)
    hour: Mapped[str | None] = mapped_column(String(8))  # bmo | amc | dmh (earnings timing)
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # estimates, actuals, surprise, amount...
    source: Mapped[str] = mapped_column(String(16))
    fetched_at: Mapped[datetime] = mapped_column(default=utcnow)


class Alert(Base):
    __tablename__ = "alert"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    kind: Mapped[str] = mapped_column(String(24))  # see argus.services.alerts.KINDS
    threshold: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str] = mapped_column(String(16), default="cli")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AlertEvent(Base):
    """One firing of an alert; at most one per alert per trading session."""

    __tablename__ = "alert_event"
    __table_args__ = (UniqueConstraint("alert_id", "session_date", name="uq_alert_session"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alert.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date)
    ts: Mapped[datetime] = mapped_column(default=utcnow)
    value: Mapped[float | None] = mapped_column(Float)
    message: Mapped[str] = mapped_column(Text)


class Note(Base):
    """Investment thesis or free-form note on a symbol, optionally with a review date."""

    __tablename__ = "note"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    kind: Mapped[str] = mapped_column(String(12), default="note")  # thesis | note
    text: Mapped[str] = mapped_column(Text)
    review_on: Mapped[date | None] = mapped_column(Date)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str] = mapped_column(String(16), default="cli")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class RefreshLog(Base):
    """When a cached dataset was last refreshed (e.g. 'events:NVDA')."""

    __tablename__ = "refresh_log"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    at: Mapped[datetime] = mapped_column(default=utcnow)


class Target(Base):
    """Target weight for a symbol or a sector within a portfolio."""

    __tablename__ = "target"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"), primary_key=True)
    level: Mapped[str] = mapped_column(String(8), primary_key=True)  # symbol | sector
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    weight_pct: Mapped[float] = mapped_column(Float)


class FundProfile(Base):
    """ETF sector weights and top holdings (Yahoo), for look-through exposure."""

    __tablename__ = "fund_profile"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    as_of: Mapped[datetime] = mapped_column(default=utcnow)
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # {"sectors": {...}, "top_holdings": [...]}


class CompanyProfile(Base):
    """Company facts (Yahoo + Finnhub) and suggested peers, cached for a week."""

    __tablename__ = "company_profile"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    as_of: Mapped[datetime] = mapped_column(default=utcnow)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class SecurityMap(Base):
    """ISIN/CUSIP -> exchange ticker (OpenFIGI), for N-PORT holdings. symbol None = no usable listing."""

    __tablename__ = "security_map"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    ticker: Mapped[str | None] = mapped_column(String(32))
    exchange: Mapped[str | None] = mapped_column(String(8))
    symbol: Mapped[str | None] = mapped_column(String(32))  # Yahoo form; US listings in canonical form
    as_of: Mapped[datetime] = mapped_column(default=utcnow)


class PeerList(Base):
    """Your own peer list for a symbol; without one, the suggested peers are shown."""

    __tablename__ = "peer_list"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    peers: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class NavDaily(Base):
    """Filled in P1 by the performance engine."""

    __tablename__ = "nav_daily"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id"), primary_key=True)
    d: Mapped[date] = mapped_column(Date, primary_key=True)
    market_value: Mapped[float] = mapped_column(Float)
    net_flow: Mapped[float] = mapped_column(Float, default=0.0)
    income: Mapped[float] = mapped_column(Float, default=0.0)


__all__ = [
    "Alert",
    "AlertEvent",
    "AuditLog",
    "CompanyProfile",
    "Event",
    "Note",
    "Base",
    "FundProfile",
    "Fundamental",
    "Instrument",
    "NavDaily",
    "PeerList",
    "Portfolio",
    "PriceBar",
    "RefreshLog",
    "SecurityMap",
    "Target",
    "QuoteCache",
    "Transaction",
    "TxnType",
    "Watchlist",
    "WatchlistItem",
    "utcnow",
]
