"""MinIO (S3-compatible) helpers. The same code works against real S3/GCS later."""
import boto3
from botocore.config import Config

from vsearch.config import settings

_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name="us-east-1",
    config=Config(s3={"addressing_style": "path"}),  # MinIO needs path-style URLs
)


def upload_file(local_path: str, key: str) -> None:
    _client.upload_file(local_path, settings.s3_bucket, key)


def download_file(key: str, local_path: str) -> None:
    _client.download_file(settings.s3_bucket, key, local_path)


def presigned_url(key: str, expires_sec: int = 3600) -> str:
    """A temporary HTTP URL for the object. ffmpeg can read it directly and seek within it,
    so a worker only fetches the bytes for its own segment instead of the whole video."""
    return _client.generate_presigned_url(
        "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires_sec)


def bucket_exists() -> bool:
    _client.head_bucket(Bucket=settings.s3_bucket)
    return True
