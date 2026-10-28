"use client";

import { daysUntil, formatDate, isNew, relativeDay } from "@/lib/format";
import { jobDate } from "@/lib/filters";
import type { Job } from "@/lib/types";
import { FieldBadge, NewBadge, TypeBadge } from "./Badges";
import { ArrowUpRightIcon, BuildingIcon, CalendarIcon, ClockIcon, GlobeIcon, MapPinIcon, StarIcon } from "./Icons";

interface Props {
  job: Job;
  saved: boolean;
  onToggleSave: (job: Job) => void;
  stale?: boolean; // on the Saved page: no longer in today's data
}

export function JobCard({ job, saved, onToggleSave, stale }: Props) {
  const primary = job.links[0];
  const fresh = !stale && isNew(job.firstSeen);
  const deadlineDays = job.deadline ? daysUntil(job.deadline) : null;

  return (
    <article
      className={`group relative min-w-0 rounded-xl border bg-white p-4 shadow-sm shadow-zinc-900/[0.03] transition hover:border-zinc-300 hover:shadow-md sm:p-5 dark:bg-zinc-900 dark:shadow-none dark:hover:border-zinc-700 ${
        stale ? "border-dashed border-zinc-300 opacity-75 dark:border-zinc-700" : "border-zinc-200 dark:border-zinc-800"
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            {fresh && <NewBadge />}
            {job.types.map((t) => (
              <TypeBadge key={t} type={t} />
            ))}
            {job.fields.map((f) => (
              <FieldBadge key={f} field={f} />
            ))}
          </div>

          <h2 className="text-[15px] leading-snug font-semibold text-zinc-900 sm:text-base dark:text-zinc-50">
            <a
              href={primary.url}
              target="_blank"
              rel="noreferrer"
              className="focus-ring rounded after:absolute after:inset-0 after:rounded-xl hover:text-indigo-600 dark:hover:text-indigo-400"
            >
              {job.title}
            </a>
          </h2>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-zinc-600 dark:text-zinc-400">
            <span className="flex min-w-0 items-center gap-1.5">
              <BuildingIcon className="shrink-0 text-zinc-400" />
              <span className="truncate">{job.company}</span>
            </span>
            <span className="flex items-center gap-1.5">
              {job.remote ? <GlobeIcon className="text-zinc-400" /> : <MapPinIcon className="text-zinc-400" />}
              {job.remote ? `Remote${job.location && job.location !== "Remote" ? ` · ${job.location}` : ""}` : job.location}
            </span>
            {job.englishFriendly && (
              <span className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                EN
              </span>
            )}
          </div>

          {job.snippet && (
            <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">{job.snippet}</p>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-zinc-500 dark:text-zinc-400">
            <span className="flex items-center gap-1.5" title={job.postedAt ? `Posted ${formatDate(job.postedAt)}` : `First seen ${formatDate(job.firstSeen)}`}>
              <ClockIcon width={13} height={13} />
              {job.postedAt ? "Posted" : "Found"} {relativeDay(jobDate(job))}
            </span>
            {deadlineDays !== null && deadlineDays >= 0 && (
              <span className={`flex items-center gap-1.5 ${deadlineDays <= 7 ? "font-medium text-amber-600 dark:text-amber-400" : ""}`}>
                <CalendarIcon width={13} height={13} />
                Apply by {formatDate(job.deadline!)}
              </span>
            )}
            <span className="flex flex-wrap items-center gap-1">
              via
              {job.links.map((l, i) => (
                <a
                  key={l.url}
                  href={l.url}
                  target="_blank"
                  rel="noreferrer"
                  className="relative z-10 font-medium text-zinc-700 hover:text-indigo-600 hover:underline dark:text-zinc-300 dark:hover:text-indigo-400"
                >
                  {l.source}
                  {i < job.links.length - 1 ? "," : ""}
                </a>
              ))}
            </span>
            {stale && <span className="font-medium text-zinc-600 dark:text-zinc-300">No longer listed</span>}
          </div>
        </div>

        <div className="relative z-10 flex shrink-0 flex-col items-end gap-2">
          <button
            type="button"
            onClick={() => onToggleSave(job)}
            aria-pressed={saved}
            aria-label={saved ? "Remove bookmark" : "Bookmark this job"}
            title={saved ? "Remove bookmark" : "Save"}
            className={`focus-ring grid size-9 place-items-center rounded-lg border transition ${
              saved
                ? "border-amber-300 bg-amber-50 text-amber-500 dark:border-amber-500/40 dark:bg-amber-500/10"
                : "border-zinc-200 text-zinc-400 hover:border-zinc-300 hover:text-amber-500 dark:border-zinc-700 dark:hover:border-zinc-600"
            }`}
          >
            <StarIcon width={17} height={17} filled={saved} />
          </button>
          <a
            href={primary.url}
            target="_blank"
            rel="noreferrer"
            className="focus-ring hidden items-center gap-1 rounded-lg bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-600 sm:inline-flex dark:bg-white dark:text-zinc-900 dark:hover:bg-indigo-400"
          >
            Apply <ArrowUpRightIcon width={13} height={13} />
          </a>
        </div>
      </div>
    </article>
  );
}

export function JobCardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-3 flex gap-2">
        <div className="h-5 w-20 rounded bg-zinc-100 dark:bg-zinc-800" />
        <div className="h-5 w-16 rounded bg-zinc-100 dark:bg-zinc-800" />
      </div>
      <div className="h-5 w-2/3 rounded bg-zinc-200 dark:bg-zinc-800" />
      <div className="mt-2 h-4 w-1/3 rounded bg-zinc-100 dark:bg-zinc-800" />
      <div className="mt-4 h-4 w-full rounded bg-zinc-100 dark:bg-zinc-800" />
    </div>
  );
}
