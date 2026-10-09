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
    openfigi_api_key: str | None = None
    # 8765 is a common default for other local tools; 8787 avoids the clash.
    port: int = 8787
    host: str = "127.0.0.1"
    # Hostnames answered besides localhost (a tunnel's name, e.g. argus.tail1234.ts.net).
    allowed_hosts: tuple[str, ...] = ()
    # Shared secret for the UI, API and MCP; None = no auth (only for loopback-only use).
    token: str | None = None
    # Allow a non-loopback listen address without a token: only for a container whose port is
    # published on the host's loopback (compose.yaml), where the network is the boundary.
    insecure_bind: bool = False
    backup_keep: int = 14
    # Live WebSocket prices (Finnhub allows one connection per key); off = REST polling only, e.g. for
    # a second instance that must not take the stream from the main one.
    stream: bool = True
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
        openfigi_api_key=os.environ.get("OPENFIGI_API_KEY") or None,
        port=int(os.environ.get("ARGUS_PORT") or 8787),
        host=os.environ.get("ARGUS_HOST") or "127.0.0.1",
        allowed_hosts=tuple(h.strip().lower() for h in (os.environ.get("ARGUS_ALLOWED_HOSTS") or "").split(",") if h.strip()),
        token=os.environ.get("ARGUS_TOKEN") or None,
        insecure_bind=(os.environ.get("ARGUS_INSECURE_BIND") or "").lower() in ("1", "true", "yes"),
        backup_keep=int(os.environ.get("ARGUS_BACKUP_KEEP") or 14),
        stream=(os.environ.get("ARGUS_STREAM") or "on").lower() not in ("off", "0", "false", "no"),
    )
