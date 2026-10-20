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

## Blocked

## Done

## Won't do
