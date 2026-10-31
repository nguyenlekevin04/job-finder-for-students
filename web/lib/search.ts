// Job search: fuzzy matching (Fuse) plus synonym groups, so "ML", "KI", "machine learning"
// and "LLM" find each other, German/English pairs match, and ä/ae are the same letter.
// Search text never leaves the browser (it isn't sent to analytics).
import Fuse from "fuse.js";
import type { Field, Job } from "./types";

/** Lowercase, umlauts and ß spelled out, other accents removed: "Künstliche" -> "kuenstliche". */
export function fold(s: string): string {
  return s
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

interface Group {
  terms: string[];
  /** Jobs tagged with this field also match, so a search finds what the filter finds. */
  field?: Field;
}

// Searching any term finds every term of its group. Keep terms lowercase; fold() runs on them.
export const SYNONYMS: Group[] = [
  {
    field: "ai",
    terms: [
      "ai", "ki", "ml", "machine learning", "maschinelles lernen", "kuenstliche intelligenz",
      "artificial intelligence", "deep learning", "llm", "llms", "large language model", "genai",
      "generative ai", "neural network", "neuronale netze", "nlp", "computer vision",
    ],
  },
  { terms: ["informatik", "computer science", "cs"] },
  { terms: ["datenanalyse", "data analysis", "data analytics", "datenanalyst", "data analyst"] },
  { terms: ["softwareentwicklung", "software development", "software engineering", "software engineer"] },
  { terms: ["entwickler", "developer", "entwicklung", "development"] },
  { terms: ["embedded", "eingebettete systeme", "firmware"] },
  { terms: ["werkstudent", "working student"] },
  { terms: ["praktikum", "internship", "intern", "praktikant"] },
  { terms: ["abschlussarbeit", "thesis", "masterarbeit", "bachelorarbeit", "master thesis", "bachelor thesis"] },
  { terms: ["it-sicherheit", "it sicherheit", "cyber security", "cybersecurity", "security"] },
  { terms: ["datenbank", "database", "sql"] },
];

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
/** Whole-word match on folded text ("ml" must not hit "html"). */
const wordRe = (term: string) => new RegExp(`(^|[^a-z0-9])${escape(fold(term))}($|[^a-z0-9])`);
const prefixRe = (term: string) => new RegExp(`(^|[^a-z0-9])${escape(fold(term))}`);

export interface SearchIndex {
  fuse: Fuse<Job>;
  text: Map<string, string>; // job id -> folded title, company, snippet and location
}

export function makeIndex(jobs: Job[]): SearchIndex {
  const fuse = new Fuse(jobs, {
    keys: [
      { name: "title", weight: 3 },
      { name: "company", weight: 2 },
      { name: "snippet", weight: 1 },
      { name: "location", weight: 0.5 },
    ],
    threshold: 0.35,
    ignoreLocation: true,
    minMatchCharLength: 2,
  });
  const text = new Map(jobs.map((j) => [j.id, fold(`${j.title} ${j.company} ${j.snippet} ${j.location}`)]));
  return { fuse, text };
}

/** Ids of the jobs that match the search. */
export function search(jobs: Job[], q: string, index: SearchIndex): Set<string> {
  const query = fold(q);
  const hits = new Set<string>();
  if (!query) return hits;

  const group = SYNONYMS.find((g) => g.terms.some((t) => fold(t) === query));
  // Synonym terms match whole words ("ml" must not hit "html"); anything else also matches the
  // start of a word, so typing "Dre" or "pyt" already finds Dresden and Python.
  const res = group ? group.terms.map(wordRe) : [prefixRe(query)];
  for (const j of jobs) {
    const text = index.text.get(j.id) ?? "";
    if (res.some((re) => re.test(text)) || (group?.field && j.fields.includes(group.field))) hits.add(j.id);
  }
  // Fuzzy matching catches typos and partial words. Short queries ("ml", "ki") stay exact,
  // or they would match half the board.
  if (query.length > 3) for (const r of index.fuse.search(q)) hits.add(r.item.id);
  return hits;
}
