"""Frame extraction with ffmpeg."""
import subprocess
from pathlib import Path


def extract_frames(video_url: str, start: float, end: float, out_dir: Path,
                   fps: float) -> list[tuple[float, Path]]:
    """Sample frames at a fixed rate from [start, end) with ffmpeg. Returns [(global_timestamp_sec, file)].

    `-ss` before `-i` seeks inside the remote file (HTTP range request), so only this
    segment's bytes are downloaded. Frame k of the output is at time start + k / fps.
    `video_url` can also be a local path.
    """
    subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(start), "-i", video_url, "-t", str(end - start),
         "-vf", f"fps={fps}", "-q:v", "3", str(out_dir / "f_%05d.jpg")],
        check=True,
    )
    files = sorted(out_dir.glob("f_*.jpg"))
    return [(round(start + k / fps, 3), f) for k, f in enumerate(files)]
