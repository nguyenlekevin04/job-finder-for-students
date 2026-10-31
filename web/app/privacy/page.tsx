import type { Metadata } from "next";
import { ANALYTICS_ON } from "@/lib/analytics";
import { LEGAL_PLACEHOLDERS, OPERATOR } from "@/lib/legal";

// TODO before launch: check this text with a privacy policy generator (e.g. eRecht24)
// and fill in the real data in web/lib/legal.ts. Keep the list of browser storage keys
// in sync with the code (useBookmarks, useApplications, ThemeToggle, useLastVisit). Also confirm the
// provider details: Vercel's, Supabase's and Umami's addresses, the Supabase project's region,
// and the legal basis for transfers outside the EU (Data Privacy Framework / SCCs).

export const metadata: Metadata = {
  title: "Privacy", // layout template adds " · dresden/jobs"
  // Keep the operator's name and address out of search results; the page stays reachable from the footer.
  robots: { index: false, follow: true },
};

const code = "rounded bg-line/60 px-1 font-mono text-[14px]";

const SECTIONS: [string, React.ReactNode][] = [
  [
    "Who is responsible",
    <>
      <p>The controller under the GDPR (DSGVO) for this website is:</p>
      <address className="not-italic">
        {OPERATOR.name}
        <br />
        {OPERATOR.street}
        <br />
        {OPERATOR.city}
        <br />
        <a href={`mailto:${OPERATOR.email}`} className="focus-ring link-u rounded">
          {OPERATOR.email}
        </a>
      </address>
    </>,
  ],
  [
    "Hosting",
    <>
      <p>
        The site is hosted by Vercel Inc., 440 N Barranca Ave #4133, Covina, CA 91723, USA. When you open a page, Vercel’s
        servers process the data your browser sends with every request: your IP address, the page requested, the time,
        the browser and operating system (user agent) and the referring page. Vercel keeps this in server logs for a short
        time to deliver the site and keep it secure.
      </p>
      <p>
        Legal basis: Art. 6 (1) (f) GDPR, our legitimate interest in a secure, working website. Data may be processed in
        the USA; Vercel is certified under the EU-US Data Privacy Framework and has signed the EU standard contractual
        clauses.
      </p>
    </>,
  ],
  [
    "Loading the jobs",
    <>
      <p>
        The job list is loaded by your browser directly from our database at Supabase (Supabase Inc., 970 Toa Payoh North #07-04, Singapore 318992).
        Like any web request, this sends your IP address and browser details to Supabase, which may log them briefly to run
        and protect the service. The request reads the public job list only; nothing about you is stored in the database.
      </p>
      <p>Legal basis: Art. 6 (1) (f) GDPR, our legitimate interest in showing you the jobs.</p>
    </>,
  ],
  [
    "Stored in your browser",
    <>
      <p>A few settings are kept in your browser’s local storage so the site works the way you left it:</p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <code className={code}>dsj:bookmarks:v1</code>: the jobs you saved for later.
        </li>
        <li>
          <code className={code}>dsj:applications:v1</code>: the application status you set on saved jobs (applied,
          interview, offer, rejected) and the day you set it.
        </li>
        <li>
          <code className={code}>dsj:theme</code>: light or dark mode, if you picked one.
        </li>
        <li>
          <code className={code}>dsj:lastVisit</code>: the times of your current and previous visit, and the date of the
          newest job you saw on each, to show which jobs are new since then.
        </li>
      </ul>
      <p>
        This data never leaves your device and is never sent to us. You can delete it at any time by clearing this site’s
        data in your browser settings.
      </p>
    </>,
  ],
  ...(ANALYTICS_ON
    ? ([
        [
          "Usage statistics",
          <>
            <p>
              To learn which parts of the board help students, we count visits with Umami (Umami Software, Inc., USA), a
              cookieless analytics service. It counts which pages are opened, the referring site, the browser and operating
              system, device type, screen size, language and approximate location (country, region, city), which filters are turned on (for example “Werkstudent” or “Up to 20 h/week”, never what you
              type into search) and clicks on “Apply now” with the job board the link goes to.
            </p>
            <p>
              Umami sets no cookies and stores nothing in your browser. It doesn’t store your IP address; it only uses it,
              together with your browser details and a value that changes every day, to count a visit once. That way we see
              totals, never a profile of you, and you can’t be followed across sites or days. If your browser sends “Do Not
              Track”, you aren’t counted at all.
            </p>
            <p>Legal basis: Art. 6 (1) (f) GDPR, our legitimate interest in improving the site with anonymous totals.</p>
          </>,
        ],
      ] as [string, React.ReactNode][])
    : []),
  [
    ANALYTICS_ON ? "No cookies, no profiles" : "No cookies, no tracking",
    <>
      <p>
        This site sets no cookies and uses no {ANALYTICS_ON ? "other analytics, " : "analytics, "}tracking pixels,
        advertising or social media plugins. Links to job postings open the employer’s or job board’s site, where their
        own privacy policy applies.
      </p>
    </>,
  ],
  [
    "Your rights",
    <>
      <p>Under the GDPR you have the right to:</p>
      <ul className="list-disc space-y-1 pl-5">
        <li>access the data we hold about you (Art. 15),</li>
        <li>have it corrected (Art. 16) or erased (Art. 17),</li>
        <li>restrict its processing (Art. 18),</li>
        <li>receive it in a portable format (Art. 20),</li>
        <li>object to processing based on legitimate interest (Art. 21).</li>
      </ul>
      <p>To use these rights, email the address above.</p>
      <p>
        You also have the right to complain to a data protection supervisory authority. For us this is the Sächsische
        Datenschutz- und Transparenzbeauftragte, Devrientstraße 5, 01067 Dresden (
        <a href="https://www.datenschutz.sachsen.de/" target="_blank" rel="noreferrer" className="focus-ring link-u rounded">
          datenschutz.sachsen.de
        </a>
        ).
      </p>
    </>,
  ],
];

export default function PrivacyPage() {
  return (
    <div className="max-w-4xl pt-10 pb-16 lg:pt-12">
      <p className="text-[13px] font-semibold text-muted">Datenschutzerklärung</p>
      <h1 className="text-[44px] leading-[0.96] font-semibold tracking-[-0.05em] sm:text-[56px]">
        Your <span className="font-serif text-[1.12em] font-normal tracking-[-0.02em] text-orange-text">privacy</span>.
      </h1>
      <p className="mt-4 max-w-md text-[17px] leading-snug text-muted">{ANALYTICS_ON ? "No account, no cookies, no profiles of you." : "No account, no cookies, no tracking."} Here’s
        what does happen.</p>
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
        <p className="mt-8 text-xs text-muted">Last updated 31 Oct 2026</p>
      </div>
    </div>
  );
}
