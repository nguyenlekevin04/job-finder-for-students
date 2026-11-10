import { describe, expect, it } from "vitest";
import { DEFAULT_FILTERS, makeIndex, type Filters } from "./filters";
import { bestRemoval, otherBoards } from "./suggest";
import type { Job } from "./types";

const job = (id: string, over: Partial<Job> = {}): Job =>
  ({
    id, title: "Werkstudent Software", company: "ACME", location: "", remote: false, type: "werkstudent",
    types: ["werkstudent"], fields: ["software"], englishFriendly: false, postedAt: null, deadline: null,
    firstSeen: "2026-10-01", lastSeen: "2026-11-10", links: [], snippet: "", city: "dresden", ...over,
  }) as Job;
const f = (over: Partial<Filters> = {}): Filters => ({ ...DEFAULT_FILTERS, ...over });

describe("otherBoards", () => {
  const all = [
    job("le1", { city: "leipzig" }),
    job("le2", { city: "leipzig", types: ["thesis"], type: "thesis" }),
    job("dd1", { city: "dresden" }),
    job("rem", { city: "", remote: true }),
    job("be1", { city: "berlin" }),
  ];

  it("suggests nearby boards first, then remote, with counts for the same filters", () => {
    expect(otherBoards(all, f({ city: "chemnitz" }))).toEqual([
      { board: "leipzig", label: "Leipzig", count: 2 },
      { board: "dresden", label: "Dresden", count: 1 },
      { board: "remote", label: "Remote", count: 1 },
    ]);
    expect(otherBoards(all, f({ city: "chemnitz", types: ["thesis"] }))).toEqual([
      { board: "leipzig", label: "Leipzig", count: 1 },
    ]);
  });

  it("never suggests the current board and leaves out empty ones", () => {
    expect(otherBoards(all, f({ city: "leipzig" })).map((s) => s.board)).toEqual(["dresden", "berlin", "remote"]);
    expect(otherBoards([job("x", { city: "leipzig" })], f({ city: "chemnitz" })).map((s) => s.board)).toEqual(["leipzig"]);
  });
});

describe("bestRemoval", () => {
  const board = [
    job("a", { hoursMax: 20 }),
    job("d", { hoursMax: 15 }),
    job("b"),
    job("c", { fields: ["ai"], englishFriendly: true }),
  ];
  const index = makeIndex(board);

  it("names the one filter whose removal shows the most jobs", () => {
    // Without "English-friendly" two jobs within 20 h show; without the hours filter only one.
    const r = bestRemoval(board, f({ hours: true, english: true }), index);
    expect(r).toEqual({ label: "“English-friendly”", patch: { english: false }, count: 2 });
    const r2 = bestRemoval(board, f({ fields: ["data"] }), index);
    expect(r2).toEqual({ label: "“Data”", patch: { fields: [] }, count: 4 });
  });

  it("is null when no single removal helps or nothing is on", () => {
    expect(bestRemoval(board, f(), index)).toBeNull();
    expect(bestRemoval([], f({ hours: true }), null)).toBeNull();
  });
});
