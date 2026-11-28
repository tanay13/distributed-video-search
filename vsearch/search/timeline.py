"""Contract: build_timeline(conn, video_id). Called once per video inside the transaction that flips it to
READY. No commit. Must be idempotent (delete + insert for that video).

STUB (Phase 0): does nothing yet. Darshil fills it in with D3."""


def build_timeline(conn, video_id: str) -> None:
    return None
