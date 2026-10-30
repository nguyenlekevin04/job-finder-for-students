import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  activeFilterCount,
  applyFilters,
  DEFAULT_FILTERS,
  filtersFromParams,
  filtersToParams,
  makeIndex,
  type Filters,
} from "./filters";
import type { Job } from "./types";

function job(over: Partial<Job>): Job {
  return {
    id: "x",
    title: "Werkstudent Software",
    company: "ACME",
    location: "Dresden",
    remote: false,
    type: "werkstudent",
    types: ["werkstudent"],
    fields: ["software"],
    englishFriendly: false,
    postedAt: null,
    deadline: null,
    firstSeen: "2026-10-01",
    lastSeen: "2026-10-29",
    links: [{ source: "Test", url: "https://example.com" }],
    snippet: "",
    ...over,
  };
}

const f = (over: Partial<Filters> = {}): Filters => ({ ...DEFAULT_FILTERS, ...over });

describe("URL <-> filters", () => {
  it("leaves the URL empty for the default view", () => {
    expect(filtersToParams(DEFAULT_FILTERS).toString()).toBe("");
    expect(filtersFromParams(new URLSearchParams())).toEqual(DEFAULT_FILTERS);
  });

  it("round-trips every filter and the open job", () => {
    const all = f({
      q: "python",
      types: ["thesis", "internship"],
      fields: ["ai"],
      english: true,
      remote: false,
      fresh: true,
      hours: true,
      since: "2026-10-27",
      sort: "company",
      job: "abc123",
    });
    const qs = filtersToParams(all).toString();
    expect(qs).toBe("q=python&type=thesis%2Cinternship&field=ai&en=1&remote=0&new=1&hours=20&since=2026-10-27&sort=company&job=abc123");
    expect(filtersFromParams(new URLSearchParams(qs))).toEqual(all);
  });

  it("ignores unknown values from hand-edited links", () => {
    const parsed = filtersFromParams(new URLSearchParams("type=hiwi,thesis&field=cooking&sort=random&job="));
    expect(parsed.types).toEqual(["thesis"]);
    expect(parsed.fields).toEqual([]);
    expect(parsed.sort).toBe("newest");
    expect(parsed.job).toBeNull();
  });

  it("only accepts a real YYYY-MM-DD date for ?since=", () => {
    expect(filtersFromParams(new URLSearchParams("since=2026-10-27")).since).toBe("2026-10-27");
    expect(filtersFromParams(new URLSearchParams("since=yesterday")).since).toBeNull();
    expect(filtersFromParams(new URLSearchParams("since=2026-10-27T10:00")).since).toBeNull();
  });

  it("rejects impossible calendar dates for ?since=", () => {
    for (const bad of ["2020-13-45", "0000-00-00", "2026-02-30"]) {
      expect(filtersFromParams(new URLSearchParams(`since=${bad}`)).since).toBeNull();
    }
    expect(filtersFromParams(new URLSearchParams("since=2024-02-29")).since).toBe("2024-02-29"); // leap day
  });

  it("rejects a ?since= date in the future", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 29, 12)); // local noon, 29 Oct 2026
    try {
      expect(filtersFromParams(new URLSearchParams("since=2026-10-29")).since).toBe("2026-10-29"); // today
      expect(filtersFromParams(new URLSearchParams("since=2026-10-30")).since).toBeNull();
      expect(filtersFromParams(new URLSearchParams("since=2028-02-29")).since).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("only turns the hours filter on for ?hours=20", () => {
    expect(filtersFromParams(new URLSearchParams("hours=20")).hours).toBe(true);
    for (const bad of ["hours=1", "hours=25", "hours=", "hours=yes"]) {
      expect(filtersFromParams(new URLSearchParams(bad)).hours).toBe(false);
    }
  });

  it("trims the search text", () => {
    expect(filtersToParams(f({ q: "  ml  " })).get("q")).toBe("ml");
    expect(filtersToParams(f({ q: "   " })).has("q")).toBe(false);
  });
});

describe("activeFilterCount", () => {
  it("counts real filters but not search, sort or the open job", () => {
    expect(activeFilterCount(f({ q: "x", sort: "company", job: "abc" }))).toBe(0);
    expect(activeFilterCount(f({ types: ["thesis"], fields: ["ai", "data"], english: true, remote: false, fresh: true }))).toBe(6);
    expect(activeFilterCount(f({ since: "2026-10-27" }))).toBe(1);
    expect(activeFilterCount(f({ hours: true }))).toBe(1);
  });
});

describe("applyFilters", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-29T10:00:00Z"));
  });
  afterEach(() => vi.useRealTimers());

  const jobs = [
    job({ id: "a", company: "Zeta", types: ["werkstudent"], fields: ["software"], postedAt: "2026-10-20" }),
    job({ id: "b", company: "Alpha", types: ["thesis"], fields: ["ai"], englishFriendly: true, postedAt: "2026-10-25" }),
    job({ id: "c", company: "Mid", types: ["internship"], fields: ["data"], remote: true, firstSeen: "2026-10-28" }),
  ];
  const ids = (list: Job[]) => list.map((j) => j.id);

  it("sorts newest first by default and by company on request", () => {
    expect(ids(applyFilters(jobs, f(), null))).toEqual(["c", "b", "a"]);
    expect(ids(applyFilters(jobs, f({ sort: "company" }), null))).toEqual(["b", "c", "a"]);
  });

  it("filters by type, field, English and remote", () => {
    expect(ids(applyFilters(jobs, f({ types: ["thesis", "werkstudent"] }), null))).toEqual(["b", "a"]);
    expect(ids(applyFilters(jobs, f({ fields: ["data"] }), null))).toEqual(["c"]);
    expect(ids(applyFilters(jobs, f({ english: true }), null))).toEqual(["b"]);
    expect(ids(applyFilters(jobs, f({ remote: false }), null))).toEqual(["b", "a"]);
  });

  it("'fresh' keeps only jobs first seen within the last 7 days", () => {
    expect(ids(applyFilters(jobs, f({ fresh: true }), null))).toEqual(["c"]);
  });

  it("'since' keeps only jobs first seen after that day", () => {
    const seen = [
      job({ id: "old", firstSeen: "2026-10-26" }),
      job({ id: "same", firstSeen: "2026-10-27" }),
      job({ id: "new", firstSeen: "2026-10-28" }),
    ];
    expect(ids(applyFilters(seen, f({ since: "2026-10-27" }), null))).toEqual(["new"]);
    expect(applyFilters(seen, f({ since: "2026-10-29" }), null)).toEqual([]);
  });

  it("'hours' keeps only jobs that state at most 20 h/week", () => {
    const stated = [
      job({ id: "exact", hoursMin: 20, hoursMax: 20 }),
      job({ id: "range", hoursMin: 15, hoursMax: 20 }),
      job({ id: "upto", hoursMax: 12 }),
      job({ id: "wide", hoursMin: 15, hoursMax: 25 }),
      job({ id: "from", hoursMin: 10 }),
      job({ id: "nulls", hoursMin: null, hoursMax: null }),
      job({ id: "unknown" }),
    ];
    expect(ids(applyFilters(stated, f({ hours: true }), null)).sort()).toEqual(["exact", "range", "upto"]);
    expect(applyFilters(stated, f(), null)).toHaveLength(stated.length);
  });

  it("never hides jobs because one is open", () => {
    expect(ids(applyFilters(jobs, f({ job: "b" }), null))).toEqual(["c", "b", "a"]);
  });

  it("searches title and company", () => {
    const index = makeIndex(jobs);
    expect(ids(applyFilters(jobs, f({ q: "alpha" }), index))).toEqual(["b"]);
  });
});
