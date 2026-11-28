"""CLI: uv run python -m vsearch.search "a person opening a door" [--top-k 3]"""
import argparse

from vsearch.search.service import search


def fmt(sec: float) -> str:
    return f"{int(sec // 60)}:{sec % 60:04.1f}"     # 75.0 -> "1:15.0"


def main() -> None:
    ap = argparse.ArgumentParser(description="Search indexed videos in plain English")
    ap.add_argument("query")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    results = search(args.query, args.top_k)
    print(f'\nQuery: "{args.query}"\n')
    if not results:
        print("No indexed frames yet. Run vsearch.pipeline.ingest and vsearch.pipeline.worker first.")
    for i, m in enumerate(results, 1):
        print(f"{i}. {m.filename:30}  {fmt(m.start_sec)} -> {fmt(m.end_sec)}   score={m.score:.3f}")


if __name__ == "__main__":
    main()
