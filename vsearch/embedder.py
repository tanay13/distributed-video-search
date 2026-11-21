"""Step 4: CLIP wrapper. The ONLY place that knows which model we use.

Both indexing (images) and search (text) go through this file, so they are guaranteed to use
the same model. Vectors from two different models live in different spaces and can't be compared.
"""
import time

import numpy as np
import open_clip
import torch
from PIL import Image

MODEL_NAME = "ViT-B-32"              # 512-dim output, matches VECTOR(512) in the schema
PRETRAINED = "laion2b_s34b_b79k"     # which set of trained weights to download

DEVICE = ("mps" if torch.backends.mps.is_available()       # Apple GPU
          else "cuda" if torch.cuda.is_available()          # NVIDIA GPU (the T4 in the cloud)
          else "cpu")

_model = _preprocess = _tokenizer = None


def load() -> None:
    """Load the model once per process. Takes a few seconds; the first run also downloads ~600 MB."""
    global _model, _preprocess, _tokenizer
    if _model is not None:
        return
    t0 = time.time()
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    _model = model.to(DEVICE).eval()          # eval() = inference mode
    _preprocess = preprocess                  # resize -> center-crop 224x224 -> normalize colors
    _tokenizer = open_clip.get_tokenizer(MODEL_NAME)
    print(f"[embedder] loaded {MODEL_NAME}/{PRETRAINED} on {DEVICE} in {time.time() - t0:.1f}s", flush=True)


def _normalize(x: torch.Tensor) -> np.ndarray:
    """Scale each vector to length 1, so cosine similarity only compares direction (= meaning)."""
    x = x / x.norm(dim=-1, keepdim=True)
    return x.float().cpu().numpy()


@torch.no_grad()  # we're not training: skip the gradient bookkeeping (faster, less memory)
def embed_images(paths: list) -> np.ndarray:
    """N image files -> array of shape (N, 512)."""
    load()
    batch = torch.stack([_preprocess(Image.open(p).convert("RGB")) for p in paths]).to(DEVICE)
    return _normalize(_model.encode_image(batch))


@torch.no_grad()
def embed_text(text: str) -> np.ndarray:
    """One sentence -> array of shape (512,). Used by search in step 5."""
    load()
    tokens = _tokenizer([text]).to(DEVICE)
    return _normalize(_model.encode_text(tokens))[0]
