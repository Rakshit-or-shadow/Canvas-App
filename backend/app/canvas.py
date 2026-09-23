"""Canvas LMS API client: fetch courses and upcoming assignment/exam deadlines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from .config import CANVAS_BASE_URL

API = f"{CANVAS_BASE_URL}/api/v1"


class CanvasError(Exception):
    pass


async def _get_paginated(client: httpx.AsyncClient, url: str, params: dict | None = None) -> list[Any]:
    items: list[Any] = []
    next_url: str | None = url
    next_params = params or {}
    while next_url:
        resp = await client.get(next_url, params=next_params)
        if resp.status_code == 401:
            raise CanvasError("Canvas token is invalid or expired (401).")
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            items.extend(data)
        else:
            items.append(data)
        next_url = resp.links.get("next", {}).get("url")
        next_params = {}  # params are baked into the next link
    return items


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def fetch_deadlines(token: str) -> list[dict]:
    """Return upcoming (and recent) assignments/quizzes across all active courses."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        courses = await _get_paginated(
            client,
            f"{API}/courses",
            {"enrollment_state": "active", "per_page": 100},
        )

        deadlines: list[dict] = []
        for course in courses:
            course_id = course.get("id")
            course_name = course.get("course_code") or course.get("name") or f"Course {course_id}"
            if not course_id:
                continue
            try:
                assignments = await _get_paginated(
                    client,
                    f"{API}/courses/{course_id}/assignments",
                    {
                        "per_page": 100,
                        "order_by": "due_at",
                        "include[]": "submission",
                    },
                )
            except (CanvasError, httpx.HTTPStatusError):
                continue  # skip courses we can't read

            for a in assignments:
                due = _parse_dt(a.get("due_at"))
                if due is None:
                    continue
                submission = a.get("submission") or {}
                is_quiz = "online_quiz" in (a.get("submission_types") or [])
                deadlines.append(
                    {
                        "id": a["id"],
                        "course_id": course_id,
                        "course": course_name,
                        "title": a.get("name", "Untitled"),
                        "due_at": due.astimezone(timezone.utc).isoformat(),
                        "html_url": a.get("html_url"),
                        "points": a.get("points_possible"),
                        "type": "exam" if is_quiz or "exam" in a.get("name", "").lower() else "assignment",
                        "submitted": bool(submission.get("submitted_at")),
                        "graded": submission.get("workflow_state") == "graded",
                    }
                )

        deadlines.sort(key=lambda d: d["due_at"])
        return deadlines


async def verify_token(token: str) -> dict:
    """Check a token by fetching the user's own profile."""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        resp = await client.get(f"{API}/users/self/profile")
        if resp.status_code == 401:
            raise CanvasError("Token rejected by Canvas (401).")
        resp.raise_for_status()
        profile = resp.json()
        return {
            "id": profile.get("id"),
            "name": profile.get("name"),
            "primary_email": profile.get("primary_email"),
        }
