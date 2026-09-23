export interface Deadline {
  id: number;
  course_id: number;
  course: string;
  title: string;
  due_at: string;
  html_url?: string;
  points?: number;
  type: "assignment" | "exam";
  submitted: boolean;
  graded: boolean;
}

export interface AppSettings {
  has_token: boolean;
  lead_minutes: number[];
  vapid_public_key: string;
  profile?: { name: string; email: string };
}

const SESSION_KEY = "session_token";

export function getSessionToken(): string | null {
  return localStorage.getItem(SESSION_KEY);
}

export function setSessionToken(token: string | null) {
  if (token) localStorage.setItem(SESSION_KEY, token);
  else localStorage.removeItem(SESSION_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const session = getSessionToken();
  if (session) headers["Authorization"] = `Bearer ${session}`;
  const res = await fetch(path, { headers, ...init });
  if (res.status === 401 && session && !path.startsWith("/api/auth/")) {
    // Session invalid — force re-login.
    setSessionToken(null);
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  getConfig: () => request<{ vapid_public_key: string }>("/api/config"),
  connect: (token: string) =>
    request<{ ok: boolean; session_token: string; profile: { name: string } }>(
      "/api/auth/connect",
      { method: "POST", body: JSON.stringify({ token }) }
    ),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  getSettings: () => request<AppSettings>("/api/settings"),
  setLeads: (lead_minutes: number[]) =>
    request<{ ok: boolean }>("/api/settings/leads", {
      method: "POST",
      body: JSON.stringify({ lead_minutes }),
    }),
  getDeadlines: () => request<Deadline[]>("/api/deadlines"),
  subscribePush: (sub: PushSubscriptionJSON) =>
    request<{ ok: boolean }>("/api/push/subscribe", {
      method: "POST",
      body: JSON.stringify(sub),
    }),
  testPush: () => request<{ sent: number }>("/api/push/test", { method: "POST" }),
};
