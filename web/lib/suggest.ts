// "Never a dead end": when a board shows few or no jobs, point to jobs the student can still take.
import { applyFilters, inCity, makeIndex, type Filters } from "./filters";
import type { SearchIndex } from "./search";
import { BOARD_LABELS, FIELD_LABELS, TYPE_LABELS, type Board, type Job } from "./types";

/** At most this many results and the list counts as short. */
export const FEW_RESULTS = 3;

/** Boards worth suggesting from each board, nearest first. Remote is added for every city. */
export const NEARBY: Record<Board, Board[]> = {
  dresden: ["leipzig", "chemnitz"],
  leipzig: ["dresden", "berlin"],
  chemnitz: ["leipzig", "dresden"],
  berlin: ["leipzig", "dresden"],
  remote: ["berlin", "dresden"],
};

export interface BoardSuggestion {
  board: Board;
  label: string;
  count: number;
}

/** Other boards with jobs for the same filters (search text included), nearest first. */
export function otherBoards(allJobs: Job[], f: Filters): BoardSuggestion[] {
  const boards = [...NEARBY[f.city], ...(f.city === "remote" ? [] : (["remote"] as Board[]))];
  return boards
    .map((board) => {
      const jobs = allJobs.filter((j) => inCity(j, board));
      const count = jobs.length ? applyFilters(jobs, { ...f, city: board, job: null }, makeIndex(jobs)).length : 0;
      return { board, label: BOARD_LABELS[board], count };
    })
    .filter((s) => s.count > 0);
}

export interface Removal {
  label: string; // what to remove, as the filter calls it
  patch: Partial<Filters>;
  count: number; // jobs on this board without it
}

/** Every filter that is on, as a one-tap removal. */
function removals(f: Filters): Omit<Removal, "count">[] {
  const out: Omit<Removal, "count">[] = [];
  if (f.q.trim()) out.push({ label: `the search “${f.q.trim()}”`, patch: { q: "" } });
  for (const t of f.types) out.push({ label: `“${TYPE_LABELS[t]}”`, patch: { types: f.types.filter((x) => x !== t) } });
  for (const x of f.fields) out.push({ label: `“${FIELD_LABELS[x]}”`, patch: { fields: f.fields.filter((y) => y !== x) } });
  if (f.english) out.push({ label: "“English-friendly”", patch: { english: false } });
  if (f.german) out.push({ label: "“German B2 is enough”", patch: { german: false } });
  if (f.hours) out.push({ label: "“Up to 20 h/week”", patch: { hours: false } });
  if (f.fresh) out.push({ label: "“Fresh this week”", patch: { fresh: false } });
  if (f.since) out.push({ label: "“New since your last visit”", patch: { since: null } });
  if (f.company) out.push({ label: `“at ${f.company}”`, patch: { company: null } });
  return out;
}

/** The one filter whose removal shows the most jobs on this board, or null when none helps. */
export function bestRemoval(boardJobs: Job[], f: Filters, index: SearchIndex | null): Removal | null {
  let best: Removal | null = null;
  for (const r of removals(f)) {
    const count = applyFilters(boardJobs, { ...f, ...r.patch, job: null }, index).length;
    if (count > 0 && (!best || count > best.count)) best = { ...r, count };
  }
  return best;
}
