import type { Job } from "./types";

// A one-day calendar entry for a job's application deadline, built in the browser.
// RFC 5545: CRLF line ends, escaped text, all-day DTSTART/DTEND (end is exclusive).
const esc = (s: string) => s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
const day = (iso: string) => iso.replace(/-/g, "");

function nextDay(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

export function deadlineIcs(job: Job, now = new Date()): string | null {
  if (!job.deadline || !/^\d{4}-\d{2}-\d{2}$/.test(job.deadline)) return null;
  const stamp = now.toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
  const link = job.links[0]?.url ?? "";
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//dresden-jobs//deadline//EN",
    "BEGIN:VEVENT",
    `UID:${job.id}-deadline@dresden-jobs`,
    `DTSTAMP:${stamp}`,
    `DTSTART;VALUE=DATE:${day(job.deadline)}`,
    `DTEND;VALUE=DATE:${day(nextDay(job.deadline))}`,
    `SUMMARY:${esc(`Apply by today: ${job.title} (${job.company})`)}`,
    `DESCRIPTION:${esc(link)}`,
    "BEGIN:VALARM",
    "TRIGGER:-P2D",
    "ACTION:DISPLAY",
    `DESCRIPTION:${esc(`Deadline in 2 days: ${job.title}`)}`,
    "END:VALARM",
    "END:VEVENT",
    "END:VCALENDAR",
    "",
  ].join("\r\n");
}
