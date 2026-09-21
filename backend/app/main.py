from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session

from . import canvas, scheduler
from .config import VAPID_PUBLIC_KEY
from .db import get_session, init_db
from .models import PushSubscription, Settings
from .push import send_to_all

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="Canvas Deadline Tracker", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your deployed frontend origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Schemas ----------

class TokenIn(BaseModel):
    token: str


class LeadsIn(BaseModel):
    lead_minutes: list[int]


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: dict  # {p256dh, auth}


# ---------- Settings / token ----------

@app.get("/api/settings")
def get_settings(session: Session = Depends(get_session)):
    s = session.get(Settings, 1)
    return {
        "has_token": bool(s and s.canvas_token),
        "lead_minutes": [int(x) for x in (s.reminder_lead_minutes if s else "1440,60").split(",") if x.strip().isdigit()],
        "vapid_public_key": VAPID_PUBLIC_KEY,
    }


@app.post("/api/settings/token")
async def set_token(body: TokenIn, session: Session = Depends(get_session)):
    try:
        profile = await canvas.verify_token(body.token.strip())
    except canvas.CanvasError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    s = session.get(Settings, 1)
    s.canvas_token = body.token.strip()
    session.add(s)
    session.commit()
    return {"ok": True, "profile": profile}


@app.post("/api/settings/leads")
def set_leads(body: LeadsIn, session: Session = Depends(get_session)):
    if not body.lead_minutes:
        raise HTTPException(status_code=400, detail="Provide at least one lead time.")
    s = session.get(Settings, 1)
    s.reminder_lead_minutes = ",".join(str(int(m)) for m in sorted(set(body.lead_minutes), reverse=True))
    session.add(s)
    session.commit()
    return {"ok": True, "lead_minutes": sorted(set(body.lead_minutes), reverse=True)}


# ---------- Deadlines ----------

@app.get("/api/deadlines")
async def get_deadlines(session: Session = Depends(get_session)):
    s = session.get(Settings, 1)
    if not s or not s.canvas_token:
        raise HTTPException(status_code=428, detail="Set your Canvas token first.")
    try:
        return await canvas.fetch_deadlines(s.canvas_token)
    except canvas.CanvasError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


# ---------- ICS export ----------

@app.get("/api/calendar.ics")
async def calendar_ics(session: Session = Depends(get_session)):
    from ics import Calendar, Event

    s = session.get(Settings, 1)
    if not s or not s.canvas_token:
        raise HTTPException(status_code=428, detail="Set your Canvas token first.")
    deadlines = await canvas.fetch_deadlines(s.canvas_token)
    cal = Calendar()
    for d in deadlines:
        ev = Event(
            name=f"[{d['course']}] {d['title']}",
            begin=datetime.fromisoformat(d["due_at"]),
            url=d.get("html_url"),
        )
        cal.events.add(ev)
    return Response(
        content=cal.serialize(),
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=deadlines.ics"},
    )


# ---------- Push subscriptions ----------

@app.post("/api/push/subscribe")
def subscribe(body: SubscriptionIn, session: Session = Depends(get_session)):
    from sqlmodel import select

    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing:
        return {"ok": True, "already": True}
    session.add(
        PushSubscription(
            endpoint=body.endpoint,
            p256dh=body.keys.get("p256dh", ""),
            auth=body.keys.get("auth", ""),
        )
    )
    session.commit()
    return {"ok": True}


@app.post("/api/push/test")
def push_test(session: Session = Depends(get_session)):
    sent = send_to_all(session, "🔔 Test notification", "Push notifications are working!")
    return {"sent": sent}


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------- Serve built frontend (single-server deployment) ----------

_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
