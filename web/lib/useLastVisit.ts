"use client";

import { useSyncExternalStore } from "react";
import { localDay } from "./format";
import type { Job } from "./types";

// "New since your last visit", kept as one JSON value in localStorage.
//
// The mark compares data with data, not with the clock: `seen` is the newest `firstSeen`
// the visitor had in front of them, so a job fetched later on the day of a visit still
// counts as new next time.
//
// - `next`/`nextAt`: the newest `firstSeen` loaded on the current visit, and when.
// - `seen`/`seenAt`: the same for the visit before. Jobs with `firstSeen > seen` are new;
//   `seenAt` names the day ("Since Tuesday"). `seen: null` = first-visit behaviour.
// - A load more than 30 minutes after `nextAt` is a new visit: `next` becomes `seen`.
//   Reloads and other tabs within 30 minutes leave the record alone, so the view stays.
// - Computed once per page load (once the data is in) and kept in memory.
// - Blocked or broken storage behaves like a first visit.
export const LAST_VISIT_KEY = "dsj:lastVisit";
const SAME_VISIT_MS = 30 * 60_000;

export interface VisitRecord {
  seen: string | null; // "YYYY-MM-DD"
  seenAt: string; // ISO date-time
  next: string | null; // "YYYY-MM-DD"
  nextAt: string; // ISO date-time
}

/** The previous visit: jobs first seen after `seen` are new; `seenAt` is when it was. */
export interface LastVisit {
  seen: string;
  seenAt: string;
}

const isDay = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
const isTime = (v: unknown): v is string => typeof v === "string" && !Number.isNaN(Date.parse(v));

/** Parses the stored value. Accepts the old format (a bare ISO date-time) once. */
export function parseVisitRecord(raw: string | null, now = new Date()): VisitRecord | null {
  if (!raw) return null;
  if (!raw.startsWith("{")) {
    // Old format: the time of the last visit. Keep it as the mark.
    if (!isTime(raw) || Date.parse(raw) > now.getTime()) return null;
    const day = localDay(raw);
    return { seen: day, seenAt: raw, next: day, nextAt: raw };
  }
  try {
    const r = JSON.parse(raw) as Partial<VisitRecord>;
    const dayOrNull = (v: unknown) => v === null || isDay(v);
    if (!r || !dayOrNull(r.seen) || !dayOrNull(r.next) || !isTime(r.seenAt) || !isTime(r.nextAt)) return null;
    return { seen: r.seen ?? null, seenAt: r.seenAt, next: r.next ?? null, nextAt: r.nextAt };
  } catch {
    return null;
  }
}

/** The record after this load. Returns `stored` itself when nothing changes. */
export function advanceVisit(stored: VisitRecord | null, maxFirstSeen: string | null, now = new Date()): VisitRecord {
  const at = now.toISOString();
  if (!stored) return { seen: null, seenAt: at, next: maxFirstSeen, nextAt: at };
  // A clock that went backwards also counts as a new visit, so the record can't get stuck.
  if (Math.abs(now.getTime() - Date.parse(stored.nextAt)) <= SAME_VISIT_MS) return stored;
  return { seen: stored.next, seenAt: stored.nextAt, next: maxFirstSeen, nextAt: at };
}

let mark: LastVisit | null | undefined; // undefined = not computed yet

/** Reads the mark (and records this visit). Exported for tests; use `useLastVisit` in components. */
export function readLastVisit(maxFirstSeen: string | null): LastVisit | null {
  if (mark !== undefined) return mark;
  let record: VisitRecord | null = null;
  try {
    const now = new Date();
    const stored = parseVisitRecord(localStorage.getItem(LAST_VISIT_KEY), now);
    record = advanceVisit(stored, maxFirstSeen, now);
    if (record !== stored) localStorage.setItem(LAST_VISIT_KEY, JSON.stringify(record));
  } catch {
    record = null;
  }
  return (mark = record?.seen ? { seen: record.seen, seenAt: record.seenAt } : null);
}

/** For tests: forget the in-memory mark. */
export function resetLastVisitCache() {
  mark = undefined;
}

const subscribe = () => () => {};

function newest(jobs: Job[]): string | null {
  let max: string | null = null;
  for (const j of jobs) if (!max || j.firstSeen > max) max = j.firstSeen;
  return max;
}

/** The previous visit; null on a first visit; undefined before hydration or while `jobs` is null (not loaded). */
export function useLastVisit(jobs: Job[] | null): LastVisit | null | undefined {
  return useSyncExternalStore(
    subscribe,
    () => (mark !== undefined ? mark : jobs ? readLastVisit(newest(jobs)) : undefined),
    () => undefined,
  );
}
