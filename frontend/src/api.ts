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
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  getSettings: () => request<AppSettings>("/api/settings"),
  setToken: (token: string) =>
    request<{ ok: boolean; profile: { name: string } }>("/api/settings/token", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
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
