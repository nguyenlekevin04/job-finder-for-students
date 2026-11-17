"use client";

import { useState } from "react";
import { track } from "@/lib/analytics";
import { promptInstall, useInstallKind } from "@/lib/install";
import { getPref, setPref, within } from "@/lib/prefs";

/** "Not now" hides the offer for this many days. */
export const INSTALL_SNOOZE_DAYS = 30;
const KEY = "dsj:install:v1"; // the day "Not now" was tapped

/**
 * "Add to home screen", shown to students who came back or saved a job (never on a first load).
 * Chrome/Android get the browser's install dialog; iPhone gets the two taps, because alerts
 * only work there from the home screen.
 */
export function InstallOffer({ eligible }: { eligible: boolean }) {
  const kind = useInstallKind();
  const [hidden, setHidden] = useState(() => typeof window !== "undefined" && within(getPref(KEY), INSTALL_SNOOZE_DAYS));
  if (!eligible || !kind || hidden) return null;

  const snooze = () => {
    setPref(KEY, new Date().toISOString().slice(0, 10));
    setHidden(true);
  };

  return (
    <div className="mb-4 flex flex-wrap items-baseline gap-x-4 gap-y-1 border-l-2 border-orange pl-3 text-sm" data-testid="install-offer">
      {kind === "prompt" ? (
        <>
          <span>Keep the board on your home screen: it opens like an app and can send job alerts.</span>
          <button
            type="button"
            onClick={async () => {
              track("install_offer");
              if (await promptInstall()) setHidden(true);
            }}
            className="focus-ring hit link-u rounded font-semibold"
          >
            Add to home screen
          </button>
        </>
      ) : (
        <span>
          Add the board to your home screen: tap <b className="font-semibold">Share</b>, then{" "}
          <b className="font-semibold">Add to Home Screen</b>. On iPhone that’s needed for job alerts.
        </span>
      )}
      <button type="button" onClick={snooze} className="focus-ring hit link-u rounded text-muted hover:text-ink">
        Not now
      </button>
    </div>
  );
}
