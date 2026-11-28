"""Indexing settings (Aditya). Values come from env vars / .env."""
import os

from dotenv import load_dotenv

load_dotenv()

FIXED_FPS = float(os.getenv("FIXED_FPS", "1"))            # frames sampled per second
KEEP_FRAMES = os.getenv("KEEP_FRAMES", "0") == "1"        # debug: copy frames to ./debug_frames/
