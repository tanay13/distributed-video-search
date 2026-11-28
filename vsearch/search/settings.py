"""Search settings (Darshil). Values come from env vars / .env."""
import os

from dotenv import load_dotenv

load_dotenv()

CANDIDATE_FRAMES = int(os.getenv("CANDIDATE_FRAMES", "50"))   # nearest frames to fetch before grouping
SCORE_MARGIN = float(os.getenv("SCORE_MARGIN", "0.05"))       # keep frames within this much of the best
MERGE_GAP_SEC = float(os.getenv("MERGE_GAP_SEC", "2.0"))      # hits this close (same video) = one moment
# A frame sampled at t stands for the video until the next sample: t .. t + 1/fps.
# Reads the same FIXED_FPS env var indexing uses, without importing indexing code.
FRAME_LEN_SEC = 1 / float(os.getenv("FIXED_FPS", "1"))
