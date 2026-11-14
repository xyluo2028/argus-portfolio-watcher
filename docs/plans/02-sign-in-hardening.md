# 02. Sign-in hardening

Roadmap items S1, S2, S4, S7, S8. Effort: medium. Mostly `backend/argus/api/`, one migration, a
small section on the Account page.

## Why

Argus is now reachable by other people and devices, and its sign-in still has shortcuts from when
it served one person on localhost:

- **S1.** Signing in with the server token stores `ARGUS_TOKEN` itself in the `argus_token`
  cookie (`api/server.py`, the `login` route). A copied cookie is the server's permanent secret,
  and signing out can't revoke it. Account sign-ins already get a random server-side session.
- **S2.** Cookies are marked Secure only when the request arrived over HTTPS. When Argus listens on
  a LAN address over plain HTTP, passwords and cookies cross the network unencrypted, and nothing
  warns about it.
- **S4.** Failed sign-ins are counted per username only, in memory. Anyone can lock a known
  username out for 15 minutes with ten bad passwords, and one address can keep guessing across
  usernames, each guess costing the server an scrypt hash.
- **S7.** Responses carry no security headers.
- **S8.** A session lasts 90 days, and there is no way to see sessions or end them all.

## What exists

- `api/auth.py`: `Authenticator.identify` accepts, in order: a Bearer credential (the token, or an
  API key), the `argus_session` cookie (looked up by `AccountService.session_principal`), the
  `argus_token` cookie compared with the token. `LoginThrottle` keeps failures per key.
  `AuthMiddleware` is pure ASGI and puts the principal in `scope["state"]["principal"]`.
- `api/server.py`: `/api/auth/login` (token branch sets `TOKEN_COOKIE`), `/api/auth/setup` (accepts
  the token from the body, a Bearer header or the token cookie), `/api/auth/signup`,
  `/api/auth/logout`, `/api/auth/status`. `_cookie()` sets `secure=request.url.scheme == "https"`.
  `serve()` runs uvicorn with `proxy_headers=True, forwarded_allow_ips="127.0.0.1"`.
- `models.py`, `LoginSession`: `id_hash` (SHA-256 of the cookie value), `account_id` (not null),
  `created_at`, `expires_at`.
- The token's principal is `AccountService.first()`: the oldest account, or nobody while no account
  exists. That is decided per request, so the same token sign-in changes meaning when the first
  account is created.
- `docs/deployment.md`, "Exposing it", already recommends `tailscale serve --bg 8787`, which gives
  HTTPS on the tailnet name in front of `http://127.0.0.1:8787`.

## Decided

### S1: token sign-ins get a server session

- A token sign-in creates a `LoginSession` like a password sign-in, with `account_id` null and a
  new column `token_fp`: the SHA-256 of the token it was made with. The browser gets the ordinary
  `argus_session` cookie.
- When a request presents such a session, it is valid only if the server still has a token and the
  token's SHA-256 equals `token_fp`. Then it acts as `accounts.first()`, exactly as the token does
  today. Changing or removing `ARGUS_TOKEN` therefore ends every token session.
- The `argus_token` cookie is no longer accepted or set. People signed in with the token sign in
  once more after the upgrade. Keep deleting that cookie on logout so old browsers shed it.
- The token still works as a Bearer credential for the API and MCP: that is its job for scripts.
- `/api/auth/setup` accepts the token in the body or as Bearer, or a request whose principal came
  from a token session.
- Logout deletes the session row, so a copied cookie stops working.

`AccountService` doesn't know the token and shouldn't. Let it return the session row's facts
(account or none, `token_fp`), and let `Authenticator`, which holds the token, decide.

### S8: see and end sessions

- Add to `LoginSession`: `user_agent` (first 200 characters, set at sign-in) and `last_seen_at`
  (updated at most every five minutes, the way `ApiKey.last_used_at` is: see `LAST_USED_EVERY`).
- `GET /api/account/sessions` lists the caller's sessions: created, last seen, user agent, expiry,
  and which one is the current request's. Identify a row by the first 12 characters of `id_hash`;
  never return the full hash.
- `DELETE /api/account/sessions` ends all of the caller's sessions except the current one.
  `DELETE /api/account/sessions/{id}` ends one. Both refuse API keys, like the other account
  management routes (`own_account(request, signed_in=True)`).
- For token sessions (no account), the list is every token session.
- Account page: a "Signed-in browsers" list with "Sign out" per row and "Sign out everywhere else".

One migration covers S1 and S8. `login_session` is referenced by nothing, so batch mode is safe.

### S4: throttle by address as well as by name

Replace the single per-name counter with three, all in the existing 15-minute window:

| Counted per | Limit | Effect when reached |
|---|---|---|
| username and client address | 10 failures | that address can't try that name |
| client address | 30 failures | that address can't sign in as anyone |
| username | 50 failures | nobody can try that name (stops a spread-out attack) |

The first is what an honest user hits. The third still allows a lockout, but it takes fifty
attempts per window, and the owner has two ways around it: the token and `argus user passwd`.

- The client address is `request.client.host`. Uvicorn already rewrites it from `X-Forwarded-For`
  when the peer is 127.0.0.1, so it is right behind `tailscale serve` or a local proxy.
- Check the address counters before hashing the password, so a blocked address costs no scrypt.
- Sign-up: add a per-address cap of 3 accounts an hour next to the global 10.
- A success clears the name-and-address counter only.

### S2: say so when sign-in is unencrypted

Argus can't tell whether a TLS proxy sits in front, so it can't refuse plain HTTP. It can warn:

- At `serve()`, when the listen address isn't loopback, log a warning: sign-ins on this address are
  not encrypted; prefer `ARGUS_HOST=127.0.0.1` behind `tailscale serve` or a TLS proxy; see
  `docs/deployment.md`.
- In `/api/auth/status`, add `insecure: true` when the request's scheme is `http` and the client
  address isn't loopback. The sign-in page shows one line then: "This connection isn't encrypted."
- `docs/deployment.md`: move the Tailscale recipe up as the recommended way to reach Argus from
  other devices, and say plainly that `ARGUS_HOST=0.0.0.0` on a LAN sends passwords in the clear.

### S7: security headers

One pure-ASGI middleware that adds, to every HTTP response:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer` (company logos load from third-party hosts; this keeps the page
  path out of those requests)
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:; connect-src 'self'; base-uri 'self'; form-action 'self';
  frame-ancestors 'none'`
- `Strict-Transport-Security: max-age=15552000` only when the request's scheme is `https`.

Why those values: the built `index.html` loads one module script from `/assets` and has no inline
script; React and the chart library set inline styles; the favicon is a `data:` URL; company logos
(`components/CompanyCard.tsx`) are remote `https:` images. It must be pure ASGI like
`AuthMiddleware`, so the live stream and MCP pass through untouched. Add headers by wrapping `send`
and appending to `http.response.start`.

## Ask the owner

Nothing to build, but tell the owner: their server currently listens on all interfaces
(`ARGUS_HOST=0.0.0.0` in `.env`). The safer setup is `ARGUS_HOST=127.0.0.1` plus
`tailscale serve --bg 8787`, with the tailnet name in `ARGUS_ALLOWED_HOSTS`. That is a change to
their `.env` and their devices' bookmarks, so it is theirs to make.

## Leave alone

- Passwords (scrypt), API keys and how accounts are created.
- Invite codes, read-only keys and request limits: plan 13.

## Done when

- A token sign-in sets only `argus_session`; the old `argus_token` cookie alone gets a 401; logout
  makes the cookie value useless; changing the token ends token sessions. Tests in
  `tests/test_deploy.py` and `tests/test_accounts.py` assert the old cookie behavior: update them,
  and add these cases.
- First-run setup still works after a token sign-in in the browser (the Account page's
  "Create your account" form sends no token): keep `test_setup_asks_for_the_server_token_when_one_is_set`
  meaningful.
- Throttle tests: ten failures from one address block that address for that name while another
  address can still sign in; thirty failures from one address block it for every name; a blocked
  address triggers no password hash (assert the hash function isn't called).
- A migration test upgrades a database that has password sessions and keeps them working.
- Every response has the headers; the stream test (`test_the_live_stream_is_per_account`) and the
  HTTP MCP test still pass.
- In a browser, with the console open, every page loads with no Content-Security-Policy violation
  (sweep all routes, including a stock page with a logo and the DCF page).
- New routes are listed in `tests/test_owners.py` (`NOT_PER_ACCOUNT`: they concern the caller's own
  sign-in).
- `docs/deployment.md` and the README's accounts section describe the new behavior.
