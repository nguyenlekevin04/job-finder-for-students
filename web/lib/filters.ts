import { isNew, localDay } from "./format";
import { search, type SearchIndex } from "./search";
export { makeIndex } from "./search";
import { ALL_FIELDS, ALL_TYPES, type Field, type Job, type JobType } from "./types";

export type Sort = "newest" | "company";

export interface Filters {
  q: string;
  types: JobType[];
  fields: Field[];
  english: boolean;
  remote: boolean; // include remote jobs
  fresh: boolean; // only jobs first seen in the last 7 days
  hours: boolean; // only jobs that state at most HOURS_LIMIT h/week
  since: string | null; // "YYYY-MM-DD": only jobs first seen after this day ("new since your last visit")
  sort: Sort;
  job: string | null; // the expanded job; not a filter, but shared through the URL
}

export const DEFAULT_FILTERS: Filters = {
  q: "",
  types: [],
  fields: [],
  english: false,
  remote: true,
  fresh: false,
  hours: false,
  since: null,
  sort: "newest",
  job: null,
};

/** The "Up to 20 h/week" filter: the most a student may work during the semester. */
export const HOURS_LIMIT = 20;

/** Known to be at most HOURS_LIMIT h/week. Only hoursMin, or a range above it, doesn't count. */
export function withinHours(job: Job): boolean {
  return typeof job.hoursMax === "number" && job.hoursMax <= HOURS_LIMIT;
}

const list = (v: string | null) => (v ? v.split(",").filter(Boolean) : []);
/** A real calendar date "YYYY-MM-DD" not after today, else null (so "2026-02-30" can't reach date formatting). */
function day(v: string | null): string | null {
  if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return null;
  const d = new Date(`${v}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().startsWith(v) && v <= localDay(new Date()) ? v : null;
}

// URL <-> filters, so a filtered view can be bookmarked or shared.
export function filtersFromParams(p: URLSearchParams): Filters {
  return {
    q: p.get("q") ?? "",
    types: list(p.get("type")).filter((t): t is JobType => ALL_TYPES.includes(t as JobType)),
    fields: list(p.get("field")).filter((f): f is Field => ALL_FIELDS.includes(f as Field)),
    english: p.get("en") === "1",
    remote: p.get("remote") !== "0",
    fresh: p.get("new") === "1",
    hours: p.get("hours") === String(HOURS_LIMIT),
    since: day(p.get("since")),
    sort: p.get("sort") === "company" ? "company" : "newest",
    job: p.get("job") || null,
  };
}

export function filtersToParams(f: Filters): URLSearchParams {
  const p = new URLSearchParams();
  if (f.q.trim()) p.set("q", f.q.trim());
  if (f.types.length) p.set("type", f.types.join(","));
  if (f.fields.length) p.set("field", f.fields.join(","));
  if (f.english) p.set("en", "1");
  if (!f.remote) p.set("remote", "0");
  if (f.fresh) p.set("new", "1");
  if (f.hours) p.set("hours", String(HOURS_LIMIT));
  if (f.since) p.set("since", f.since);
  if (f.sort !== "newest") p.set("sort", f.sort);
  if (f.job) p.set("job", f.job);
  return p;
}

export function activeFilterCount(f: Filters): number {
  return (
    f.types.length +
    f.fields.length +
    (f.english ? 1 : 0) +
    (f.remote ? 0 : 1) +
    (f.fresh ? 1 : 0) +
    (f.hours ? 1 : 0) +
    (f.since ? 1 : 0)
  );
}

export function jobDate(job: Job): string {
  return job.postedAt ?? job.firstSeen;
}

export function applyFilters(jobs: Job[], f: Filters, index: SearchIndex | null): Job[] {
  let result = jobs;
  const q = f.q.trim();
  if (q && index) {
    const hits = search(jobs, q, index);
    result = result.filter((j) => hits.has(j.id));
  }
  result = result.filter(
    (j) =>
      (!f.types.length || j.types.some((t) => f.types.includes(t))) &&
      (!f.fields.length || j.fields.some((x) => f.fields.includes(x))) &&
      (!f.english || j.englishFriendly) &&
      (f.remote || !j.remote) &&
      (!f.fresh || isNew(j.firstSeen)) &&
      (!f.hours || withinHours(j)) &&
      (!f.since || j.firstSeen > f.since)
  );
  return [...result].sort((a, b) =>
    f.sort === "company"
      ? a.company.localeCompare(b.company, "de") || a.title.localeCompare(b.title, "de")
      : jobDate(b).localeCompare(jobDate(a)) || b.firstSeen.localeCompare(a.firstSeen),
  );
}
