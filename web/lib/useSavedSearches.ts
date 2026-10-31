"use client";

import { useCallback, useSyncExternalStore } from "react";
import { activeFilterCount, filtersFromParams, filtersToParams, type Filters } from "./filters";
import { FIELD_LABELS, TYPE_LABELS } from "./types";

// Saved searches, in this browser only: a free stand-in for email alerts. Each search keeps
// the newest firstSeen it showed when last opened, so the Saved page can say "3 new".
const KEY = "dsj:searches:v1";
const EVENT = "dsj:searches";
export const MAX_SEARCHES = 10;

export interface SavedSearch {
  qs: string; // the filters as a query string, without the open job
  seen: string | null; // newest firstSeen among its matches when last opened ("YYYY-MM-DD")
}

let snapshot: SavedSearch[] | null = null;
const EMPTY: SavedSearch[] = [];

function read(): SavedSearch[] {
  if (snapshot) return snapshot;
  try {
    const raw = JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as unknown;
    snapshot = Array.isArray(raw)
      ? raw
          .filter((s): s is SavedSearch => !!s && typeof s.qs === "string" && (s.seen === null || typeof s.seen === "string"))
          .slice(0, MAX_SEARCHES)
      : EMPTY;
  } catch {
    snapshot = EMPTY;
  }
  return snapshot;
}

function write(next: SavedSearch[]) {
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
      snapshot = null;
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

/** The search part of the filters, as a stable query string (the open job doesn't count). */
export function searchKey(f: Filters): string {
  return filtersToParams({ ...f, job: null, since: null }).toString();
}

/** A short name for a search: "Thesis · AI / ML · “python”". */
export function searchLabel(qs: string): string {
  const f = filtersFromParams(new URLSearchParams(qs));
  const parts = [
    ...f.types.map((t) => TYPE_LABELS[t]),
    ...f.fields.map((x) => FIELD_LABELS[x]),
    f.english && "English-friendly",
    f.german && "German B2 is enough",
    f.hours && "Up to 20 h/week",
    !f.remote && "No remote",
    f.fresh && "This week",
    f.q.trim() && `“${f.q.trim()}”`,
  ].filter(Boolean) as string[];
  return parts.join(" · ") || "All jobs";
}

/** Worth saving: a search text or at least one filter (sort, open job and "since" don't count). */
export function isSearch(f: Filters): boolean {
  return !!f.q.trim() || activeFilterCount({ ...f, since: null }) > 0;
}

export function useSavedSearches() {
  const searches = useSyncExternalStore(subscribe, read, () => EMPTY);

  const add = useCallback((qs: string, seen: string | null) => {
    const current = read();
    if (current.some((s) => s.qs === qs)) return;
    write([{ qs, seen }, ...current].slice(0, MAX_SEARCHES));
  }, []);

  const remove = useCallback((qs: string) => write(read().filter((s) => s.qs !== qs)), []);

  /** Opening a search marks its current jobs as seen. */
  const markSeen = useCallback((qs: string, seen: string | null) => {
    write(read().map((s) => (s.qs === qs ? { ...s, seen } : s)));
  }, []);

  return { searches, add, remove, markSeen, isSaved: (qs: string) => searches.some((s) => s.qs === qs) };
}
