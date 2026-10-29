// "Fresh this week" card, styled like a ticket with a tear-off stub.

function isoWeek(d: Date): number {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const yearStart = Date.UTC(t.getUTCFullYear(), 0, 1);
  return Math.ceil(((t.getTime() - yearStart) / 86_400_000 + 1) / 7);
}

export function NewTicket({ count, active, onToggle }: { count: number; active: boolean; onToggle: () => void }) {
  return (
    <div className="relative mb-7 grid grid-cols-[minmax(0,1fr)_auto] overflow-hidden rounded-[14px] bg-sage text-sage-ink">
      <div className="px-5 py-4 sm:px-6 sm:py-5">
        <p className="text-xs font-semibold opacity-80">Fresh this week</p>
        <p className="mt-1 text-[34px] leading-none font-semibold tracking-[-0.045em] sm:text-[40px]">
          {count} new <span className="font-serif text-[1.1em] font-normal tracking-[-0.01em]">{count === 1 ? "job" : "jobs"}</span>
        </p>
      </div>
      <div className="flex w-[124px] flex-col items-end justify-between border-l-2 border-dashed border-sage-ink/30 px-4 py-4 text-xs font-semibold sm:w-[150px] sm:px-5 sm:py-5">
        <span className="tabular-nums">Week {isoWeek(new Date())}</span>
        <button type="button" onClick={onToggle} aria-pressed={active} className="focus-ring rounded text-right underline decoration-2 underline-offset-4">
          {active ? "Show all →" : "Show them →"}
        </button>
      </div>
      {/* punched notches where the stub tears off */}
      <span aria-hidden className="absolute -top-[9px] right-[115px] size-[18px] rounded-full bg-canvas sm:right-[141px]" />
      <span aria-hidden className="absolute -bottom-[9px] right-[115px] size-[18px] rounded-full bg-canvas sm:right-[141px]" />
    </div>
  );
}
