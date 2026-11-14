# 03. Running it on a Mac: supervision, backups, logs

Roadmap items O1 to O5 and O8. Effort: medium, in five independent parts. Do them in any order;
each can be its own commit.

## Why

The owner runs Argus on a Mac, started from a shell with `nohup uv run argus serve`. The repo's
`deploy/` folder only has systemd units, so on macOS:

- nothing starts Argus at login or restarts it if it dies (O1);
- the nightly backup never runs: at the time of the review exactly one backup existed, taken by
  hand (O2);
- the log has no timestamps, drops Argus's own messages, and grows forever (O3);
- a schema migration runs at startup with no copy of the database taken first (O4);
- `/api/health` only says the process is up (O5);
- stopping the server can hang on open live-stream connections; it once needed `kill -9` (O8).

## Part A: launchd agents (O1, O2)

Add `deploy/macos/` with:

- `com.argus.serve.plist.template`: a user agent that runs the server. `RunAtLoad` true;
  `KeepAlive` with `SuccessfulExit` false (restart after a crash, not after a clean stop);
  `ThrottleInterval` 30; `WorkingDirectory` the repo; `ProgramArguments`
  `/usr/bin/caffeinate -i <uv> run --frozen --no-sync argus serve`; `EnvironmentVariables` with
  `PYTHONUNBUFFERED=1` and a `PATH` that includes uv's directory; `StandardOutPath` and
  `StandardErrorPath` to `<repo>/data/logs/launchd.log`.
- `com.argus.backup.plist.template`: runs `<uv> run --frozen --no-sync argus backup` with
  `StartCalendarInterval` at 03:30. launchd runs a missed job when the Mac next wakes.
- `install.sh`: fills the templates with the repo path and `command -v uv`, writes them to
  `~/Library/LaunchAgents/`, and loads them with `launchctl bootstrap gui/$(id -u) <plist>`.
  `uninstall.sh` does the reverse (`launchctl bootout`). Both print what they did. `install.sh`
  must refuse to start the server agent while another Argus holds the data directory (the lock file
  `data/argus.lock` holds its pid): tell the user to stop it first, don't kill it.

Why `--frozen --no-sync`: the same reason as the systemd unit, it starts offline from the installed
environment. Why `caffeinate -i`: it stops idle sleep while Argus runs. It does not keep a laptop
awake with the lid closed on battery; say so in the docs, with the System Settings options that do.

Docs: a "Setup on a Mac (launchd)" section in `docs/deployment.md`, beside the Linux one: install,
check (`launchctl print gui/$(id -u)/com.argus.serve`), logs, uninstall, and how to restart after
`git pull` (`launchctl kickstart -k gui/$(id -u)/com.argus.serve`).

Verify with `plutil -lint` on the generated files. You can only load the agents on a Mac; if you
are not on one, say the agents are unverified. On the owner's Mac, do not swap the running server
for the agent without asking: it is their live instance.

## Part B: logging (O3)

Today nothing configures logging. Uvicorn prints its own lines without timestamps, and the
`argus.*` loggers have no handler, so INFO messages such as "caches warmed" and "alerts fired"
vanish and only warnings reach stderr.

- New `backend/argus/logs.py` with `configure(settings)`: a root configuration with one format,
  `%(asctime)s %(levelname)s %(name)s: %(message)s`, two handlers (stderr, and a
  `RotatingFileHandler` at `<data_dir>/logs/argus.log`, 5 MB, 5 files), level from a new setting
  `ARGUS_LOG_LEVEL` (default `INFO`).
- Call it from `serve()` in `api/server.py` before `uvicorn.run`, and pass `log_config=None` to
  `uvicorn.run` so uvicorn's loggers use that configuration instead of installing their own.
- Only `serve` configures logging. The CLI prints for a person, and `argus mcp` (stdio) must keep
  stdout for the protocol: leave both as they are.
- While here, give the 33 broad `except Exception` blocks a second look (C5): each should log with
  enough context to find it. Most do. Fix the ones that swallow silently; don't restructure.

## Part C: a copy before migrating (O4)

In `db.migrate`, when the database already has tables and its revision isn't head, copy it before
upgrading: SQLite's online backup (as `services/backup.py` does) to
`<db dir>/backups/pre-migration/<old revision>-<timestamp>.sqlite`, keeping the newest three. Skip
it for `:memory:` and for brand-new databases. If the copy fails, stop: don't migrate without it.
Log the path. Add a case to `tests/test_migrations.py`.

## Part D: status (O5)

Keep `/api/health` as it is: public, minimal, for liveness checks. Add an authenticated
`GET /api/status` for people:

```json
{"started_at": "...", "version": "0.1.0", "revision": "0005",
 "database": {"bytes": 62300000}, "cache": {"bytes": 790000000},
 "stream": "connected", "session": "regular",
 "quotes": {"symbols": 82, "oldest_age_s": 41, "newest_age_s": 2},
 "warm": {"last_at": "...", "report": {"fundamentals": "ok", "...": "..."}},
 "backup": {"last_at": "...", "age_h": 9.5},
 "providers": {"finnhub": true, "sec": true}}
```

- The hub must remember when it last warmed the caches and the report (`live.py`, `_warm_loop`;
  `Argus.warm_caches` already returns the report).
- `backup.last_at` is the newest set name under `<data_dir>/backups/` (`SET_NAME` in
  `services/backup.py`).
- It describes the server, not anyone's records, so any signed-in account may read it. List it in
  `NOT_PER_ACCOUNT` in `tests/test_owners.py`.
- UI: a small "Server" card on the Data page: last backup (red when older than 48 hours, with the
  command to run), database and cache size, live stream state.

## Part E: stop cleanly (O8)

The live stream's generator (`/api/stream`) loops until the client disconnects, so uvicorn waits
on open tabs at shutdown. Pass `timeout_graceful_shutdown=5` to `uvicorn.run`. Confirm on a
throwaway server: open the stream with `curl -N`, send the server SIGTERM, and it exits within
about five seconds.

## Leave alone

- The systemd units and Docker files, apart from pointing at the new log location if relevant.
- Cache pruning: plan 05.

## Done when

- `deploy/macos/` installs and removes both agents, and the docs explain it; state whether you
  could load them.
- Server log lines carry timestamps and include Argus's INFO messages; the file rotates.
- A migration leaves a pre-migration copy; a test proves it.
- `/api/status` answers as above and the Data page shows the Server card.
- SIGTERM with a stream open exits promptly.
- `.env.example` and the settings table in `docs/deployment.md` list `ARGUS_LOG_LEVEL`.
