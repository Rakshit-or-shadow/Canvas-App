# 📚 Canvas Deadline Tracker

A PWA that shows all your **assignment & exam deadlines** from Canvas
(canvas.ualberta.ca) with **push-notification reminders** you can configure
(1 week / 1 day / 1 hour before, etc.) and **Apple Calendar export**.
Installable on iPhone via *Add to Home Screen*.

## Features

- ⏰ All upcoming deadlines across every active course, sorted by due date
- 🔔 Web-push reminders at lead times you choose (works on iOS 16.4+ when added to Home Screen)
- ✅ Shows submitted/graded status; urgent items highlighted
- 📅 One-tap `.ics` export → Apple Calendar (calendar alerts can ring like alarms)
- 🔐 Your Canvas token stays in the backend SQLite DB, never in the browser

## Project layout

| Path | What |
|---|---|
| `backend/` | FastAPI: Canvas API proxy, APScheduler reminder loop (every 5 min), pywebpush |
| `frontend/` | Vite + React + TypeScript PWA (service worker, push subscription) |
| `Dockerfile` | Single-container build (backend serves the built frontend) |

## Run locally (Windows)

**Backend** — from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

**Frontend (dev)** — from `frontend/`:

```powershell
npm run dev    # http://localhost:5173, proxies /api to :8000
```

First-time setup already done by the scaffold:
- `backend/.venv` created, `pip install -r requirements.txt`
- `backend/.env` created with generated VAPID keys (edit `VAPID_CLAIM_EMAIL`)
- `npm install` in `frontend/`

## Connect Canvas

1. Open the app → **Connect to Canvas** card.
2. In Canvas: **Account → Settings → + New Access Token** → copy token.
3. Paste and **Save** — the app verifies it against `canvas.ualberta.ca`.

## Reminders / notifications

- Pick lead times (chips) in ⚙️ Settings — e.g. *2 days*, *1 day*, *1 hour*.
- Tap **🔔 Enable Notifications** (on iPhone: must be opened from the Home-Screen icon).
- The backend checks every 5 minutes and pushes a notification when a
  deadline enters one of your lead windows. Submitted assignments are skipped.
- **Send test** verifies push end-to-end.

> True "alarm" behavior isn't possible from a web app on iOS. For ringing
> alerts, use **Export to Apple Calendar** — calendar events support loud,
> repeating alerts.

## Deploy (so it works on your iPhone anywhere)

Push notifications require **HTTPS**, so deploy to any host with free TLS.
The included `Dockerfile` works on [Render](https://render.com),
[Railway](https://railway.app), or [Fly.io](https://fly.io):

1. Push this repo to GitHub.
2. On Render: **New → Web Service → connect repo**, Environment = *Docker*.
3. Set env vars from `backend/.env.example`:
   `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIM_EMAIL`,
   `CANVAS_BASE_URL=https://canvas.ualberta.ca`.
   - Generate fresh keys for production: `python -m app.gen_vapid`
4. Add a persistent disk (Render: 1 GB) mounted at `/app/backend` **or** set
   `DATABASE_URL` to a mounted path so the SQLite DB survives restarts.
5. Open the deployed URL on your iPhone in Safari →
   **Share → Add to Home Screen** → open from the icon →
   paste your Canvas token → **Enable Notifications**.

> ⚠️ Free tiers sleep on idle; a sleeping server can't send reminders.
> Use a paid instance, a keep-alive ping (e.g. UptimeRobot on `/api/health`),
> or a host without sleep (Fly.io machines with `min_machines_running=1`).

## Security notes

- Single-user app: anyone with the URL can see your deadlines. For public
  hosting, add basic auth or keep the URL private.
- Tighten `allow_origins` in `backend/app/main.py` to your deployed domain.
- Never commit `backend/.env` or `data.db` (already in `.gitignore`).
