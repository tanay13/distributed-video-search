import subprocess

import pytest

from vsearch.indexing.frames import extract_frames


@pytest.fixture(scope="module")
def test_video(tmp_path_factory):
    """A generated 10 s, 10 fps test pattern (no download needed)."""
    path = tmp_path_factory.mktemp("video") / "testsrc.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=10:size=160x120:rate=10",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_timestamps_are_global(test_video, tmp_path):
    frames = extract_frames(str(test_video), 4.0, 7.0, tmp_path, fps=1)
    assert [t for t, _ in frames] == [4.0, 5.0, 6.0]      # global seconds, not 0, 1, 2
    assert all(f.exists() for _, f in frames)


def test_higher_fps(test_video, tmp_path):
    frames = extract_frames(str(test_video), 0.0, 2.0, tmp_path, fps=2)
    assert [t for t, _ in frames] == [0.0, 0.5, 1.0, 1.5]
