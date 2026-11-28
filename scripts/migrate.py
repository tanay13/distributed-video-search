"""Apply db/migrations/*.sql in filename order, each one exactly once.

Run:  uv run python scripts/migrate.py           # apply pending migrations
      uv run python scripts/migrate.py --status  # list applied / pending

db/init/* only runs when the Postgres volume is brand new. Every later schema change is a new file here,
numbered by owner (Tanay 100-199, Aditya 200-299, Darshil 300-399). Applied filenames are recorded in
`schema_migrations`. Each file runs in its own transaction: it is either fully applied and recorded, or not at all.
Files must still be idempotent (IF NOT EXISTS), so a fresh database with no history is safe too.
"""
import sys
from pathlib import Path

from vsearch.common.db import connect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def main() -> None:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with connect() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
        applied = {r[0] for r in conn.execute("SELECT filename FROM schema_migrations")}
        pending = [f for f in files if f.name not in applied]
        conn.commit()   # end the read transaction, so each conn.transaction() below is a real BEGIN/COMMIT

        if "--status" in sys.argv:
            for f in files:
                print(f"  {'applied' if f.name in applied else 'PENDING'}  {f.name}")
            return

        for f in pending:
            with conn.transaction():
                conn.execute(f.read_text())
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (f.name,))
            print(f"applied {f.name}")
    print(f"{len(pending)} applied, {len(files) - len(pending)} already up to date")


if __name__ == "__main__":
    main()
