import { describe, expect, it } from "vitest";
import { fold, makeIndex, search } from "./search";
import type { Job } from "./types";

const job = (id: string, title: string, fields: Job["fields"] = [], snippet = ""): Job =>
  ({ id, title, company: "ACME", location: "Dresden", snippet, fields, types: ["werkstudent"], links: [] }) as unknown as Job;

const jobs = [
  job("ml", "Werkstudent Machine Learning", ["ai"]),
  job("ki", "Werkstudent KI-Anwendungen", ["ai"], "Wir bauen KI für die Fertigung."),
  job("llm", "Research Intern (Multimodal LLM)", ["ai"]),
  job("tagged", "Working Student Virtual Metrology", ["ai"]),
  job("web", "Werkstudent HTML und CSS", ["software"]),
  job("inf", "Praktikum Informatik", ["software"]),
  job("cs", "Thesis in Computer Science", ["software"]),
  job("kuenstl", "Masterarbeit Künstliche Intelligenz", ["ai"]),
];
const index = makeIndex(jobs);
const find = (q: string) => [...search(jobs, q, index)].sort();

describe("search", () => {
  it("folds umlauts so ä and ae are the same", () => {
    expect(fold("Künstliche  Intelligenz")).toBe("kuenstliche intelligenz");
    expect(find("kuenstliche intelligenz")).toEqual(find("künstliche intelligenz"));
  });

  it("treats ML, KI, AI, LLM and machine learning as one group", () => {
    const ai = ["ki", "kuenstl", "llm", "ml", "tagged"];
    for (const q of ["machine learning", "ML", "ki", "AI", "LLM", "deep learning"]) expect(find(q)).toEqual(ai);
  });

  it("finds at least everything the AI/ML filter finds", () => {
    const filter = jobs.filter((j) => j.fields.includes("ai")).map((j) => j.id);
    const hits = find("machine learning");
    expect(filter.every((id) => hits.includes(id))).toBe(true);
  });

  it("matches short terms as whole words only", () => {
    expect(find("ml")).not.toContain("web"); // "HTML"
  });

  it("pairs German and English terms", () => {
    expect(find("informatik")).toEqual(["cs", "inf"]);
    expect(find("computer science")).toEqual(["cs", "inf"]);
  });

  it("still finds plain words and typos", () => {
    expect(find("metrology")).toEqual(["tagged"]);
    expect(find("metrolgy")).toEqual(["tagged"]);
  });

  it("finds word starts while typing short queries", () => {
    expect(find("Dre").length).toBe(jobs.length); // every job is in Dresden
    expect(find("metr")).toEqual(["tagged"]);
    expect(find("inf")).toEqual(["inf"]);
  });
});
