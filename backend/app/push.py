"""Web push helpers using pywebpush + VAPID."""

from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush
from sqlmodel import Session, select

from .config import VAPID_CLAIM_EMAIL, VAPID_PRIVATE_KEY
from .models import PushSubscription

log = logging.getLogger(__name__)


def send_to_all(session: Session, title: str, body: str, url: str | None = None) -> int:
    """Send a push notification to every stored subscription. Returns count sent."""
    subs = session.exec(select(PushSubscription)).all()
    payload = json.dumps({"title": title, "body": body, "url": url or "/"})
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                log.info("Removing expired push subscription %s", sub.endpoint[:60])
                session.delete(sub)
                session.commit()
            else:
                log.warning("Push failed: %s", exc)
    return sent
