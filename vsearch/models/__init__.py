"""Which CLIP model we use. Kept here (not in embedder.py) so code can read the model id without importing
torch, e.g. indexing.config_version() called from ingest / the API.

Changing the model = [contract] PR + re-index: vectors from two models can't be compared.
"""
CLIP_MODEL = "ViT-B-32"              # 512-dim output, matches VECTOR(512) in the schema
CLIP_PRETRAINED = "laion2b_s34b_b79k"
EMBED_DIM = 512
