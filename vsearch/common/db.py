"""PostgreSQL connection helper."""
import psycopg
from pgvector.psycopg import register_vector

from vsearch.common.config import settings


def connect() -> psycopg.Connection:
    """Open a connection that understands the pgvector VECTOR type (numpy arrays in/out)."""
    conn = psycopg.connect(settings.pg_dsn)
    register_vector(conn)
    return conn
