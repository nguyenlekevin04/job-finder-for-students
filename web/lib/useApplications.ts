"use client";

import { useCallback, useSyncExternalStore } from "react";

// Application status per saved job ("applied on 31 Oct"), kept in this browser only.
// Same pattern as useBookmarks: an external store over localStorage, every access in try/catch.
const KEY = "dsj:applications:v1";
const EVENT = "dsj:applications";

export const STATUSES = ["applied", "interview", "offer", "rejected"] as const;
export type AppStatus = (typeof STATUSES)[number];
export const STATUS_LABELS: Record<AppStatus, string> = {
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

export interface Application {
  status: AppStatus;
  date: string; // "YYYY-MM-DD", the day the status was set
}
type Store = Record<string, Application>;

const EMPTY: Store = {};
let snapshot: Store | null = null;
let persistent = true; // false once a write failed (private mode, blocked storage)

function valid(v: unknown): v is Application {
  const a = v as Application;
  return !!a && STATUSES.includes(a.status) && typeof a.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(a.date);
}

function read(): Store {
  if (snapshot) return snapshot;
  try {
    const raw = JSON.parse(window.localStorage.getItem(KEY) ?? "{}") as Record<string, unknown>;
    snapshot = Object.fromEntries(Object.entries(raw).filter(([, v]) => valid(v))) as Store;
  } catch {
    snapshot = EMPTY;
  }
  return snapshot;
}

function write(next: Store) {
  snapshot = next;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
    persistent = true;
  } catch {
    persistent = false; // keep the in-memory copy for this visit
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === KEY) {
      snapshot = null; // changed in another tab
      onChange();
    }
  };
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

function today(): string {
  const d = new Date();
  return [d.getFullYear(), d.getMonth() + 1, d.getDate()].map((n) => String(n).padStart(2, "0")).join("-");
}

export function useApplications() {
  const store = useSyncExternalStore(subscribe, read, () => EMPTY);

  /** Set a status (dated today) or clear it with null. */
  const setStatus = useCallback((id: string, status: AppStatus | null) => {
    const next = { ...read() };
    if (status) next[id] = { status, date: today() };
    else delete next[id];
    write(next);
  }, []);

  return { applications: store, setStatus, persistent };
}
