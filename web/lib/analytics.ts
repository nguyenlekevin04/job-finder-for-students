// Cookieless usage counts (Umami Cloud). Off unless NEXT_PUBLIC_UMAMI_WEBSITE_ID is set
// at build time, so local builds, tests and environments without it send nothing.
// Never send personal data or free text: no search terms, no job ids, no query strings.
import type { Filters } from "./filters";

export const UMAMI_WEBSITE_ID = process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID?.trim() || "";
// Our own pinned copy of Umami's tracker (public/vendor/umami.js), so no third-party code runs
// on the site; it only sends counts to gateway.umami.is (allowed in scripts/csp.mjs).
// To update: download https://cloud.umami.is/script.js, read it, and replace the file
// (keep the header comment with the new date and sha256).
export const UMAMI_SCRIPT = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/vendor/umami.js`;
export const ANALYTICS_ON = UMAMI_WEBSITE_ID !== "";

type EventData = Record<string, string>;
type Umami = { track: (name: string, data?: EventData) => void };

export function track(name: string, data?: EventData): void {
  if (!ANALYTICS_ON) return;
  try {
    (window as unknown as { umami?: Umami }).umami?.track(name, data);
  } catch {
    // Blocked or not loaded yet: counting is best effort.
  }
}

/** The filters a user just turned on or changed, as "filter" events. Turning a filter off isn't counted. */
export function filterEvents(prev: Filters, next: Filters): EventData[] {
  const out: EventData[] = [];
  if (next.city !== prev.city) out.push({ name: "city", value: next.city });
  for (const t of next.types) if (!prev.types.includes(t)) out.push({ name: "type", value: t });
  for (const f of next.fields) if (!prev.fields.includes(f)) out.push({ name: "field", value: f });
  if (next.english && !prev.english) out.push({ name: "english" });
  if (next.german && !prev.german) out.push({ name: "german-b2" });
  if (!next.remote && prev.remote) out.push({ name: "no-remote" });
  if (next.fresh && !prev.fresh) out.push({ name: "new-this-week" });
  if (next.hours && !prev.hours) out.push({ name: "hours" });
  if (next.since && next.since !== prev.since) out.push({ name: "since-last-visit" });
  if (next.sort !== prev.sort) out.push({ name: "sort", value: next.sort });
  if (next.q.trim() && !prev.q.trim()) out.push({ name: "search" }); // that a search ran, never the text
  return out;
}
