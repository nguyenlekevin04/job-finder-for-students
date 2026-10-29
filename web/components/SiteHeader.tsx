"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useBookmarks } from "@/lib/useBookmarks";
import { ThemeToggle } from "./ThemeToggle";

export function SiteHeader() {
  const pathname = usePathname();
  const { count } = useBookmarks();
  const onSaved = pathname.replace(/\/$/, "").endsWith("/saved");

  return (
    <header className="mx-auto w-full max-w-7xl px-4 sm:px-8 lg:px-10">
      <div className="flex h-[68px] items-center justify-between gap-3 border-b border-line">
        <Link href="/" className="focus-ring rounded text-[19px] font-bold tracking-[-0.035em]">
          dresden<span className="text-orange">/</span>jobs
        </Link>
        <nav className="flex items-center gap-1 sm:gap-5">
          <Link
            href="/"
            aria-current={onSaved ? undefined : "page"}
            className={`focus-ring hidden rounded px-1 font-medium sm:inline ${onSaved ? "text-muted hover:text-ink" : ""}`}
          >
            Jobs
          </Link>
          <a href="#about" className="focus-ring hidden rounded px-1 font-medium text-muted hover:text-ink sm:inline">
            How it works
          </a>
          <ThemeToggle />
          <Link
            href="/saved/"
            aria-current={onSaved ? "page" : undefined}
            className="focus-ring inline-flex items-center gap-2 rounded-[10px] bg-btn px-4 py-2.5 text-[15px] font-semibold tracking-[-0.02em] text-btn-ink transition hover:opacity-90"
          >
            Saved
            <span className="min-w-5 rounded-md bg-orange px-1.5 text-center text-[13px] text-[#1f1d1a] tabular-nums">{count}</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}
