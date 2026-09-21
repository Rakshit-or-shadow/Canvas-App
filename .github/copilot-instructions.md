<!-- Workspace-specific instructions for Copilot -->
# Canvas Deadline Tracker (PWA)

Full-stack app: FastAPI backend + React (Vite, TypeScript) PWA frontend.
Purpose: show Canvas LMS (canvas.ualberta.ca) assignment/exam deadlines with
configurable push-notification reminders and ICS calendar export, usable on iPhone
via Add to Home Screen.

## Structure
- `backend/` — FastAPI app, Canvas API proxy, APScheduler reminder scheduler, pywebpush.
- `frontend/` — Vite + React + TS PWA (service worker, web push subscription).

## Conventions
- Backend run: `uvicorn app.main:app --reload --port 8000` from `backend/`.
- Frontend dev: `npm run dev` from `frontend/` (proxies `/api` to :8000).
- Canvas token is stored per-user in backend SQLite DB, never in frontend code.
- VAPID keys for web push live in `backend/.env` (not committed).

## Checklist
- [x] Create copilot-instructions.md
- [x] Scaffold the project
- [x] Compile & run
- [x] README complete
