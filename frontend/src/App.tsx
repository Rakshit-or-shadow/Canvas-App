import { useCallback, useEffect, useMemo, useState } from "react";
import { api, AppSettings, Deadline, getSessionToken, setSessionToken } from "./api";
import { enablePushNotifications } from "./push";

const LEAD_PRESETS = [
  { label: "1 week", minutes: 10080 },
  { label: "3 days", minutes: 4320 },
  { label: "2 days", minutes: 2880 },
  { label: "1 day", minutes: 1440 },
  { label: "6 hours", minutes: 360 },
  { label: "1 hour", minutes: 60 },
  { label: "30 min", minutes: 30 },
];

function timeLeft(dueISO: string): { text: string; urgent: boolean; past: boolean } {
  const diff = new Date(dueISO).getTime() - Date.now();
  if (diff < 0) return { text: "past due", urgent: false, past: true };
  const mins = Math.floor(diff / 60000);
  const days = Math.floor(mins / 1440);
  const hours = Math.floor((mins % 1440) / 60);
  if (days > 0) return { text: `${days}d ${hours}h left`, urgent: days < 2, past: false };
  if (hours > 0) return { text: `${hours}h ${mins % 60}m left`, urgent: true, past: false };
  return { text: `${mins}m left`, urgent: true, past: false };
}

function fmtDue(dueISO: string): string {
  return new Date(dueISO).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function App() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [deadlines, setDeadlines] = useState<Deadline[] | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPast, setShowPast] = useState(false);

  const refreshDeadlines = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDeadlines(await api.getDeadlines());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!getSessionToken()) {
      // Not signed in — just fetch the public config so push can work later.
      api.getConfig().then((c) =>
        setSettings({ has_token: false, lead_minutes: [1440, 60], vapid_public_key: c.vapid_public_key })
      );
      return;
    }
    api
      .getSettings()
      .then((s) => {
        setSettings(s);
        if (s.has_token) refreshDeadlines();
      })
      .catch(async () => {
        // Session expired — fall back to logged-out state.
        setSessionToken(null);
        const c = await api.getConfig();
        setSettings({ has_token: false, lead_minutes: [1440, 60], vapid_public_key: c.vapid_public_key });
      });
  }, [refreshDeadlines]);

  const saveToken = async () => {
    setError("");
    setStatus("Verifying token with Canvas…");
    try {
      const res = await api.connect(tokenInput);
      setSessionToken(res.session_token);
      setTokenInput("");
      const s = await api.getSettings();
      setSettings(s);
      setStatus(`Connected as ${res.profile.name} ✅`);
      refreshDeadlines();
    } catch (e) {
      setStatus("");
      setError((e as Error).message);
    }
  };

  const signOut = async () => {
    try {
      await api.logout();
    } catch {
      /* session may already be dead */
    }
    setSessionToken(null);
    setDeadlines(null);
    setShowSettings(false);
    const c = await api.getConfig();
    setSettings({ has_token: false, lead_minutes: [1440, 60], vapid_public_key: c.vapid_public_key });
    setStatus("Signed out.");
  };

  const toggleLead = async (minutes: number) => {
    if (!settings) return;
    const cur = new Set(settings.lead_minutes);
    cur.has(minutes) ? cur.delete(minutes) : cur.add(minutes);
    if (cur.size === 0) return;
    const next = [...cur].sort((a, b) => b - a);
    setSettings({ ...settings, lead_minutes: next });
    try {
      await api.setLeads(next);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const enablePush = async () => {
    if (!settings) return;
    setError("");
    try {
      setStatus(await enablePushNotifications(settings.vapid_public_key));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const sendTest = async () => {
    try {
      const r = await api.testPush();
      setStatus(r.sent > 0 ? `Test sent to ${r.sent} device(s) 🔔` : "No subscribed devices yet — tap Enable Notifications first.");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const { upcoming, past } = useMemo(() => {
    const now = Date.now();
    const list = deadlines ?? [];
    return {
      upcoming: list.filter((d) => new Date(d.due_at).getTime() >= now),
      past: list.filter((d) => new Date(d.due_at).getTime() < now).reverse(),
    };
  }, [deadlines]);

  const needsToken = settings && !settings.has_token;

  return (
    <div className="app">
      <header>
        <h1>📚 Deadlines</h1>
        <div className="header-actions">
          <button className="icon-btn" onClick={refreshDeadlines} disabled={loading} title="Refresh">
            {loading ? "⏳" : "🔄"}
          </button>
          <button className="icon-btn" onClick={() => setShowSettings((v) => !v)} title="Settings">
            ⚙️
          </button>
        </div>
      </header>

      {status && <div className="banner ok" onClick={() => setStatus("")}>{status}</div>}
      {error && <div className="banner err" onClick={() => setError("")}>{error}</div>}

      {(needsToken || showSettings) && settings && (
        <section className="card settings">
          <h2>{needsToken ? "Connect to Canvas" : "Settings"}</h2>
          {needsToken && (
            <p className="hint">
              In Canvas go to <b>Account → Settings → + New Access Token</b>, copy the token and paste it
              here. Your token is encrypted and only used to fetch your own deadlines.
            </p>
          )}
          {!needsToken && settings.profile?.name && (
            <p className="hint">Signed in as <b>{settings.profile.name}</b></p>
          )}
          <div className="token-row">
            <input
              type="password"
              placeholder={settings.has_token ? "Replace Canvas token…" : "Paste Canvas access token"}
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
            />
            <button onClick={saveToken} disabled={!tokenInput.trim()}>
              Save
            </button>
          </div>

          <h3>Remind me before each deadline:</h3>
          <div className="leads">
            {LEAD_PRESETS.map((p) => (
              <button
                key={p.minutes}
                className={`chip ${settings.lead_minutes.includes(p.minutes) ? "on" : ""}`}
                onClick={() => toggleLead(p.minutes)}
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="push-row">
            <button className="primary" onClick={enablePush}>🔔 Enable Notifications</button>
            <button onClick={sendTest}>Send test</button>
          </div>

          <a
            className="ics-link"
            href={`/api/calendar.ics?key=${encodeURIComponent(getSessionToken() ?? "")}`}
          >
            📅 Export to Apple Calendar (.ics)
          </a>

          {!needsToken && (
            <button className="signout" onClick={signOut}>
              Sign out
            </button>
          )}
        </section>
      )}

      {deadlines && (
        <main>
          {upcoming.length === 0 && !loading && <p className="empty">No upcoming deadlines 🎉</p>}
          <ul className="list">
            {upcoming.map((d) => {
              const t = timeLeft(d.due_at);
              return (
                <li key={d.id} className={`card item ${t.urgent ? "urgent" : ""} ${d.submitted ? "done" : ""}`}>
                  <div className="item-top">
                    <span className={`badge ${d.type}`}>{d.type === "exam" ? "📝 Exam/Quiz" : "📄 Assignment"}</span>
                    <span className={`countdown ${t.urgent ? "urgent" : ""}`}>{t.text}</span>
                  </div>
                  <a className="title" href={d.html_url} target="_blank" rel="noreferrer">
                    {d.title}
                  </a>
                  <div className="meta">
                    <span className="course">{d.course}</span>
                    <span className="due">{fmtDue(d.due_at)}</span>
                    {d.submitted && <span className="submitted">✅ submitted</span>}
                  </div>
                </li>
              );
            })}
          </ul>

          {past.length > 0 && (
            <>
              <button className="past-toggle" onClick={() => setShowPast((v) => !v)}>
                {showPast ? "Hide" : "Show"} past deadlines ({past.length})
              </button>
              {showPast && (
                <ul className="list past">
                  {past.map((d) => (
                    <li key={d.id} className="card item done">
                      <a className="title" href={d.html_url} target="_blank" rel="noreferrer">
                        {d.title}
                      </a>
                      <div className="meta">
                        <span className="course">{d.course}</span>
                        <span className="due">{fmtDue(d.due_at)}</span>
                        {d.submitted && <span className="submitted">✅</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </main>
      )}
    </div>
  );
}
