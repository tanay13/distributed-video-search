"""Contract: process_segment(task) -> SegmentResult. Frames -> CLIP vectors. Touches no database."""
import shutil
import tempfile
import time
from pathlib import Path

from vsearch.common import storage
from vsearch.common.contracts import FrameRow, SegmentResult, SegmentTask
from vsearch.indexing import settings
from vsearch.indexing.frames import extract_frames
from vsearch.models import embedder


def process_segment(task: SegmentTask) -> SegmentResult:
    """Raises on failure (the worker then marks the segment FAILED)."""
    url = storage.presigned_url(task.object_key)
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.time()
        frames = extract_frames(url, task.start_sec, task.end_sec, Path(tmp), settings.FIXED_FPS)
        t1 = time.time()
        if not frames:
            raise RuntimeError("ffmpeg produced no frames")

        if settings.KEEP_FRAMES:  # debug: copy frames out so you can look at them
            dest = Path("debug_frames") / task.video_id / f"seg_{task.segment_id}"
            dest.mkdir(parents=True, exist_ok=True)
            for t, f in frames:
                shutil.copy(f, dest / f"{t:08.2f}s.jpg")

        vectors = embedder.embed_images([f for _, f in frames])   # shape (N, 512)
        t2 = time.time()

    rows = [FrameRow(task.video_id, task.segment_id, t, vec) for (t, _), vec in zip(frames, vectors)]
    return SegmentResult(frames=rows, transcripts=[],
                         stats={"frames": len(rows), "ffmpeg_s": round(t1 - t0, 2), "clip_s": round(t2 - t1, 2)})
