"""The worker loop. Claims segments one at a time and, for each one:
indexing.process_segment (frames -> CLIP) -> ONE transaction: indexing.save_segment + DONE (+ READY + hooks).

Run:  uv run python -m vsearch.pipeline.worker      # process until no PENDING segments are left
      KEEP_FRAMES=1 uv run python -m vsearch.pipeline.worker   # also save frames to ./debug_frames/

Run it in 2 terminals at once and both will share the work without taking the same segment.
"""
from vsearch.common.contracts import SegmentResult, SegmentTask
from vsearch.common.db import connect
from vsearch.common.log import WORKER_ID, log
from vsearch.indexing.persist import save_segment
from vsearch.indexing.process import process_segment
from vsearch.models import embedder
from vsearch.pipeline.hooks import on_video_ready
from vsearch.pipeline.queue import postgres as queue


def finish_segment(conn, task: SegmentTask, result: SegmentResult) -> bool:
    """ONE transaction: save indexing rows + mark segment DONE + maybe mark video READY (+ hooks).
    Either all of it is saved or none of it, so a segment can never be DONE without its frames.
    Returns True if this was the video's last segment."""
    save_segment(conn, task, result)
    conn.execute(
        "UPDATE segments SET status = 'DONE', updated_at = now() WHERE video_id = %s AND segment_id = %s",
        (task.video_id, task.segment_id))
    # Lock the video row so two workers finishing the last two segments at the same moment take
    # turns on the "am I the last one?" check below.
    conn.execute("SELECT 1 FROM videos WHERE video_id = %s FOR UPDATE", (task.video_id,))
    became_ready = conn.execute(
        """UPDATE videos SET status = 'READY'
           WHERE video_id = %s AND status <> 'READY' AND NOT EXISTS (
               SELECT 1 FROM segments WHERE video_id = %s AND status <> 'DONE')
           RETURNING video_id""",
        (task.video_id, task.video_id)).fetchone() is not None
    if became_ready:
        on_video_ready(conn, task.video_id)
    conn.commit()
    return became_ready


def mark_failed(conn, task: SegmentTask) -> None:
    conn.rollback()  # discard anything half-written for this segment
    conn.execute(
        "UPDATE segments SET status = 'FAILED', updated_at = now() WHERE video_id = %s AND segment_id = %s",
        (task.video_id, task.segment_id))
    conn.commit()


def run() -> None:
    log("started")
    embedder.load()  # load CLIP once, before taking any work
    with connect() as conn:
        while (task := queue.claim(conn, WORKER_ID)) is not None:
            log(f"claimed segment {task.start_sec:.1f}s-{task.end_sec:.1f}s (attempt {task.attempt})",
                task.video_id, task.segment_id)
            try:
                result = process_segment(task)
                log(f"indexed {result.stats}", task.video_id, task.segment_id)
                ready = finish_segment(conn, task, result)
                log(f"DONE, saved {len(result.frames)} frame embeddings"
                    + (" | video READY" if ready else ""), task.video_id, task.segment_id)
            except Exception as e:
                mark_failed(conn, task)
                log(f"FAILED: {e!r}", task.video_id, task.segment_id)
    log("no PENDING segments left, exiting")


if __name__ == "__main__":
    run()
