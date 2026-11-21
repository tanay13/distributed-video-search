"""Step 2: register a local video so workers can index it.

Run:  uv run python -m vsearch.ingest path/to/video.mp4

What it does (this is what POST /videos will do later):
  1. get the video duration with ffprobe
  2. upload the file to MinIO at raw/{video_id}/original.mp4
  3. insert one row in `videos` and N PENDING rows in `segments`
Workers then pick up the PENDING segments (step 3).
"""
import json
import subprocess
import sys
import uuid
from pathlib import Path

from vsearch import storage
from vsearch.config import settings
from vsearch.db import connect


def probe_duration(path: str) -> float:
    """Ask ffprobe for the container duration in seconds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def make_segments(duration: float, seg_len: float, overlap: float) -> list[tuple[float, float]]:
    """Split [0, duration] into windows of seg_len that overlap by `overlap` seconds.

    Example (duration=70, seg_len=30, overlap=2):  (0,30) (28,58) (56,70)
    The overlap means an event right at a cut is fully inside at least one segment.
    """
    step = seg_len - overlap
    segments, start = [], 0.0
    while True:
        end = min(start + seg_len, duration)
        segments.append((round(start, 3), round(end, 3)))
        if end >= duration:
            return segments
        start += step


def ingest(path: str) -> str:
    video_id = str(uuid.uuid4())
    filename = Path(path).name
    object_key = f"raw/{video_id}/original{Path(path).suffix.lower()}"

    duration = probe_duration(path)
    segments = make_segments(duration, settings.segment_sec, settings.segment_overlap_sec)

    storage.upload_file(path, object_key)
    print(f"Uploaded {filename} ({duration:.1f}s) -> s3://{settings.s3_bucket}/{object_key}")

    # One transaction: either the video and all its segments exist, or none do.
    with connect() as conn:
        conn.execute(
            "INSERT INTO videos (video_id, object_key, filename, duration_sec, status) "
            "VALUES (%s, %s, %s, %s, 'INDEXING')",
            (video_id, object_key, filename, duration),
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO segments (video_id, segment_id, start_sec, end_sec) VALUES (%s, %s, %s, %s)",
                [(video_id, i, s, e) for i, (s, e) in enumerate(segments)],
            )

    print(f"video_id={video_id}  segments={len(segments)}")
    for i, (s, e) in enumerate(segments):
        print(f"  segment {i}: {s:7.2f}s -> {e:7.2f}s  PENDING")
    return video_id


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m vsearch.ingest <video_file>")
    ingest(sys.argv[1])
