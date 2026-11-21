"""Step 5: search indexed videos with a plain-English query.

Run:  uv run python -m vsearch.search "a person opening a door"
      uv run python -m vsearch.search "a red car" --top-k 3

How it works:
  1. embed the query text with CLIP (same model as the frames -> same vector space)
  2. ask pgvector for the N frames whose vectors are closest to the query vector,
     and keep only those scoring close to the best one
  3. group hits that are close in time (same video) into one moment: start -> end
  4. rank the moments by their best frame's score and print them
"""
import argparse
from dataclasses import dataclass

from vsearch import embedder
from vsearch.config import settings
from vsearch.db import connect

CANDIDATE_FRAMES = 50   # how many nearest frames to fetch before grouping
SCORE_MARGIN = 0.05     # keep only frames scoring within this much of the best frame
MERGE_GAP_SEC = 2.0     # hits at most this far apart (same video) belong to the same moment

SEARCH_SQL = """
SELECT v.video_id, v.filename, f.timestamp_sec,
       1 - (f.embedding <=> %(q)s) AS score          -- cosine similarity (1 = identical direction)
FROM frames f
JOIN videos v ON v.video_id = f.video_id
ORDER BY f.embedding <=> %(q)s                       -- smallest cosine distance first
LIMIT %(n)s
"""


@dataclass
class Moment:
    filename: str
    start_sec: float
    end_sec: float
    score: float        # best frame score inside the moment
    hits: int           # how many matching frames it contains


def group_hits(hits, merge_gap: float, frame_len: float) -> list[Moment]:
    """Turn individual frame hits into time ranges.

    hits: [(video_id, filename, timestamp_sec, score), ...] in any order.
    Example (merge_gap=2, frame_len=1):
        video A at 12s, 13s, 14s, 40s  ->  A 12-15s (3 hits), A 40-41s (1 hit)
    """
    # 1. The same timestamp can appear twice (segment overlap) -> keep its best score.
    best = {}
    for video_id, filename, t, score in hits:
        key = (video_id, t)
        if key not in best or score > best[key][1]:
            best[key] = (filename, score)

    # 2. Walk each video's hits in time order; start a new moment when the gap is too big.
    moments, current, last_key = [], None, None
    for (video_id, t), (filename, score) in sorted(best.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        if current and video_id == last_key[0] and t - last_key[1] <= merge_gap:
            current.end_sec = t + frame_len          # extend the current moment
            current.score = max(current.score, score)
            current.hits += 1
        else:
            current = Moment(filename, t, t + frame_len, score, 1)
            moments.append(current)
        last_key = (video_id, t)

    # 3. Best moment first.
    return sorted(moments, key=lambda m: m.score, reverse=True)


def search(query: str, top_k: int = 5) -> list[Moment]:
    q = embedder.embed_text(query)
    with connect() as conn:
        hits = conn.execute(SEARCH_SQL, {"q": q, "n": CANDIDATE_FRAMES}).fetchall()
    if not hits:
        return []
    # Drop weak hits. CLIP scores are relative, so "weak" means "much worse than the best match",
    # not "below some fixed number". Without this, weak frames next to a real match stretch the range.
    best_score = hits[0][3]                       # rows come back best-first
    hits = [h for h in hits if h[3] >= best_score - SCORE_MARGIN]
    # A frame sampled at t stands for the video until the next sample, i.e. t .. t + 1/fps.
    return group_hits(hits, MERGE_GAP_SEC, frame_len=1 / settings.fixed_fps)[:top_k]


def fmt(sec: float) -> str:
    return f"{int(sec // 60)}:{sec % 60:04.1f}"     # 75.0 -> "1:15.0"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Search indexed videos in plain English")
    ap.add_argument("query")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    results = search(args.query, args.top_k)
    print(f'\nQuery: "{args.query}"\n')
    if not results:
        print("No indexed frames yet. Run vsearch.ingest and vsearch.worker first.")
    for i, m in enumerate(results, 1):
        print(f"{i}. {m.filename:30}  {fmt(m.start_sec)} -> {fmt(m.end_sec)}   "
              f"score={m.score:.3f}  ({m.hits} matching frames)")
