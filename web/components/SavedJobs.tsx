"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { jobDate } from "@/lib/filters";
import { useBookmarks } from "@/lib/useBookmarks";
import { useJobsFile } from "@/lib/useJobs";
import type { Job } from "@/lib/types";
import { JobRow } from "./JobRow";
import { EmptyState, LoadingList } from "./States";

export function SavedJobs() {
  const { saved, toggle, count } = useBookmarks();
  const { state } = useJobsFile();
  const [open, setOpen] = useState<string | null>(null);
  const current = useMemo(
    () => (state.status === "ready" ? new Map(state.data.jobs.map((j) => [j.id, j])) : null),
    [state],
  );

  // Prefer today's version of a job (fresh dates/links). A saved job missing from today's
  // data has closed (the daily fetch removes closed jobs), so it keeps the saved copy.
  const list = useMemo(() => {
    const jobs: { job: Job; closed: boolean }[] = Object.values(saved).map((s) => {
      const live = current?.get(s.id);
      return { job: live ?? s, closed: current ? !live : false };
    });
    return jobs.sort((a, b) => Number(a.closed) - Number(b.closed) || jobDate(b.job).localeCompare(jobDate(a.job)));
  }, [saved, current]);

  return (
    <div className="max-w-4xl pt-10 lg:pt-12">
      <h1 className="text-[44px] leading-[0.96] font-semibold tracking-[-0.05em] sm:text-[56px]">
        Your <span className="font-serif text-[1.12em] font-normal tracking-[-0.02em] text-orange-text">saved</span> jobs.
      </h1>
      <p className="mt-4 max-w-md text-[17px] leading-snug text-muted">
        {count > 0
          ? `${count} job${count === 1 ? "" : "s"} kept for later, stored in this browser only.`
          : "Jobs you save show up here. They're stored in this browser only."}
      </p>

      <div className="mt-10">
        {state.status === "loading" && count > 0 ? (
          <LoadingList count={Math.min(count, 4)} />
        ) : count === 0 ? (
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
          <ol className="border-b-[1.5px] border-rule">
            {list.map(({ job, closed }) => (
              <JobRow
                key={job.id}
                job={job}
                open={open === job.id}
                onToggle={(id) => setOpen((o) => (o === id ? null : id))}
                saved
                onToggleSave={toggle}
                closed={closed}
              />
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
