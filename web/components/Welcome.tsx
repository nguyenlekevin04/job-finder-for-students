"use client";

import { useEffect, useRef, useState } from "react";
import { track } from "@/lib/analytics";
import type { Filters } from "@/lib/filters";
import { setPref } from "@/lib/prefs";
import { ALL_FIELDS, ALL_TYPES, BOARD_LABELS, BOARDS, FIELD_LABELS, TYPE_LABELS, type Board } from "@/lib/types";
import { AlertButton } from "./AlertButton";

/** Set once the setup was finished or skipped; it never comes back. */
export const WELCOME_KEY = "dsj:welcome:v1";

interface Props {
  filters: Filters;
  counts: Record<string, number>; // jobs per board
  onChange: (patch: Partial<Filters>) => void;
  onClose: () => void;
}

const chip =
  "focus-ring hit rounded-full border-[1.5px] border-rule px-3.5 py-1.5 text-[14px] font-semibold hover:border-ink";

/** "Set up your board in 3 taps": looking for, field, city, then the alert offer. Not a modal: skip any time. */
export function Welcome({ filters, counts, onChange, onClose }: Props) {
  const [step, setStep] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const moved = useRef(false);
  useEffect(() => {
    if (moved.current) headingRef.current?.focus(); // keep keyboard users with the card as it changes
  }, [step]);

  const close = (how: "done" | "skip") => {
    setPref(WELCOME_KEY, how);
    track(how === "done" ? "welcome_done" : "welcome_skip");
    onClose();
  };
  const answer = (patch: Partial<Filters>) => {
    onChange(patch);
    moved.current = true;
    setStep((s) => s + 1);
  };

  const steps: { title: string; body: React.ReactNode }[] = [
    {
      title: "What are you looking for?",
      body: (
        <>
          {ALL_TYPES.map((t) => (
            <button key={t} type="button" className={chip} onClick={() => answer({ types: [t] })}>
              {TYPE_LABELS[t]}
            </button>
          ))}
          <button type="button" className={`${chip} text-muted`} onClick={() => answer({ types: [] })}>
            Anything
          </button>
        </>
      ),
    },
    {
      title: "Your field?",
      body: (
        <>
          {ALL_FIELDS.filter((f) => f !== "other").map((f) => (
            <button key={f} type="button" className={chip} onClick={() => answer({ fields: [f] })}>
              {FIELD_LABELS[f]}
            </button>
          ))}
          <button type="button" className={`${chip} text-muted`} onClick={() => answer({ fields: [] })}>
            Any field
          </button>
        </>
      ),
    },
    {
      title: "Which city?",
      body: (
        <>
          {BOARDS.map((b: Board) => (
            <button
              key={b}
              type="button"
              aria-pressed={filters.city === b}
              className={`${chip} ${filters.city === b ? "border-ink" : ""}`}
              onClick={() => answer({ city: b })}
            >
              {BOARD_LABELS[b]} <span className="font-normal text-muted tabular-nums">{counts[b] ?? 0}</span>
            </button>
          ))}
        </>
      ),
    },
    {
      title: "Hear about new jobs like these?",
      body: (
        <div className="w-full">
          <p className="text-[14px] text-muted">One notification a day, only when new jobs match. No account, no email.</p>
          <div className="mt-2 flex flex-wrap items-baseline gap-x-5 gap-y-2">
            <AlertButton filters={filters} />
            <button type="button" onClick={() => close("done")} className="focus-ring hit link-u rounded text-[14px] font-semibold">
              Done, show my jobs
            </button>
          </div>
        </div>
      ),
    },
  ];
  const current = steps[step];

  return (
    <section aria-label="Set up your board" className="mb-6 rounded-[14px] border-[1.5px] border-ink px-5 py-4" data-testid="welcome">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-[13px] text-muted tabular-nums">
          Set up your board · {Math.min(step + 1, 3)} of 3
        </p>
        <button type="button" onClick={() => close("skip")} className="focus-ring hit link-u rounded text-[13px] text-muted hover:text-ink">
          {step === steps.length - 1 ? "Close" : "Skip"}
        </button>
      </div>
      <h2 ref={headingRef} tabIndex={-1} className="focus-ring mt-1 rounded-sm text-xl font-semibold tracking-[-0.03em]">
        {current.title}
      </h2>
      <div className="mt-3 flex flex-wrap gap-2">{current.body}</div>
    </section>
  );
}
