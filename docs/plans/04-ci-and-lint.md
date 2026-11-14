# 04. CI and lint

Roadmap items O7, C3, C7. Effort: small.

## Why

Nothing checks a push except whoever made it. The improvement loop pushes code every day, and
humans and agents both work on this repo. The backend tests take 15 seconds and the frontend build
a few more: cheap to run on every push.

There is also no linter. A basic check finds real leftovers today:

- `backend/argus/app.py`: about 30 unreachable lines after `return quotes` in `_holding_quotes`
  (the old body of `fund_holdings`, using names that no longer exist: `sym`, `out`).
- `backend/argus/services/research.py`: an unused variable `ni`.
- Unused imports in `tests/test_importer.py` and `tests/test_owners.py`.
- `numpy` is imported in `services/risk.py` but not declared in `pyproject.toml`; it arrives
  through pandas (C7).

## Decided

1. **Ruff, starting narrow.** Add `ruff` to the `dev` dependency group and configure
   `[tool.ruff]` in `pyproject.toml` with `line-length = 130` and
   `lint.select = ["E9", "F"]`: syntax errors and pyflakes (undefined names, unused imports and
   variables). That set reports 10 problems today, all listed above; fix them and it passes.
   Do not enable `E501` or reformat: 108 lines exceed 120 characters and a formatting commit would
   bury history for no gain.
2. **Why not more rules yet:** the code already carries `# noqa` comments for `BLE001`, `E731`,
   `E741`, `SIM115` and `A002`, so someone linted with a wider set once. Run
   `ruff check --select E,F,B,BLE,SIM,A,I --statistics` and put the counts in your report (about
   200 findings at review time, 65 auto-fixable). Widening the set is a separate, later change.
3. **No type checker yet.** The code has type hints but has never been checked; turning one on
   would produce a long list that needs judgment. Record it as a follow-up.
4. **One workflow, three jobs**, on every push and pull request:
   - `backend`: install uv, `uv sync --frozen`, `uv run ruff check backend tests`,
     `uv run pytest -q`. Python from `.python-version`.
   - `frontend`: `npm ci`, `npm run build` (type check and bundle), in `frontend/`.
   - `phone-ui`: `npm ci`, `npx playwright install --with-deps chromium`,
     `npx playwright test --project=chromium --trace off`. Chromium only: two WebKit tests fail
     for known reasons (plan 14 fixes them, then add WebKit).
   The frontend tests start their own Vite dev server and mock the API, so they need no backend.
5. **Declare numpy** in `pyproject.toml` and refresh `uv.lock`.

## Do

- `.github/workflows/ci.yml` as above. Cache uv's and npm's downloads.
- `pyproject.toml`: the ruff dependency and config; numpy.
- Fix the 10 findings. For the unreachable block in `app.py`, delete from the line after
  `return quotes` to the end of that leftover (it stops before `def set_peers`). Confirm with the
  tests that `fund_holdings` (the real one, earlier in the file) is unaffected.
- `CLAUDE.md` does not exist on `main`; put the three check commands in the README's Development
  section so every contributor runs the same ones.

## Watch out

- A push that adds or changes a file under `.github/workflows/` can be refused when the pushing
  credential lacks GitHub's workflow permission (the loop's backlog notes this under B-001). If
  the push is rejected for that reason, commit everything else, leave the workflow file in the
  working tree, and tell the owner to commit and push it themselves.
- The loop branch (`claude-code-recursive-oncloud`) has its own `scripts/` Python files. They are
  not on `main`; nothing to lint here.

## Done when

- `uv run ruff check backend tests` passes locally.
- The workflow runs green on the branch (or the owner has been told to push the workflow file).
- The README's Development section lists the checks.
- Your report includes the wider rule set's counts, as input for the follow-up.
