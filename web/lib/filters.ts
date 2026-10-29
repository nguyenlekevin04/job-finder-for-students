import Fuse from "fuse.js";
import { isNew } from "./format";
import { ALL_FIELDS, ALL_TYPES, type Field, type Job, type JobType } from "./types";

export type Sort = "newest" | "company";

export interface Filters {
  q: string;
  types: JobType[];
  fields: Field[];
  english: boolean;
  remote: boolean; // include remote jobs
  fresh: boolean; // only jobs first seen in the last 7 days
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
  since: null,
  sort: "newest",
  job: null,
};

const list = (v: string | null) => (v ? v.split(",").filter(Boolean) : []);
const day = (v: string | null) => (v && /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : null);

// URL <-> filters, so a filtered view can be bookmarked or shared.
export function filtersFromParams(p: URLSearchParams): Filters {
  return {
    q: p.get("q") ?? "",
    types: list(p.get("type")).filter((t): t is JobType => ALL_TYPES.includes(t as JobType)),
    fields: list(p.get("field")).filter((f): f is Field => ALL_FIELDS.includes(f as Field)),
    english: p.get("en") === "1",
    remote: p.get("remote") !== "0",
    fresh: p.get("new") === "1",
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
  if (f.since) p.set("since", f.since);
  if (f.sort !== "newest") p.set("sort", f.sort);
  if (f.job) p.set("job", f.job);
  return p;
}

export function activeFilterCount(f: Filters): number {
  return f.types.length + f.fields.length + (f.english ? 1 : 0) + (f.remote ? 0 : 1) + (f.fresh ? 1 : 0) + (f.since ? 1 : 0);
}

export function jobDate(job: Job): string {
  return job.postedAt ?? job.firstSeen;
}

export function makeIndex(jobs: Job[]) {
  return new Fuse(jobs, {
    keys: [
      { name: "title", weight: 3 },
      { name: "company", weight: 2 },
      { name: "snippet", weight: 1 },
      { name: "location", weight: 0.5 },
    ],
    threshold: 0.35,
    ignoreLocation: true,
    minMatchCharLength: 2,
  });
}

export function applyFilters(jobs: Job[], f: Filters, index: Fuse<Job> | null): Job[] {
  let result = jobs;
  const q = f.q.trim();
  if (q && index) {
    const hits = new Set(index.search(q).map((r) => r.item.id));
    result = result.filter((j) => hits.has(j.id));
  }
  result = result.filter(
    (j) =>
      (!f.types.length || j.types.some((t) => f.types.includes(t))) &&
      (!f.fields.length || j.fields.some((x) => f.fields.includes(x))) &&
      (!f.english || j.englishFriendly) &&
      (f.remote || !j.remote) &&
      (!f.fresh || isNew(j.firstSeen)) &&
      (!f.since || j.firstSeen > f.since)
  );
  return [...result].sort((a, b) =>
    f.sort === "company"
      ? a.company.localeCompare(b.company, "de") || a.title.localeCompare(b.title, "de")
      : jobDate(b).localeCompare(jobDate(a)) || b.firstSeen.localeCompare(a.firstSeen),
  );
}
