"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  activeFilterCount,
  applyFilters,
  DEFAULT_FILTERS,
  filtersFromParams,
  filtersToParams,
  makeIndex,
  type Filters,
  type Sort,
} from "@/lib/filters";
import { isNew, relativeTime } from "@/lib/format";
import { useBookmarks } from "@/lib/useBookmarks";
import { useJobsFile } from "@/lib/useJobs";
import { FilterPanel } from "./FilterPanel";
import { FilterIcon, SearchIcon, XIcon } from "./Icons";
import { JobCard } from "./JobCard";
import { EmptyState, ErrorState, LoadingList } from "./States";

export function JobBoard() {
  const { state, retry } = useJobsFile();
  const { isSaved, toggle } = useBookmarks();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  // Filters live in state (instant UI) and are mirrored into the URL shortly
  // after, so a view can be shared. URL changes we didn't make (back/forward)
  // flow back into state.
  const paramStr = params.toString();
  const [filters, setFilters] = useState<Filters>(() => filtersFromParams(new URLSearchParams(paramStr)));
  const [seenParams, setSeenParams] = useState(paramStr);
  // The query string we last pushed, until its URL arrives. Cleared then, so a
  // later back/forward to the same URL still restores filters.
  const [pushed, setPushed] = useState<string | null>(null);
  if (paramStr !== seenParams) {
    setSeenParams(paramStr);
    if (paramStr === pushed) setPushed(null);
    else setFilters(filtersFromParams(new URLSearchParams(paramStr)));
  }

  useEffect(() => {
    const qs = filtersToParams(filters).toString();
    if (qs === paramStr) return;
    const t = setTimeout(() => {
      setPushed(qs);
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const [showFilters, setShowFilters] = useState(false);
  const query = filters.q;
  const setQuery = (q: string) => setFilters((f) => ({ ...f, q }));
  const update = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));
  const reset = () => setFilters(DEFAULT_FILTERS);

  const data = state.status === "ready" ? state.data : null;
  const jobs = useMemo(() => data?.jobs ?? [], [data]);
  const index = useMemo(() => (jobs.length ? makeIndex(jobs) : null), [jobs]);
  const results = useMemo(() => applyFilters(jobs, filters, index), [jobs, filters, index]);
  const sources = useMemo(
    () => [...new Set(jobs.flatMap((j) => j.links.map((l) => l.source)))].sort(),
    [jobs],
  );
  const newCount = useMemo(() => jobs.filter((j) => isNew(j.firstSeen, 7)).length, [jobs]);
  const active = activeFilterCount(filters);

  return (
    <div>
      {/* Hero */}
      <section className="pt-10 pb-8 sm:pt-14">
        <h1 className="max-w-2xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Student jobs in AI, ML &amp; Computer Science around Dresden
        </h1>
        <p className="mt-3 max-w-2xl text-zinc-600 dark:text-zinc-400">
          Werkstudent positions, internships and thesis topics from job boards, Fraunhofer, HZDR and TU Dresden, checked
          every morning.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
          {data ? (
            <>
              <Stat value={data.count} label="open positions" />
              <Stat value={newCount} label="new this week" accent />
              <span className="text-zinc-500 dark:text-zinc-400" title={new Date(data.generatedAt).toLocaleString("en-GB")}>
                Updated {relativeTime(data.generatedAt)}
              </span>
            </>
          ) : (
            <span className="h-7 w-72 animate-pulse rounded-full bg-zinc-200 dark:bg-zinc-800" />
          )}
        </div>
      </section>

      {/* Search + sort */}
      <div className="sticky top-14 z-20 -mx-4 mb-6 border-b border-zinc-200/80 bg-zinc-50/90 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6 dark:border-zinc-800/80 dark:bg-zinc-950/90">
        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-zinc-400" width={17} height={17} />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search jobs, companies, skills…"
              aria-label="Search jobs"
              className="focus-ring h-10 w-full rounded-lg border border-zinc-200 bg-white pr-9 pl-9 text-sm placeholder:text-zinc-400 dark:border-zinc-700 dark:bg-zinc-900 [&::-webkit-search-cancel-button]:hidden"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className="focus-ring absolute top-1/2 right-2 grid size-6 -translate-y-1/2 place-items-center rounded text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
              >
                <XIcon width={14} height={14} />
              </button>
            )}
          </div>
          <select
            value={filters.sort}
            onChange={(e) => update({ sort: e.target.value as Sort })}
            aria-label="Sort jobs"
            className="focus-ring h-10 w-[7.5rem] shrink-0 rounded-lg border border-zinc-200 bg-white px-2 text-sm sm:w-auto sm:px-2.5 dark:border-zinc-700 dark:bg-zinc-900"
          >
            <option value="newest">Newest</option>
            <option value="company">Company A–Z</option>
          </select>
          <button
            type="button"
            onClick={() => setShowFilters((s) => !s)}
            aria-expanded={showFilters}
            className="focus-ring inline-flex h-10 items-center gap-1.5 rounded-lg border border-zinc-200 bg-white px-3 text-sm font-medium lg:hidden dark:border-zinc-700 dark:bg-zinc-900"
          >
            <FilterIcon />
            <span className="hidden sm:inline">Filters</span>
            {active > 0 && <span className="rounded-full bg-indigo-600 px-1.5 text-xs text-white">{active}</span>}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[240px_minmax(0,1fr)] lg:gap-8">
        <aside className={`${showFilters ? "block" : "hidden"} lg:block`}>
          <div className="rounded-xl border border-zinc-200 bg-white p-4 lg:sticky lg:top-36 lg:border-0 lg:bg-transparent lg:p-0 dark:border-zinc-800 dark:bg-zinc-900 lg:dark:bg-transparent">
            {data ? (
              <FilterPanel
                filters={filters}
                jobs={jobs}
                sources={sources}
                onChange={update}
                onReset={reset}
                activeCount={active}
              />
            ) : (
              <div className="space-y-3">
                {Array.from({ length: 8 }, (_, i) => (
                  <div key={i} className="h-7 animate-pulse rounded bg-zinc-200/70 dark:bg-zinc-800" />
                ))}
              </div>
            )}
          </div>
        </aside>

        <section aria-live="polite" className="min-w-0">
          {state.status === "loading" && <LoadingList />}
          {state.status === "error" && <ErrorState message={state.message} onRetry={retry} />}
          {data && (
            <>
              <div className="mb-3 flex items-center justify-between text-sm text-zinc-500 dark:text-zinc-400">
                <span>
                  {results.length === jobs.length ? (
                    <>Showing all <b className="font-semibold text-zinc-900 dark:text-zinc-100">{jobs.length}</b> jobs</>
                  ) : (
                    <>
                      <b className="font-semibold text-zinc-900 dark:text-zinc-100">{results.length}</b> of {jobs.length} jobs match
                    </>
                  )}
                </span>
                {(active > 0 || query) && (
                  <button type="button" onClick={reset} className="focus-ring rounded font-medium text-indigo-600 hover:underline dark:text-indigo-400">
                    Reset all
                  </button>
                )}
              </div>
              {results.length === 0 ? (
                <EmptyState title="No jobs match these filters" icon={<SearchIcon width={20} height={20} />}>
                  Try a broader search, fewer filters, or turn on remote jobs.
                </EmptyState>
              ) : (
                <div className="space-y-3">
                  {results.map((job) => (
                    <JobCard key={job.id} job={job} saved={isSaved(job.id)} onToggleSave={toggle} />
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({ value, label, accent }: { value: number; label: string; accent?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 ring-1 ring-inset ${
        accent
          ? "bg-emerald-50 text-emerald-800 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/25"
          : "bg-white text-zinc-700 ring-zinc-200 dark:bg-zinc-900 dark:text-zinc-300 dark:ring-zinc-800"
      }`}
    >
      <b className="font-semibold tabular-nums">{value}</b> {label}
    </span>
  );
}
