import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_FILTERS } from "./filters";
import { DIGEST_MAX, digestJobs, digestText, isGermanPosting, translateUrl } from "./share";
import type { Job } from "./types";

const job = (over: Partial<Job> = {}): Job => ({
  id: "a1", title: "Werkstudent Data", company: "ACME", location: "Dresden", remote: false,
  type: "werkstudent", types: ["werkstudent"], fields: ["data"], englishFriendly: false,
  postedAt: null, deadline: null, firstSeen: "2026-11-02", lastSeen: "2026-11-03",
  links: [{ source: "X", url: "https://x.example/1" }], snippet: "", city: "dresden", ...over,
});

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-11-03T10:00:00"));
});
afterEach(() => vi.useRealTimers());

describe("isGermanPosting", () => {
  it("is true only for German postings that need German", () => {
    expect(isGermanPosting(job())).toBe(true);
    expect(isGermanPosting(job({ englishFriendly: true }))).toBe(false);
    expect(isGermanPosting(job({ germanLevel: "none" }))).toBe(false);
    expect(isGermanPosting(job({ germanLevel: "fluent" }))).toBe(true);
  });
});

describe("translateUrl", () => {
  it("wraps the posting URL for Google Translate", () => {
    expect(translateUrl("https://a.example/job?id=1&x=2")).toBe(
      "https://translate.google.com/translate?sl=de&tl=en&u=https%3A%2F%2Fa.example%2Fjob%3Fid%3D1%26x%3D2",
    );
  });
});

describe("digest", () => {
  it("keeps only this week's jobs, newest first, at most DIGEST_MAX", () => {
    const jobs = [
      job({ id: "old", firstSeen: "2026-10-01" }),
      job({ id: "b", firstSeen: "2026-11-01" }),
      job({ id: "c", firstSeen: "2026-11-03" }),
      ...Array.from({ length: 12 }, (_, i) => job({ id: `n${i}`, firstSeen: "2026-10-30" })),
    ];
    const picked = digestJobs(jobs);
    expect(picked).toHaveLength(DIGEST_MAX);
    expect(picked.map((j) => j.id).slice(0, 2)).toEqual(["c", "b"]);
    expect(picked.some((j) => j.id === "old")).toBe(false);
  });

  it("lists title, company and a job link, then the board link without the search text", () => {
    const text = digestText(
      [job({ id: "a b" })],
      { ...DEFAULT_FILTERS, city: "berlin", q: "my secret", types: ["werkstudent"], fields: ["ai"], job: "x" },
      "https://site.example",
    );
    expect(text).toBe(
      [
        "New student tech jobs in Berlin this week (Werkstudent, AI / ML):",
        "",
        "• Werkstudent Data – ACME",
        "  https://site.example/?job=a%20b",
        "",
        "All new jobs: https://site.example/berlin/?type=werkstudent&field=ai&new=1",
      ].join("\n"),
    );
    expect(text).not.toContain("secret");
  });

  it("says remote for the remote board and has no type line without filters", () => {
    const text = digestText([job()], { ...DEFAULT_FILTERS, city: "remote" }, "https://s.example");
    expect(text.split("\n")[0]).toBe("New student tech jobs remote this week:");
    expect(text).toContain("https://s.example/remote/?new=1");
  });
});
