from vsearch.pipeline.ingest import make_segments


def test_overlapping_windows():
    assert make_segments(70, 30, 2) == [(0, 30), (28, 58), (56, 70)]


def test_short_video_is_one_segment():
    assert make_segments(12.5, 30, 2) == [(0, 12.5)]


def test_exact_fit_has_no_empty_tail():
    segs = make_segments(58, 30, 2)
    assert segs == [(0, 30), (28, 58)]
    assert all(e > s for s, e in segs)


def test_segments_cover_the_whole_video():
    segs = make_segments(183.4, 30, 2)
    assert segs[0][0] == 0 and segs[-1][1] == 183.4
    for (_, prev_end), (start, _) in zip(segs, segs[1:]):
        assert start < prev_end          # neighbours overlap, no gaps
