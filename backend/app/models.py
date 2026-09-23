from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """One row per person. Identified by their Canvas user id."""

    id: Optional[int] = Field(default=None, primary_key=True)
    canvas_user_id: int = Field(index=True, unique=True)
    name: str = ""
    email: str = ""
    # Canvas token encrypted at rest (Fernet).
    canvas_token_encrypted: str = ""
    # Comma-separated lead times in minutes, e.g. "2880,1440,60"
    reminder_lead_minutes: str = "1440,60"
    created_at: datetime = Field(default_factory=utcnow)


class SessionToken(SQLModel, table=True):
    """Opaque bearer session issued to the frontend after connecting Canvas."""

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utcnow)
    last_used_at: datetime = Field(default_factory=utcnow)


class PushSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    endpoint: str = Field(index=True, unique=True)
    p256dh: str
    auth: str
    created_at: datetime = Field(default_factory=utcnow)


class SentReminder(SQLModel, table=True):
    """Dedup log so we never send the same reminder twice (per user)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, default=0)
    assignment_key: str = Field(index=True)  # f"{assignment_id}:{lead_minutes}"
    sent_at: datetime = Field(default_factory=utcnow)
