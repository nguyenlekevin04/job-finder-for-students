import type { Metadata, Viewport } from "next";
import { Instrument_Serif, Schibsted_Grotesk } from "next/font/google";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

const grotesk = Schibsted_Grotesk({ variable: "--font-grotesk", subsets: ["latin"] });
const serif = Instrument_Serif({ variable: "--font-instrument-serif", subsets: ["latin"], weight: "400", style: "italic" });

export const metadata: Metadata = {
  title: "dresden/jobs · Student tech jobs in Dresden",
  description:
    "Werkstudent, internship and thesis positions in AI, ML and Computer Science around Dresden – collected daily from several job sources.",
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
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="isolate flex min-h-full flex-col font-sans">
        <SiteHeader />
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-20 sm:px-8 lg:px-10">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
