# 11. Alert delivery

Roadmap item I9. Effort: medium.

## Why

Alerts fire into the web UI and the daily brief only. `services/alerts.py` says so at its top:
"There are no push notifications by design." That was fine for a dashboard that is always open.
An investor wants the phone to buzz when a stock crosses a level, and the owner now reaches Argus
from a phone.

## What exists

- `services/alerts.py`: `KINDS` (12 alert kinds), `AlertService.evaluate(...)`, which records a
  firing at most once per alert per trading session (`AlertEvent`) and returns the new ones, each
  with `alert_id`, `account_id`, `symbol`, `kind`, `message`, `note`.
- `Argus.evaluate_alerts` (`app.py`) gathers quotes, fundamentals and costs, and calls it. Two
  callers: the hub every 30 seconds as `SYSTEM` (`live.py`, `_check_alerts`), and the MCP
  `list_alerts` tool as the calling account.
- `httpx` is already a dependency (the providers use it).

## Decided

1. **Each account configures its own channels.** A new owned table `notify_channel`: `id`,
   `account_id`, `kind`, `name`, `config` (JSON), `enabled`, `created_at`, `last_ok_at`,
   `last_error`. It is an owned table, so it needs every step in the ground rules (owner column,
   `OWNED`, the leak tests).
2. **Three kinds to start**, all plain HTTPS posts:
   - `ntfy`: `{"server": "https://ntfy.sh", "topic": "<secret topic>", "token": optional}`. The
     simplest path to a phone: install the ntfy app, subscribe to the topic.
   - `telegram`: `{"bot_token": "...", "chat_id": "..."}`.
   - `webhook`: `{"url": "https://...", "secret": optional}`: a JSON post, with an HMAC signature
     header when a secret is set.
   No email yet: it needs SMTP settings and a sender, a bigger setup than the three above.
3. **Send from one place.** `Argus.evaluate_alerts` is the only code that learns of new firings,
   so it hands them to a new `services/notify.py`. That covers both callers. Group the firings by
   `account_id` and send each to that account's enabled channels.
4. **Never block the hub.** Sending runs on a background thread with a 10-second timeout per
   request and no retry. `Argus.run_background` is single-flight by name and drops a second call
   while the first runs, which would lose notifications: give delivery its own worker (a small
   queue and one thread) instead. Record `last_ok_at` or `last_error` on the channel.
5. **The message** is the alert's own text plus the note, for example
   `NVDA: price 201.10 ≥ 200.00. Trim above 200`. If a new optional setting `ARGUS_PUBLIC_URL` is
   set, add a link to the stock page.
6. **Secrets are write-only.** The API returns a channel with its secrets masked (the last four
   characters at most). They are stored as given, since Argus must send them: say so in the docs.
   Channels are left out of both snapshot formats for the same reason; document that a restore
   doesn't bring them back.
7. **A test button** sends "Test from Argus" to one channel and reports the result.

## Security: a user-supplied URL is a way into the server's network

With open sign-up, any account can make Argus send requests to a URL of its choosing (`webhook`,
and `ntfy` with a custom server). That is a server-side request forgery risk: the target could be
`http://127.0.0.1:8787/...`, a router's admin page, or a cloud metadata address.

- Require `https://`.
- Resolve the host and refuse loopback, private, link-local and unspecified addresses, for every
  address it resolves to. Check again at send time, not only when the channel is saved (DNS can
  change). Don't follow redirects.
- A setting `ARGUS_NOTIFY_ALLOW_PRIVATE=1` lifts the address check for people who self-host ntfy
  on their own network. Default off.
- Cap channels per account (5) and sends per account per hour (60), so an account can't use Argus
  to flood a third party.
- Send no response body back to the user beyond a status code and a short error.

## Do

- Model, migration, `services/notify.py` (the three senders, the address check, the worker),
  wiring in `Argus.evaluate_alerts`.
- API under the caller's account: `GET /api/account/notify`, `POST` (create), `PATCH /{id}`
  (enable, rename), `DELETE /{id}`, `POST /{id}/test`. Managing channels is refused to API keys,
  like the other account-management routes: a leaked key shouldn't redirect someone's alerts.
- UI: a "Notifications" section on the Account page: add a channel (kind, name, fields), test,
  enable or disable, delete, with last success or error shown.
- MCP: none. Bots don't need to manage delivery.
- Docs: how to set up ntfy and Telegram in three steps each; the privacy note that alert text
  (a symbol and a price) leaves the server; the new settings in `.env.example` and
  `docs/deployment.md`.

## Follow-ups, not in this plan

- More alert kinds, each a small addition to `KINDS` and `check()`: portfolio drawdown from its
  peak, a moving-average cross, a position above its target weight, an index or yield level (backlog
  B-078: alerts reject `^TNX` as "not a US ticker").
- Delivering the daily brief on a schedule through the same channels (roadmap F7).
- Email.

## Done when

- Tests with a fake HTTP transport: a firing for account A reaches A's channels and not B's; a
  disabled channel is skipped; a failing channel records its error and doesn't stop the others; the
  hub's tick returns without waiting for delivery.
- Address tests: loopback, private ranges, link-local, a hostname that resolves to a private
  address, and a redirect are all refused; the override setting allows them.
- The leak test lists the new routes and shows one account can't read, change or test another's
  channels.
- On a throwaway server, a real ntfy topic receives a test message and a real alert firing. Use a
  topic you create for the test; don't leave it configured.
- The module docstring in `services/alerts.py` no longer says there are no notifications.
