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
      sort: "company",
      job: "abc123",
    });
    const qs = filtersToParams(all).toString();
    expect(qs).toBe("q=python&type=thesis%2Cinternship&field=ai&en=1&remote=0&new=1&sort=company&job=abc123");
    expect(filtersFromParams(new URLSearchParams(qs))).toEqual(all);
  });

  it("ignores unknown values from hand-edited links", () => {
    const parsed = filtersFromParams(new URLSearchParams("type=hiwi,thesis&field=cooking&sort=random&job="));
    expect(parsed.types).toEqual(["thesis"]);
    expect(parsed.fields).toEqual([]);
    expect(parsed.sort).toBe("newest");
    expect(parsed.job).toBeNull();
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

  it("never hides jobs because one is open", () => {
    expect(ids(applyFilters(jobs, f({ job: "b" }), null))).toEqual(["c", "b", "a"]);
  });

  it("searches title and company", () => {
    const index = makeIndex(jobs);
    expect(ids(applyFilters(jobs, f({ q: "alpha" }), index))).toEqual(["b"]);
  });
});
