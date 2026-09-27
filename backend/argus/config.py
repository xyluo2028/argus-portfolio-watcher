"""Runtime configuration, read from environment variables and the repo-root `.env`."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    finnhub_api_key: str | None
    sec_user_agent: str | None
    # 8765 is a common default for other local tools; 8787 avoids the clash.
    port: int = 8787
    # A cached quote younger than this is served without hitting a provider.
    quote_max_age_s: int = 15
    fundamentals_max_age_s: int = 24 * 3600

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("ARGUS_DATA_DIR", REPO_ROOT / "data"))
    db_path = Path(os.environ.get("ARGUS_DB", data_dir / "argus.sqlite"))
    return Settings(
        data_dir=data_dir,
        db_path=db_path,
        finnhub_api_key=os.environ.get("FINNHUB_API_KEY") or None,
        sec_user_agent=os.environ.get("SEC_USER_AGENT") or None,
        port=int(os.environ.get("ARGUS_PORT") or 8787),
    )
