"""Contract: save_segment(conn, task, result). Upserts only, and must NOT commit: the worker commits it in
the same transaction that marks the segment DONE, so a segment can never be DONE without its rows."""
from vsearch.common.contracts import SegmentResult, SegmentTask

UPSERT_FRAME_SQL = """
INSERT INTO frames (video_id, segment_id, timestamp_sec, embedding)
VALUES (%s, %s, %s, %s)
ON CONFLICT (video_id, segment_id, timestamp_sec)
DO UPDATE SET embedding = EXCLUDED.embedding     -- re-processing overwrites instead of duplicating
"""


def save_segment(conn, task: SegmentTask, result: SegmentResult) -> None:
    with conn.cursor() as cur:
        cur.executemany(UPSERT_FRAME_SQL, [
            (f.video_id, f.segment_id, f.timestamp_sec, f.embedding) for f in result.frames])
    # result.transcripts: written here once Whisper lands (A3)
