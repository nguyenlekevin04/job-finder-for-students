import type { Metadata } from "next";
import Link from "next/link";

// Every rule links an official source. Re-check the numbers each January (minimum wage and the
// minijob limit change then) and update CHECKED.
const CHECKED = "3 Nov 2026";

const OG_IMAGE = { url: "/og.png", width: 1200, height: 630, alt: "dresden/jobs: student tech jobs, updated daily" };
const title = "Can I take this job? Work rules for students in Germany";
const description =
  "Werkstudent, internship, minijob and the 140-day rule for international students, in two minutes, with official sources.";

export const metadata: Metadata = {
  title: "Work rules for students", // layout template adds " · dresden/jobs"
  description,
  alternates: { canonical: "/guide/" },
  openGraph: { type: "article", siteName: "dresden/jobs", title, description, url: "/guide/", images: [OG_IMAGE] },
  twitter: { card: "summary_large_image", title, description, images: [OG_IMAGE.url] },
};

const ext = "focus-ring link-u rounded";

function Source({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <p className="text-[13px] text-muted">
      Source:{" "}
      <a href={href} target="_blank" rel="noreferrer" className={ext}>
        {children}
      </a>
    </p>
  );
}

const SECTIONS: [string, React.ReactNode][] = [
  [
    "EU, EEA or Swiss citizen",
    <>
      <p>
        You can work like any German student. No day limit and no work permit. The Werkstudent and minijob rules below
        still decide what you pay into social insurance.
      </p>
    </>,
  ],
  [
    "International student (non-EU): 140 days a year",
    <>
      <p>
        With a residence permit for studying you may work up to <b>140 full days a year</b>. A day of up to 4 hours counts as
        half a day.
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <b>Werkstudent at up to 20 h/week fits.</b> During the lecture period a week of up to 20 hours counts as 2.5 days,
          however you split the hours. A whole year of that is 130 days.
        </li>
        <li>
          <b>Jobs at your university</b> (student or research assistant, HiWi) don’t count towards the 140 days.
        </li>
        <li>
          <b>Voluntary internships count</b>, even unpaid ones. Whether a <b>mandatory internship</b> from your study
          regulations counts is handled differently by universities, so ask your international office first.
        </li>
        <li>More than that needs approval from the immigration office (Ausländerbehörde).</li>
      </ul>
      <Source href="https://www.gesetze-im-internet.de/aufenthg_2004/__16b.html">§ 16b (3) Residence Act (AufenthG)</Source>
      <Source href="https://www.make-it-in-germany.com/en/study-training/studies-in-germany/work">Make it in Germany (federal government)</Source>
    </>,
  ],
  [
    "Werkstudent: 20 hours in the semester",
    <>
      <p>
        If you work <b>up to 20 hours a week during the lecture period</b>, you pay only pension insurance (no health,
        care or unemployment insurance). More hours are fine on evenings, weekends and in the semester break, but over 20
        hours in no more than 26 weeks a year.
      </p>
      <Source href="https://www.deutsche-rentenversicherung.de/DRV/DE/Experten/Arbeitgeber-und-Steuerberater/summa-summarum/Lexikon/W/werkstudentenprivileg.html">
        Deutsche Rentenversicherung: Werkstudentenprivileg
      </Source>
    </>,
  ],
  [
    "Minijob: up to €603 a month",
    <>
      <p>
        In 2026 a minijob may pay up to <b>€603 a month</b> (tied to the minimum wage of €13.90/h). Above that it’s a
        regular job, or a Werkstudent job if you’re enrolled.
      </p>
      <Source href="https://www.deutsche-rentenversicherung.de/Rheinland/DE/Presse/Pressemitteilungen/2025/25-11-21-mindestlohn.html">
        Deutsche Rentenversicherung: minijob limit 2026
      </Source>
    </>,
  ],
  [
    "Internships: when the minimum wage applies",
    <>
      <p>
        <b>Mandatory internships</b> (required by your study regulations) don’t have to pay the minimum wage. Neither do
        voluntary internships of up to three months alongside your studies, once per employer. A <b>longer voluntary
        internship</b> must pay at least €13.90/h (2026).
      </p>
      <Source href="https://www.gesetze-im-internet.de/milog/__22.html">§ 22 Minimum Wage Act (MiLoG)</Source>
    </>,
  ],
];

export default function GuidePage() {
  return (
    <div className="max-w-4xl pt-10 pb-16 lg:pt-12">
      <p className="text-[13px] font-semibold text-muted">Guide</p>
      <h1 className="text-[44px] leading-[0.96] font-semibold tracking-[-0.05em] sm:text-[56px]">
        Can I take <span className="font-serif text-[1.12em] font-normal tracking-[-0.02em] text-orange-text">this job</span>?
      </h1>
      <p className="mt-4 max-w-md text-[17px] leading-snug text-muted">
        The work rules for students in Germany on one page, each with its official source.
      </p>
      <p role="note" className="mt-6 max-w-[65ch] border-l-2 border-rule pl-3 text-sm text-muted">
        A summary, not legal advice. Your residence permit can set other limits: check its additional sheet
        (Zusatzblatt), and ask your university’s international office when you’re unsure.
      </p>

      <div className="mt-10 max-w-[65ch]">
        {SECTIONS.map(([heading, body], i) => (
          <section key={heading} className="border-t-[1.5px] border-rule py-6">
            <span className="text-[13px] text-muted tabular-nums">{String(i + 1).padStart(2, "0")}</span>
            <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em]">{heading}</h2>
            <div className="mt-2 space-y-3 text-[16px] leading-relaxed text-ink">{body}</div>
          </section>
        ))}
        <p className="mt-6 text-[15px]">
          <Link href="/?hours=20" className={`${ext} font-semibold`}>
            Show jobs up to 20 h/week
          </Link>
        </p>
        <p className="mt-8 text-xs text-muted">Last checked {CHECKED}</p>
      </div>
    </div>
  );
}
