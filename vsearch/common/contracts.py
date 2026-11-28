"""The contracts between the three areas (docs/WORK_PLAN.md §4). SHARED: change only via a [contract] PR.

Data shapes passed across area boundaries live here. The functions that cross boundaries live in their
owner's module (signatures frozen, bodies belong to the owner):

    indexing.process.process_segment(task) -> SegmentResult       Aditya   no DB access, raise on failure
    indexing.persist.save_segment(conn, task, result)             Aditya   upserts only, must NOT commit
    indexing.finalize.finalize_video(conn, video_id)              Aditya   once per video, no commit, idempotent
    indexing.config_version() -> str                              Aditya   e.g. "clip=ViT-B-32/laion2b...;fps=1"
    models.embedder.embed_images(paths) -> (N, 512)               Aditya   normalized float32
    models.embedder.embed_text(text) -> (512,)                    Aditya   normalized float32
    search.timeline.build_timeline(conn, video_id)                Darshil  no commit, idempotent
    search.service.search(query, top_k=5) -> list[Moment]         Darshil  read-only
    common.storage.presigned_url(key, expires_sec)                shared

All timestamps are GLOBAL video seconds, never segment-relative.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SegmentTask:
    """What a worker receives (README §5.2; the protobuf message mirrors it in T4)."""
    video_id: str
    segment_id: int
    start_sec: float          # global video time
    end_sec: float
    object_key: str           # MinIO key of the original video
    attempt: int
    config_version: str       # sampling settings + model versions, from indexing.config_version()


@dataclass
class FrameRow:
    video_id: str
    segment_id: int
    timestamp_sec: float
    embedding: np.ndarray     # (512,) normalized float32
    scene_id: int | None = None


@dataclass
class TranscriptRow:
    video_id: str
    segment_id: int
    start_sec: float
    end_sec: float
    text: str


@dataclass
class SegmentResult:
    """Everything indexing produced for one segment. Building it needs no DB access."""
    frames: list[FrameRow]
    transcripts: list[TranscriptRow]
    stats: dict               # e.g. {"frames": 30, "ffmpeg_s": 0.1, "clip_s": 0.5, "whisper_s": 2.0}


@dataclass
class Moment:
    """One search result (README §5.1)."""
    video_id: str
    filename: str
    start_sec: float
    end_sec: float
    score: float
    clip_url: str | None = None


@dataclass
class Event:
    id: int
    description: str
    weights: dict[str, float]     # {"visual": 0.8, "speech": 0.2}


@dataclass
class Relation:
    before: int                   # Event.id that happens first
    after: int
    max_gap_sec: float


@dataclass
class QueryPlan:
    """Query planner output (README §5.3)."""
    events: list[Event]
    relations: list[Relation]
