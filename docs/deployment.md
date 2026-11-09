# Deploying Argus to an always-on host

Argus was built as a local, single-user tool: one `argus serve` process (FastAPI) serves the web UI,
the JSON API, MCP at `/mcp/` and an in-memory live-price hub, all on top of one SQLite file in
`data/`. This checklist covers what changes when it runs unattended and is reachable from other
devices: a cloud VM, a home server, or your own PC behind Tailscale or a Cloudflare Tunnel.

Status: ✅ done · 🟡 done, not yet verified end to end · ⬜ to do

## Must do before exposing it

| # | Item | Status |
|---|------|--------|
| 1 | **Access control.** Accounts (`argus user add`) sign in to the UI with a password; bots, scripts and MCP clients use an account's API key (`argus key create`). The optional shared token (`ARGUS_TOKEN`) still works and acts as the oldest account. Once an account exists or the token is set, every request to the API, the live stream and `/mcp/` must sign in, from localhost too. Network-level access (Tailscale, Cloudflare Access) stays the first line. The server refuses to listen beyond loopback with sign-in off. | ✅ |
| 2 | **Configurable hosts.** `ARGUS_ALLOWED_HOSTS` adds the tunnel's hostname to the localhost allow-list (otherwise every proxied request gets HTTP 400); `ARGUS_HOST` sets the listen address; proxy headers are honored. | ✅ |
| 3 | **Schema migrations.** Alembic with a baseline of the current schema. New databases are created at the latest revision, pre-Alembic databases are stamped, and every start upgrades to head. A test keeps models and migrations in sync. | ✅ |
| 4 | **Backups.** `argus backup` writes an SQLite online backup plus a JSON snapshot and prunes old sets; a systemd timer runs it nightly. Copying backups off the machine is described below. | ✅ |
| 5 | **One instance.** `argus serve` takes a lock on the data directory, so a second server on the same data fails clearly. Running a second copy elsewhere with the same Finnhub key isn't detectable; see "Moving your data". | ✅ |
| 6 | **Process supervision.** systemd units (`deploy/`) and a Dockerfile + compose file: restart on failure, start at boot, one worker, `/api/health` for health checks. The units pass `systemd-analyze verify` and their command was run; the image was built and run (healthy, non-root, migrations, token mode, snapshot load, backup). | ✅ |
| 7 | **Setup docs.** `.env.example` restored and tracked; README covers Linux/server setup. | ✅ |
| 7a | **Static files stay inside the UI folder.** The UI route served any file reachable from `frontend/dist` by an encoded `../` (e.g. `/%2e%2e/%2e%2e/.env`, your API keys). Fixed and covered by tests. | ✅ |

## Should do

| # | Item | Status |
|---|------|--------|
| 8 | **Yahoo from cloud IPs.** yfinance is often throttled from datacenter IPs; price history, dividends, ETF and company profiles and the fallback quotes depend on it. Test from the target before committing to a cloud VM (`uv run argus history SPY --period 1mo`). | ⬜ |
| 9 | **CI.** Run `pytest` and the frontend build/type check on every push. | ⬜ |
| 10 | **Warm caches.** First views of dividends and the holdings tabs take ~20 s per portfolio; a nightly background refresh would make them instant. | ⬜ |
| 11 | **Check the live stream through the tunnel.** Keep-alives (15 s) and `X-Accel-Buffering: no` are set; confirm prices stream on the dashboard. | ⬜ |
| 12 | **Phone layout.** Check the UI at phone width. | ⬜ |
| 13 | **Hygiene.** Non-root user, `.env` mode 600, log level. (The systemd unit and container already run unprivileged.) | ⬜ |

Time zones need no work: the market calendar uses New York time explicitly and pandas ships the
zone data.

## Choosing where it runs

| | Tailscale (recommended start) | Cloudflare Tunnel | Cloud VM |
|---|---|---|---|
| Who can reach it | Only your devices | Anyone with the URL | Your choice (still use a tunnel) |
| Sign-in (accounts or `ARGUS_TOKEN`) | Optional, recommended | **Required**, plus Cloudflare Access | Required |
| Claude Desktop/Code MCP | Works on tailnet devices | Works with service-token headers | Same |
| Yahoo data | Your home IP, fine | Your home IP, fine | Risky from datacenter IPs |

Keep `argus serve` on `127.0.0.1` in all three: `tailscale serve` and `cloudflared` connect to it
locally, so nothing listens on a public interface.

## Configuration

Settings come from environment variables or the repo-root `.env` (see `.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `FINNHUB_API_KEY` | – | Live quotes, metrics, events (free tier is fine) |
| `SEC_USER_AGENT` | – | Needed for `argus financials` (`"argus you@example.com"`) |
| `ARGUS_PORT` | `8787` | Listen port |
| `ARGUS_HOST` | `127.0.0.1` | Listen address; anything else requires sign-in (an account or `ARGUS_TOKEN`) |
| `ARGUS_ALLOWED_HOSTS` | – | Extra hostnames to answer, comma-separated (e.g. `argus.tail1234.ts.net`) |
| `ARGUS_TOKEN` | – | Shared secret for the UI, API and MCP; acts as the oldest account. Optional once you have accounts. Generate with `openssl rand -hex 32` |
| `ARGUS_INSECURE_BIND` | – | `1` allows a non-loopback `ARGUS_HOST` with sign-in off; only for a container published on the host's loopback (`compose.yaml` sets it) |
| `ARGUS_DATA_DIR` | `./data` | Database, caches, snapshots, backups |
| `ARGUS_BACKUP_KEEP` | `14` | Backup sets kept by `argus backup` |
| `ARGUS_STREAM` | `on` | `off` = no live WebSocket, REST polling only (for a second instance sharing the Finnhub key) |

## Setup on a Linux host (systemd)

```bash
# as the user that will run Argus
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv
git clone <repo> ~/argus && cd ~/argus
uv sync --frozen
(cd frontend && npm ci && npm run build)                  # needs Node >= 20.19
cp .env.example .env && chmod 600 .env                     # fill in keys, ARGUS_TOKEN, ARGUS_ALLOWED_HOSTS

mkdir -p ~/.config/systemd/user
cp deploy/argus.service deploy/argus-backup.service deploy/argus-backup.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now argus.service argus-backup.timer
loginctl enable-linger "$USER"                              # keep running after logout / start at boot
journalctl --user -u argus -f                               # logs
```

The units assume the checkout is at `~/argus` and uv at `~/.local/bin/uv`; edit `WorkingDirectory`
and `ExecStart` if not.

## Setup with Docker

```bash
cp .env.example .env    # fill in
docker compose up -d --build
docker compose logs -f
```

Data lives in the `argus-data` volume. Full walkthrough (configuration, moving your data, backups
and restore, updates, troubleshooting): **[docker.md](docker.md)**.

## Exposing it

**Tailscale** (on the same host):

```bash
tailscale serve --bg 8787        # https://<host>.<tailnet>.ts.net -> http://127.0.0.1:8787
```

Set `ARGUS_ALLOWED_HOSTS=<host>.<tailnet>.ts.net`. Don't use Funnel unless sign-in is on (an account
or `ARGUS_TOKEN`); Funnel makes it public.

**Cloudflare Tunnel**: point a public hostname at `http://127.0.0.1:8787`, add a Cloudflare Access
application for that hostname (email one-time code or your SSO), turn on sign-in (create an account,
or set `ARGUS_TOKEN`) and set `ARGUS_ALLOWED_HOSTS=<hostname>`. For MCP clients, create an Access
service token and send its headers along with the Argus API key (below).

**Your PC (WSL)**: WSL stops when idle and doesn't start at boot. Enable systemd (`/etc/wsl.conf`:
`[boot] systemd=true`), install the user units above, add a Windows Task Scheduler task that runs
`wsl.exe -d Ubuntu --exec /bin/true` at logon, and turn off sleep. Run `tailscale` or `cloudflared`
inside WSL: both connect outbound, which avoids Windows' localhost forwarding.

## Accounts and API keys

There is one kind of account; a bot is an account you create for it. Manage them on the server:

```bash
uv run argus user add me                       # asks for a password; make your own account first
uv run argus user add trader-bot --no-password # a bot that only uses API keys
uv run argus key create trader-bot --name "sim routine" [--expires-days 90]   # shown once
uv run argus user list
uv run argus key list
uv run argus key revoke 3                      # stops working at once
uv run argus user passwd me                    # new password; signs out every browser
uv run argus user disable trader-bot           # sessions and keys stop working until `enable`
```

- The first account switches sign-in on for every request, including from this machine, so a bot
  can't skip its key by calling `localhost`. Disabling accounts doesn't switch it off again.
- `ARGUS_TOKEN` acts as the oldest account, so create your own account before the bot's.
- Passwords are stored as scrypt hashes, session ids and API keys as SHA-256; no secret is stored as given.
- An API key can read and write like its account, but can't create keys or change the password.
- Ten failed sign-ins for a name within 15 minutes block it for the rest of that window.
- The CLI and `argus mcp` (stdio) open the database file directly and need no sign-in. They act as
  the oldest account, or as `argus --as <user> ...`: give a bot only an API key for the HTTP MCP
  endpoint, never a shell on the server.
- Accounts and keys are in `argus backup` and in JSON snapshots (hashes only). Web sessions aren't,
  so everyone signs in again after `argus snapshot load`.

### Whose records are whose

| | Who sees it |
|---|---|
| Portfolios (transactions, targets, performance history) | The account that created it, plus accounts it's shared with (read-only) |
| Watchlists, alerts, notes, peer lists, saved DCF models | Only the account that created them |
| Market data, the screener, market context, the events calendar | Everyone |
| Snapshot dump and restore | Only the CLI (a snapshot holds every account's records) |

- **The first account takes over** everything recorded before any account existed (and, when you
  upgrade to this version with accounts already set up, the oldest account does).
- **Names are per account:** a bot can have its own `growth` portfolio or `Watchlist`. Anyone
  else's portfolio is "not found", so its existence doesn't leak.
- **"All portfolios"** (`all`) combines only your own portfolios, never ones shared with you.
- **Sharing:** the owner shares a portfolio read-only with `argus portfolio share <portfolio> --with <user>`
  (a bot's: `argus --as <bot> portfolio share ...`), the `share_portfolio` MCP tool, or
  `PUT /api/portfolios/<portfolio>/shares/<user>`. The other account can view positions,
  performance and analysis, but changing anything returns `READ_ONLY`. `unshare`, or deleting
  the portfolio, ends it. A shared portfolio whose name matches one of yours is reached by its id.
- **Live updates:** the price stream carries only the symbols in your own holdings, watchlists and
  benchmarks (and those of a shared portfolio you open), and a fired alert reaches only its owner.
  Cost alerts compare with the owner's own average cost.
- **Audit log:** each entry records the account that made the change.

## Claude (MCP) against the deployed server

```bash
claude mcp add --transport http argus https://<host>/mcp/ --header "Authorization: Bearer <API key>"
```

The key is an account's API key (`argus key create`), or `ARGUS_TOKEN`.

Behind Cloudflare Access, also pass `--header "CF-Access-Client-Id: …" --header "CF-Access-Client-Secret: …"`.
Use this instead of the stdio server once the data lives on the server, so there is only one database.

## Moving your data

1. On the old machine: `uv run argus snapshot dump` (writes `data/snapshots/argus-snapshot-<time>.json`).
2. Copy the file to the server and run `uv run argus snapshot load <file> --dry-run`, then without `--dry-run`.
3. Stop `argus serve` on the old machine. Two servers with the same Finnhub key fight over its single
   WebSocket and 60 calls/minute, and their databases drift apart.
4. Run the CLI on the server (over SSH) from then on.

## Backups and restore

`argus backup` writes `data/backups/<time>/argus.sqlite` (a consistent online copy, safe while the
server runs) and `snapshot.json`, then keeps the newest `ARGUS_BACKUP_KEEP` sets. The timer runs it
nightly at 03:30. Copy `data/backups/` off the machine, for example with `rclone sync` or
`tailscale file cp`, from a cron job.

Restore, either way:

- **Snapshot** (portable across versions): `argus snapshot load data/backups/<time>/snapshot.json --replace`
- **Database file**: stop the server, copy `data/backups/<time>/argus.sqlite` over `data/argus.sqlite`, start it.

## Schema changes (developers)

Models live in `backend/argus/models.py`; migrations in `backend/argus/migrations/versions/`.
After changing a model:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run pytest tests/test_migrations.py   # migrations must reproduce the models exactly
```

The server applies pending migrations at start.
