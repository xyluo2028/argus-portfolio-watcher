"""A single error type with a stable code, so CLI and MCP callers can branch on it."""

from __future__ import annotations


class ArgusError(Exception):
    def __init__(self, code: str, message: str, hint: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint

    def to_dict(self) -> dict:
        out = {"code": self.code, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        return out
