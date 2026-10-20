# Backlog

Every finding from the investor reviews, deduplicated. The round lead keeps this file; see
`README.md` for how items are picked.

Format, one item per heading, newest IDs at the bottom of their section:

```markdown
### B-001 Short title
- kind: bug | ux | perf | feature | removal · severity: high | medium | low
- reported by: macro r001, income r002
- evidence: one or two lines, or a link to the round report
- acceptance: what "done" means (written when the item is picked)
- status: open | in progress rNNN | done (rNNN, <commit>) | blocked: <reason> | won't do: <reason>
```

## Open

### B-001 Run tests and the frontend build on every push (CI)
- kind: ux · severity: medium
- reported by: seed (docs/deployment.md, "Should do" #9)
- evidence: nothing checks the loop's pushes besides the loop itself
- note: pushing a new `.github/workflows/` file can be refused for the loop's GitHub access; if so, mark it blocked and leave the workflow file for a human to add
- status: open

### B-002 Check every page at phone width
- kind: ux · severity: low
- reported by: seed (docs/deployment.md, "Should do" #12)
- evidence: pages were mostly designed and checked at desktop width
- status: open

### B-003 Header badge says "no Finnhub key" when the stream is only switched off
- kind: bug · severity: low
- reported by: cloud smoke test (2026-10-21)
- evidence: with `ARGUS_STREAM=off` and a working key (quotes come from Finnhub), the badge reads
  "polling each minute (no Finnhub key)"; `frontend/src/components/LiveBadge.tsx` shows that text
  for every `stream.state === "disabled"`, and `backend/argus/live.py` doesn't say why it's disabled
- status: open

### B-004 Markets, Screener and Watchlist are hidden until a portfolio exists
- kind: ux · severity: medium
- reported by: cloud smoke test (2026-10-21)
- evidence: on a fresh instance `/markets` shows only "No portfolios yet" (`frontend/src/App.tsx`
  routes every page except `/data` to that card); market data and the screener don't need a portfolio
- status: open

## Blocked

## Done

## Won't do
