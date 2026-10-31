"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { applyFilters, filtersFromParams, isExpired, jobDate, makeIndex } from "@/lib/filters";
import { STATUS_LABELS, STATUSES, useApplications, type AppStatus } from "@/lib/useApplications";
import { useBookmarks } from "@/lib/useBookmarks";
import { searchLabel, useSavedSearches } from "@/lib/useSavedSearches";
import { useJobsFile } from "@/lib/useJobs";
import type { Job } from "@/lib/types";
import { JobRow } from "./JobRow";
import { EmptyState, LoadingList } from "./States";

export function SavedJobs() {
  const { saved, toggle, count } = useBookmarks();
  const { state } = useJobsFile();
  const [open, setOpen] = useState<string | null>(null);
  // Jobs removed during this visit stay in the list as "Save for later", so the
  // same button undoes a mis-tap and keeps focus. Gone on the next visit.
  const [removed, setRemoved] = useState<Record<string, Job>>({});
  const [announce, setAnnounce] = useState("");
  const { applications, setStatus, persistent } = useApplications();
  const { searches, remove: removeSearch, markSeen } = useSavedSearches();
  // Per saved search: its matches today and how many are newer than when it was last opened.
  const searchRows = useMemo(() => {
    if (state.status !== "ready") return searches.map((s) => ({ ...s, total: null, fresh: 0, newest: s.seen }));
    const jobs = state.data.jobs.filter((j) => !isExpired(j));
    const index = makeIndex(jobs);
    return searches.map((s) => {
      const hits = applyFilters(jobs, filtersFromParams(new URLSearchParams(s.qs)), index);
      const newest = hits.reduce<string | null>((m, j) => (!m || j.firstSeen > m ? j.firstSeen : m), null);
      return { ...s, total: hits.length, fresh: hits.filter((j) => !s.seen || j.firstSeen > s.seen).length, newest };
    });
  }, [searches, state]);
  // "none" = saved but not applied yet; null = all.
  const [show, setShow] = useState<AppStatus | "none" | null>(null);
  const matches = (id: string, st: AppStatus | "none" | null) =>
    st === null ? true : st === "none" ? !applications[id] : applications[id]?.status === st;
  const current = useMemo(
    () => (state.status === "ready" ? new Map(state.data.jobs.map((j) => [j.id, j])) : null),
    [state],
  );

  // Prefer today's version of a job (fresh dates/links). A saved job missing from today's
  // data has closed (the daily fetch removes closed jobs), so it keeps the saved copy.
  const list = useMemo(() => {
    const jobs: { job: Job; closed: boolean; isSaved: boolean }[] = Object.values({ ...removed, ...saved }).map((s) => {
      const live = current?.get(s.id);
      return { job: live ?? s, closed: current ? !live : false, isSaved: s.id in saved };
    });
    return jobs.sort((a, b) => Number(a.closed) - Number(b.closed) || jobDate(b.job).localeCompare(jobDate(a.job)));
  }, [saved, removed, current]);

  // A status filter whose last job changed status falls back to "All" instead of an empty list.
  const shown = show !== null && list.some(({ job }) => matches(job.id, show)) ? show : null;

  const toggleSave = (job: Job) => {
    const wasSaved = job.id in saved;
    setRemoved((r) => {
      const next = { ...r };
      if (wasSaved) next[job.id] = saved[job.id];
      else delete next[job.id];
      return next;
    });
    toggle(job);
    // Include the title, so two removals in a row are both announced.
    setAnnounce(wasSaved ? `Removed ${job.title} from saved` : `Saved ${job.title} again`);
  };

  return (
    <div className="max-w-4xl pt-10 lg:pt-12">
      <h1 className="text-[44px] leading-[0.96] font-semibold tracking-[-0.05em] sm:text-[56px]">
        Your <span className="font-serif text-[1.12em] font-normal tracking-[-0.02em] text-orange-text">saved</span> jobs.
      </h1>
      <p className="mt-4 max-w-md text-[17px] leading-snug text-muted">
        {/* Removed rows stay listed this visit, so keep counting instead of showing the empty text. */}
        {count > 0 || list.length > 0
          ? `${count} job${count === 1 ? "" : "s"} kept for later, stored in this browser only.`
          : "Jobs you save show up here. They're stored in this browser only."}
      </p>
      <p role="status" className="sr-only">
        {announce}
      </p>

      {searchRows.length > 0 && (
        <section aria-labelledby="searches-title" className="mt-10">
          <h2 id="searches-title" className="text-xl font-semibold tracking-[-0.03em]">
            Saved searches
          </h2>
          <ul className="mt-3 border-b-[1.5px] border-rule">
            {searchRows.map((s) => (
              <li key={s.qs} className="flex items-center justify-between gap-4 border-t-[1.5px] border-rule py-3.5">
                <Link
                  href={`/?${s.qs}`}
                  onClick={() => markSeen(s.qs, s.newest)}
                  className="focus-ring link-u min-w-0 rounded text-[17px] font-semibold tracking-[-0.02em]"
                >
                  {searchLabel(s.qs)}
                </Link>
                <span className="flex shrink-0 items-center gap-4 text-sm">
                  {s.total !== null && (
                    <span className={s.fresh > 0 ? "font-semibold text-orange-text" : "text-muted"} data-testid="search-new">
                      {s.fresh > 0 ? `${s.fresh} new` : `${s.total} job${s.total === 1 ? "" : "s"}`}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => removeSearch(s.qs)}
                    aria-label={`Remove saved search ${searchLabel(s.qs)}`}
                    className="focus-ring hit link-u rounded text-muted hover:text-ink"
                  >
                    Remove
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="mt-10">
        {state.status === "loading" && count > 0 ? (
          <LoadingList count={Math.min(count, 4)} />
        ) : list.length === 0 ? (
          <EmptyState title="Nothing saved yet">
            <p>Open any job and choose “Save for later” to keep it here.</p>
            <Link
              href="/"
              className="focus-ring mt-5 inline-flex rounded-[10px] bg-btn px-4 py-2.5 text-[15px] font-semibold text-btn-ink hover:opacity-90"
            >
              Browse jobs
            </Link>
          </EmptyState>
        ) : (
          <>
          <div role="group" aria-label="Application status" className="mb-4 flex flex-wrap gap-x-5 gap-y-2 text-[15px]">
            {([null, "none", ...STATUSES] as const).map((st) => {
              const n = list.filter(({ job }) => matches(job.id, st)).length;
              if (st !== null && n === 0) return null;
              return (
                <button
                  key={st ?? "all"}
                  type="button"
                  aria-pressed={shown === st}
                  onClick={() => setShow(st)}
                  className={`focus-ring hit rounded-sm border-b-2 pb-0.5 ${shown === st ? "border-ink font-semibold" : "border-transparent text-muted hover:text-ink"}`}
                >
                  {st === null ? "All" : st === "none" ? "Not applied" : STATUS_LABELS[st]} <span className="tabular-nums">{n}</span>
                </button>
              );
            })}
          </div>
          {!persistent && (
            <p role="note" className="mb-4 border-l-2 border-rule pl-3 text-sm text-muted">
              Your browser blocks storage, so statuses are kept only until you close this tab.
            </p>
          )}
          <ol className="border-b-[1.5px] border-rule">
            {list
              .filter(({ job }) => matches(job.id, shown))
              .map(({ job, closed, isSaved }) => (
              <JobRow
                key={job.id}
                job={job}
                open={open === job.id}
                onToggle={(id) => setOpen((o) => (o === id ? null : id))}
                saved={isSaved}
                onToggleSave={toggleSave}
                closed={closed}
                application={applications[job.id]}
                onStatus={setStatus}
              />
            ))}
          </ol>
          </>
        )}
      </div>
    </div>
  );
}
