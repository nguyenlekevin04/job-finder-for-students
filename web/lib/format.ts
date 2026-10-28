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

export function isNew(firstSeen: string, withinDays = 3): boolean {
  return daysBetween(firstSeen) <= withinDays;
}

export function daysUntil(isoDay: string): number {
  return -daysBetween(isoDay);
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
