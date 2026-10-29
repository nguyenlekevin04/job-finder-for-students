// The one place for "new", styled like a ticket with a tear-off stub. Two modes:
// - `since` unset: "Fresh this week", jobs first seen in the last 7 days.
// - `since` set ("YYYY-MM-DD"): "Welcome back", jobs first seen after your last visit.

import { NEW_DAYS, visitDayLabel } from "@/lib/format";

interface Props {
  count: number;
  active: boolean;
  onToggle: () => void;
  since?: string | null;
}

export function NewTicket({ count, active, onToggle, since }: Props) {
  return (
    <div className="relative mb-7 grid grid-cols-[minmax(0,1fr)_auto] overflow-hidden rounded-[14px] bg-sage text-sage-ink">
      <div className="px-5 py-4 sm:px-6 sm:py-5">
        <p className="text-xs font-semibold opacity-80">{since ? "Welcome back" : "Fresh this week"}</p>
        <p className="mt-1 text-[34px] leading-none font-semibold tracking-[-0.045em] sm:text-[40px]">
          {count} new <span className="font-serif text-[1.1em] font-normal tracking-[-0.01em]">{count === 1 ? "job" : "jobs"}</span>
        </p>
      </div>
      <div className="flex w-[124px] flex-col items-end justify-between gap-2 border-l-2 border-dashed border-sage-ink/30 px-4 py-4 text-right text-xs font-semibold sm:w-[150px] sm:px-5 sm:py-5">
        <span className="tabular-nums">{since ? `Since ${visitDayLabel(since)}` : `Last ${NEW_DAYS} days`}</span>
        <button type="button" onClick={onToggle} aria-pressed={active} className="focus-ring hit rounded text-right underline decoration-2 underline-offset-4">
          {/* no-break space: the arrow wraps with its word, not alone in the narrow stub */}
          {active ? "Show all →" : "Show only new →"}
        </button>
      </div>
      {/* punched notches where the stub tears off */}
      <span aria-hidden className="absolute -top-[9px] right-[115px] size-[18px] rounded-full bg-canvas sm:right-[141px]" />
      <span aria-hidden className="absolute -bottom-[9px] right-[115px] size-[18px] rounded-full bg-canvas sm:right-[141px]" />
    </div>
  );
}
