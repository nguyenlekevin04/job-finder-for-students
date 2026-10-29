"use client";

import { useState } from "react";
import { HOURS_LIMIT, withinHours, type Filters, type Sort } from "@/lib/filters";
import { ALL_FIELDS, ALL_TYPES, FIELD_LABELS, TYPE_LABELS, type Job } from "@/lib/types";

interface Props {
  filters: Filters;
  jobs: Job[]; // all jobs, for the type counts
  onChange: (patch: Partial<Filters>) => void;
  onReset: () => void;
  activeCount: number;
}

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={title} className="mt-5">
      <h3 className="mb-1.5 text-xs font-medium text-muted">{title}</h3>
      <div className="flex flex-wrap gap-x-[18px] gap-y-3 text-[15px] lg:gap-y-1.5 font-semibold tracking-[-0.02em]">{children}</div>
    </div>
  );
}

function Option({ on, onClick, count, children }: { on: boolean; onClick: () => void; count?: number; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`focus-ring hit rounded-sm border-b-2 pb-0.5 transition ${
        on ? "border-orange text-ink" : "border-transparent text-muted hover:text-ink"
      } ${count === 0 && !on ? "opacity-50" : ""}`}
    >
      {children}
      {count !== undefined && <sup className="ml-0.5 text-[10px] font-medium tabular-nums">{count}</sup>}
    </button>
  );
}

export function FilterGroups({ filters, jobs, onChange, onReset, activeCount }: Props) {
  // Only the type row shows until "More filters" is opened. It opens by itself when one
  // of its filters is active (e.g. from a shared link) and then stays open, so an active
  // filter is never hidden and the panel doesn't jump. "Fresh" is left out: the ticket
  // in the list already shows that state.
  const [more, setMore] = useState(false);
  const moreActive = filters.fields.length > 0 || filters.english || !filters.remote || filters.hours;
  if (moreActive && !more) setMore(true);
  const count = (pred: (j: Job) => boolean) => jobs.filter(pred).length;

  return (
    <div className="mt-2">
      <Group title="Type">
        <Option on={filters.types.length === 0} onClick={() => onChange({ types: [] })} count={jobs.length}>
          All
        </Option>
        {ALL_TYPES.map((t) => (
          <Option
            key={t}
            on={filters.types.includes(t)}
            onClick={() => onChange({ types: toggle(filters.types, t) })}
            count={count((j) => j.types.includes(t))}
          >
            {TYPE_LABELS[t]}
          </Option>
        ))}
      </Group>

      <div className={more ? "block" : "hidden"}>
        <Group title="Field">
          {ALL_FIELDS.map((f) => (
            <Option
              key={f}
              on={filters.fields.includes(f)}
              onClick={() => onChange({ fields: toggle(filters.fields, f) })}
            >
              {FIELD_LABELS[f]}
            </Option>
          ))}
        </Group>

        <Group title="Options">
          <Option on={filters.hours} onClick={() => onChange({ hours: !filters.hours })} count={count(withinHours)}>
            Up to {HOURS_LIMIT} h/week
          </Option>
          <Option on={filters.remote} onClick={() => onChange({ remote: !filters.remote })}>
            Include remote
          </Option>
          <Option on={filters.english} onClick={() => onChange({ english: !filters.english })}>
            English-friendly
          </Option>
          <Option on={filters.fresh} onClick={() => onChange({ fresh: !filters.fresh })}>
            Fresh this week
          </Option>
        </Group>
        {/* Always present, so screen readers announce the note when the filter turns on. */}
        <p aria-live="polite" className={filters.hours ? "mt-2 text-xs text-muted" : "sr-only"}>
          {filters.hours ? "Only jobs that state their hours." : ""}
        </p>
      </div>

      <div className="mt-5 flex gap-5 text-sm">
        {!(more && moreActive) && (
          <button type="button" onClick={() => setMore((m) => !m)} aria-expanded={more} className="focus-ring hit link-u rounded">
            {more ? "Fewer filters" : "More filters"}
          </button>
        )}
        {activeCount > 0 && (
          <button type="button" onClick={onReset} className="focus-ring hit link-u rounded">
            Clear {activeCount} filter{activeCount === 1 ? "" : "s"}
          </button>
        )}
      </div>
    </div>
  );
}

export function SortSelect({ value, onChange }: { value: Sort; onChange: (s: Sort) => void }) {
  return (
    <label className="flex items-center gap-1.5">
      <span className="sr-only">Sort jobs</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Sort)}
        className="focus-ring min-h-10 cursor-pointer rounded bg-transparent pr-1 text-right text-muted hover:text-ink"
      >
        <option value="newest">Sorted by newest</option>
        <option value="company">Sorted by company</option>
      </select>
    </label>
  );
}
