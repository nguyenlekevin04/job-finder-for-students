"use client";

import { useMemo } from "react";
import { track } from "@/lib/analytics";
import type { Filters } from "@/lib/filters";
import type { SearchIndex } from "@/lib/search";
import { bestRemoval, otherBoards } from "@/lib/suggest";
import type { Job } from "@/lib/types";
import { AlertButton } from "./AlertButton";

interface Props {
  allJobs: Job[]; // every board
  boardJobs: Job[]; // this board
  index: SearchIndex | null;
  filters: Filters;
  shown: number; // jobs in the list now
  onChange: (patch: Partial<Filters>) => void;
}

/** Under a short or empty list: other boards with jobs for the same filters, or the filter to drop. */
export function MoreJobs({ allJobs, boardJobs, index, filters, shown, onChange }: Props) {
  const boards = useMemo(() => otherBoards(allJobs, filters), [allJobs, filters]);
  const removal = useMemo(
    () => (shown === 0 ? bestRemoval(boardJobs, filters, index) : null),
    [shown, boardJobs, filters, index],
  );
  const use = (patch: Partial<Filters>) => {
    onChange(patch);
    track("suggestion");
  };

  if (!boards.length && !removal) {
    return shown === 0 ? (
      <div className="mt-5 text-[15px]" data-testid="more-jobs">
        <p className="text-muted">Nothing on the other boards either. Get a notification when one appears:</p>
        <div className="mt-1">
          <AlertButton filters={filters} />
        </div>
      </div>
    ) : null;
  }

  return (
    <div className="mt-5 rounded-[14px] border-[1.5px] border-rule px-5 py-4 text-[15px]" data-testid="more-jobs">
      {removal && (
        <p>
          <button type="button" onClick={() => use(removal.patch)} className="focus-ring hit link-u rounded font-semibold">
            Remove {removal.label}
          </button>{" "}
          <span className="text-muted">
            → {removal.count} {removal.count === 1 ? "job" : "jobs"} here
          </span>
        </p>
      )}
      {boards.length > 0 && (
        <p className={removal ? "mt-2" : ""}>
          <span className="text-muted">{shown === 0 ? "Same search elsewhere:" : "More with the same filters:"} </span>
          {boards.map((s, i) => (
            <span key={s.board}>
              <button type="button" onClick={() => use({ city: s.board, job: null })} className="focus-ring hit link-u rounded font-semibold">
                {s.label} ({s.count})
              </button>
              {i < boards.length - 1 && <span className="text-muted"> · </span>}
            </span>
          ))}
        </p>
      )}
    </div>
  );
}
