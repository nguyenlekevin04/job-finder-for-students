"use client";

// Job alerts by browser push: free, no email and no account. The browser gives us a
// subscription (a secret push URL plus keys); we store it with the search it is for via the
// subscribe_push database function, and the daily update sends at most one notification a day.
// One alert per device: a new one replaces the old.
import type { Filters } from "./filters";

export const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY?.trim() || "";
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/+$/, "") || "";
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
const KEY = "dsj:push:v1"; // which search this device gets alerts for (its label), for the UI only

export type PushState = "unsupported" | "off" | "on" | "blocked";

/** Push needs a service worker, the Push API, our key and the database (production only). */
export function pushAvailable(): boolean {
  if (!VAPID_PUBLIC_KEY || !SUPABASE_URL || !SUPABASE_KEY || typeof window === "undefined") return false;
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

/** On iPhone, push only works once the site was added to the home screen. */
export function needsInstall(): boolean {
  if (typeof window === "undefined") return false;
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent);
  const standalone = window.matchMedia?.("(display-mode: standalone)").matches;
  return ios && !standalone;
}

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const b64 = (base64url + "=".repeat((4 - (base64url.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

async function rpc(name: string, body: Record<string, unknown>): Promise<void> {
  const headers: Record<string, string> = { apikey: SUPABASE_KEY, "Content-Type": "application/json" };
  if (SUPABASE_KEY.startsWith("eyJ")) headers.Authorization = `Bearer ${SUPABASE_KEY}`;
  const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${name}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`Alerts are unavailable right now (${res.status}).`);
}

export function savedAlert(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function remember(label: string | null) {
  try {
    if (label) window.localStorage.setItem(KEY, label);
    else window.localStorage.removeItem(KEY);
  } catch {
    // Blocked storage: the alert still works, only the label isn't shown next time.
  }
}

export async function currentState(): Promise<PushState> {
  if (!pushAvailable()) return "unsupported";
  if (Notification.permission === "denied") return "blocked";
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  return sub && savedAlert() ? "on" : "off";
}

/** Ask for permission, subscribe this device and store it for these filters. */
export async function enableAlerts(f: Filters, label: string): Promise<PushState> {
  if (!pushAvailable()) return "unsupported";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return permission === "denied" ? "blocked" : "off";
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  const sub =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(VAPID_PUBLIC_KEY) }));
  const json = sub.toJSON();
  await rpc("subscribe_push", {
    p_endpoint: sub.endpoint,
    p_p256dh: json.keys?.p256dh ?? "",
    p_auth: json.keys?.auth ?? "",
    p_board: f.city,
    p_types: f.types,
    p_fields: f.fields,
  });
  remember(label);
  return "on";
}

export async function disableAlerts(): Promise<PushState> {
  const reg = await navigator.serviceWorker.getRegistration();
  const sub = await reg?.pushManager.getSubscription();
  if (sub) {
    await rpc("unsubscribe_push", { p_endpoint: sub.endpoint }).catch(() => undefined);
    await sub.unsubscribe();
  }
  remember(null);
  return "off";
}
