"""Queue backend #1: the `segments` table itself is the queue (FOR UPDATE SKIP LOCKED).
RabbitMQ (T2) will be a second backend with the same claim() shape."""
from vsearch.common.contracts import SegmentTask

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
RETURNING s.video_id, s.segment_id, s.start_sec, s.end_sec, v.object_key, s.attempt,
          COALESCE(v.config_version, '')
"""


def claim(conn, worker_id: str) -> SegmentTask | None:
    """Atomically take one PENDING segment and mark it PROCESSING. Returns None if no work is left."""
    row = conn.execute(CLAIM_SQL, {"worker": worker_id}).fetchone()
    conn.commit()  # commit right away so other workers see it as PROCESSING
    if row is None:
        return None
    video_id, segment_id, start, end, object_key, attempt, config_version = row
    return SegmentTask(str(video_id), segment_id, start, end, object_key, attempt, config_version)
