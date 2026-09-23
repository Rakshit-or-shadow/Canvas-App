"""Session-based auth: resolve the current user from a Bearer session token."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from .db import get_session
from .models import SessionToken, User, utcnow
from .security import hash_session_token


def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in.")
    st = session.exec(
        select(SessionToken).where(SessionToken.token_hash == hash_session_token(token))
    ).first()
    if not st:
        raise HTTPException(status_code=401, detail="Session expired — reconnect your Canvas token.")
    user = session.get(User, st.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    st.last_used_at = utcnow()
    session.add(st)
    session.commit()
    return user
