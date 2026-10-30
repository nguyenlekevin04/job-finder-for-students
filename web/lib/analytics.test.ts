import { describe, expect, it } from "vitest";
import { filterEvents } from "./analytics";
import { DEFAULT_FILTERS, type Filters } from "./filters";

const f = (patch: Partial<Filters>): Filters => ({ ...DEFAULT_FILTERS, ...patch });

describe("filterEvents", () => {
  it("counts only filters that were turned on", () => {
    expect(filterEvents(DEFAULT_FILTERS, f({ types: ["werkstudent"], english: true }))).toEqual([
      { name: "type", value: "werkstudent" },
      { name: "english" },
    ]);
    expect(filterEvents(f({ types: ["werkstudent"], english: true }), DEFAULT_FILTERS)).toEqual([]);
  });

  it("counts a new value next to an existing one once", () => {
    expect(filterEvents(f({ types: ["thesis"] }), f({ types: ["thesis", "internship"] }))).toEqual([
      { name: "type", value: "internship" },
    ]);
  });

  it("never sends the search text, and counts a search once", () => {
    const events = filterEvents(DEFAULT_FILTERS, f({ q: "max mustermann" }));
    expect(events).toEqual([{ name: "search" }]);
    expect(JSON.stringify(events)).not.toContain("mustermann");
    expect(filterEvents(f({ q: "py" }), f({ q: "python" }))).toEqual([]);
  });

  it("ignores opening a job", () => {
    expect(filterEvents(DEFAULT_FILTERS, f({ job: "abc" }))).toEqual([]);
  });

  it("counts remote off, sort and the other toggles", () => {
    expect(
      filterEvents(DEFAULT_FILTERS, f({ remote: false, fresh: true, hours: true, since: "2026-10-01", sort: "company" })),
    ).toEqual([
      { name: "no-remote" },
      { name: "new-this-week" },
      { name: "hours" },
      { name: "since-last-visit" },
      { name: "sort", value: "company" },
    ]);
  });
});
