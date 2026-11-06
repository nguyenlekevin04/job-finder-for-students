import { describe, expect, it } from "vitest";
import { capHidden } from "./useHidden";

describe("capHidden", () => {
  it("keeps the newest entries when there are too many", () => {
    const store = { a: "2026-11-01", b: "2026-11-05", c: "2026-11-03" };
    expect(capHidden(store, 2)).toEqual({ b: "2026-11-05", c: "2026-11-03" });
    expect(capHidden(store, 5)).toBe(store);
  });
});
