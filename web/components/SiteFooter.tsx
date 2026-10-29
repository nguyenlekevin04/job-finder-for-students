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

const STEPS = [
  ["Collected every morning", "Job boards, Fraunhofer, HZDR and TU Dresden are checked once a day. A job disappears a week after its last listing."],
  ["Filtered for students", "Only Werkstudent roles, internships and thesis topics in AI, data, software and embedded systems make the cut."],
  ["Saved in your browser", "Bookmarks stay on this device. There's no account and nothing is tracked."],
];

export function SiteFooter() {
  const { state } = useJobsFile();
  const sources = state.status === "ready" ? state.data.sources : null;

  return (
    <footer id="about" className="mx-auto w-full max-w-7xl scroll-mt-6 px-4 sm:px-8 lg:px-10">
      <div className="border-t-[1.5px] border-rule py-12">
        <h2 className="text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">
          How it <span className="font-serif text-[1.1em] tracking-[-0.02em] text-orange-text">works</span>
        </h2>
        <ol className="mt-8 grid gap-8 sm:grid-cols-3">
          {STEPS.map(([title, text], i) => (
            <li key={title}>
              <span className="text-[13px] text-muted tabular-nums">{String(i + 1).padStart(2, "0")}</span>
              <h3 className="mt-1 text-lg font-semibold tracking-[-0.03em]">{title}</h3>
              <p className="mt-1.5 text-[15px] leading-relaxed text-muted">{text}</p>
            </li>
          ))}
        </ol>

        <div className="mt-12 flex flex-col gap-4 border-t border-line pt-6 text-sm text-muted md:flex-row md:items-start md:justify-between">
          <ul className="flex flex-wrap gap-x-5 gap-y-2" aria-label="Data sources">
            {Object.entries(SOURCE_LINKS).map(([name, url]) => {
              const s = sources?.[name];
              const dot = !s ? "bg-line" : s.ok ? "bg-live" : s.skipped ? "bg-muted/50" : "bg-red-500";
              const title = !s ? "" : s.ok ? `${s.count} postings checked` : s.skipped ? "Not enabled" : `Failed last run: ${s.error ?? ""}`;
              return (
                <li key={name} className="flex items-center gap-2" title={title}>
                  <span className={`size-1.5 rounded-full ${dot}`} />
                  <a href={url} target="_blank" rel="noreferrer" className="hover:text-ink hover:underline">
                    {name}
                  </a>
                </li>
              );
            })}
          </ul>
          <p className="max-w-md text-xs leading-relaxed">
            Matched by keywords, so a few may be off. Check the original posting before applying. Remote jobs come from{" "}
            <a className="underline hover:text-ink" href="https://www.arbeitnow.com/" target="_blank" rel="noreferrer">
              Arbeitnow
            </a>{" "}
            and Adzuna.
          </p>
        </div>
      </div>
    </footer>
  );
}
