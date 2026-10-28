"use client";

import type { Filters } from "@/lib/filters";
import { ALL_FIELDS, ALL_TYPES, FIELD_LABELS, TYPE_LABELS, type Field, type Job, type JobType } from "@/lib/types";
import { FIELD_DOTS } from "./Badges";

interface Props {
  filters: Filters;
  jobs: Job[]; // all jobs, for the counts next to each option
  sources: string[];
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  activeCount: number;
}

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 text-xs font-semibold tracking-wider text-zinc-500 uppercase dark:text-zinc-400">{title}</legend>
      {children}
    </fieldset>
  );
}

function CheckRow({
  checked,
  onChange,
  label,
  count,
  dot,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  count: number;
  dot?: string;
}) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition select-none ${
        checked
          ? "bg-indigo-50 text-indigo-900 dark:bg-indigo-500/15 dark:text-indigo-100"
          : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800/70"
      } ${count === 0 && !checked ? "opacity-50" : ""}`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="size-4 rounded border-zinc-300 accent-indigo-600 dark:border-zinc-600"
      />
      {dot && <span className={`size-2 rounded-full ${dot}`} />}
      <span className="flex-1">{label}</span>
      <span className="text-xs text-zinc-400 tabular-nums dark:text-zinc-500">{count}</span>
    </label>
  );
}

function Switch({ checked, onChange, label, hint }: { checked: boolean; onChange: () => void; label: string; hint: string }) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-3 rounded-lg px-2 py-1.5 select-none hover:bg-zinc-100 dark:hover:bg-zinc-800/70">
      <span>
        <span className="block text-sm text-zinc-700 dark:text-zinc-300">{label}</span>
        <span className="block text-xs text-zinc-500 dark:text-zinc-400">{hint}</span>
      </span>
      <input type="checkbox" role="switch" checked={checked} onChange={onChange} className="peer sr-only" />
      <span
        aria-hidden
        className="relative mt-0.5 h-5 w-9 shrink-0 rounded-full bg-zinc-300 transition peer-checked:bg-indigo-600 peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-500 peer-focus-visible:ring-offset-2 after:absolute after:top-0.5 after:left-0.5 after:size-4 after:rounded-full after:bg-white after:shadow after:transition peer-checked:after:translate-x-4 dark:bg-zinc-700"
      />
    </label>
  );
}

export function FilterPanel({ filters, jobs, sources, onChange, onReset, activeCount }: Props) {
  const typeCount = (t: JobType) => jobs.filter((j) => j.types.includes(t)).length;
  const fieldCount = (f: Field) => jobs.filter((j) => j.fields.includes(f)).length;
  const sourceCount = (s: string) => jobs.filter((j) => j.links.some((l) => l.source === s)).length;

  return (
    <div className="space-y-6">
      <Section title="Job type">
        {ALL_TYPES.map((t) => (
          <CheckRow
            key={t}
            label={TYPE_LABELS[t]}
            count={typeCount(t)}
            checked={filters.types.includes(t)}
            onChange={() => onChange({ types: toggle(filters.types, t) })}
          />
        ))}
      </Section>

      <Section title="Field">
        {ALL_FIELDS.map((f) => (
          <CheckRow
            key={f}
            label={FIELD_LABELS[f]}
            dot={FIELD_DOTS[f]}
            count={fieldCount(f)}
            checked={filters.fields.includes(f)}
            onChange={() => onChange({ fields: toggle(filters.fields, f) })}
          />
        ))}
      </Section>

      <Section title="Options">
        <Switch
          label="English-friendly only"
          hint="Posting in English or English team"
          checked={filters.english}
          onChange={() => onChange({ english: !filters.english })}
        />
        <Switch
          label="Include remote"
          hint="Fully remote roles in Germany"
          checked={filters.remote}
          onChange={() => onChange({ remote: !filters.remote })}
        />
      </Section>

      {sources.length > 1 && (
        <Section title="Source">
          {sources.map((s) => (
            <CheckRow
              key={s}
              label={s}
              count={sourceCount(s)}
              checked={filters.sources.includes(s)}
              onChange={() => onChange({ sources: toggle(filters.sources, s) })}
            />
          ))}
        </Section>
      )}

      {activeCount > 0 && (
        <button
          type="button"
          onClick={onReset}
          className="focus-ring w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          Clear {activeCount} filter{activeCount === 1 ? "" : "s"}
        </button>
      )}
    </div>
  );
}
