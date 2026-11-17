import { describe, expect, it } from "vitest";
import { within } from "./prefs";

describe("within", () => {
  const now = new Date("2026-11-17T12:00:00Z");
  it("is true only for a stored day less than N days ago", () => {
    expect(within("2026-11-17", 30, now)).toBe(true);
    expect(within("2026-10-20", 30, now)).toBe(true);
    expect(within("2026-10-18", 30, now)).toBe(false);
    expect(within("2026-12-01", 30, now)).toBe(false); // in the future: ignore
  });
  it("ignores missing or broken values", () => {
    expect(within(null, 30, now)).toBe(false);
    expect(within("soon", 30, now)).toBe(false);
  });
});
