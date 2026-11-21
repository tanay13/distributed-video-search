"""The worker (steps 3-4). Claims PENDING segments one at a time and, for each one:
extracts frames with ffmpeg -> embeds them with CLIP -> saves vectors to `frames` -> marks DONE.

Run:  uv run python -m vsearch.worker            # process until no PENDING segments are left
      uv run python -m vsearch.worker --keep-frames   # also save the frames to ./debug_frames/

Run it in 2 terminals at once and both will share the work without taking the same segment.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from vsearch import embedder, storage
from vsearch.config import settings
from vsearch.db import connect

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


def log(msg: str, video_id="-", segment_id="-") -> None:
    # Every line carries video_id / segment_id / worker_id (README §8) so one segment is traceable.
    print(f"[worker={WORKER_ID} video={str(video_id)[:8]} seg={segment_id}] {msg}", flush=True)


# ---------------------------------------------------------------- claiming work

CLAIM_SQL = """
UPDATE segments s
SET status = 'PROCESSING', attempt = s.attempt + 1, worker_id = %(worker)s, updated_at = now()
FROM videos v
WHERE v.video_id = s.video_id
  AND (s.video_id, s.segment_id) = (
        SELECT video_id, segment_id FROM segments
        WHERE status = 'PENDING'
        ORDER BY updated_at, segment_id
        LIMIT 1
        FOR UPDATE SKIP LOCKED          -- skip rows another worker is claiming right now
  )
RETURNING s.video_id, s.segment_id, s.start_sec, s.end_sec, v.object_key
"""


def claim_segment(conn):
    """Atomically take one PENDING segment and mark it PROCESSING. Returns None if no work is left."""
    row = conn.execute(CLAIM_SQL, {"worker": WORKER_ID}).fetchone()
    conn.commit()  # commit right away so other workers see it as PROCESSING
    return row


UPSERT_FRAME_SQL = """
INSERT INTO frames (video_id, segment_id, timestamp_sec, embedding)
VALUES (%s, %s, %s, %s)
ON CONFLICT (video_id, segment_id, timestamp_sec)
DO UPDATE SET embedding = EXCLUDED.embedding     -- re-processing overwrites instead of duplicating
"""


def finish_segment(conn, video_id, segment_id, rows) -> None:
    """ONE transaction: save frame embeddings + mark segment DONE + maybe mark video READY.
    Either all of it is saved or none of it, so a segment can never be DONE without its frames."""
    with conn.cursor() as cur:
        cur.executemany(UPSERT_FRAME_SQL, rows)
    conn.execute(
        "UPDATE segments SET status = 'DONE', updated_at = now() WHERE video_id = %s AND segment_id = %s",
        (video_id, segment_id))
    # Lock the video row so two workers finishing the last two segments at the same moment take
    # turns on the "am I the last one?" check below (fixes the race explained in step 3).
    conn.execute("SELECT 1 FROM videos WHERE video_id = %s FOR UPDATE", (video_id,))
    conn.execute(
        """UPDATE videos SET status = 'READY'
           WHERE video_id = %s AND NOT EXISTS (
               SELECT 1 FROM segments WHERE video_id = %s AND status <> 'DONE')""",
        (video_id, video_id))
    conn.commit()


def mark_failed(conn, video_id, segment_id) -> None:
    conn.rollback()  # discard anything half-written for this segment
    conn.execute(
        "UPDATE segments SET status = 'FAILED', updated_at = now() WHERE video_id = %s AND segment_id = %s",
        (video_id, segment_id))
    conn.commit()


# ---------------------------------------------------------------- frame extraction

def extract_frames(video_url: str, start: float, end: float, out_dir: Path) -> list[tuple[float, Path]]:
    """Sample frames at a fixed rate (FIXED_FPS) from [start, end) with ffmpeg.

    `-ss` before `-i` seeks inside the remote file (HTTP range request), so only this
    segment's bytes are downloaded. Frame k of the output is at time start + k / fps.
    """
    fps = settings.fixed_fps
    subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-i", video_url, "-t", str(end - start),
         "-vf", f"fps={fps}", "-q:v", "3", str(out_dir / "f_%05d.jpg")],
        check=True,
    )
    files = sorted(out_dir.glob("f_*.jpg"))
    return [(round(start + k / fps, 3), f) for k, f in enumerate(files)]


# ---------------------------------------------------------------- main loop

def process_segment(video_id, segment_id, start, end, object_key, keep_frames: bool) -> list:
    """Frames -> CLIP vectors. Returns rows ready for the `frames` table. Touches no database."""
    url = storage.presigned_url(object_key)
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.time()
        frames = extract_frames(url, start, end, Path(tmp))
        t1 = time.time()
        if not frames:
            raise RuntimeError("ffmpeg produced no frames")

        if keep_frames:  # debug: copy frames out so you can look at them
            dest = Path("debug_frames") / str(video_id) / f"seg_{segment_id}"
            dest.mkdir(parents=True, exist_ok=True)
            for t, f in frames:
                shutil.copy(f, dest / f"{t:08.2f}s.jpg")

        vectors = embedder.embed_images([f for _, f in frames])   # shape (N, 512)
        t2 = time.time()

    log(f"{len(frames)} frames {start:.1f}s-{end:.1f}s | ffmpeg {t1 - t0:.2f}s, "
        f"CLIP {t2 - t1:.2f}s", video_id, segment_id)
    return [(video_id, segment_id, t, vec) for (t, _), vec in zip(frames, vectors)]


def run(keep_frames: bool) -> None:
    log("started")
    embedder.load()  # load CLIP once, before taking any work
    with connect() as conn:
        while (task := claim_segment(conn)) is not None:
            video_id, segment_id, start, end, object_key = task
            log(f"claimed segment {start:.1f}s-{end:.1f}s", video_id, segment_id)
            try:
                rows = process_segment(video_id, segment_id, start, end, object_key, keep_frames)
                finish_segment(conn, video_id, segment_id, rows)
                log(f"DONE, saved {len(rows)} frame embeddings", video_id, segment_id)
            except Exception as e:
                mark_failed(conn, video_id, segment_id)
                log(f"FAILED: {e!r}", video_id, segment_id)
    log("no PENDING segments left, exiting")


if __name__ == "__main__":
    run(keep_frames="--keep-frames" in sys.argv)
