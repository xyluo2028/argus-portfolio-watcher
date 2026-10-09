"""Daily Fama-French factors from Kenneth French's data library (free, no key).

Five factors (Mkt-RF, SMB, HML, RMW, CMA, plus RF) and momentum (Mom), as daily decimal returns.
The library updates monthly with a lag of a month or two, so the latest days are missing; a
one-year regression only needs the overlap. Cached on disk for a week.
"""

from __future__ import annotations

import io
import json
import re
import time
import zipfile
from datetime import date
from pathlib import Path

import httpx

from argus.providers.base import ProviderError

BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = {"ff5": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", "mom": "F-F_Momentum_Factor_daily_CSV.zip"}
MAX_AGE_S = 7 * 24 * 3600
FACTORS = ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom")


def parse_csv(text: str) -> dict[str, dict[str, float]]:
    """{YYYY-MM-DD: {column: decimal return}} from a French daily CSV (percent values, header row
    before the data, footnotes after)."""
    out: dict[str, dict[str, float]] = {}
    header: list[str] | None = None
    for line in text.splitlines():
        cells = [c.strip() for c in line.split(",")]
        if header is None and len(cells) > 1 and cells[0] == "" and any(cells[1:]):
            header = cells[1:]
            continue
        if header and re.fullmatch(r"\d{8}", cells[0]):
            d = f"{cells[0][:4]}-{cells[0][4:6]}-{cells[0][6:]}"
            out[d] = {h: float(v) / 100 for h, v in zip(header, cells[1:]) if v not in ("", "-99.99", "-999")}
    return out


class FrenchFactors:
    def __init__(self, cache_dir: Path | None = None, client: httpx.Client | None = None):
        self._cache = cache_dir / "french_factors.json" if cache_dir else None
        self._client = client or httpx.Client(timeout=30, follow_redirects=True,
                                              headers={"User-Agent": "argus portfolio monitor"})

    def daily(self) -> dict[date, dict[str, float]]:
        """{date: {"Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom", "RF"}} as decimals."""
        rows = None
        if self._cache and self._cache.exists() and time.time() - self._cache.stat().st_mtime < MAX_AGE_S:
            rows = json.loads(self._cache.read_text())
        if rows is None:
            rows = {}
            for name in ("ff5", "mom"):
                try:
                    r = self._client.get(BASE + FILES[name])
                    r.raise_for_status()
                    z = zipfile.ZipFile(io.BytesIO(r.content))
                    text = z.read(z.namelist()[0]).decode("latin-1")
                except (httpx.HTTPError, zipfile.BadZipFile, KeyError) as e:
                    if self._cache and self._cache.exists():  # stale beats nothing
                        rows = json.loads(self._cache.read_text())
                        break
                    raise ProviderError(f"French data library: {e}") from e
                for d, vals in parse_csv(text).items():
                    rows.setdefault(d, {}).update({("Mom" if k.lower().startswith("mom") else k): v for k, v in vals.items()})
            else:
                if self._cache:
                    self._cache.parent.mkdir(parents=True, exist_ok=True)
                    self._cache.write_text(json.dumps(rows))
        return {date.fromisoformat(d): v for d, v in rows.items() if all(f in v for f in (*FACTORS, "RF"))}
