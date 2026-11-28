"""Pipeline settings (Tanay). Values come from env vars / .env."""
import os

from dotenv import load_dotenv

load_dotenv()

SEGMENT_SEC = float(os.getenv("SEGMENT_SEC", "30"))                    # length of each segment
SEGMENT_OVERLAP_SEC = float(os.getenv("SEGMENT_OVERLAP_SEC", "2"))     # overlap between neighbours
# Coming with T1 (crash recovery): LEASE_SEC, MAX_ATTEMPTS. With T2: QUEUE_BACKEND=postgres|rabbitmq.
