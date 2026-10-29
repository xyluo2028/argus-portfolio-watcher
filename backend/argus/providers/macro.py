"""Market-wide data: index/commodity/currency history (Yahoo), the Treasury yield curve (treasury.gov),
FOMC meeting dates (federalreserve.gov) and US economic releases (Nasdaq's calendar). All free and
keyless; each piece is cached in memory and fails on its own.
"""

from __future__ import annotations

import csv
import html
import io
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from argus.providers.base import ProviderError

log = logging.getLogger("argus.macro")

TREASURY_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
FED_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
NASDAQ_URL = "https://api.nasdaq.com/api/calendar/economicevents"
# By first three letters: the Fed writes "January" but also "Apr/May", "Oct/Nov" for meetings across a month end.
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
# Nasdaq's calendar is off from what it looks like. The "gmt" column is a clock time at a fixed UTC-4
# (EDT) all year, so in winter it runs an hour ahead of New York (payrolls at "09:30"). And `?date=D`
# usually returns the releases of the day before D, but some dates answer with D's own (cached per date,
# it seems): a Monday query with Monday's releases, or two queries in a row with the same rows.
# Checked against the raw feed in Oct 2026 (B-006); `_nasdaq_days` sorts out which day each answer is.
NASDAQ_LAG = timedelta(days=1)
NASDAQ_TZ = timezone(timedelta(hours=-4))
NY = ZoneInfo("America/New_York")
TENORS = ["1 Mo", "2 Mo", "3 Mo", "4 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]


class MacroProvider:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=20, follow_redirects=True,
                                              headers={"User-Agent": "Mozilla/5.0 (argus portfolio monitor)",
                                                       "Accept": "application/json, text/csv, text/html"})
        self._cache: dict[str, tuple[float, object]] = {}
        self._lock = threading.Lock()

    def _memo(self, key: str, ttl: float, fn):
        with self._lock:
            hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < ttl:
            return hit[1]
        try:
            value = fn()
        except Exception as e:  # noqa: BLE001
            if hit:  # stale beats nothing
                log.warning("%s refresh failed, serving cached: %s", key, e)
                return hit[1]
            raise ProviderError(f"{key}: {e}") from e
        with self._lock:
            self._cache[key] = (time.monotonic(), value)
        return value

    # -- prices ------------------------------------------------------------------------------
    def closes(self, symbols: list[str], period: str = "13mo") -> dict[str, dict[date, float]]:
        """Daily closes for Yahoo symbols as given (^VIX, JPY=X, CL=F...), one batch download."""
        def fetch():
            from argus.providers.yahoo import _yf

            df = _yf().download(symbols, period=period, interval="1d", auto_adjust=False, group_by="ticker",
                             progress=False, threads=True)
            out: dict[str, dict[date, float]] = {}
            for s in symbols:
                try:
                    col = df[s]["Close"].dropna()
                except KeyError:
                    continue
                out[s] = {ts.date(): float(v) for ts, v in col.items()}
            return out
        return self._memo(f"closes:{','.join(symbols)}:{period}", 15 * 60, fetch)

    def quote_rows(self, symbols: list[str], fields: str, ttl: float = 5 * 60) -> list[dict]:
        """Yahoo batch quote rows (100 symbols per request) for a fixed list, e.g. the breadth universe."""
        from argus.providers.yahoo import YahooProvider

        return self._memo(f"quotes:{len(symbols)}:{hash(tuple(symbols))}:{fields}", ttl,
                          lambda: YahooProvider._quote_rows(symbols, fields))

    # -- Treasury curve ----------------------------------------------------------------------
    def treasury_curve(self) -> dict[date, dict[str, float]]:
        """{date: {tenor: yield %}} for this year and last year (par yield curve, daily)."""
        def fetch():
            out: dict[date, dict[str, float]] = {}
            year = date.today().year
            for y in (year - 1, year):
                r = self._client.get(TREASURY_URL.format(year=y), params={
                    "type": "daily_treasury_yield_curve", "field_tdr_date_value": str(y), "page": "", "_format": "csv"})
                r.raise_for_status()
                for row in csv.DictReader(io.StringIO(r.text)):
                    d = datetime.strptime(row["Date"], "%m/%d/%Y").date()
                    out[d] = {t: float(row[t]) for t in TENORS if row.get(t) not in (None, "")}
            return out
        return self._memo("treasury", 6 * 3600, fetch)

    # -- FOMC --------------------------------------------------------------------------------
    def fomc_meetings(self) -> list[dict]:
        """Scheduled FOMC meetings (this year and next, as far as published). `projections` marks the
        meetings with a Summary of Economic Projections (dot plot)."""
        def fetch():
            text = self._client.get(FED_URL).text
            out = []
            for year in (date.today().year, date.today().year + 1):
                start = text.find(f"{year} FOMC Meetings")
                if start < 0:
                    continue
                end = text.find(" FOMC Meetings", start + 20)
                section = text[start:end if end > 0 else None]
                for month, days in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<',
                                              section, re.S):
                    names = [x.strip() for x in month.split("/")]
                    keys = [n[:3].lower() for n in names]
                    nums = re.findall(r"\d+", days)
                    if any(k not in MONTHS for k in keys) or not nums:
                        continue
                    m, first_m = MONTHS[keys[-1]], MONTHS[keys[0]]
                    last = int(nums[-1])
                    if len(keys) == 1 and len(nums) == 2 and int(nums[1]) < int(nums[0]):  # "31-1" under one month name
                        m = m % 12 + 1
                    rolls = m < first_m  # "Dec/Jan": the meeting ends in January of the next year
                    month = names[-1]
                    out.append({"date": date(year + rolls, m, last).isoformat(), "days": days.replace("*", "").strip(),
                                "month": month, "projections": "*" in days})
            return out
        return self._memo("fomc", 24 * 3600, fetch)

    # -- US economic releases ----------------------------------------------------------------
    @staticmethod
    def nasdaq_slot(day: date, gmt: str | None) -> tuple[date, str | None]:
        """(New York date, "HH:MM" Eastern) for a row of Nasdaq's calendar for `day`. Non-clock values
        ("All Day", "Tentative") keep the day and the text as is."""
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", gmt or "")
        if not m:
            return day, gmt
        t = datetime(day.year, day.month, day.day, int(m[1]), int(m[2]), tzinfo=NASDAQ_TZ).astimezone(NY)
        return t.date(), t.strftime("%H:%M")

    @staticmethod
    def _nasdaq_days(queries: list[date], per_day: list[list[dict]]) -> list[tuple[date, list[dict]]]:
        """(release day, rows) for the answers to consecutive daily queries.
        A query answers with the day before (the usual case) or its own day. Its own day when: the next
        query repeats its rows; it's a Monday with releases (the day before is Sunday); or the query
        before answered with its own day and this one doesn't repeat it (a query never skips a day)."""
        sig = lambda rows: [(x["gmt"], x["eventName"]) for x in rows]  # noqa: E731  actuals fill in between fetches
        out, own_prev = [], False
        for i, (q, rows) in enumerate(zip(queries, per_day)):
            if i and rows and sig(rows) == sig(per_day[i - 1]):
                own_prev = False  # the copy of the previous answer, already placed
                continue
            repeated = i + 1 < len(per_day) and sig(rows) == sig(per_day[i + 1])
            own = (bool(rows) and (repeated or q.weekday() == 0)) or (own_prev and bool(per_day[i - 1]))
            out.append((q if own else q - NASDAQ_LAG, rows))
            own_prev = own
        return out

    def economic_events(self, days: int = 21) -> list[dict]:
        """US releases from Nasdaq's economic calendar for today and the next `days` days. Times are
        Eastern; values are as published ("1,716K", "3.6%")."""
        clean = lambda v: (html.unescape(v or "").strip() or None)  # noqa: E731

        def day(d: date) -> list[dict]:
            r = self._client.get(NASDAQ_URL, params={"date": d.isoformat()})
            r.raise_for_status()
            rows = ((r.json().get("data") or {}).get("rows")) or []
            return [{k: clean(x.get(k)) for k in ("gmt", "eventName", "actual", "consensus", "previous")}
                    for x in rows if x.get("country") == "United States" and x.get("eventName")]

        # New York's date, not the server's (UTC): after 8 pm ET the UTC date is already tomorrow and
        # today's releases, with their actuals, would drop off (B-034). In the key so the window rolls
        # at New York midnight rather than whenever the 6 h cache expires.
        today = datetime.now(NY).date()

        def fetch():
            # From today's query (yesterday's or today's rows) to one past the last day, to compare with.
            queries = [today + timedelta(days=i) for i in range(days + 3)]
            with ThreadPoolExecutor(max_workers=7) as pool:
                per_day = list(pool.map(day, queries))
            out = []
            for d, rows in self._nasdaq_days(queries, per_day):
                if not today <= d <= today + timedelta(days=days):
                    continue
                for x in rows:
                    when, time_et = self.nasdaq_slot(d, x["gmt"])
                    out.append({"date": when.isoformat(), "time_et": time_et, "event": x["eventName"],
                                "actual": x["actual"], "consensus": x["consensus"], "previous": x["previous"]})
            return out
        return self._memo(f"econ:{days}:{today.isoformat()}", 6 * 3600, fetch)
