import { api } from "./api";

function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export async function enablePushNotifications(vapidPublicKey: string): Promise<string> {
  if (!("serviceWorker" in navigator)) throw new Error("Service workers not supported here.");
  if (!("PushManager" in window))
    throw new Error(
      "Push not supported. On iPhone: add this app to your Home Screen first (Share → Add to Home Screen), then open it from there."
    );

  if (Notification.permission === "denied")
    throw new Error(
      "Notifications are blocked for this site. Click the lock/tune icon next to the address bar → Site settings → allow Notifications, then try again."
    );
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Notification permission was denied.");

  const regs = await navigator.serviceWorker.getRegistrations();
  if (regs.length === 0)
    throw new Error("Service worker not registered yet — reload the page and try again.");
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    try {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });
    } catch (e) {
      const msg = (e as Error).message || "";
      if (/push service|abort/i.test(msg)) {
        throw new Error(
          "Your browser couldn't reach its push service. If you use Brave: enable 'Use Google services for push messaging' in brave://settings/privacy. Otherwise check VPN/firewall/ad-blocker, or try Firefox."
        );
      }
      throw e;
    }
  }
  await api.subscribePush(sub.toJSON());
  return "Notifications enabled!";
}
