import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL", "https://canvas.ualberta.ca").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")


def _load_or_create_secret() -> str:
    """App secret used to encrypt Canvas tokens at rest.

    Prefer APP_SECRET_KEY from the environment; otherwise generate one once and
    persist it next to the database so restarts don't invalidate stored tokens.
    """
    env_secret = os.getenv("APP_SECRET_KEY")
    if env_secret:
        return env_secret
    secret_file = Path(__file__).resolve().parent.parent / ".app_secret"
    if secret_file.exists():
        return secret_file.read_text().strip()
    import secrets

    secret = secrets.token_urlsafe(48)
    secret_file.write_text(secret)
    return secret


APP_SECRET_KEY = _load_or_create_secret()
