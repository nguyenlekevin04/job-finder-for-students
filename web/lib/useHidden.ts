"use client";

import { useCallback, useSyncExternalStore } from "react";

// Jobs a student ruled out ("Not for me"), in this browser only: job id -> day hidden.
// Same external-store pattern as useBookmarks; every storage access is in try/catch.
const KEY = "dsj:hidden:v1";
const EVENT = "dsj:hidden";
export const MAX_HIDDEN = 500; // oldest are dropped first; jobs rarely live that long

type Store = Record<string, string>;

const EMPTY: Store = {};
let snapshot: Store | null = null;

function read(): Store {
  if (snapshot) return snapshot;
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    snapshot = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Store) : EMPTY;
  } catch {
    snapshot = EMPTY; // private mode, blocked storage, bad JSON
  }
  return snapshot;
}

function write(next: Store) {
  snapshot = next;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Storage unavailable: keep the in-memory copy for this visit.
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

/** Keeps the newest MAX_HIDDEN entries. */
export function capHidden(store: Store, max = MAX_HIDDEN): Store {
  const entries = Object.entries(store);
  if (entries.length <= max) return store;
  return Object.fromEntries(entries.sort((a, b) => b[1].localeCompare(a[1])).slice(0, max));
}

export function useHidden() {
  const store = useSyncExternalStore(subscribe, read, () => EMPTY);

  const hide = useCallback((id: string) => {
    write(capHidden({ ...read(), [id]: new Date().toISOString().slice(0, 10) }));
  }, []);

  const unhide = useCallback((id: string) => {
    const next = { ...read() };
    if (!(id in next)) return;
    delete next[id];
    write(next);
  }, []);

  return { isHidden: (id: string) => id in store, hide, unhide };
}
