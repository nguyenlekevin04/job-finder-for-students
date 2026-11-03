"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { track } from "@/lib/analytics";
import type { Filters } from "@/lib/filters";
import { digestJobs, digestText } from "@/lib/share";
import type { Job } from "@/lib/types";

const noSubscribe = () => () => {};
// Native share sheet only on touch devices (straight into WhatsApp); elsewhere copy the text.
const canNativeShare = () => typeof navigator.share === "function" && matchMedia("(pointer: coarse)").matches;

/** "Share this week's jobs": the new jobs on this board and filters as text for a course group. */
export function DigestButton({ jobs, filters }: { jobs: Job[]; filters: Filters }) {
  const native = useSyncExternalStore(noSubscribe, canNativeShare, () => false);
  const [status, setStatus] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);

  const count = digestJobs(jobs).length;
  if (count === 0) return null;

  const show = (msg: string) => {
    clearTimeout(timer.current);
    setStatus(msg);
    timer.current = setTimeout(() => setStatus(""), 2500);
  };

  const share = async () => {
    const text = digestText(jobs, filters, `${location.origin}${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}`);
    track("share_digest");
    if (native) {
      try {
        await navigator.share({ text });
        return;
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(text);
      show("Copied, paste it into your group chat");
    } catch {
      show("Couldn't copy");
    }
  };

  return (
    <p className="mt-5 text-[15px]">
      <span className="text-muted">Know someone looking? </span>
      <button
        type="button"
        onClick={share}
        className="focus-ring hit link-u rounded font-semibold"
        title={`The ${count} newest jobs from this week as a short text with links, for WhatsApp, Discord or Telegram`}
      >
        {native ? "Share this week's jobs" : "Copy this week's jobs"}
      </button>
      <span role="status" className={status ? "ml-2 text-muted" : "sr-only"}>
        {status}
      </span>
    </p>
  );
}
