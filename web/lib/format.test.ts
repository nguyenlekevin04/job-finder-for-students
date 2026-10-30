import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { daysUntil, formatDate, isNew, jobTerms, localDay, NEW_DAYS, relativeDay, relativeTime, visitDayLabel } from "./format";

describe("jobTerms", () => {
  it("formats every hours shape", () => {
    expect(jobTerms({ hoursMin: 20, hoursMax: 20 }).hours).toBe("20 h/week");
    expect(jobTerms({ hoursMin: 15, hoursMax: 20 }).hours).toBe("15–20 h/week");
    expect(jobTerms({ hoursMax: 20 }).hours).toBe("up to 20 h/week");
    expect(jobTerms({ hoursMin: null, hoursMax: 20 }).hours).toBe("up to 20 h/week");
    expect(jobTerms({ hoursMin: 20 }).hours).toBe("from 20 h/week");
  });

  it("formats pay in English without a trailing .00", () => {
    expect(jobTerms({ payAmount: 15, payUnit: "hour" }).pay).toBe("€15/h");
    expect(jobTerms({ payAmount: 15.5, payUnit: "hour" }).pay).toBe("€15.50/h");
    expect(jobTerms({ payAmount: 1200, payUnit: "month" }).pay).toBe("€1,200/month");
  });

  it("joins the present parts into one line", () => {
    expect(jobTerms({ hoursMin: 15, hoursMax: 20, payAmount: 15, payUnit: "hour" }).line).toBe("15–20 h/week · €15/h");
    expect(jobTerms({ hoursMax: 20 }).line).toBe("up to 20 h/week");
    expect(jobTerms({ payAmount: 1200, payUnit: "month" }).line).toBe("€1,200/month");
  });

  it("shows nothing for missing or incomplete data", () => {
    expect(jobTerms({})).toEqual({});
    expect(jobTerms({ hoursMin: null, hoursMax: null, payAmount: null, payUnit: null })).toEqual({});
    expect(jobTerms({ payAmount: 15 })).toEqual({}); // no unit: don't guess
    expect(jobTerms({ payUnit: "hour" })).toEqual({});
  });
});

describe("date helpers", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 9, 29, 12, 0)); // local noon, 29 Oct 2026
  });
  afterEach(() => vi.useRealTimers());

  it("'New' lasts 7 calendar days, today included", () => {
    expect(NEW_DAYS).toBe(7);
    expect(isNew("2026-10-29")).toBe(true); // today
    expect(isNew("2026-10-23")).toBe(true); // 6 days ago = day 7
    expect(isNew("2026-10-22")).toBe(false); // 7 days ago = day 8
  });

  it("relativeDay reads naturally", () => {
    expect(relativeDay("2026-10-29")).toBe("today");
    expect(relativeDay("2026-10-28")).toBe("yesterday");
    expect(relativeDay("2026-10-24")).toBe("5 days ago");
    expect(relativeDay("2026-10-15")).toBe("2 weeks ago");
    expect(relativeDay("2026-06-01")).toBe("1 Jun 2026");
  });

  it("daysUntil counts forward", () => {
    expect(daysUntil("2026-11-05")).toBe(7);
    expect(daysUntil("2026-10-29")).toBe(0);
  });

  it("formatDate doesn't shift the day with the time zone", () => {
    expect(formatDate("2026-11-12")).toBe("12 Nov 2026");
  });

  it("relativeTime for the last update", () => {
    expect(relativeTime(new Date(Date.now() - 5 * 60_000).toISOString())).toBe("5 minutes ago");
    expect(relativeTime(new Date(Date.now() - 3 * 3_600_000).toISOString())).toBe("3 hours ago");
    expect(relativeTime(new Date(Date.now() - 3 * 86_400_000).toISOString())).toBe("3 days ago");
  });

  it("localDay uses the local calendar date", () => {
    expect(localDay(new Date(2026, 9, 27, 23, 59))).toBe("2026-10-27");
    expect(localDay(new Date(2026, 0, 3, 0, 1).toISOString())).toBe("2026-01-03");
  });

  it("visitDayLabel names the last visit naturally", () => {
    expect(visitDayLabel("2026-10-29")).toBe("earlier today");
    expect(visitDayLabel("2026-10-28")).toBe("yesterday");
    expect(visitDayLabel("2026-10-27")).toBe("Tuesday");
    expect(visitDayLabel("2026-10-23")).toBe("Friday"); // 6 days ago
    expect(visitDayLabel("2026-10-22")).toBe("22 Oct"); // 7 days ago
    expect(visitDayLabel("2025-12-30")).toBe("30 Dec 2025");
  });

  it("visitDayLabel falls back instead of throwing on an invalid date", () => {
    expect(visitDayLabel("2020-13-45")).toBe("your last visit");
    expect(visitDayLabel("garbage")).toBe("your last visit");
  });
});
