"""APScheduler job: every 5 minutes, check deadlines and fire due reminders."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select

from . import canvas
from .db import engine
from .models import SentReminder, Settings
from .push import send_to_all

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

CHECK_INTERVAL_MINUTES = 5


def _lead_list(settings: Settings) -> list[int]:
    out = []
    for part in settings.reminder_lead_minutes.split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out or [1440, 60]


def _humanize(minutes: int) -> str:
    if minutes % 1440 == 0:
        d = minutes // 1440
        return f"{d} day{'s' if d != 1 else ''}"
    if minutes % 60 == 0:
        h = minutes // 60
        return f"{h} hour{'s' if h != 1 else ''}"
    return f"{minutes} min"


async def check_and_send_reminders() -> None:
    with Session(engine) as session:
        settings = session.get(Settings, 1)
        if not settings or not settings.canvas_token:
            return
        try:
            deadlines = await canvas.fetch_deadlines(settings.canvas_token)
        except Exception as exc:  # noqa: BLE001 - keep scheduler alive
            log.warning("Reminder check: Canvas fetch failed: %s", exc)
            return

        now = datetime.now(timezone.utc)
        leads = _lead_list(settings)
        for d in deadlines:
            if d["submitted"]:
                continue
            due = datetime.fromisoformat(d["due_at"])
            if due < now:
                continue
            for lead in leads:
                fire_at = due - timedelta(minutes=lead)
                # Fire once we've passed fire_at (with a 1h grace window in case
                # the server was down), but never after the deadline itself.
                if not (fire_at <= now < due and now - fire_at < timedelta(hours=1)):
                    continue
                key = f"{d['id']}:{lead}"
                if session.exec(select(SentReminder).where(SentReminder.assignment_key == key)).first():
                    continue
                title = f"⏰ Due in {_humanize(lead)}: {d['title']}"
                body = f"{d['course']} — due {due.strftime('%a %b %d, %I:%M %p UTC')}"
                sent = send_to_all(session, title, body, d.get("html_url"))
                session.add(SentReminder(assignment_key=key))
                session.commit()
                log.info("Sent reminder %s to %d subscriber(s)", key, sent)


def start() -> None:
    scheduler.add_job(check_and_send_reminders, "interval", minutes=CHECK_INTERVAL_MINUTES, id="reminders")
    scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
