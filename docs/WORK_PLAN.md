# Work Plan: dividing the build between Tanay, Aditya and Darshil

> **Goal:** three people (each with their own Claude) build in parallel **without editing the same files**.
> How: (1) every file has one owner (`OWNERS`); (2) areas talk only through fixed **contracts** (§4);
> (3) a one-time **Phase 0** split (§3) creates that structure before parallel work starts;
> (4) coordination happens in per-person files and small `[contract]` PRs (§6).
>
> Spec: `README.md`. Rules for Claude: `CLAUDE.md`. Status: `docs/team/STATUS-<name>.md`.

---

## 0. Who owns what

| Person | Area | Owns (folders) | README stream |
|---|---|---|---|
| **Tanay** | Infrastructure + pipeline | `vsearch/pipeline/`, `vsearch/api/`, `docker-compose.yml`, `Dockerfile*`, `k8s/`, `proto/`, `scripts/`, `db/migrations/1xx` | 1. Infrastructure |
| **Aditya** | Indexing | `vsearch/indexing/`, `vsearch/models/`, `db/migrations/2xx` | 2. Workers and indexing |
| **Darshil** | Search | `vsearch/search/`, `eval/`, `db/migrations/3xx` | 3. Timelines and search |
| *shared* | Contracts | `vsearch/common/`, `pyproject.toml`, `uv.lock`, `.env.example`, `db/init/`, `README.md`, `OWNERS`, `CLAUDE.md`, this file | change only via `[contract]` PR |

Database tables also have owners. Only the owner's migrations may `ALTER` them:

| Tables | Owner | Written by |
|---|---|---|
| `videos`, `segments`, `schema_migrations` | Tanay | ingest, worker loop, migrate script |
| `frames`, `transcripts`, `scenes` (new) | Aditya | `indexing.persist`, `indexing.finalize` |
| `timeline` (new), any search cache tables | Darshil | `search.timeline` |

*Assignment follows the README's three streams. Tanay takes infrastructure because he set up Docker and
the v1 prototype. To swap, change the names in this table and in `OWNERS` in one `[contract]` PR.*

---

## 1. Where we are (v1 prototype, done)

Working end to end on a laptop, with no API, no RabbitMQ and no Redis:
```
uv run python -m vsearch.ingest video.mp4    # upload to MinIO + segments rows (PENDING)
uv run python -m vsearch.worker              # claim (FOR UPDATE SKIP LOCKED) -> ffmpeg 1 fps -> CLIP -> pgvector
uv run python -m vsearch.search "a red car"  # CLIP text -> nearest frames -> grouped time ranges
```
Known gaps: a crashed worker leaves its segment `PROCESSING`; `FAILED` is never retried; vision only
(no speech); center-crop hides frame edges; single-event queries only; text on screen is weak.

---

## 2. Target repository layout (after Phase 0)

```text
vsearch/
├── common/                 SHARED: imported by everyone, changed only via [contract] PR
│   ├── config.py           DB + MinIO settings only (moved from vsearch/config.py)
│   ├── db.py               connect()
│   ├── storage.py          upload_file / download_file / presigned_url
│   ├── contracts.py        dataclasses + the cross-area function list (§4)
│   └── log.py              log(msg, video_id, segment_id), shared log format
├── pipeline/               TANAY
│   ├── settings.py         SEGMENT_SEC, OVERLAP, LEASE_SEC, MAX_ATTEMPTS, QUEUE_BACKEND ...
│   ├── ingest.py           (moved) python -m vsearch.pipeline.ingest
│   ├── worker.py           loop: claim -> indexing.process_segment -> persist -> DONE (+ hooks)
│   ├── queue/              postgres.py (today's SKIP LOCKED), rabbitmq.py (T2)
│   ├── claims.py           Redis claims + progress (T3)
│   └── hooks.py            on_video_ready(): calls indexing.finalize + search.timeline
├── api/                    TANAY: FastAPI (T5)
├── models/                 ADITYA
│   └── embedder.py         (moved) CLIP: embed_images / embed_text
├── indexing/               ADITYA
│   ├── settings.py         FIXED_FPS, SAMPLING_MODE, THRESHOLD, MIN_GAP, MAX_GAP, WHISPER_MODEL ...
│   ├── frames.py           (moved) extract_frames (ffmpeg)
│   ├── sampling.py         adaptive frame selection (A2)
│   ├── transcribe.py       Whisper (A3)
│   ├── process.py          process_segment(task) -> SegmentResult   (contract)
│   ├── persist.py          save_segment(conn, task, result)          (contract)
│   └── finalize.py         finalize_video(conn, video_id)            (contract, stub in Phase 0)
└── search/                 DARSHIL
    ├── settings.py         CANDIDATE_FRAMES, SCORE_MARGIN, MERGE_GAP, PLANNER_MODEL ...
    ├── __main__.py         python -m vsearch.search "query" (CLI, same as today)
    ├── service.py          search(query, top_k) -> list[Moment]     (contract)
    ├── retrieve.py         frame / transcript / scene candidate retrieval
    ├── grouping.py         (moved) group_hits
    ├── planner.py          LLM query planner (D4)
    ├── rerank.py           temporal reranker (D5)
    └── timeline.py         build_timeline(conn, video_id)            (contract, stub in Phase 0)
db/init/                    SHARED, frozen (runs only on a fresh volume)
db/migrations/              1xx Tanay · 2xx Aditya · 3xx Darshil
scripts/migrate.py          TANAY: applies db/migrations/*.sql in order, records them in schema_migrations
tests/{pipeline,api,indexing,search}/   each owner's tests
eval/                       DARSHIL: harness + metrics;  eval/queries/<name>.jsonl  each person labels their own
experiments/{scaling,failure}/ TANAY · {adaptive}/ ADITYA · {temporal}/ DARSHIL
docs/areas/{pipeline,indexing,search}.md   each owner documents their area
docs/team/STATUS-{tanay,aditya,darshil}.md each owner's status + requests
```

**Why this prevents conflicts:** today `worker.py` mixes Tanay's work (claiming, status) with Aditya's
(frames, CLIP), and `config.py` holds everyone's settings. Phase 0 cuts those files along the ownership
lines, so after that nobody needs to touch anyone else's file for normal work.

---

## 3. Phase 0: the split (Tanay, BLOCKING, ~1 session)

**Nobody else starts coding until this is merged** (they can read, plan, find datasets and label queries).
Branch: `tanay/phase0-split`. One PR, titled `[contract] Phase 0: split into owned packages`.

- [ ] Create the folders in §2 (with `__init__.py`; `.gitkeep` in empty dirs).
- [ ] **Move** (`git mv`, so history follows): `config.py, db.py, storage.py -> common/`;
      `embedder.py -> models/embedder.py`; `ingest.py -> pipeline/ingest.py`; `search.py -> search/`
      (split into `service.py`, `grouping.py`, `__main__.py`).
- [ ] **Split `worker.py`:** claim / finish / mark_failed / loop -> `pipeline/worker.py`;
      `extract_frames` -> `indexing/frames.py`; frame + CLIP part of `process_segment` -> `indexing/process.py`;
      the frames upsert -> `indexing/persist.py`.
- [ ] Write `common/contracts.py` exactly as in §4, and make the moved code use it.
- [ ] Add **stubs** with final signatures: `indexing/finalize.py::finalize_video` (no-op),
      `search/timeline.py::build_timeline` (no-op), `pipeline/hooks.py::on_video_ready` (calls both inside
      the same transaction that flips the video to READY).
- [ ] Move area settings out of `common/config.py` into `pipeline/settings.py`, `indexing/settings.py`
      and `search/settings.py`.
- [ ] `scripts/migrate.py` + `schema_migrations` table. `db/init` stays as-is.
- [ ] `pyproject.toml`: add **every dependency we expect** now (fastapi, uvicorn, python-multipart, httpx,
      pika, redis, protobuf, grpcio-tools, faster-whisper, scenedetect, opencv-python-headless, anthropic,
      pytest), then `uv lock`. This makes later dependency PRs rare.
- [ ] `.env.example`: one section per area (`# --- pipeline (Tanay)`, `# --- indexing (Aditya)`, `# --- search (Darshil)`).
- [ ] Tests that pass: `tests/pipeline/test_segments.py` (make_segments), `tests/search/test_grouping.py`
      (group_hits), `tests/indexing/test_frames.py` (timestamps for a generated test video).
- [ ] **Regression check:** ingest -> worker -> search on the Big Buck Bunny clip gives the same results as v1.
- [ ] `OWNERS`: delete the temporary `vsearch/*.py tanay` line. README §6 layout: point to this file.
- [ ] Merge, then post in the team chat: "Phase 0 merged, pull main".

---

## 4. Contracts (the only coupling between areas)

All of this lives in `vsearch/common/contracts.py`. **Signatures are frozen.** Bodies belong to the owner.

### 4.1 Data shapes
```python
@dataclass(frozen=True)
class SegmentTask:                 # what a worker receives (README §5.2; protobuf mirrors it in T4)
    video_id: str
    segment_id: int
    start_sec: float               # global video time
    end_sec: float
    object_key: str                # MinIO key of the original video
    attempt: int
    config_version: str            # sampling settings + model versions, from indexing.config_version()

@dataclass
class FrameRow:      video_id: str; segment_id: int; timestamp_sec: float; embedding: np.ndarray; scene_id: int | None = None
@dataclass
class TranscriptRow: video_id: str; segment_id: int; start_sec: float; end_sec: float; text: str

@dataclass
class SegmentResult:               # everything indexing produced for one segment. No DB access needed to build it
    frames: list[FrameRow]
    transcripts: list[TranscriptRow]
    stats: dict                    # e.g. {"frames": 30, "ffmpeg_s": 0.1, "clip_s": 0.5, "whisper_s": 2.0}

@dataclass
class Moment:                      # one search result (README §5.1)
    video_id: str; filename: str; start_sec: float; end_sec: float; score: float
    clip_url: str | None = None

@dataclass
class Event:     id: int; description: str; weights: dict[str, float]        # {"visual": .8, "speech": .2}
@dataclass
class Relation:  before: int; after: int; max_gap_sec: float
@dataclass
class QueryPlan: events: list[Event]; relations: list[Relation]               # README §5.3
```

### 4.2 Functions that cross area boundaries
| Function | Owner (implements) | Called by | Rules |
|---|---|---|---|
| `indexing.process.process_segment(task) -> SegmentResult` | Aditya | pipeline worker | No DB access. Raise on failure. Deterministic for the same task + config. |
| `indexing.persist.save_segment(conn, task, result)` | Aditya | pipeline worker | Upserts only. **Must not commit**: the worker commits it together with `DONE`. |
| `indexing.finalize.finalize_video(conn, video_id)` | Aditya | `pipeline.hooks.on_video_ready` | Runs once when all segments are DONE (scenes etc.). No commit. Idempotent. |
| `indexing.config_version() -> str` | Aditya | pipeline ingest | e.g. `"clip=ViT-B-32/laion2b;fps=1;whisper=small"` |
| `models.embedder.embed_images(paths) -> (N,512)` / `embed_text(str) -> (512,)` | Aditya | indexing, search | Normalized float32. Changing the model = `[contract]` PR + re-index. |
| `search.timeline.build_timeline(conn, video_id)` | Darshil | `pipeline.hooks.on_video_ready` | No commit. Idempotent (delete + insert for that video). |
| `search.service.search(query, top_k=5) -> list[Moment]` | Darshil | CLI, API (T5) | Read-only. |
| `common.storage.presigned_url(key, expires)` | shared | API, worker | |

### 4.3 How a segment flows after Phase 0 (who does what)
```
pipeline.ingest  (Tanay)   upload, videos + segments rows, enqueue SegmentTask
pipeline.worker  (Tanay)   claim task (Postgres now, RabbitMQ+Redis later)
   └─ indexing.process_segment(task)        (Aditya)  frames/CLIP/Whisper -> SegmentResult
   └─ BEGIN
        indexing.save_segment(conn, ...)    (Aditya)  upsert frames, transcripts
        segment -> DONE                     (Tanay)
        if last segment: video -> READY     (Tanay)
           └─ hooks.on_video_ready:  indexing.finalize_video (Aditya) + search.build_timeline (Darshil)
      COMMIT, then ack the queue message    (Tanay)
search.service.search(query)  (Darshil)     planner -> retrieve -> rerank -> list[Moment]
api  (Tanay)                                 thin HTTP layer over ingest / status / search
```

---

## 5. Task lists

Each task says **what to build**, the **files** (all inside the owner's area) and **done when**.
Tasks are in suggested order. A `needs` line marks a real dependency; everything else can start right after Phase 0.

### 5.1 Tanay: infrastructure + pipeline

**T0. Phase 0 split** (§3). Blocking for everyone.

**T1. Crash recovery + retries** (`pipeline/worker.py`, `pipeline/settings.py`)
- Reclaim segments stuck in `PROCESSING` longer than `LEASE_SEC` (default 300). Retry `FAILED` until
  `attempt >= MAX_ATTEMPTS` (default 3), then leave them `FAILED` for good. Skip if already `DONE`.
- Done when: `kill -9` on a worker mid-segment, then a new worker finishes the video, with the frame count
  equal to a clean run (test in `tests/pipeline/`).

**T2. RabbitMQ queue** (`docker-compose.yml`, `pipeline/queue/rabbitmq.py`)
- Add `rabbitmq:management` to compose. Durable queue `segment_tasks` with `x-max-length` +
  `overflow=reject-publish`, DLQ `segment_tasks_dlq`, prefetch 1, **manual ack only after commit** (README §5.6).
- `QUEUE_BACKEND=postgres|rabbitmq` switch; the Postgres queue stays as fallback.
- Done when: 2 workers drain a video via RabbitMQ; a poison segment ends up in the DLQ after MAX_ATTEMPTS.

**T3. Redis claims + progress** (`docker-compose.yml`, `pipeline/claims.py`)
- `SET claim:{video_id}:{segment_id} <worker_id> NX EX 60`, renewed by a heartbeat; `job:{video_id}:progress`
  hash (total/done/failed) (README §5.5).
- Done when: killing a worker lets another one pick the segment up after expiry, with no duplicate rows.

**T4. Protobuf task message** (`proto/segment_task.proto`, `pipeline/queue/`)
- Mirrors `SegmentTask`; RabbitMQ messages are protobuf. Conversion lives in `pipeline/`.

**T5. FastAPI** (`vsearch/api/`, `tests/api/`)
- `POST /videos` (multipart -> ingest), `GET /videos/{id}/status`, `POST /search` -> `search.service.search`,
  `GET /health`. `clip_url` = presigned URL + `#t=start,end`. Redis cache `cache:search:{hash}` with a short TTL.
- Done when: the README §5.1 endpoints work with `httpx` tests against a running stack.

**T6. Containers** (`Dockerfile.api`, `Dockerfile.worker`, `docker-compose.yml`)
- `docker compose up --build` runs everything (README §7). `scripts/e2e_demo.sh`: upload, poll, search.

**T7. Kubernetes on GCP** (`k8s/`)
- Deployments for api and worker (GPU node pool for workers), Services, ConfigMap/Secrets, manual replicas 1/2/4.

**T8. Experiments A (scaling) + D (failure)** (`experiments/scaling/`, `experiments/failure/`)
- Scripts that run unattended and write CSVs + plots (README §9).

### 5.2 Aditya: indexing

**A1. Embedder hardening** (`models/embedder.py`, `indexing/settings.py`)
- Option `PAD_TO_SQUARE=true` (letterbox instead of center-crop; v1 hides ~44% of a 16:9 frame's width).
  Embed in chunks of `EMBED_BATCH` frames. Implement `indexing.config_version()`.
- Done when: an object at the frame edge is found with padding and missed without (small test video).

**A2. Adaptive frame selection** (`indexing/sampling.py`, `indexing/frames.py`, `tests/indexing/`)
- The deterministic rule in README §4.2: decode low-res grayscale (ffmpeg pipe or OpenCV), accumulate
  mean pixel difference, keep a frame on scene cut, `THRESHOLD` or `MAX_GAP`, never closer than `MIN_GAP`.
  Write it as a **pure function** over (timestamp, diff) data so it's unit-testable.
- `SAMPLING_MODE=fixed|adaptive`.
- Done when: unit tests for a static clip (≈1 frame per MAX_GAP), fast motion (capped by MIN_GAP), slow drift
  (accumulation triggers), and the same input giving the same output.

**A3. Whisper transcripts** (`indexing/transcribe.py`, `indexing/process.py`, `indexing/persist.py`)
- `faster-whisper` (`WHISPER_MODEL=small`, CPU on laptops, GPU in cloud) on each segment's audio (ffmpeg -> 16 kHz wav).
  **Global** timestamps. Overlap rule: keep a transcript piece only if its midpoint lies in the segment's
  core `[start + overlap/2, end - overlap/2)` (or the segment's real start/end at the video edges), so overlaps aren't duplicated.
- Fills the existing `transcripts` table. Videos without audio work (empty list).
- Done when: a lecture clip's transcripts are searchable with `websearch_to_tsquery`, with no duplicated sentences at segment boundaries.

**A4. Scenes** (`db/migrations/201_scenes.sql`, `indexing/finalize.py`, `indexing/process.py`)
- PySceneDetect cuts per segment -> `frames.scene_id`; `finalize_video` merges the cuts across segments and
  writes `scenes(video_id, scene_id, start_sec, end_sec, embedding = mean of frame embeddings)` + an HNSW index.
- Done when: a 3-minute video has sensible scene boundaries, and `finalize_video` run twice gives the same rows.

**A5. config_version in rows** (`db/migrations/202_config_version.sql`, `indexing/persist.py`)
- Store `config_version` on frames and transcripts so Experiment B can compare settings side by side.

**A6. Experiment B (adaptive vs fixed vs uniform at the same budget)** (`experiments/adaptive/`)
- Number of embeddings, GPU time, storage, Recall@K (uses Darshil's eval harness, D7). Plot accuracy against cost.

**Stretch: OCR** (`indexing/ocr.py`, migration 2xx `ocr_text` table) fixes "text on screen" queries, which are weak in v1.

### 5.3 Darshil: search

**D1. Search package** (`search/service.py`, `search/retrieve.py`, `search/grouping.py`, `tests/search/`)
- Start from the moved v1 code. `retrieve.frames(query_vec, n)` returns candidates; `service.search` returns `list[Moment]`.
  Unit tests for `group_hits` (overlap duplicates, gaps, different videos).

**D2. Speech retrieval + fusion** (`search/retrieve.py`)
- `retrieve.transcripts(text, n)` uses `search_vector @@ websearch_to_tsquery` + `ts_rank_cd`.
  Combine with frame scores: `w_visual * clip_sim + w_speech * normalized_text_rank` (README §5.7).
- Doesn't wait for A3: tests insert fake `transcripts` rows.
- Done when: "where does he say deadlock" ranks the right transcript moment first on fixture data.

**D3. Timeline** (`db/migrations/301_timeline.sql`, `search/timeline.py`)
- `build_timeline(conn, video_id)`: merge visual intervals (frames/scenes) and speech intervals into
  `timeline(video_id, start_sec, end_sec, kind, text)`, joining pieces split by segment boundaries (README §4.1 step 4).
- Done when: it's idempotent, and pieces split across a segment boundary come out as one interval.

**D4. Query planner** (`search/planner.py`, `search/settings.py`)
- LLM turns the query into `QueryPlan` (README §5.3); strict JSON validation; on any failure, **fallback = one event**
  with default weights; cache plans by query hash. API key from env (`ANTHROPIC_API_KEY`), never committed.
  Use the provider's current recommended model (ask Claude to check the latest Claude model IDs when implementing).
- Done when: simple / compositional / temporal example queries give sensible plans, and the fallback is tested.

**D5. Temporal reranker** (`search/rerank.py`, `tests/search/`)
- Given top-N candidates per event, find `t1 < t2 < ...` meeting every relation within `max_gap_sec`,
  maximizing `sum(score_i) - lambda * sum(gap_i)` (README §5.7, dynamic programming over candidates).
  Return `[t1 - pad, tn + pad]`.
- Done when: unit tests on hand-made timelines (right order wins, wrong order rejected, gap limit enforced).

**D6. Coarse-to-fine retrieval** (`search/retrieve.py`). Needs A4 (scenes).
- Top scenes first, then frames inside them (README §4.3 step 6).

**D7. Evaluation harness + Experiment C** (`eval/`, `experiments/temporal/`)
- Query file format from README §9 (`eval/queries/<name>.jsonl`, everyone labels their own file).
  `eval/run_eval.py` computes Recall@K and temporal IoU per query level. Dataset choice and download script
  (for example a Charades-STA subset). Experiment C: frame-only vs ordered-event search.

### 5.4 Shared work (each person in their own files)
- **Labelling:** ~12 queries each in `eval/queries/<name>.jsonl` (simple, compositional, temporal).
- **Docs:** `docs/areas/<area>.md`, covering how your part works and how to run it.
- **Final report:** one section per area plus a shared intro and conclusion (write it in a doc, not in this repo).

---

## 6. Coordination system

### 6.1 Daily loop (for each person and their Claude)
1. `git fetch && git pull --rebase origin main` on your branch.
2. Read all three `docs/team/STATUS-*.md`. Anything addressed to you is in other people's "Requests to others".
3. Work only in your folders. Small commits.
4. End of the day: update **your** STATUS file and push. Open or refresh your PR.

### 6.2 Needing something from another area
| Situation | What to do |
|---|---|
| You need a **new behaviour** behind an existing contract | Add a request line in **your** STATUS file ("→ aditya: transcripts for videos without audio should return []") and tell them in chat. Meanwhile use a fake in your tests. |
| You need a **new or changed contract** (signature, dataclass field, table column you'd read) | Open a small PR titled `[contract] ...` touching only shared files (+ stub bodies). Tag the affected owner. Merge within 24h. Everyone rebases. |
| You need a **dependency** | Same as a contract PR (`pyproject.toml` + `uv.lock`). |
| You found a **bug in someone else's file** | Don't fix it there. Add a failing test in your own tests or describe it in your STATUS file, and tell them. |

### 6.3 Git rules
- Branches: `<name>/<topic>`, e.g. `tanay/rabbitmq`, `aditya/whisper`, `darshil/reranker`.
- PRs into `main` only, at least 1 teammate review, squash merge. Keep PRs small (≤ ~400 lines).
- Never push to `main` directly. Never force-push a branch someone else uses.
- `uv.lock` conflict: `git checkout origin/main -- uv.lock && uv lock`, then continue the rebase.
- Merge `[contract]` PRs **first** when several PRs are open.

### 6.4 The ownership guard
`.claude/settings.json` registers `.claude/hooks/check_ownership.py`. Before Claude edits a file, it checks
`OWNERS`: your files go through normally; another person's file or a shared file makes Claude **ask you
first** and explain why. Set who you are once, in `.claude/settings.local.json` (gitignored):
```json
{ "env": { "VSEARCH_OWNER": "aditya" } }
```
(Without it, the hook uses the first name in `git config user.name`.) The guard only covers Claude's file-edit
tools. The rule in `CLAUDE.md` covers Bash edits.

---

## 7. Milestones and integration checkpoints

Each milestone ends with an **integration check**: everyone merges, then on a fresh `main` run
`docker compose up -d && uv run python scripts/migrate.py`, ingest the shared test videos, and run the e2e demo.

| Milestone | Tanay | Aditya | Darshil | Integration check |
|---|---|---|---|---|
| **M0** (day 1–2) | T0 Phase 0 merged | set up env, choose datasets | set up env, query format, start labels | v1 regression passes on the new layout |
| **M1** (end of week 1) | T1 crash recovery, T2 RabbitMQ | A1 embedder, A2 adaptive sampling + tests | D1 package, D2 speech retrieval, D5 reranker (unit tests) | kill a worker mid-video, index still correct |
| **M2** (end of week 2) | T3 Redis, T4 protobuf | A3 Whisper, A5 config_version | D3 timeline, D4 planner | a speech query and a two-event query work end to end |
| **M3** (end of week 3) | T5 API, T6 containers, T7 K8s | A4 scenes | D6 coarse-to-fine, D7 eval harness | `docker compose up --build` demo; the same flow on GKE |
| **M4** (week 4) | Experiments A, D | Experiment B | Experiment C | all experiments produce CSVs + plots |
| **M5** (week 5) | report + demo | report + demo | report + demo | final presentation |

*Weeks are relative to the Phase 0 merge. Adjust to the course deadline; the order matters more than the dates.*
If behind, cut in README §11 order (the 4-worker run, the third query level, the second baseline in B), then OCR and D6.

---

## 8. Getting started (each person, once Phase 0 is merged)
```bash
git checkout main && git pull
cp .env.example .env                 # set your own local passwords (+ ANTHROPIC_API_KEY for Darshil)
echo '{ "env": { "VSEARCH_OWNER": "<your-name>" } }' > .claude/settings.local.json
docker compose up -d && uv sync && uv run python scripts/migrate.py
uv run pytest                        # everything green before you start
git checkout -b <your-name>/<first-task>
```
Then open Claude in the repo and say: *"Read CLAUDE.md, docs/WORK_PLAN.md and the STATUS files, then start my
next task."* `CLAUDE.md` is loaded automatically, and it tells Claude which area is yours and what it may touch.
