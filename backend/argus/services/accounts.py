"""Accounts that sign in to Argus: a password for the web UI, API keys for bots, scripts and MCP.

There is one kind of account; a bot is an account you create for it. No secret is stored as given:
passwords as scrypt hashes, session ids and API keys as SHA-256 (they are long and random, so a fast
hash is enough to make a stolen database useless for signing in). Once any account exists, every
request has to sign in, from this machine too (see argus.api.auth). Each account sees only its own
records (argus.access); the first one takes over what was recorded before it.

Who can make accounts: the CLI (whoever has a shell here can read the database anyway); the web
UI's first-run setup while there are none (with ARGUS_TOKEN when it is set); and after that the
owner, the oldest account, signed in with its password or the token (never an API key).
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, delete, func, select, update

from argus.db import session_scope
from argus.errors import ArgusError
from argus.access import NOBODY
from argus.models import OWNED, Account, ApiKey, AuditLog, LoginSession

USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")
MIN_PASSWORD = 8
SESSION_DAYS = 90
KEY_PREFIX = "argus_"
LAST_USED_EVERY = timedelta(minutes=5)  # how stale a key's last_used_at may get (saves a write per request)
# scrypt cost: ~50 ms and 16 MB per check, enough to make guessing a stolen hash slow.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        want = base64.b64decode(digest)
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                             dklen=len(want))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, want)


@functools.cache
def _dummy_hash() -> str:
    """Checked against when the username is unknown, so a wrong name takes as long as a wrong password."""
    return hash_password(secrets.token_hex(8))


def _sha(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=UTC)


@dataclass(frozen=True)
class Principal:
    """Who a request acts as. `account_id` is None only for the server token before any account
    exists, and for open mode (no token, no accounts)."""

    account_id: int | None
    username: str | None
    via: str  # session | key | token | open


def account_to_dict(a: Account) -> dict:
    return {"id": a.id, "username": a.username, "has_password": a.password_hash is not None,
            "disabled": a.disabled, "created_at": a.created_at.isoformat()}


def key_to_dict(k: ApiKey, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    expired = k.expires_at is not None and _aware(k.expires_at) <= now
    return {"id": k.id, "account_id": k.account_id, "name": k.name, "prefix": k.prefix,
            "created_at": k.created_at.isoformat(),
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            "active": k.revoked_at is None and not expired}


def claim_unowned(s, account_id: int) -> dict[str, int]:
    """Give `account_id` everything recorded while no account existed (owner 0)."""
    out = {}
    for model in OWNED:
        n = s.execute(update(model).where(model.account_id == NOBODY).values(account_id=account_id)).rowcount
        if n:
            out[model.__tablename__] = n
    return out


def normalize_username(username: str) -> str:
    name = (username or "").strip().lower()
    if not USERNAME.match(name):
        raise ArgusError("INVALID_ARG", f"'{username}' is not a valid username.",
                         hint="Up to 40 characters: letters, digits, '.', '_' or '-', starting with a letter or digit.")
    return name


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise ArgusError("INVALID_ARG", f"Password must be at least {MIN_PASSWORD} characters.")


class AccountService:
    def __init__(self, engine: Engine):
        self.engine = engine

    @staticmethod
    def _find(s, ref: str | int) -> Account:
        a = s.get(Account, ref) if isinstance(ref, int) else s.scalar(
            select(Account).where(Account.username == (ref or "").strip().lower()))
        if a is None:
            raise ArgusError("NOT_FOUND", f"No account '{ref}'.", hint="See `argus user list`.")
        return a

    def exist(self) -> bool:
        """Whether sign-in is on: any account, disabled ones too (disabling the last one must not open the door)."""
        with session_scope(self.engine) as s:
            return s.scalar(select(Account.id).limit(1)) is not None

    def first(self) -> Principal:
        """Who the server token (ARGUS_TOKEN) acts as: the oldest account, or nobody before one exists."""
        with session_scope(self.engine) as s:
            a = s.scalar(select(Account).order_by(Account.id).limit(1))
            return Principal(a.id, a.username, "token") if a else Principal(None, None, "token")

    # -- accounts ---------------------------------------------------------------------
    def is_owner(self, account_id: int | None) -> bool:
        """The oldest account: the one that can manage the others from the web UI."""
        return account_id is not None and self.first().account_id == account_id

    def create(self, username: str, password: str | None, actor: str = "cli", only_first: bool = False) -> dict:
        """Make an account. `only_first`: refuse once any exists (the web UI's first-run setup)."""
        name = normalize_username(username)
        if password is not None:
            _check_password(password)
        with session_scope(self.engine) as s:
            first = s.scalar(select(Account.id).limit(1)) is None
            if only_first and not first:
                raise ArgusError("ALREADY_EXISTS", "Argus already has an account.",
                                 hint="Sign in with it; its owner can add more on the Account page.")
            if s.scalar(select(Account).where(Account.username == name)):
                raise ArgusError("ALREADY_EXISTS", f"Account '{name}' already exists.")
            a = Account(username=name, password_hash=hash_password(password) if password is not None else None)
            s.add(a)
            s.flush()
            claimed = claim_unowned(s, a.id) if first else {}
            s.add(AuditLog(actor=actor, action="create", entity="account", entity_id=str(a.id),
                           after={"username": name, "has_password": password is not None, "claimed": claimed}))
            return account_to_dict(a) | {"first": first, "claimed": claimed}

    def list_accounts(self) -> list[dict]:
        with session_scope(self.engine) as s:
            keys = dict(s.execute(select(ApiKey.account_id, func.count()).where(ApiKey.revoked_at.is_(None))
                                  .group_by(ApiKey.account_id)).all())
            return [account_to_dict(a) | {"keys": keys.get(a.id, 0)}
                    for a in s.scalars(select(Account).order_by(Account.id))]

    def get(self, ref: str | int) -> dict:
        with session_scope(self.engine) as s:
            return account_to_dict(self._find(s, ref))

    def set_password(self, ref: str | int, password: str, keep_session: str | None = None,
                     actor: str = "cli") -> dict:
        """Set a new password and sign out every web session but `keep_session` (the caller's own)."""
        _check_password(password)
        with session_scope(self.engine) as s:
            a = self._find(s, ref)
            a.password_hash = hash_password(password)
            q = delete(LoginSession).where(LoginSession.account_id == a.id)
            if keep_session:
                q = q.where(LoginSession.id_hash != _sha(keep_session))
            ended = s.execute(q).rowcount
            s.add(AuditLog(actor=actor, action="set_password", entity="account", entity_id=str(a.id)))
            return account_to_dict(a) | {"sessions_ended": ended}

    def change_password(self, account_id: int, current: str, new: str, keep_session: str | None = None,
                        actor: str = "ui") -> dict:
        with session_scope(self.engine) as s:
            a = self._find(s, account_id)
            ok = a.password_hash is not None and verify_password(current, a.password_hash)
        if not ok:
            raise ArgusError("WRONG_PASSWORD", "Current password is wrong.")
        return self.set_password(account_id, new, keep_session, actor)

    def set_disabled(self, ref: str | int, disabled: bool, actor: str = "cli") -> dict:
        """A disabled account can't sign in, and its sessions and keys stop working (they come back on enable)."""
        with session_scope(self.engine) as s:
            a = self._find(s, ref)
            a.disabled = disabled
            s.add(AuditLog(actor=actor, action="disable" if disabled else "enable", entity="account",
                           entity_id=str(a.id)))
            return account_to_dict(a)

    # -- web sessions -----------------------------------------------------------------
    def authenticate(self, username: str, password: str) -> Principal | None:
        with session_scope(self.engine) as s:
            a = s.scalar(select(Account).where(Account.username == (username or "").strip().lower()))
            stored = a.password_hash if a is not None else None
            ok = verify_password(password, stored or _dummy_hash()) and stored is not None
            if not ok or a.disabled:
                return None
            return Principal(a.id, a.username, "session")

    def create_session(self, account_id: int) -> str:
        """Start a web session; returns the cookie value (shown nowhere else)."""
        raw = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            s.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
            s.add(LoginSession(id_hash=_sha(raw), account_id=account_id, created_at=now,
                               expires_at=now + timedelta(days=SESSION_DAYS)))
        return raw

    def end_session(self, raw: str) -> None:
        with session_scope(self.engine) as s:
            s.execute(delete(LoginSession).where(LoginSession.id_hash == _sha(raw)))

    def session_principal(self, raw: str) -> Principal | None:
        with session_scope(self.engine) as s:
            row = s.execute(select(LoginSession, Account).join(Account, Account.id == LoginSession.account_id)
                            .where(LoginSession.id_hash == _sha(raw))).first()
            if row is None:
                return None
            sess, a = row
            if a.disabled or _aware(sess.expires_at) <= datetime.now(UTC):
                return None
            return Principal(a.id, a.username, "session")

    # -- API keys ---------------------------------------------------------------------
    def create_key(self, ref: str | int, name: str, expires_days: int | None = None, actor: str = "cli") -> dict:
        """Make an API key. The returned `key` is the only time it is shown."""
        name = (name or "").strip()
        if not name or len(name) > 80:
            raise ArgusError("INVALID_ARG", "Give the key a name of 1-80 characters, e.g. what will use it.")
        if expires_days is not None and expires_days <= 0:
            raise ArgusError("INVALID_ARG", "expires_days must be positive (or omitted for no expiry).")
        raw = KEY_PREFIX + secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            a = self._find(s, ref)
            k = ApiKey(account_id=a.id, name=name, prefix=raw[:12], key_hash=_sha(raw), created_at=now,
                       expires_at=now + timedelta(days=expires_days) if expires_days else None)
            s.add(k)
            s.flush()
            s.add(AuditLog(actor=actor, action="create", entity="api_key", entity_id=str(k.id),
                           after={"account": a.username, "name": name, "prefix": k.prefix}))
            return key_to_dict(k, now) | {"username": a.username, "key": raw}

    def list_keys(self, ref: str | int | None = None, include_revoked: bool = False) -> list[dict]:
        with session_scope(self.engine) as s:
            q = select(ApiKey, Account.username).join(Account, Account.id == ApiKey.account_id).order_by(ApiKey.id)
            if ref is not None:
                q = q.where(ApiKey.account_id == self._find(s, ref).id)
            if not include_revoked:
                q = q.where(ApiKey.revoked_at.is_(None))
            now = datetime.now(UTC)
            return [key_to_dict(k, now) | {"username": u} for k, u in s.execute(q).all()]

    def revoke_key(self, key_id: int, account_id: int | None = None, actor: str = "cli") -> dict:
        """Revoke a key for good. With `account_id`, only that account's own keys."""
        with session_scope(self.engine) as s:
            k = s.get(ApiKey, key_id)
            if k is None or (account_id is not None and k.account_id != account_id):
                raise ArgusError("NOT_FOUND", f"No API key {key_id}.")
            if k.revoked_at is None:
                k.revoked_at = datetime.now(UTC)
                s.add(AuditLog(actor=actor, action="revoke", entity="api_key", entity_id=str(k.id),
                               after={"name": k.name, "prefix": k.prefix}))
            return key_to_dict(k)

    def key_principal(self, raw: str) -> Principal | None:
        if not raw.startswith(KEY_PREFIX):
            return None
        now = datetime.now(UTC)
        with session_scope(self.engine) as s:
            row = s.execute(select(ApiKey, Account).join(Account, Account.id == ApiKey.account_id)
                            .where(ApiKey.key_hash == _sha(raw))).first()
            if row is None:
                return None
            k, a = row
            if a.disabled or k.revoked_at is not None or (k.expires_at and _aware(k.expires_at) <= now):
                return None
            if k.last_used_at is None or now - _aware(k.last_used_at) >= LAST_USED_EVERY:
                k.last_used_at = now
            return Principal(a.id, a.username, "key")
