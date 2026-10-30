import type { Metadata } from "next";
import { LEGAL_PLACEHOLDERS, OPERATOR } from "@/lib/legal";

// TODO before launch: check this text with an imprint generator (e.g. eRecht24)
// and fill in the real data in web/lib/legal.ts.

export const metadata: Metadata = {
  title: "Imprint", // layout template adds " · dresden/jobs"
  // Keep the operator's name and address out of search results; the page stays reachable from the footer.
  robots: { index: false, follow: true },
};

const SECTIONS: [string, React.ReactNode][] = [
  [
    "Contact",
    <>
      <p>Information according to § 5 DDG (Digitale-Dienste-Gesetz):</p>
      <address className="not-italic">
        {OPERATOR.name}
        <br />
        {OPERATOR.street}
        <br />
        {OPERATOR.city}
        <br />
        Germany
      </address>
      <p>
        Email:{" "}
        <a href={`mailto:${OPERATOR.email}`} className="focus-ring link-u rounded">
          {OPERATOR.email}
        </a>
      </p>
    </>,
  ],
  [
    "Responsible for content",
    <>
      <p>Responsible for the content according to § 18 Abs. 2 MStV (Medienstaatsvertrag):</p>
      <address className="not-italic">
        {OPERATOR.name}
        <br />
        {OPERATOR.street}
        <br />
        {OPERATOR.city}
      </address>
    </>,
  ],
  [
    "Job postings belong to their employers",
    <>
      <p>
        dresden/jobs collects student job postings from public job boards and employer career pages once a day and links to
        the original posting. The postings, their text and their conditions belong to the employers and the sites that
        publish them.
      </p>
      <p>
        Jobs are matched by keywords, so a few may be wrong or out of date. Always check the original posting before you
        apply. We are not responsible for the content of external sites we link to.
      </p>
    </>,
  ],
];

export default function ImprintPage() {
  return (
    <div className="max-w-4xl pt-10 pb-16 lg:pt-12">
      <p className="text-[13px] font-semibold text-muted">Impressum</p>
      <h1 className="text-[44px] leading-[0.96] font-semibold tracking-[-0.05em] sm:text-[56px]">
        Who runs <span className="font-serif text-[1.12em] font-normal tracking-[-0.02em] text-orange-text">this</span> board.
      </h1>
      <p className="mt-4 max-w-md text-[17px] leading-snug text-muted">dresden/jobs is a free, non-commercial job board.</p>
      {LEGAL_PLACEHOLDERS && (
        <p role="note" className="mt-6 border-l-2 border-rule pl-3 text-sm text-muted">
          Draft: the contact details below are placeholders and will be filled in before launch.
        </p>
      )}

      <div className="mt-10 max-w-[65ch]">
        {SECTIONS.map(([title, body], i) => (
          <section key={title} className="border-t-[1.5px] border-rule py-6">
            <span className="text-[13px] text-muted tabular-nums">{String(i + 1).padStart(2, "0")}</span>
            <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em]">{title}</h2>
            <div className="mt-2 space-y-3 text-[16px] leading-relaxed text-ink">{body}</div>
          </section>
        ))}
        <p className="mt-8 text-xs text-muted">Last updated 29 Oct 2026</p>
      </div>
    </div>
  );
}
