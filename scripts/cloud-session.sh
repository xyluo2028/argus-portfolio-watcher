#!/bin/bash
# SessionStart hook (.claude/settings.json). In a Claude Code cloud session: install dependencies,
# build the UI, create the trader bot's account, start Argus and restore the bot's records. Does nothing locally.
[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0
# The hook sets CLAUDE_PROJECT_DIR; run by hand (the round lead restarts Argus with it), use the repo root.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/..}" || exit 1
mkdir -p data
export ARGUS_STREAM=off  # the WebSocket carries the key in its URL, where the network secret can't reach

URL="http://127.0.0.1:${ARGUS_PORT:-8787}"
health() { curl -sf -m 3 "$URL/api/health" >/dev/null; }
if health; then
  echo "Argus is already running at $URL (log: data/server.log)"
  exit 0
fi

uv sync --quiet >data/setup.log 2>&1 || { echo "uv sync failed: see data/setup.log"; exit 0; }
(cd frontend && npm ci --silent && npm run build --silent) >>data/setup.log 2>&1 \
  || echo "Frontend build failed (see data/setup.log); the API and MCP still work."

# A fresh VM has an empty database. Create the trader bot's account (docs/loop/README.md) and an API
# key for it: the key is how the bot, sim.py and the screenshot script sign in. Both stay in data/,
# which is never committed. ARGUS_BOT_PASSWORD (optional, from the cloud environment) also lets a
# person sign in to this session's web UI as the bot.
FRESH=""
if [ ! -f data/argus.sqlite ]; then
  FRESH=1
  if [ -n "$ARGUS_BOT_PASSWORD" ]; then
    uv run argus user add bot0 --password "$ARGUS_BOT_PASSWORD" >>data/setup.log 2>&1
  else
    uv run argus user add bot0 --no-password >>data/setup.log 2>&1
  fi
  uv run argus key create bot0 --name "improvement loop" --json 2>>data/setup.log \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["key"])' >data/bot0.key 2>>data/setup.log \
    && chmod 600 data/bot0.key || echo "Couldn't create the bot's account or key: see data/setup.log"
fi

setsid nohup uv run argus serve >data/server.log 2>&1 </dev/null &
for _ in $(seq 1 60); do health && break; sleep 1; done
if health; then
  echo "Argus is running at $URL (log: data/server.log). It warms caches and builds the screener universe in the background (a few minutes)."
  echo "Sign-in is on: the bot's account is bot0 and its API key is in data/bot0.key."
  # The bot's portfolio, watchlists, notes and alerts live in the repo between sessions.
  if [ -n "$FRESH" ]; then
    python3 scripts/sim.py load 2>&1 | tee -a data/setup.log
  fi
else
  echo "Argus didn't start: see data/server.log"
fi
exit 0
