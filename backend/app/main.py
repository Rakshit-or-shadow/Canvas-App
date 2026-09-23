from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select

from . import canvas, scheduler
from .auth import get_current_user
from .config import VAPID_PUBLIC_KEY
from .db import get_session, init_db
from .models import PushSubscription, SessionToken, User
from .push import send_to_user
from .security import (
    decrypt_token,
    encrypt_token,
    hash_session_token,
    new_session_token,
)

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


# ---------- Public config ----------

@app.get("/api/config")
def get_config():
    return {"vapid_public_key": VAPID_PUBLIC_KEY}


# ---------- Auth: connect Canvas token -> session ----------

@app.post("/api/auth/connect")
async def connect(body: TokenIn, session: Session = Depends(get_session)):
    """Verify a Canvas token, create/update the user, and issue a session token."""
    token = body.token.strip()
    try:
        profile = await canvas.verify_token(token)
    except canvas.CanvasError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    canvas_user_id = profile.get("id")
    if not canvas_user_id:
        raise HTTPException(status_code=401, detail="Could not read your Canvas profile.")

    user = session.exec(
        select(User).where(User.canvas_user_id == canvas_user_id)
    ).first()
    if not user:
        user = User(canvas_user_id=canvas_user_id)
    user.name = profile.get("name") or user.name
    user.email = profile.get("primary_email") or user.email
    user.canvas_token_encrypted = encrypt_token(token)
    session.add(user)
    session.commit()
    session.refresh(user)

    session_token = new_session_token()
    session.add(SessionToken(token_hash=hash_session_token(session_token), user_id=user.id))
    session.commit()
    return {
        "ok": True,
        "session_token": session_token,
        "profile": {"name": user.name, "email": user.email},
    }


@app.post("/api/auth/logout")
def logout(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    for st in session.exec(select(SessionToken).where(SessionToken.user_id == user.id)).all():
        session.delete(st)
    session.commit()
    return {"ok": True}


# ---------- Per-user settings ----------

@app.get("/api/settings")
def get_settings(user: User = Depends(get_current_user)):
    return {
        "has_token": bool(user.canvas_token_encrypted),
        "lead_minutes": [int(x) for x in user.reminder_lead_minutes.split(",") if x.strip().isdigit()],
        "vapid_public_key": VAPID_PUBLIC_KEY,
        "profile": {"name": user.name, "email": user.email},
    }


@app.post("/api/settings/leads")
def set_leads(
    body: LeadsIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if not body.lead_minutes:
        raise HTTPException(status_code=400, detail="Provide at least one lead time.")
    user.reminder_lead_minutes = ",".join(str(int(m)) for m in sorted(set(body.lead_minutes), reverse=True))
    session.add(user)
    session.commit()
    return {"ok": True, "lead_minutes": sorted(set(body.lead_minutes), reverse=True)}


# ---------- Deadlines ----------

@app.get("/api/deadlines")
async def get_deadlines(user: User = Depends(get_current_user)):
    token = decrypt_token(user.canvas_token_encrypted)
    if not token:
        raise HTTPException(status_code=428, detail="Set your Canvas token first.")
    try:
        return await canvas.fetch_deadlines(token)
    except canvas.CanvasError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


# ---------- ICS export ----------

@app.get("/api/calendar.ics")
async def calendar_ics(
    key: str = Query(""), session: Session = Depends(get_session)
):
    """ICS feed. Auth via ?key=<session token> since calendar apps can't set headers."""
    from ics import Calendar, Event

    st = session.exec(
        select(SessionToken).where(SessionToken.token_hash == hash_session_token(key))
    ).first() if key else None
    user = session.get(User, st.user_id) if st else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing calendar key.")
    token = decrypt_token(user.canvas_token_encrypted)
    if not token:
        raise HTTPException(status_code=428, detail="Set your Canvas token first.")
    deadlines = await canvas.fetch_deadlines(token)
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
def subscribe(
    body: SubscriptionIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing:
        # Re-bind the device to whoever is currently signed in on it.
        if existing.user_id != user.id:
            existing.user_id = user.id
            session.add(existing)
            session.commit()
        return {"ok": True, "already": True}
    session.add(
        PushSubscription(
            user_id=user.id,
            endpoint=body.endpoint,
            p256dh=body.keys.get("p256dh", ""),
            auth=body.keys.get("auth", ""),
        )
    )
    session.commit()
    return {"ok": True}


@app.post("/api/push/test")
def push_test(
    user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    sent = send_to_user(session, user.id, "🔔 Test notification", "Push notifications are working!")
    return {"sent": sent}


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------- Serve built frontend (single-server deployment) ----------

_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
