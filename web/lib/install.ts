"use client";

// "Add to home screen": Chrome/Android hand us their install prompt (beforeinstallprompt);
// iPhone has none, so we explain the two taps instead.
import { useSyncExternalStore } from "react";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferred: InstallPromptEvent | null = null;
const listeners = new Set<() => void>();

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault(); // we offer it at a better moment than page load
    deferred = e as InstallPromptEvent;
    listeners.forEach((l) => l());
  });
  window.addEventListener("appinstalled", () => {
    deferred = null;
    listeners.forEach((l) => l());
  });
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

/** Running as an installed app already. */
export function isInstalled(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia?.("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;
}

export function isIos(): boolean {
  return typeof navigator !== "undefined" && /iPhone|iPad|iPod/.test(navigator.userAgent);
}

/** "prompt" (Chrome can install), "ios" (explain Share → Add to Home Screen) or null. */
export function useInstallKind(): "prompt" | "ios" | null {
  return useSyncExternalStore(
    subscribe,
    () => (isInstalled() ? null : deferred ? "prompt" : isIos() ? "ios" : null),
    () => null,
  );
}

/** Shows the browser's install dialog; true when the student installed. */
export async function promptInstall(): Promise<boolean> {
  const e = deferred;
  if (!e) return false;
  deferred = null;
  listeners.forEach((l) => l());
  await e.prompt();
  return (await e.userChoice).outcome === "accepted";
}
