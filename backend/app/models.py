from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Settings(SQLModel, table=True):
    """Single-user settings row (id is always 1)."""

    id: int = Field(default=1, primary_key=True)
    canvas_token: str = ""
    # Comma-separated lead times in minutes, e.g. "2880,1440,60"
    reminder_lead_minutes: str = "1440,60"


class PushSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint: str = Field(index=True, unique=True)
    p256dh: str
    auth: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SentReminder(SQLModel, table=True):
    """Dedup log so we never send the same reminder twice."""

    id: Optional[int] = Field(default=None, primary_key=True)
    assignment_key: str = Field(index=True)  # f"{assignment_id}:{lead_minutes}"
    sent_at: datetime = Field(default_factory=datetime.utcnow)
