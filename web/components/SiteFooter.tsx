"use client";

import { useJobsFile } from "@/lib/useJobs";

const SOURCE_LINKS: Record<string, string> = {
  Arbeitsagentur: "https://www.arbeitsagentur.de/jobsuche/",
  Arbeitnow: "https://www.arbeitnow.com/",
  Adzuna: "https://www.adzuna.de/",
  "TU Dresden": "https://tu-dresden.de/tu-dresden/arbeiten-an-der-tud/stellenangebote",
  Fraunhofer: "https://jobs.fraunhofer.de/",
  HZDR: "https://www.hzdr.de/db/Cms?pNid=490",
};

export function SiteFooter() {
  const { state } = useJobsFile();
  const sources = state.status === "ready" ? state.data.sources : null;

  return (
    <footer className="border-t border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto max-w-6xl space-y-3 px-4 py-8 text-sm text-zinc-500 sm:px-6 dark:text-zinc-400">
        <p className="font-medium text-zinc-700 dark:text-zinc-300">Data sources</p>
        <ul className="flex flex-wrap gap-x-5 gap-y-2">
          {Object.entries(SOURCE_LINKS).map(([name, url]) => {
            const s = sources?.[name];
            const dot = !s ? "bg-zinc-300 dark:bg-zinc-700" : s.ok ? "bg-emerald-500" : s.skipped ? "bg-zinc-400" : "bg-red-500";
            const title = !s ? "" : s.ok ? `${s.count} postings checked` : s.skipped ? "Not enabled" : `Failed last run: ${s.error ?? ""}`;
            return (
              <li key={name} className="flex items-center gap-2" title={title}>
                <span className={`size-1.5 rounded-full ${dot}`} />
                <a href={url} target="_blank" rel="noreferrer" className="hover:text-zinc-900 hover:underline dark:hover:text-zinc-100">
                  {name}
                </a>
              </li>
            );
          })}
        </ul>
        <p className="max-w-2xl text-xs leading-relaxed">
          Postings are collected automatically every morning and filtered by keywords, so a few may be off. Always check
          the original posting before applying. Remote jobs come from <a className="underline" href="https://www.arbeitnow.com/" target="_blank" rel="noreferrer">Arbeitnow</a>{" "}
          and Adzuna. Bookmarks are stored only in this browser.
        </p>
      </div>
    </footer>
  );
}
