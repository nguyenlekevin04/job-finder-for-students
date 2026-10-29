const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

function daysBetween(isoDay: string, now = new Date()): number {
  const [y, m, d] = isoDay.slice(0, 10).split("-").map(Number);
  const then = Date.UTC(y, m - 1, d);
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((today - then) / 86_400_000);
}

/** "today", "yesterday", "5 days ago", "3 weeks ago", or a date for old ones. */
export function relativeDay(isoDay: string): string {
  const days = daysBetween(isoDay);
  if (days < 0) return dateFmt.format(new Date(isoDay));
  if (days < 7) return rtf.format(-days, "day");
  if (days < 60) return rtf.format(-Math.floor(days / 7), "week");
  return dateFmt.format(new Date(isoDay));
}

/** How long a job counts as "New": today is day 1, so 7 calendar days. */
export const NEW_DAYS = 7;

export function isNew(firstSeen: string, withinDays = NEW_DAYS): boolean {
  return daysBetween(firstSeen) < withinDays;
}

export function daysUntil(isoDay: string): number {
  return 0 - daysBetween(isoDay); // not -x: that gives -0 for today
}

export function formatDate(isoDay: string): string {
  return dateFmt.format(new Date(isoDay));
}

/** "2 hours ago" for the generatedAt timestamp. */
export function relativeTime(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 60) return rtf.format(-Math.max(minutes, 0), "minute");
  const hours = Math.round(minutes / 60);
  if (hours < 48) return rtf.format(-hours, "hour");
  return rtf.format(-Math.round(hours / 24), "day");
}

const weekdayFmt = new Intl.DateTimeFormat("en-GB", { weekday: "long", timeZone: "UTC" });
const dayMonthFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

/** The local calendar date ("YYYY-MM-DD") of an ISO date-time or Date. */
export function localDay(at: string | Date): string {
  const d = typeof at === "string" ? new Date(at) : at;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** The day of the last visit, for "Since …" and "Nothing new since …":
 *  "earlier today", "yesterday", a weekday for 2–6 days ago, else "21 Oct".
 *  An invalid date gives "your last visit" instead of throwing. */
export function visitDayLabel(isoDay: string, now = new Date()): string {
  const date = new Date(`${isoDay.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return "your last visit";
  const days = daysBetween(isoDay, now);
  if (days <= 0) return "earlier today";
  if (days === 1) return "yesterday";
  if (days < 7) return weekdayFmt.format(date);
  return date.getUTCFullYear() === now.getFullYear() ? dayMonthFmt.format(date) : dateFmt.format(date);
}
