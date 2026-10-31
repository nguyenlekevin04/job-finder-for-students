import { describe, expect, it } from "vitest";
import { deadlineIcs } from "./ics";
import type { Job } from "./types";

const job = (deadline: string | null) =>
  ({ id: "abc", title: "Werkstudent ML, Vision; R&D", company: "ACME", deadline, links: [{ source: "X", url: "https://x.example/j" }] }) as unknown as Job;

describe("deadlineIcs", () => {
  it("makes an all-day event on the deadline with a reminder", () => {
    const ics = deadlineIcs(job("2026-11-30"), new Date("2026-10-31T10:00:00Z"))!;
    expect(ics).toContain("DTSTART;VALUE=DATE:20261130\r\n");
    expect(ics).toContain("DTEND;VALUE=DATE:20261201\r\n");
    expect(ics).toContain("SUMMARY:Apply by today: Werkstudent ML\\, Vision\\; R&D (ACME)\r\n");
    expect(ics).toContain("TRIGGER:-P2D");
    expect(ics).toContain("DTSTAMP:20261031T100000Z");
  });

  it("needs a deadline", () => {
    expect(deadlineIcs(job(null))).toBeNull();
  });
});
