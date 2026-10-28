import { FIELD_LABELS, TYPE_LABELS, type Field, type JobType } from "@/lib/types";

const chip = "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset";

export const TYPE_STYLES: Record<JobType, string> = {
  werkstudent: "bg-indigo-50 text-indigo-700 ring-indigo-600/15 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/25",
  internship: "bg-teal-50 text-teal-700 ring-teal-600/15 dark:bg-teal-500/10 dark:text-teal-300 dark:ring-teal-400/25",
  thesis: "bg-rose-50 text-rose-700 ring-rose-600/15 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/25",
};

export const FIELD_DOTS: Record<Field, string> = {
  ai: "bg-violet-500",
  data: "bg-sky-500",
  software: "bg-emerald-500",
  hardware: "bg-amber-500",
  other: "bg-zinc-400",
};

export function TypeBadge({ type }: { type: JobType }) {
  return <span className={`${chip} ${TYPE_STYLES[type]}`}>{TYPE_LABELS[type]}</span>;
}

export function FieldBadge({ field }: { field: Field }) {
  return (
    <span className={`${chip} gap-1.5 bg-zinc-50 text-zinc-600 ring-zinc-500/15 dark:bg-zinc-800/60 dark:text-zinc-300 dark:ring-zinc-400/15`}>
      <span className={`size-1.5 rounded-full ${FIELD_DOTS[field]}`} />
      {FIELD_LABELS[field]}
    </span>
  );
}

export function NewBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-emerald-500 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white">
      New
    </span>
  );
}
