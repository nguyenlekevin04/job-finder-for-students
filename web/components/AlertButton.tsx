"use client";

import { useEffect, useState } from "react";
import { track } from "@/lib/analytics";
import type { Filters } from "@/lib/filters";
import { currentState, disableAlerts, enableAlerts, needsInstall, pushAvailable, savedAlert, type PushState } from "@/lib/push";
import { BOARD_LABELS, FIELD_LABELS, TYPE_LABELS } from "@/lib/types";

/** What an alert covers: the board, types and fields (not the search text or other options). */
export function alertLabel(f: Filters): string {
  return [BOARD_LABELS[f.city], ...f.types.map((t) => TYPE_LABELS[t]), ...f.fields.map((x) => FIELD_LABELS[x])].join(" · ");
}

/** "Get alerts": one push notification a day when new jobs match this board, type and field. */
export function AlertButton({ filters }: { filters: Filters }) {
  const [state, setState] = useState<PushState | "busy" | "install" | null>(null);
  const [error, setError] = useState("");
  const label = alertLabel(filters);
  const current = savedAlert();

  useEffect(() => {
    // Browser-only checks, so they run after the first render (the page is pre-rendered).
    const check = async (): Promise<PushState | "install"> =>
      pushAvailable() ? currentState() : needsInstall() ? "install" : "unsupported";
    check().then(setState, () => setState("off"));
  }, []);

  if (state === null || state === "unsupported") return null;

  if (state === "install") {
    return (
      <p className="text-xs text-muted">
        For job alerts on iPhone, tap Share → “Add to Home Screen” and open the board from there.
      </p>
    );
  }

  const on = async () => {
    setError("");
    setState("busy");
    try {
      setState(await enableAlerts(filters, label));
      track("alert_on");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't turn on alerts.");
      setState("off");
    }
  };
  const off = async () => {
    setState("busy");
    setState(await disableAlerts().catch(() => "off" as const));
  };

  return (
    <div className="text-[13px]">
      {state === "on" && current === label ? (
        <span>
          <span className="font-semibold text-ink">Alerts on</span> for {label}.{" "}
          <button type="button" onClick={off} className="focus-ring link-u rounded text-muted hover:text-ink">
            Turn off
          </button>
        </span>
      ) : state === "blocked" ? (
        <span className="text-muted">Notifications are blocked for this site in your browser settings.</span>
      ) : (
        <button
          type="button"
          onClick={on}
          disabled={state === "busy"}
          className="focus-ring hit link-u rounded font-semibold text-ink disabled:opacity-60"
          title={`One notification a day when new jobs match: ${label}`}
        >
          {state === "busy" ? "Turning on…" : state === "on" ? `Switch alerts to ${label}` : "Get daily alerts"}
        </button>
      )}
      {error && <p role="alert" className="mt-1 text-xs text-orange-text">{error}</p>}
    </div>
  );
}
