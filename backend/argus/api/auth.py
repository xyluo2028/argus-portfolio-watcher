"""Shared-token access control for the API, the live stream and MCP.

With `ARGUS_TOKEN` set, every `/api/*` and `/mcp*` request must carry the token, either as
`Authorization: Bearer <token>` (MCP clients, scripts) or in the `argus_token` cookie the UI gets
from `POST /api/auth/login`. The UI's static files, `/api/health` and the auth endpoints stay
public: they hold no portfolio data. Without a token configured, everything is open, which is only
acceptable while the server listens on loopback (see `serve`).
"""

from __future__ import annotations

import hmac
import json
from http.cookies import SimpleCookie

COOKIE = "argus_token"
COOKIE_MAX_AGE = 90 * 24 * 3600
PUBLIC_PATHS = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/logout"}


def token_ok(expected: str | None, given: str | None) -> bool:
    return bool(expected) and bool(given) and hmac.compare_digest(expected.encode(), given.encode())


def request_token(headers: dict[str, str]) -> str | None:
    auth = headers.get("authorization", "")
    if auth[:7].lower() == "bearer ":
        return auth[7:].strip()
    cookie = SimpleCookie()
    try:
        cookie.load(headers.get("cookie", ""))
    except Exception:  # noqa: BLE001 - malformed cookie header: treat as absent
        return None
    return cookie[COOKIE].value if COOKIE in cookie else None


def protected(path: str) -> bool:
    return (path.startswith("/api/") or path == "/mcp" or path.startswith("/mcp/")) and path not in PUBLIC_PATHS


class TokenAuthMiddleware:
    """Pure ASGI, so streaming responses (SSE, MCP) pass through untouched."""

    def __init__(self, app, token: str | None):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if not self.token or scope["type"] not in ("http", "websocket") or not protected(scope.get("path", "")):
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        if token_ok(self.token, request_token(headers)):
            return await self.app(scope, receive, send)
        if scope["type"] == "websocket":
            return await send({"type": "websocket.close", "code": 4401})
        body = json.dumps({"error": {"code": "UNAUTHORIZED", "message": "Sign in to Argus.",
                                     "hint": "Send 'Authorization: Bearer <ARGUS_TOKEN>' or sign in in the web UI."}}).encode()
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
