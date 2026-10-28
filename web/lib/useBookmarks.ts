"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { Job } from "./types";

// Bookmarks live in this browser only. Whole jobs are stored, so a saved job
// stays visible even after it disappears from the daily data.
const KEY = "dsj:bookmarks:v1";
const EVENT = "dsj:bookmarks";

type Store = Record<string, Job>;

const EMPTY: Store = {};
let snapshot: Store | null = null;

function read(): Store {
  if (snapshot) return snapshot;
  try {
    const raw = window.localStorage.getItem(KEY);
    snapshot = raw ? (JSON.parse(raw) as Store) : EMPTY;
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

export function useBookmarks() {
  const store = useSyncExternalStore(subscribe, read, () => EMPTY);

  const toggle = useCallback((job: Job) => {
    const current = read();
    const next = { ...current };
    if (next[job.id]) delete next[job.id];
    else next[job.id] = job;
    write(next);
  }, []);

  return {
    saved: store,
    count: Object.keys(store).length,
    isSaved: (id: string) => Boolean(store[id]),
    toggle,
  };
}
