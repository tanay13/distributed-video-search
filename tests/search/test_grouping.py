from vsearch.search.grouping import group_hits


def test_close_hits_merge_and_far_hits_split():
    hits = [("A", "a.mp4", 12.0, 0.30), ("A", "a.mp4", 13.0, 0.32),
            ("A", "a.mp4", 14.0, 0.31), ("A", "a.mp4", 40.0, 0.29)]
    moments = group_hits(hits, merge_gap=2, frame_len=1)
    assert [(m.start_sec, m.end_sec) for m in moments] == [(12.0, 15.0), (40.0, 41.0)]
    assert moments[0].score == 0.32


def test_overlap_duplicates_keep_best_score():
    # The same timestamp indexed by two overlapping segments.
    hits = [("A", "a.mp4", 29.0, 0.20), ("A", "a.mp4", 29.0, 0.25)]
    [m] = group_hits(hits, merge_gap=2, frame_len=1)
    assert (m.start_sec, m.end_sec, m.score) == (29.0, 30.0, 0.25)


def test_different_videos_never_merge():
    hits = [("A", "a.mp4", 5.0, 0.30), ("B", "b.mp4", 5.0, 0.31)]
    moments = group_hits(hits, merge_gap=2, frame_len=1)
    assert [m.video_id for m in moments] == ["B", "A"]     # best first


def test_empty():
    assert group_hits([], merge_gap=2, frame_len=1) == []
