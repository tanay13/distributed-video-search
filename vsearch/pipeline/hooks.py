"""Per-video steps that run once all of a video's segments are DONE."""
from vsearch.indexing.finalize import finalize_video
from vsearch.search.timeline import build_timeline


def on_video_ready(conn, video_id: str) -> None:
    """Called inside the transaction that flips the video to READY (no commit here). If either step raises,
    the whole transaction rolls back, so a video is never READY without its scenes and timeline."""
    finalize_video(conn, video_id)      # Aditya: scenes etc.
    build_timeline(conn, video_id)      # Darshil: merged timeline
