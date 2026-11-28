"""Shared log format. Every line carries worker / video / segment (README §8), so one segment is traceable
across processes with a single grep."""
import os
import socket

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


def log(msg: str, video_id="-", segment_id="-") -> None:
    print(f"[worker={WORKER_ID} video={str(video_id)[:8]} seg={segment_id}] {msg}", flush=True)
