"""Indexing (Aditya): frames, CLIP, Whisper, scenes. Called by the pipeline worker through the contracts."""
from vsearch.indexing import settings
from vsearch.models import CLIP_MODEL, CLIP_PRETRAINED


def config_version() -> str:
    """Contract: a string naming every setting that changes what indexing produces. Stored with each
    video at ingest, so results from different settings can be told apart (Experiment B)."""
    return f"clip={CLIP_MODEL}/{CLIP_PRETRAINED};fps={settings.FIXED_FPS:g}"
