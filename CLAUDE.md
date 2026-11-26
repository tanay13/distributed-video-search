# Distributed Video Search — rules for every Claude session

Three people work on this repo in parallel, each with their own Claude: **Tanay** (infrastructure + pipeline),
**Aditya** (indexing), **Darshil** (search). These rules keep us out of each other's files.
The full plan is `docs/WORK_PLAN.md`. Ownership is in `OWNERS`. The project spec is `README.md`.

## 1. Start of every session
1. Work out whose session this is: `VSEARCH_OWNER` env var, else the first name in `git config user.name`.
   If unclear, ask.
2. `git fetch origin && git status`. Never work on `main`. Use or create `<name>/<topic>` (e.g. `aditya/whisper`)
   and rebase it on `origin/main` (`git pull --rebase origin main`).
3. Read: your section of `docs/WORK_PLAN.md`, **all three** `docs/team/STATUS-*.md` (other people's
   "Requests to others" may be addressed to you), and `vsearch/common/contracts.py` once it exists.

## 2. Ownership: the main rule
- **Only edit files you own** (see `OWNERS`; the last matching line wins). New files go only in your own folders.
- A PreToolUse hook (`.claude/hooks/check_ownership.py`) asks the human before any edit to someone else's
  file or a `shared` file. **Don't get around it** with Bash (`sed`, `cat >`, `cp`) on files you don't own.
- **You need a change in someone else's file:** don't make it. Code against the contract and use a fake or
  stub inside **your own** tests. Then add a line under "Requests to others" in **your** STATUS file and tell
  your human, so they can message the owner.
- **Shared files** (`vsearch/common/*`, `pyproject.toml`, `uv.lock`, `.env.example`, `db/init/*`, `README.md`,
  `OWNERS`, `CLAUDE.md`, `docs/WORK_PLAN.md`, `.claude/*`) change only in a separate, small PR titled
  `[contract] <what>`, announced to the team and merged quickly. Never mix contract changes into a feature PR.

## 3. Contracts: how our code connects
The cross-area function signatures and data shapes are listed in `docs/WORK_PLAN.md` §4 and live in
`vsearch/common/contracts.py`. Don't change a signature you don't own. To call another area that isn't built
yet, call the contract function; its stub returns something harmless until the owner fills it in.

## 4. Database changes
- Never edit `db/init/*` (it only runs on a brand-new volume). Schema changes are **new** files in `db/migrations/`
  inside your number range: **Tanay 100–199, Aditya 200–299, Darshil 300–399**, e.g. `db/migrations/203_scenes.sql`.
- Migrations must be idempotent (`IF NOT EXISTS`) and never edit or drop another owner's tables or columns.
- Apply them with `uv run python scripts/migrate.py` (added in Phase 0).

## 5. Dependencies
- Adding a package changes shared files (`pyproject.toml`, `uv.lock`), so put it in a `[contract]` PR.
  Phase 0 pre-adds everything we expect to need.
- `uv.lock` merge conflict: never hand-edit it. Run `git checkout origin/main -- uv.lock && uv lock`.

## 6. Code conventions
- Python 3.13, run everything with `uv run ...`. Settings come from env vars / `.env`; never commit `.env` or keys.
- Area-specific settings go in your own module (`vsearch/<area>/settings.py`), not in `vsearch/common/config.py`.
- Every log line carries `video_id`, `segment_id`, `worker_id` where they apply (README §8).
- Workers stay idempotent: running the same segment twice must give the same database state (upserts).
- Tests live in `tests/<your area>/` and must not need another person's unfinished code. Use fakes.
- Store timestamps in **global video seconds**, never segment-relative.

## 7. End of every session
1. Run your tests: `uv run pytest tests/<your area>`.
2. Update **your** `docs/team/STATUS-<name>.md`: done, in progress, blocked, requests to others, contract changes.
3. Commit to your branch with clear messages. Open or update the PR into `main`; one teammate reviews before merge.
4. Never push to `main`, never force-push someone else's branch, never `git push --force` on a shared branch.
