"use client";

import Link from "next/link";
import { useMemo } from "react";
import { jobDate } from "@/lib/filters";
import { useBookmarks } from "@/lib/useBookmarks";
import { useJobsFile } from "@/lib/useJobs";
import type { Job } from "@/lib/types";
import { StarIcon } from "./Icons";
import { JobCard } from "./JobCard";
import { EmptyState, LoadingList } from "./States";

export function SavedJobs() {
  const { saved, toggle, count } = useBookmarks();
  const { state } = useJobsFile();
  const current = useMemo(
    () => (state.status === "ready" ? new Map(state.data.jobs.map((j) => [j.id, j])) : null),
    [state],
  );

  // Prefer today's version of a job (fresh dates/links); fall back to the saved copy.
  const list = useMemo(() => {
    const jobs: { job: Job; stale: boolean }[] = Object.values(saved).map((s) => {
      const live = current?.get(s.id);
      return { job: live ?? s, stale: current ? !live : false };
    });
    return jobs.sort((a, b) => Number(a.stale) - Number(b.stale) || jobDate(b.job).localeCompare(jobDate(a.job)));
  }, [saved, current]);

  return (
    <div className="pt-10 sm:pt-14">
      <h1 className="text-3xl font-semibold tracking-tight">Saved jobs</h1>
      <p className="mt-2 text-zinc-600 dark:text-zinc-400">
        {count > 0
          ? `${count} bookmarked job${count === 1 ? "" : "s"}, stored in this browser.`
          : "Jobs you star show up here. They're stored in this browser only."}
      </p>

      <div className="mt-8">
        {state.status === "loading" && count > 0 ? (
          <LoadingList count={Math.min(count, 4)} />
        ) : count === 0 ? (
          <EmptyState title="No saved jobs yet" icon={<StarIcon width={20} height={20} />}>
            <p>Tap the star on any job to keep it here.</p>
            <Link
              href="/"
              className="focus-ring mt-4 inline-flex rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 dark:bg-white dark:text-zinc-900"
            >
              Browse jobs
            </Link>
          </EmptyState>
        ) : (
          <div className="space-y-3">
            {list.map(({ job, stale }) => (
              <JobCard key={job.id} job={job} saved onToggleSave={toggle} stale={stale} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
