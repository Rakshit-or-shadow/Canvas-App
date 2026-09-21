import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "https://canvas.ualberta.ca").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")
