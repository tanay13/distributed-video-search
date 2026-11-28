"""Shared settings: database + object storage only. Values come from .env (the same file docker compose uses)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # PostgreSQL (docker compose publishes it on localhost:POSTGRES_PORT)
    pg_host: str = os.getenv("POSTGRES_HOST", "localhost")
    pg_port: int = int(os.getenv("POSTGRES_PORT", "5433"))
    pg_user: str = os.environ["POSTGRES_USER"]
    pg_password: str = os.environ["POSTGRES_PASSWORD"]
    pg_db: str = os.environ["POSTGRES_DB"]

    # MinIO / S3. Locally we reuse the MinIO root credentials (dev only).
    s3_endpoint: str = os.getenv("S3_ENDPOINT_URL", f"http://localhost:{os.getenv('MINIO_API_PORT', '9000')}")
    s3_access_key: str = os.getenv("S3_ACCESS_KEY", os.environ["MINIO_ROOT_USER"])
    s3_secret_key: str = os.getenv("S3_SECRET_KEY", os.environ["MINIO_ROOT_PASSWORD"])
    s3_bucket: str = os.getenv("MINIO_BUCKET", "videos")

    # Area-specific settings do NOT go here: see vsearch/{pipeline,indexing,search}/settings.py

    @property
    def pg_dsn(self) -> str:
        return (f"host={self.pg_host} port={self.pg_port} user={self.pg_user} "
                f"password={self.pg_password} dbname={self.pg_db}")


settings = Settings()
