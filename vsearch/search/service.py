"""Contract: search(query, top_k=5) -> list[Moment]. Read-only.

How it works:
  1. embed the query text with CLIP (same model as the frames -> same vector space)
  2. ask pgvector for the N frames whose vectors are closest to the query vector,
     and keep only those scoring close to the best one
  3. group hits that are close in time (same video) into one moment: start -> end
  4. rank the moments by their best frame's score
"""
from vsearch.common.contracts import Moment
from vsearch.common.db import connect
from vsearch.models import embedder
from vsearch.search import settings
from vsearch.search.grouping import group_hits

SEARCH_SQL = """
SELECT v.video_id, v.filename, f.timestamp_sec,
       1 - (f.embedding <=> %(q)s) AS score          -- cosine similarity (1 = identical direction)
FROM frames f
JOIN videos v ON v.video_id = f.video_id
ORDER BY f.embedding <=> %(q)s                       -- smallest cosine distance first
LIMIT %(n)s
"""


def search(query: str, top_k: int = 5) -> list[Moment]:
    q = embedder.embed_text(query)
    with connect() as conn:
        hits = conn.execute(SEARCH_SQL, {"q": q, "n": settings.CANDIDATE_FRAMES}).fetchall()
    if not hits:
        return []
    # Drop weak hits. CLIP scores are relative, so "weak" means "much worse than the best match",
    # not "below some fixed number". Without this, weak frames next to a real match stretch the range.
    best_score = hits[0][3]                       # rows come back best-first
    hits = [h for h in hits if h[3] >= best_score - settings.SCORE_MARGIN]
    return group_hits(hits, settings.MERGE_GAP_SEC, settings.FRAME_LEN_SEC)[:top_k]
