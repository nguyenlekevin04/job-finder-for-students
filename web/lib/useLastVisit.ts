"use client";

import { useSyncExternalStore } from "react";

// "New since your last visit": the time of the previous visit, kept in localStorage.
//
// - Read once per page load and kept in memory, so the mark doesn't move while you browse.
// - `now` is written only when the stored value is missing or more than 30 minutes old,
//   so quick returns count as the same visit.
// - The mark this tab started with is also pinned in sessionStorage. Without it, a reload
//   would read back the `now` this visit just wrote and the "new since" view would vanish.
// - Blocked or broken storage behaves like a first visit.
export const LAST_VISIT_KEY = "dsj:lastVisit";
const SAME_VISIT_MS = 30 * 60_000;

let mark: string | null | undefined; // undefined = not read yet

function valid(v: string | null): v is string {
  if (!v) return false;
  const t = Date.parse(v);
  return !Number.isNaN(t) && t <= Date.now();
}

/** Reads the mark (and records this visit). Exported for tests; use `useLastVisit` in components. */
export function readLastVisit(): string | null {
  if (mark !== undefined) return mark;
  try {
    const pinned = sessionStorage.getItem(LAST_VISIT_KEY);
    if (pinned !== null) return (mark = valid(pinned) ? pinned : null);
  } catch {
    // fall through to localStorage
  }

  let stored: string | null = null;
  try {
    const raw = localStorage.getItem(LAST_VISIT_KEY);
    stored = valid(raw) ? raw : null;
    const now = Date.now();
    if (!stored || now - Date.parse(stored) > SAME_VISIT_MS) localStorage.setItem(LAST_VISIT_KEY, new Date(now).toISOString());
  } catch {
    stored = null;
  }
  try {
    sessionStorage.setItem(LAST_VISIT_KEY, stored ?? "");
  } catch {
    // no pin: a reload just reads localStorage again
  }
  return (mark = stored);
}

/** For tests: forget the in-memory mark. */
export function resetLastVisitCache() {
  mark = undefined;
}

const subscribe = () => () => {};

/** ISO date-time of the previous visit; null on a first visit; undefined before hydration. */
export function useLastVisit(): string | null | undefined {
  return useSyncExternalStore(subscribe, readLastVisit, () => undefined);
}
