import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { localDay } from "./format";
import { advanceVisit, LAST_VISIT_KEY, parseVisitRecord, readLastVisit, resetLastVisitCache, type VisitRecord } from "./useLastVisit";

class MemoryStorage {
  data = new Map<string, string>();
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.data.set(k, v);
  }
}

const NOW = new Date("2026-10-29T12:00:00Z");
const minutes = (n: number) => new Date(NOW.getTime() + n * 60_000);

describe("advanceVisit", () => {
  it("first visit: no mark, remembers the newest job and the time", () => {
    expect(advanceVisit(null, "2026-10-29", NOW)).toEqual({
      seen: null,
      seenAt: NOW.toISOString(),
      next: "2026-10-29",
      nextAt: NOW.toISOString(),
    });
  });

  it("a reload within 30 minutes keeps the mark and slides the window", () => {
    const rec: VisitRecord = { seen: "2026-10-26", seenAt: "2026-10-26T08:00:00.000Z", next: "2026-10-29", nextAt: NOW.toISOString() };
    const a = advanceVisit(rec, "2026-10-29", minutes(25));
    expect(a).toMatchObject({ seen: "2026-10-26", seenAt: rec.seenAt, next: "2026-10-29", nextAt: minutes(25).toISOString() });
    // 50 minutes after the first load but only 25 after the last one: still the same visit.
    expect(advanceVisit(a, "2026-10-29", minutes(50))).toMatchObject({ seen: "2026-10-26", nextAt: minutes(50).toISOString() });
  });

  it("the next day rolls forward: this visit's newest job becomes the mark", () => {
    const first = advanceVisit(null, "2026-10-29", NOW);
    const nextDay = new Date("2026-10-30T09:00:00Z");
    expect(advanceVisit(first, "2026-10-30", nextDay)).toEqual({
      seen: "2026-10-29",
      seenAt: NOW.toISOString(),
      next: "2026-10-30",
      nextAt: nextDay.toISOString(),
    });
  });

  it("a job fetched later on the day of a visit is new on the next visit", () => {
    // Visit early on the 29th, before the daily fetch: the newest job is from the 28th.
    const early = new Date("2026-10-29T05:00:00Z");
    const visit = advanceVisit(null, "2026-10-28", early);
    // The fetch later that day adds a job first seen on the 29th; next visit is the 30th.
    const next = advanceVisit(visit, "2026-10-29", new Date("2026-10-30T09:00:00Z"));
    expect(next.seen).toBe("2026-10-28");
    expect("2026-10-29" > next.seen!).toBe(true); // firstSeen > seen → new
    expect(localDay(next.seenAt)).toBe(localDay(early)); // the label still names the visit day
  });
});

describe("parseVisitRecord", () => {
  it("reads the JSON record", () => {
    const rec: VisitRecord = { seen: null, seenAt: NOW.toISOString(), next: "2026-10-29", nextAt: NOW.toISOString() };
    expect(parseVisitRecord(JSON.stringify(rec), NOW)).toEqual(rec);
  });

  it("migrates the old format (a bare ISO date-time) to a mark on that day", () => {
    const old = "2026-10-26T08:00:00.000Z";
    const day = localDay(old);
    expect(parseVisitRecord(old, NOW)).toEqual({ seen: day, seenAt: old, next: day, nextAt: old });
    // ... and the first load rolls it forward without losing the mark.
    const rolled = advanceVisit(parseVisitRecord(old, NOW), "2026-10-29", NOW);
    expect(rolled).toMatchObject({ seen: day, seenAt: old, next: "2026-10-29" });
  });

  it("ignores garbage, broken records and future old-format values", () => {
    expect(parseVisitRecord(null, NOW)).toBeNull();
    expect(parseVisitRecord("not a date", NOW)).toBeNull();
    expect(parseVisitRecord("2099-01-01T00:00:00.000Z", NOW)).toBeNull();
    expect(parseVisitRecord("{broken", NOW)).toBeNull();
    expect(parseVisitRecord(JSON.stringify({ seen: "yesterday", seenAt: "x", next: null, nextAt: "x" }), NOW)).toBeNull();
  });
});

describe("readLastVisit", () => {
  let local: MemoryStorage;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
    local = new MemoryStorage();
    vi.stubGlobal("localStorage", local);
    resetLastVisitCache();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("first visit: no mark, writes the record", () => {
    expect(readLastVisit("2026-10-29")).toBeNull();
    expect(JSON.parse(local.getItem(LAST_VISIT_KEY)!)).toEqual({
      seen: null,
      seenAt: NOW.toISOString(),
      next: "2026-10-29",
      nextAt: NOW.toISOString(),
    });
  });

  it("returning: returns the previous visit and rolls the record forward", () => {
    const prev: VisitRecord = { seen: "2026-10-20", seenAt: "2026-10-20T08:00:00.000Z", next: "2026-10-26", nextAt: "2026-10-26T08:00:00.000Z" };
    local.setItem(LAST_VISIT_KEY, JSON.stringify(prev));
    expect(readLastVisit("2026-10-29")).toEqual({ seen: "2026-10-26", seenAt: "2026-10-26T08:00:00.000Z" });
    expect(JSON.parse(local.getItem(LAST_VISIT_KEY)!)).toMatchObject({ seen: "2026-10-26", next: "2026-10-29", nextAt: NOW.toISOString() });
  });

  it("is read once: later calls return the same mark", () => {
    expect(readLastVisit("2026-10-29")).toBeNull();
    expect(readLastVisit("2026-10-30")).toBeNull();
  });

  it("a reload within 30 minutes keeps the mark", () => {
    local.setItem(LAST_VISIT_KEY, "2026-10-26T08:00:00.000Z"); // old format
    const mark = readLastVisit("2026-10-29");
    expect(mark).toEqual({ seen: localDay("2026-10-26T08:00:00.000Z"), seenAt: "2026-10-26T08:00:00.000Z" });
    resetLastVisitCache(); // reload
    vi.setSystemTime(minutes(5));
    expect(readLastVisit("2026-10-29")).toEqual(mark);
  });

  it("blocked storage behaves like a first visit", () => {
    const blocked = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    vi.stubGlobal("localStorage", blocked);
    expect(readLastVisit("2026-10-29")).toBeNull();
  });
});
