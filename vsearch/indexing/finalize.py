"""Contract: finalize_video(conn, video_id). Called once, when all segments of a video are DONE, inside the
transaction that flips the video to READY. No commit. Must be idempotent.

STUB (Phase 0): does nothing yet. Aditya fills it in with A4 (merge scene cuts across segments)."""


def finalize_video(conn, video_id: str) -> None:
    return None
