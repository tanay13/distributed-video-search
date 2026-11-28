# Status: Tanay (Infrastructure + pipeline)

_Only Tanay (and Tanay's Claude) edits this file. Everyone reads all three STATUS files at the start of a session._
_Last updated: 2026-11-27_

## Current task
- T0 Phase 0 split: code done, PR `[contract] Phase 0: split into owned packages` open for review (branch `tanay/phase0-split`)
- Next: T1 crash recovery + retries

## Done
- v1 local prototype: `vsearch/` ingest -> worker (Postgres SKIP LOCKED queue, ffmpeg 1 fps, CLIP ViT-B/32) -> search.
  Verified on a 3-min Big Buck Bunny clip (bird / butterfly / squirrel / apple found at the right timestamps).
- Team system: `OWNERS`, `CLAUDE.md`, `docs/WORK_PLAN.md`, these STATUS files, `.claude/` ownership hook.
- T0 Phase 0 (2026-11-27):
  - Layout from WORK_PLAN §2: `common/` (config, db, storage, log, contracts), `pipeline/` (ingest, worker,
    queue/postgres, hooks, settings, check), `models/embedder.py`, `indexing/` (frames, process, persist,
    finalize stub, settings, `config_version()`), `search/` (service, grouping, `__main__`, timeline stub, settings).
  - `scripts/migrate.py` + `schema_migrations`; migration `100_videos_config_version.sql` (`videos.config_version`).
  - All planned deps added to `pyproject.toml` (pytest + grpcio-tools as dev deps). `.env.example` split by area.
  - Tests: `tests/{pipeline,search,indexing}/`, 10 passing.
  - Regression: search output identical to v1 on the indexed bunny clip; re-indexing it with the new
    pipeline gives the same 192 frame rows with bit-identical embeddings.

## In progress
- Phase 0 PR review/merge

## Blocked / waiting on
-

## Requests to others
<!-- One line each, e.g.  "- [ ] → aditya: transcripts for silent videos should return []  (needed for D2)".
     The person it's addressed to ticks it off by mentioning it in THEIR status file, not by editing this one. -->
- [ ] → aditya, darshil: review the Phase 0 PR, then `git pull` and run `uv sync && uv run python scripts/migrate.py`

## Contract changes I'm proposing
<!-- Link the [contract] PR, and say what changes for whom. -->
- Phase 0 PR (this branch). What changes for you:
  - Commands: `python -m vsearch.pipeline.ingest`, `python -m vsearch.pipeline.worker`, `python -m vsearch.search "..."`.
  - Worker `--keep-frames` flag is now the env var `KEEP_FRAMES=1` (indexing setting).
  - `Moment` follows the contract (`video_id, filename, start_sec, end_sec, score, clip_url`); the v1 `hits` count is gone.
  - New column `videos.config_version` (run `scripts/migrate.py`).

## Notes for teammates
- aditya: `vsearch/models/__init__.py` holds the CLIP model id so `config_version()` doesn't import torch
  (ingest / the API container shouldn't need torch). `process_segment` returns `transcripts=[]` for now.
- aditya: on macOS, importing both `cv2` (opencv) and `av` (faster-whisper) in one process prints an objc
  "libavdevice implemented in both" warning; both bundle ffmpeg. Avoid importing both in the worker if it causes trouble.
- darshil: `search/settings.py::FRAME_LEN_SEC` reads the `FIXED_FPS` env var directly instead of importing indexing code.
