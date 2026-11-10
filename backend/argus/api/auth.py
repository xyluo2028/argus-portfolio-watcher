"""Access control for the API, the live stream and MCP.

Sign-in is on once any account exists (argus.services.accounts) or `ARGUS_TOKEN` is set. Every
`/api/*` and `/mcp*` request must then carry one of:
- `Authorization: Bearer <key>`: an account's API key (bots, scripts, MCP clients) or the server token;
- the `argus_session` cookie the UI gets from signing in with a username and password;
- the `argus_token` cookie the UI gets from signing in with the server token.
The server token acts as the oldest account. The UI's static files, `/api/health` and the auth
endpoints stay public: they hold no portfolio data. (`/api/auth/setup` makes the first account only,
and asks for the token when one is set; `/api/auth/signup` makes any later one, which starts empty.) With neither accounts nor a token, everything is
open, which is only acceptable while the server listens on loopback (see `serve`).

The middleware leaves who the request acts as in `scope["state"]["principal"]`, and runs the request
as that account (argus.access), so it sees only that account's records.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import threading
import time
from http.cookies import SimpleCookie

from argus import access
from argus.services.accounts import AccountService, Principal

TOKEN_COOKIE = "argus_token"
SESSION_COOKIE = "argus_session"
COOKIE_MAX_AGE = 90 * 24 * 3600
PUBLIC_PATHS = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/logout", "/api/auth/setup",
                "/api/auth/signup"}
OPEN = Principal(None, None, "open")


def token_ok(expected: str | None, given: str | None) -> bool:
    return bool(expected) and bool(given) and hmac.compare_digest(expected.encode(), given.encode())


def credentials(headers: dict[str, str]) -> tuple[str | None, str | None, str | None]:
    """(bearer, session cookie, token cookie) from lower-cased request headers."""
    auth = headers.get("authorization", "")
    bearer = (auth[7:].strip() or None) if auth[:7].lower() == "bearer " else None
    cookie = SimpleCookie()
    try:
        cookie.load(headers.get("cookie", ""))
    except Exception:  # noqa: BLE001 - malformed cookie header: treat as absent
        return bearer, None, None
    value = lambda name: cookie[name].value if name in cookie else None  # noqa: E731
    return bearer, value(SESSION_COOKIE), value(TOKEN_COOKIE)


def protected(path: str) -> bool:
    return (path.startswith("/api/") or path == "/mcp" or path.startswith("/mcp/")) and path not in PUBLIC_PATHS


class Authenticator:
    """Turns a request's credentials into a Principal. Synchronous (it reads SQLite): call it off the event loop."""

    def __init__(self, token: str | None, accounts: AccountService):
        self.token = token
        self.accounts = accounts

    def required(self) -> bool:
        return bool(self.token) or self.accounts.exist()

    def identify(self, headers: dict[str, str]) -> Principal | None:
        bearer, session, token_cookie = credentials(headers)
        if bearer:
            return self.accounts.first() if token_ok(self.token, bearer) else self.accounts.key_principal(bearer)
        if session and (p := self.accounts.session_principal(session)):
            return p
        if token_ok(self.token, token_cookie):
            return self.accounts.first()
        return None

    def check(self, headers: dict[str, str]) -> Principal | None:
        """Who the request acts as, or None when it must be refused."""
        p = self.identify(headers)
        return p if p is not None or self.required() else OPEN


class LoginThrottle:
    """Refuse sign-in for a name after `limit` failures within `window_s` (on top of the per-try delay)."""

    def __init__(self, limit: int = 10, window_s: float = 15 * 60):
        self.limit = limit
        self.window_s = window_s
        self._fails: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str) -> list[float]:
        cutoff = time.monotonic() - self.window_s
        fails = self._fails[key] = [t for t in self._fails.get(key, []) if t > cutoff]
        return fails

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._recent(key)) >= self.limit

    def failed(self, key: str) -> None:
        with self._lock:
            self._recent(key).append(time.monotonic())

    def succeeded(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


class AuthMiddleware:
    """Pure ASGI, so streaming responses (SSE, MCP) pass through untouched."""

    def __init__(self, app, auth: Authenticator):
        self.app = app
        self.auth = auth

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not protected(scope.get("path", "")):
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        principal = await asyncio.to_thread(self.auth.check, headers)
        if principal is not None:
            scope.setdefault("state", {})["principal"] = principal
            with access.acting_as(principal.account_id):
                return await self.app(scope, receive, send)
        if scope["type"] == "websocket":
            return await send({"type": "websocket.close", "code": 4401})
        body = json.dumps({"error": {"code": "UNAUTHORIZED", "message": "Sign in to Argus.",
                                     "hint": "Sign in in the web UI, or send 'Authorization: Bearer <API key>' "
                                             "(see `argus key create`)."}}).encode()
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
