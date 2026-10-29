"use client";

import { jobDate } from "@/lib/filters";
import { daysUntil, formatDate, isNew, relativeDay } from "@/lib/format";
import { FIELD_LABELS, TYPE_LABELS, type Job } from "@/lib/types";
import { ArrowUpRightIcon, StarIcon } from "./Icons";

interface Props {
  job: Job;
  index: number;
  open: boolean;
  onToggle: (id: string) => void;
  saved: boolean;
  onToggleSave: (job: Job) => void;
  stale?: boolean; // on the Saved page: no longer in today's data
}

export function jobPlace(job: Job): string {
  if (!job.remote) return job.location;
  return job.location && !/remote/i.test(job.location) ? `Remote · ${job.location}` : "Remote";
}

export function JobRow({ job, index, open, onToggle, saved, onToggleSave, stale }: Props) {
  const fresh = !stale && isNew(job.firstSeen);
  const primary = job.links[0];
  const deadlineDays = job.deadline ? daysUntil(job.deadline) : null;
  const panelId = `job-${job.id}`;
  const typeLabel = job.types.map((t) => TYPE_LABELS[t]).join(" / ");

  return (
    <li id={`row-${job.id}`} className="scroll-mt-4 border-t-[1.5px] border-rule">
      <button
        type="button"
        onClick={() => onToggle(job.id)}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        className="focus-ring group grid w-full grid-cols-[2.25rem_minmax(0,1fr)_auto] gap-x-2 py-[18px] text-left sm:grid-cols-[2.75rem_minmax(0,1fr)_auto]"
      >
        <span className="pt-1.5 text-[13px] text-muted tabular-nums">{String(index + 1).padStart(2, "0")}</span>
        <span className="min-w-0">
          <span
            className={`block text-lg leading-tight font-semibold tracking-[-0.035em] decoration-orange decoration-2 underline-offset-4 group-hover:underline sm:text-[22px] ${
              stale ? "text-muted" : ""
            }`}
          >
            {job.title}
          </span>
          <span className="mt-1.5 block text-[14.5px] text-muted">
            <b className="font-semibold text-ink">{job.company}</b> · {jobPlace(job)} · {relativeDay(jobDate(job))}
          </span>
          <span className={`mt-1.5 block text-[13px] font-semibold sm:hidden ${fresh ? "text-orange-text" : "text-muted"}`}>
            {fresh && "New · "}
            {typeLabel}
          </span>
        </span>
        <span className="flex items-start gap-3.5 pt-1">
          <span className={`hidden text-[13px] font-semibold sm:inline ${fresh ? "text-orange-text" : "text-muted"}`}>
            {fresh && "New · "}
            {typeLabel}
          </span>
          {saved && (
            <span className="mt-[7px] text-orange">
              <StarIcon width={16} height={16} filled />
              <span className="sr-only">Saved</span>
            </span>
          )}
          <span
            aria-hidden
            className={`grid size-[30px] place-items-center rounded-[9px] border-[1.5px] border-ink text-lg leading-none transition ${
              open ? "bg-ink text-canvas" : "group-hover:bg-ink/5"
            }`}
          >
            {open ? "−" : "+"}
          </span>
        </span>
      </button>

      {open && (
        <div id={panelId} className="pb-7 sm:pl-[2.75rem]">
          {stale && (
            <p className="mb-4 rounded-[10px] bg-sage px-3 py-2 text-sm text-sage-ink">
              This job is no longer listed by its sources. It may be filled.
            </p>
          )}
          <dl className="grid grid-cols-2 gap-x-7 gap-y-3 text-sm sm:flex sm:flex-wrap">
            <Fact label="Field">{job.fields.map((f) => FIELD_LABELS[f]).join(", ")}</Fact>
            <Fact label="Language">{job.englishFriendly ? "English OK" : "German"}</Fact>
            <Fact label={job.postedAt ? "Posted" : "Found"}>{formatDate(jobDate(job))}</Fact>
            {deadlineDays !== null && deadlineDays >= 0 && (
              <Fact label="Apply by">
                <span className={deadlineDays <= 7 ? "font-semibold text-orange-text" : ""}>{formatDate(job.deadline!)}</span>
              </Fact>
            )}
            <Fact label="Found on">
              {job.links.map((l, i) => (
                <span key={l.url}>
                  <a href={l.url} target="_blank" rel="noreferrer" className="hover:underline">
                    {l.source}
                  </a>
                  {i < job.links.length - 1 && ", "}
                </span>
              ))}
            </Fact>
          </dl>
          {job.snippet && <p className="mt-4 max-w-[62ch] text-[15px] leading-relaxed">{job.snippet}</p>}
          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
            <a
              href={primary.url}
              target="_blank"
              rel="noreferrer"
              className="focus-ring inline-flex items-center gap-2 rounded-[10px] bg-btn px-4 py-2.5 text-[15px] font-semibold tracking-[-0.02em] text-btn-ink transition hover:opacity-90"
            >
              Apply now <ArrowUpRightIcon width={15} height={15} />
            </a>
            <button type="button" onClick={() => onToggleSave(job)} aria-pressed={saved} className="focus-ring link-u rounded">
              {saved ? "Remove from saved" : "Save for later"}
            </button>
          </div>
        </div>
      )}
    </li>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[12.5px] text-muted">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function JobRowSkeleton() {
  return (
    <div className="animate-pulse border-t-[1.5px] border-line py-5 sm:pl-[2.75rem]">
      <div className="h-6 w-2/3 rounded bg-line" />
      <div className="mt-2.5 h-4 w-1/3 rounded bg-line/70" />
    </div>
  );
}
