import Fuse from "fuse.js";
import { ALL_FIELDS, ALL_TYPES, type Field, type Job, type JobType } from "./types";

export type Sort = "newest" | "company";

export interface Filters {
  q: string;
  types: JobType[];
  fields: Field[];
  english: boolean;
  remote: boolean; // include remote jobs
  sources: string[];
  sort: Sort;
}

export const DEFAULT_FILTERS: Filters = {
  q: "",
  types: [],
  fields: [],
  english: false,
  remote: true,
  sources: [],
  sort: "newest",
};

const list = (v: string | null) => (v ? v.split(",").filter(Boolean) : []);

// URL <-> filters, so a filtered view can be bookmarked or shared.
export function filtersFromParams(p: URLSearchParams): Filters {
  return {
    q: p.get("q") ?? "",
    types: list(p.get("type")).filter((t): t is JobType => ALL_TYPES.includes(t as JobType)),
    fields: list(p.get("field")).filter((f): f is Field => ALL_FIELDS.includes(f as Field)),
    english: p.get("en") === "1",
    remote: p.get("remote") !== "0",
    sources: list(p.get("source")),
    sort: p.get("sort") === "company" ? "company" : "newest",
  };
}

export function filtersToParams(f: Filters): URLSearchParams {
  const p = new URLSearchParams();
  if (f.q.trim()) p.set("q", f.q.trim());
  if (f.types.length) p.set("type", f.types.join(","));
  if (f.fields.length) p.set("field", f.fields.join(","));
  if (f.english) p.set("en", "1");
  if (!f.remote) p.set("remote", "0");
  if (f.sources.length) p.set("source", f.sources.join(","));
  if (f.sort !== "newest") p.set("sort", f.sort);
  return p;
}

export function activeFilterCount(f: Filters): number {
  return f.types.length + f.fields.length + f.sources.length + (f.english ? 1 : 0) + (f.remote ? 0 : 1);
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
      (!f.sources.length || j.links.some((l) => f.sources.includes(l.source))),
  );
  return [...result].sort((a, b) =>
    f.sort === "company"
      ? a.company.localeCompare(b.company, "de") || a.title.localeCompare(b.title, "de")
      : jobDate(b).localeCompare(jobDate(a)) || b.firstSeen.localeCompare(a.firstSeen),
  );
}
