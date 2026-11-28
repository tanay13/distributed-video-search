"""Sanity check: can we reach PostgreSQL (with pgvector + our tables) and the MinIO bucket?

Run:  uv run python -m vsearch.pipeline.check
"""
from vsearch.common import storage
from vsearch.common.config import settings
from vsearch.common.db import connect


def main() -> None:
    with connect() as conn:
        ext = conn.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'").fetchone()
        tables = [r[0] for r in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")]
    print(f"Postgres OK  pgvector={ext[0] if ext else 'MISSING'}  tables={tables}")

    storage.bucket_exists()
    print(f"MinIO OK     bucket='{settings.s3_bucket}' at {settings.s3_endpoint}")


if __name__ == "__main__":
    main()
