"use client";

import { track } from "@/lib/analytics";
import { jobDate } from "@/lib/filters";
import { daysUntil, formatDate, isNew, jobTerms, relativeDay } from "@/lib/format";
import { FIELD_LABELS, TYPE_LABELS, type Job } from "@/lib/types";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { ArrowUpRightIcon, StarIcon } from "./Icons";

interface Props {
  job: Job;
  open: boolean;
  onToggle: (id: string) => void;
  saved: boolean;
  onToggleSave: (job: Job) => void;
  closed?: boolean; // on the Saved page: no longer on the board, so no longer open
  showNew?: boolean; // false when every job is new, so the label would mean nothing
  newSince?: string | null; // "YYYY-MM-DD": "New" means first seen after this day instead of this week
}

function jobPlace(job: Job): string {
  if (!job.remote) return job.location;
  return job.location && !/remote/i.test(job.location) ? `Remote · ${job.location}` : "Remote";
}

export function JobRow({ job, open, onToggle, saved, onToggleSave, closed, showNew = true, newSince }: Props) {
  const fresh = showNew && !closed && (newSince ? job.firstSeen > newSince : isNew(job.firstSeen));
  const primary = job.links[0];
  const deadlineDays = job.deadline ? daysUntil(job.deadline) : null;
  const panelId = `job-${job.id}`;
  const typeLabel = closed ? "Closed" : job.types.map((t) => TYPE_LABELS[t]).join(" / ");
  const terms = jobTerms(job);

  return (
    <li id={`row-${job.id}`} className="scroll-mt-4 border-t-[1.5px] border-rule">
      <button
        type="button"
        onClick={() => onToggle(job.id)}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        className="focus-ring group grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-4 py-[18px] text-left"
      >
        <span className="min-w-0">
          <span
            className={`block text-lg leading-tight font-semibold tracking-[-0.035em] decoration-orange decoration-2 underline-offset-4 group-hover:underline sm:text-[22px] ${
              closed ? "text-muted" : ""
            }`}
          >
            {job.title}
          </span>
          <span className="mt-1.5 block text-[14.5px] text-muted">
            <b className="font-semibold text-ink">{job.company}</b> · {jobPlace(job)} · {relativeDay(jobDate(job))}
          </span>
          {terms.line && (
            <span className="mt-1 hidden text-[13px] font-semibold text-muted tabular-nums sm:block">{terms.line}</span>
          )}
          <span className={`mt-1.5 block text-[13px] font-semibold sm:hidden ${fresh ? "text-orange-text" : "text-muted"}`}>
            {fresh && "New · "}
            {typeLabel}
            {terms.line && <span className="text-muted tabular-nums"> · {terms.line}</span>}
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
        <div id={panelId} className="pb-7">
          {closed && (
            <p className="mb-4 border-l-2 border-rule pl-3 text-sm text-muted">This job is no longer available.</p>
          )}
          <dl className="grid grid-cols-2 gap-x-7 gap-y-3 text-sm sm:flex sm:flex-wrap">
            {terms.hours && <Fact label="Hours">{terms.hours}</Fact>}
            {terms.pay && <Fact label="Pay">{terms.pay}</Fact>}
            <Fact label="Field">{job.fields.map((f) => FIELD_LABELS[f]).join(", ")}</Fact>
            <Fact label="Language">{job.englishFriendly ? "English OK" : "German"}</Fact>
            <Fact label={job.postedAt ? "Posted" : "Found"}>{formatDate(jobDate(job))}</Fact>
            {/* A closed job's deadline means nothing any more. */}
            {!closed && deadlineDays !== null && deadlineDays >= 0 && (
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
            {closed ? (
              <>
                <button
                  type="button"
                  onClick={() => onToggleSave(job)}
                  aria-pressed={saved}
                  className="focus-ring rounded-[10px] bg-btn px-4 py-2.5 text-[15px] font-semibold tracking-[-0.02em] text-btn-ink transition hover:opacity-90"
                >
                  {saved ? "Remove from saved" : "Save for later"}
                </button>
                <a href={primary.url} target="_blank" rel="noreferrer" className="focus-ring hit link-u inline-flex items-center gap-1 rounded">
                  View original posting <ArrowUpRightIcon width={14} height={14} />
                </a>
              </>
            ) : (
              <>
                <a
                  href={primary.url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => track("apply", { source: primary.source })}
                  className="focus-ring inline-flex items-center gap-2 rounded-[10px] bg-btn px-4 py-2.5 text-[15px] font-semibold tracking-[-0.02em] text-btn-ink transition hover:opacity-90"
                >
                  Apply now <ArrowUpRightIcon width={15} height={15} />
                </a>
                <button type="button" onClick={() => onToggleSave(job)} aria-pressed={saved} className="focus-ring hit link-u rounded">
                  {saved ? "Remove from saved" : "Save for later"}
                </button>
                <ShareButton job={job} />
              </>
            )}
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
    <div className="animate-pulse border-t-[1.5px] border-line py-5">
      <div className="h-6 w-2/3 rounded bg-line" />
      <div className="mt-2.5 h-4 w-1/3 rounded bg-line/70" />
    </div>
  );
}

const noSubscribe = () => () => {};
// Native share sheet only on touch devices; desktop share dialogs are clumsy, a copied link is better there.
const canNativeShare = () => typeof navigator.share === "function" && matchMedia("(pointer: coarse)").matches;

/** Link to one job on the board: only ?job=, no filters, no tracking. */
function jobUrl(id: string): string {
  return `${location.origin}${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/?job=${encodeURIComponent(id)}`;
}

function ShareButton({ job }: { job: Job }) {
  const native = useSyncExternalStore(noSubscribe, canNativeShare, () => false);
  // label: the short text on the button; status: the full message for screen readers.
  const [message, setMessage] = useState<{ label: string; status: string } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  const show = (label: string, status: string, ms: number) => {
    clearTimeout(timer.current);
    setMessage({ label, status });
    timer.current = setTimeout(() => setMessage(null), ms);
  };

  const share = async () => {
    const url = jobUrl(job.id);
    if (native) {
      const text = `${job.title} at ${job.company}`;
      try {
        await navigator.share({ title: text, text, url });
        return;
      } catch (e) {
        // AbortError: the user closed the sheet. Anything else (e.g. NotAllowedError):
        // sharing failed, so fall back to copying the link.
        if (e instanceof DOMException && e.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url);
      show("Link copied", "Link copied", 2000);
    } catch {
      show("Copy failed", "Couldn't copy, use the address bar", 4000);
    }
  };

  return (
    <>
      <button type="button" onClick={share} className="focus-ring hit link-u rounded">
        {message?.label ?? (native ? "Share" : "Copy link")}
      </button>
      <span role="status" className="sr-only">
        {message?.status}
      </span>
    </>
  );
}
