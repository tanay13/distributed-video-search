"""Turn individual frame hits into time ranges (moments). Pure function, no DB."""
from vsearch.common.contracts import Moment


def group_hits(hits, merge_gap: float, frame_len: float) -> list[Moment]:
    """hits: [(video_id, filename, timestamp_sec, score), ...] in any order.

    Example (merge_gap=2, frame_len=1):
        video A at 12s, 13s, 14s, 40s  ->  A 12-15s, A 40-41s
    """
    # 1. The same timestamp can appear twice (segment overlap) -> keep its best score.
    best = {}
    for video_id, filename, t, score in hits:
        key = (str(video_id), t)
        if key not in best or score > best[key][1]:
            best[key] = (filename, score)

    # 2. Walk each video's hits in time order; start a new moment when the gap is too big.
    moments, current, last_key = [], None, None
    for (video_id, t), (filename, score) in sorted(best.items()):
        if current and video_id == last_key[0] and t - last_key[1] <= merge_gap:
            current.end_sec = t + frame_len          # extend the current moment
            current.score = max(current.score, score)
        else:
            current = Moment(video_id, filename, t, t + frame_len, score)
            moments.append(current)
        last_key = (video_id, t)

    # 3. Best moment first.
    return sorted(moments, key=lambda m: m.score, reverse=True)
