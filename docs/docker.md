# Running Argus with Docker

One container runs everything: the web UI, the JSON API, MCP at `/mcp/` and the live-price hub.
Your data lives in a Docker volume. These steps were tested with Docker 28.5 (Docker Desktop on
Windows/WSL); the image is about 680 MB.

For what to set up around it (tunnels, tokens, backups off the machine), see
[deployment.md](deployment.md).

## 1. Prerequisites

- Docker Engine with Compose v2 (`docker compose version`), or Docker Desktop.
- On WSL: Docker Desktop → Settings → Resources → WSL integration → enable your distro, so `docker`
  works inside Ubuntu. (Without it, call `docker.exe` instead.)
- A Finnhub API key (free) is recommended; without it quotes fall back to Yahoo.

## 2. Configure

```bash
git clone <repo> argus && cd argus
cp .env.example .env && chmod 600 .env
```

Edit `.env`:

| Setting | Local only (this machine) | Reached from other devices |
|---|---|---|
| `FINNHUB_API_KEY` | your key | your key |
| `SEC_USER_AGENT` | `argus you@example.com` | same |
| `ARGUS_TOKEN` | leave empty | **required**: `openssl rand -hex 32` |
| `ARGUS_ALLOWED_HOSTS` | leave empty | your tunnel's hostname, e.g. `argus.tail1234.ts.net` |

Leave `ARGUS_HOST` and `ARGUS_DATA_DIR` empty: the image sets them (`0.0.0.0`, `/data`).

`compose.yaml` publishes the port on the host's **loopback only** (`127.0.0.1:8787`) and sets
`ARGUS_INSECURE_BIND=1`, which lets the server listen on all interfaces *inside* the container
without a token. Nothing outside the host can reach it unless you add a tunnel or change the port
mapping. If you publish it more widely, remove that line and set `ARGUS_TOKEN`.

## 3. Build and start

```bash
docker compose up -d --build        # first build takes a few minutes; later ones seconds
docker compose ps                   # STATUS should become "healthy" within ~20 s
docker compose logs -f              # Ctrl+C to stop following
```

Open http://localhost:8787. With `ARGUS_TOKEN` set you'll get a sign-in screen; paste the token
once per browser.

The container runs as an unprivileged user, restarts unless stopped, and has a health check on
`/api/health`. Database migrations run automatically at start.

## 4. Bring your data in

On the machine that has your data now:

```bash
uv run argus snapshot dump                     # -> data/snapshots/argus-snapshot-<time>.json
```

Then, next to `compose.yaml`:

```bash
docker compose cp argus-snapshot-<time>.json argus:/tmp/snap.json
docker compose exec argus argus snapshot load /tmp/snap.json --dry-run
docker compose exec argus argus snapshot load /tmp/snap.json
```

Or use the web UI: **Data → Restore → Choose file**. A CSV from Investing.com can be imported there
too (**Data → Import**).

Stop the old server afterwards. Two servers with the same Finnhub key fight over its single
live-price connection, and their databases drift apart.

## 5. Everyday use

```bash
docker compose exec argus argus portfolio show all      # any CLI command
docker compose exec argus argus brief growth --json
docker compose restart                                   # after editing .env
docker compose down                                      # stop (data stays in the volume)
```

Never run `docker compose down -v` unless you mean it: `-v` deletes the data volume.

Claude Code against the container (use `https://<tunnel-host>/mcp/` from other devices):

```bash
claude mcp add --transport http argus http://localhost:8787/mcp/ \
  --header "Authorization: Bearer <ARGUS_TOKEN>"
```

## 6. Backups

```bash
docker compose exec argus argus backup                  # /data/backups/<time>/{argus.sqlite,snapshot.json}
docker compose cp argus:/data/backups ./argus-backups   # copy them out of the volume
```

Nightly, from the host's crontab (`crontab -e`):

```cron
30 3 * * * cd /path/to/argus && docker compose exec -T argus argus backup && docker compose cp argus:/data/backups ./argus-backups
```

Restore:

- **Snapshot** (works across versions):
  `docker compose cp ./argus-backups/<time>/snapshot.json argus:/tmp/s.json` then
  `docker compose exec argus argus snapshot load /tmp/s.json --replace`
  (the current records are backed up first).
- **Whole database**: `docker compose stop`, then copy the `.sqlite` file into the volume, e.g.
  `docker run --rm -v argus_argus-data:/data -v "$PWD/argus-backups/<time>:/b" alpine cp /b/argus.sqlite /data/argus.sqlite`,
  then `docker compose start`. (`docker volume ls` shows the volume's exact name.)

## 7. Updating

```bash
docker compose exec argus argus backup     # first, always
git pull
docker compose up -d --build               # pending migrations run at start
```

## 8. Exposing it

Keep the loopback-only port mapping and run the tunnel on the host:

- **Tailscale**: `tailscale serve --bg 8787` → `https://<host>.<tailnet>.ts.net`. Put that name in
  `ARGUS_ALLOWED_HOSTS`, then `docker compose restart`.
- **Cloudflare Tunnel**: point a public hostname at `http://localhost:8787`, protect it with a
  Cloudflare Access application, and set `ARGUS_TOKEN` and `ARGUS_ALLOWED_HOSTS`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Container exits: `Refusing to listen on 0.0.0.0 without ARGUS_TOKEN` | You removed `ARGUS_INSECURE_BIND` (or ran `docker run` without it): set `ARGUS_TOKEN`, or add `-e ARGUS_INSECURE_BIND=1` with a loopback-only `-p 127.0.0.1:...` |
| `Invalid host header` (HTTP 400) through a tunnel | Add the tunnel hostname to `ARGUS_ALLOWED_HOSTS` and restart |
| Every API call is 401 | `ARGUS_TOKEN` is set: sign in in the UI, or send `Authorization: Bearer <token>` |
| Live prices say "reconnecting" | Another server uses the same Finnhub key; stop it |
| Charts or dividends empty on a cloud VM | Yahoo is throttling the datacenter IP; see deployment.md item 8 |
| `docker: command not found` in WSL | Enable WSL integration in Docker Desktop, or use `docker.exe` |
