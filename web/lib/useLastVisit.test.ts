import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LAST_VISIT_KEY, readLastVisit, resetLastVisitCache } from "./useLastVisit";

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
let local: MemoryStorage;
let session: MemoryStorage;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
  local = new MemoryStorage();
  session = new MemoryStorage();
  vi.stubGlobal("localStorage", local);
  vi.stubGlobal("sessionStorage", session);
  resetLastVisitCache();
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("readLastVisit", () => {
  it("first visit: no mark, records now", () => {
    expect(readLastVisit()).toBeNull();
    expect(local.getItem(LAST_VISIT_KEY)).toBe(NOW.toISOString());
  });

  it("returning: returns the old mark and records now", () => {
    local.setItem(LAST_VISIT_KEY, "2026-10-26T08:00:00.000Z");
    expect(readLastVisit()).toBe("2026-10-26T08:00:00.000Z");
    expect(local.getItem(LAST_VISIT_KEY)).toBe(NOW.toISOString());
  });

  it("doesn't move a mark that is under 30 minutes old", () => {
    const recent = new Date(NOW.getTime() - 10 * 60_000).toISOString();
    local.setItem(LAST_VISIT_KEY, recent);
    expect(readLastVisit()).toBe(recent);
    expect(local.getItem(LAST_VISIT_KEY)).toBe(recent);
  });

  it("is read once: later calls return the same mark", () => {
    local.setItem(LAST_VISIT_KEY, "2026-10-26T08:00:00.000Z");
    readLastVisit();
    expect(readLastVisit()).toBe("2026-10-26T08:00:00.000Z");
  });

  it("a reload in the same tab keeps the mark it started with", () => {
    local.setItem(LAST_VISIT_KEY, "2026-10-26T08:00:00.000Z");
    readLastVisit();
    resetLastVisitCache(); // reload
    expect(readLastVisit()).toBe("2026-10-26T08:00:00.000Z");
  });

  it("ignores garbage and future values", () => {
    local.setItem(LAST_VISIT_KEY, "not a date");
    expect(readLastVisit()).toBeNull();
    resetLastVisitCache();
    session.data.clear();
    local.setItem(LAST_VISIT_KEY, "2099-01-01T00:00:00.000Z");
    expect(readLastVisit()).toBeNull();
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
    vi.stubGlobal("sessionStorage", blocked);
    expect(readLastVisit()).toBeNull();
  });
});
