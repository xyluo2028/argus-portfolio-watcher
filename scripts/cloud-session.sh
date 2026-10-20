#!/bin/bash
# SessionStart hook (.claude/settings.json). In a Claude Code cloud session: install dependencies,
# build the UI, restore the improvement loop's model portfolios and start Argus. Does nothing locally.
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

# A fresh VM has an empty database: load the model portfolios the loop keeps in the repo.
if [ -f docs/loop/sim/snapshot.json ] && [ ! -f data/argus.sqlite ]; then
  uv run argus snapshot load docs/loop/sim/snapshot.json >>data/setup.log 2>&1 \
    && echo "Loaded the model portfolios from docs/loop/sim/snapshot.json" \
    || echo "Snapshot load failed: see data/setup.log"
fi

setsid nohup uv run argus serve >data/server.log 2>&1 </dev/null &
for _ in $(seq 1 60); do health && break; sleep 1; done
if health; then
  echo "Argus is running at $URL (log: data/server.log). It warms caches and builds the screener universe in the background (a few minutes)."
else
  echo "Argus didn't start: see data/server.log"
fi
exit 0
