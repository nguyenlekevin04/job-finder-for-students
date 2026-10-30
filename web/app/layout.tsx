import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Schibsted_Grotesk } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { ANALYTICS_ON, UMAMI_SCRIPT, UMAMI_WEBSITE_ID } from "@/lib/analytics";
import { moveScript } from "@/lib/legacyHost";

const grotesk = Schibsted_Grotesk({ variable: "--font-grotesk", subsets: ["latin"] });
const serif = Instrument_Serif({ variable: "--font-instrument-serif", subsets: ["latin"], weight: "400", style: "italic" });

// "staging" on Vercel preview deployments (staging branch and PRs); unset in production and locally.
const isStaging = process.env.NEXT_PUBLIC_DEPLOY_ENV === "staging";

const titlePrefix = isStaging ? "[STAGING] " : "";

export const metadata: Metadata = {
  // The template applies to child segments (/saved/); the home page shares this
  // segment, so it gets `default`. Both carry the staging prefix.
  title: {
    default: `${titlePrefix}dresden/jobs · Student tech jobs in Dresden`,
    template: `${titlePrefix}%s · dresden/jobs`,
  },
  description:
    "Werkstudent, internship and thesis positions in AI, ML and Computer Science around Dresden – collected daily from several job sources.",
  // Keep the staging site out of search results so students only ever find production.
  ...(isStaging && { robots: { index: false, follow: false } }),
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8f5ee" },
    { media: "(prefers-color-scheme: dark)", color: "#252523" },
  ],
};

// Runs before first paint so dark mode never flashes.
const themeScript = `try{var t=localStorage.getItem("dsj:theme");var d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d)}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${grotesk.variable} ${serif.variable} h-full antialiased`}
    >
      <head>
        {/* Must run before the theme script, so a theme carried over from the old address applies. */}
        <script dangerouslySetInnerHTML={{ __html: moveScript }} />
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        {/* Cookieless page counts. Query strings stay out (they can hold search terms), and
            browsers that send Do Not Track aren't counted. Events come from lib/analytics.ts. */}
        {ANALYTICS_ON && (
          <script
            defer
            src={UMAMI_SCRIPT}
            data-website-id={UMAMI_WEBSITE_ID}
            data-exclude-search="true"
            data-exclude-hash="true"
            data-do-not-track="true"
          />
        )}
      </head>
      <body className="isolate flex min-h-full flex-col font-sans">
        {isStaging && (
          <div role="note" className="bg-orange px-4 py-1.5 text-center text-[13px] font-semibold text-[#1f1d1a]">
            STAGING · test site with test data. The real site is dresden-jobs.vercel.app
          </div>
        )}
        <SiteHeader />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-20 sm:px-8 lg:px-10">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
