import { isNew } from "./format";
import { boardPath, filtersToParams, type Filters } from "./filters";
import { BOARD_LABELS, FIELD_LABELS, TYPE_LABELS, type Job } from "./types";

/** A posting written in German: not marked English-friendly, and not one that says no German is needed. */
export function isGermanPosting(job: Job): boolean {
  return !job.englishFriendly && job.germanLevel !== "none";
}

/** The original posting through Google Translate (German → English). No API, nothing sent until clicked. */
export function translateUrl(url: string): string {
  return `https://translate.google.com/translate?sl=de&tl=en&u=${encodeURIComponent(url)}`;
}

export const DIGEST_MAX = 10;

/** The jobs worth posting in a group: new this week, newest first, at most DIGEST_MAX. */
export function digestJobs(jobs: Job[]): Job[] {
  return jobs
    .filter((j) => isNew(j.firstSeen))
    .sort((a, b) => b.firstSeen.localeCompare(a.firstSeen))
    .slice(0, DIGEST_MAX);
}

/**
 * This week's new jobs for the current board and filters, as plain text for WhatsApp, Discord or Telegram.
 * Links point to our board (one job each, plus the filtered board), with no tracking parameters.
 * The search text isn't included: it may be personal.
 */
export function digestText(jobs: Job[], filters: Filters, origin: string): string {
  const picked = digestJobs(jobs);
  const where = filters.city === "remote" ? "remote" : `in ${BOARD_LABELS[filters.city]}`;
  const what = [...filters.types.map((t) => TYPE_LABELS[t]), ...filters.fields.map((f) => FIELD_LABELS[f])].join(", ");
  const params = filtersToParams({ ...filters, q: "", job: null, fresh: true, since: null }, filters.city);
  const boardUrl = `${origin}${boardPath(filters.city)}?${params}`;
  const lines = [
    `New student tech jobs ${where} this week${what ? ` (${what})` : ""}:`,
    "",
    ...picked.flatMap((j) => [`• ${j.title} – ${j.company}`, `  ${origin}/?job=${encodeURIComponent(j.id)}`]),
    "",
    `All new jobs: ${boardUrl}`,
  ];
  return lines.join("\n");
}
