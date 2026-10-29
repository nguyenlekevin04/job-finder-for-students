"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  activeFilterCount,
  applyFilters,
  DEFAULT_FILTERS,
  filtersFromParams,
  filtersToParams,
  makeIndex,
  type Filters,
} from "@/lib/filters";
import { isNew, localDay, relativeTime, visitDayLabel } from "@/lib/format";
import { useBookmarks } from "@/lib/useBookmarks";
import { useJobsFile } from "@/lib/useJobs";
import { useLastVisit } from "@/lib/useLastVisit";
import { FilterGroups, SortSelect } from "./FilterGroups";
import { SearchIcon, XIcon } from "./Icons";
import { JobRow } from "./JobRow";
import { NewTicket } from "./NewTicket";
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

  const update = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));
  const reset = () => setFilters((f) => ({ ...DEFAULT_FILTERS, job: f.job }));
  const openJob = (id: string) => setFilters((f) => ({ ...f, job: f.job === id ? null : id }));

  const data = state.status === "ready" ? state.data : null;
  const jobs = useMemo(() => data?.jobs ?? [], [data]);
  const index = useMemo(() => (jobs.length ? makeIndex(jobs) : null), [jobs]);
  const results = useMemo(() => applyFilters(jobs, filters, index), [jobs, filters, index]);
  const newCount = useMemo(() => jobs.filter((j) => isNew(j.firstSeen)).length, [jobs]);
  const active = activeFilterCount(filters);

  // "New" is either "since your last visit" or, on a first visit, "this week".
  // A ?since= link wins over the stored mark, so a shared link shows the same set.
  const lastVisit = useLastVisit(); // undefined until hydrated, null on a first visit
  const markDay = lastVisit ? localDay(lastVisit) : null;
  const sinceDay = filters.since ?? markDay;
  const sinceCount = useMemo(() => (sinceDay ? jobs.filter((j) => j.firstSeen > sinceDay).length : 0), [jobs, sinceDay]);
  const newMode: "since" | "nothing" | "week" | null = filters.since || (markDay && sinceCount > 0)
    ? "since"
    : markDay
      ? "nothing"
      : lastVisit === null
        ? "week"
        : null;

  // A shared link with ?job= scrolls to that job once the data is in.
  const scrolled = useRef(false);
  useEffect(() => {
    if (!data || scrolled.current) return;
    scrolled.current = true;
    if (filters.job) document.getElementById(`row-${filters.job}`)?.scrollIntoView({ block: "start" });
  }, [data, filters.job]);

  // "/" jumps to the search field, like the hint says.
  const searchRef = useRef<HTMLInputElement>(null);
  // Focus target after dismissing the "no longer available" notice, which unmounts.
  const countRef = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (e.key !== "/" || e.metaKey || e.ctrlKey || el.closest("input, textarea, select, [contenteditable]")) return;
      e.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-10 pt-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-14 lg:pt-12">
      {/* Intro, search and filters */}
      {/* max-h + scroll so short screens can reach every filter; px/pb keep focus rings inside the scroll box */}
      <section className="lg:sticky lg:top-6 lg:-mx-1.5 lg:max-h-[calc(100vh-3rem)] lg:self-start lg:overflow-y-auto lg:px-1.5 lg:pb-1.5 lg:[scrollbar-color:var(--c-line)_transparent] lg:[scrollbar-width:thin]">
        <h1 className="text-[34px] leading-[0.98] font-semibold tracking-[-0.05em] text-balance sm:text-[42px] xl:text-[48px]">
          Student tech jobs, made in{" "}
          <span className="font-serif text-[1.12em] font-normal tracking-[-0.02em] text-orange-text">Dresden.</span>
        </h1>
        <p className="mt-3 text-[17px] leading-snug text-muted">Student jobs in AI, data and software. Updated daily.</p>

        <div className="mt-6 flex items-center gap-3 border-b-2 border-rule py-1 text-lg">
          <SearchIcon width={19} height={19} className="shrink-0 text-muted" />
          <input
            ref={searchRef}
            type="search"
            value={filters.q}
            onChange={(e) => update({ q: e.target.value })}
            placeholder="Search jobs, companies, skills…"
            aria-label="Search jobs"
            className="h-11 min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted [&::-webkit-search-cancel-button]:hidden"
          />
          {filters.q ? (
            <button
              type="button"
              onClick={() => {
                update({ q: "" });
                searchRef.current?.focus(); // the button unmounts; keep keyboard users in the field
              }}
              aria-label="Clear search"
              className="focus-ring grid size-6 place-items-center rounded text-muted hover:text-ink"
            >
              <XIcon width={15} height={15} />
            </button>
          ) : (
            <kbd className="hidden rounded-md border border-line px-1.5 font-sans text-xs text-muted sm:block">/</kbd>
          )}
        </div>

        {data ? (
          <FilterGroups filters={filters} jobs={jobs} onChange={update} onReset={reset} activeCount={active} />
        ) : (
          <div className="mt-6 space-y-3">
            {Array.from({ length: 3 }, (_, i) => (
              <div key={i} className="h-5 w-4/5 animate-pulse rounded bg-line" />
            ))}
          </div>
        )}
      </section>

      {/* Job list */}
      <section aria-live="polite" className="min-w-0">
        {state.status === "loading" && <LoadingList />}
        {state.status === "error" && <ErrorState message={state.message} onRetry={retry} />}
        {data && (
          <>
            {/* Highlighting "new" only means something when some jobs aren't. */}
            {newMode === "since" && sinceDay && (
              <NewTicket
                since={sinceDay}
                count={sinceCount}
                active={!!filters.since}
                onToggle={() => update({ since: filters.since ? null : sinceDay })}
              />
            )}
            {newMode === "nothing" && markDay && markDay !== localDay(new Date()) && (
              <p className="mb-6 border-l-2 border-rule pl-3 text-sm text-muted">
                Nothing new since {visitDayLabel(markDay)}. The list updates every morning.
              </p>
            )}
            {newMode === "week" && newCount > 0 && newCount < jobs.length && (
              <NewTicket count={newCount} active={filters.fresh} onToggle={() => update({ fresh: !filters.fresh })} />
            )}
            {/* A shared ?job= link to a job that closed since: say so instead of opening nothing. */}
            {filters.job && !jobs.some((j) => j.id === filters.job) && (
              <p role="status" className="mb-4 flex flex-wrap items-baseline gap-x-3 border-l-2 border-rule pl-3 text-sm text-muted">
                This job is no longer available.
                <button
                  type="button"
                  onClick={() => {
                    update({ job: null });
                    countRef.current?.focus();
                  }}
                  className="focus-ring hit link-u rounded text-ink"
                >
                  Dismiss
                </button>
              </p>
            )}
            <div className="flex items-center justify-between gap-4 pb-2.5 text-[13px] text-muted">
              <span ref={countRef} tabIndex={-1} data-testid="results-count" className="focus-ring rounded">
                {results.length === jobs.length ? `${jobs.length} jobs` : `${results.length} of ${jobs.length} jobs`}
                {data.generatedAt ? ` · updated ${relativeTime(data.generatedAt)}` : " · first update pending"}
              </span>
              <SortSelect value={filters.sort} onChange={(sort) => update({ sort })} />
            </div>
            {jobs.length === 0 ? (
              <EmptyState title="No jobs yet">The list is filled every morning. Check back soon.</EmptyState>
            ) : results.length === 0 ? (
              <EmptyState title="Nothing matches">
                Try a broader search or fewer filters.{" "}
                <button type="button" onClick={reset} className="focus-ring link-u rounded text-ink">
                  Clear filters
                </button>
              </EmptyState>
            ) : (
              <ol className="border-b-[1.5px] border-rule">
                {results.map((job) => (
                  <JobRow
                    key={job.id}
                    job={job}
                    open={filters.job === job.id}
                    onToggle={openJob}
                    saved={isSaved(job.id)}
                    onToggleSave={toggle}
                    showNew={newMode === "since" || (newMode === "week" && newCount < jobs.length)}
                    newSince={newMode === "since" ? sinceDay : null}
                  />
                ))}
              </ol>
            )}
          </>
        )}
      </section>
    </div>
  );
}
