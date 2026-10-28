"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useBookmarks } from "@/lib/useBookmarks";
import { StarIcon } from "./Icons";
import { ThemeToggle } from "./ThemeToggle";

export function SiteHeader() {
  const pathname = usePathname();
  const { count } = useBookmarks();
  const onSaved = pathname.replace(/\/$/, "").endsWith("/saved");

  const tab = (active: boolean) =>
    `focus-ring inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
      active
        ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
        : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
    }`;

  return (
    <header className="sticky top-0 z-30 border-b border-zinc-200/80 bg-zinc-50/85 backdrop-blur-md dark:border-zinc-800/80 dark:bg-zinc-950/85">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/" className="focus-ring group flex min-w-0 items-center gap-2.5 rounded-lg">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 font-mono text-xs font-bold text-white shadow-sm shadow-indigo-500/30">
            DD
          </span>
          <span className="truncate text-[15px] font-semibold tracking-tight">
            Student Tech Jobs <span className="hidden font-normal text-zinc-500 sm:inline dark:text-zinc-400">Dresden</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          <Link href="/" className={tab(!onSaved)}>
            Jobs
          </Link>
          <Link href="/saved/" className={tab(onSaved)}>
            <StarIcon width={14} height={14} filled={onSaved || count > 0} className={onSaved ? "" : "text-amber-500"} />
            Saved
            {count > 0 && (
              <span
                className={`min-w-5 rounded-full px-1.5 text-center text-xs tabular-nums ${
                  onSaved ? "bg-white/20 dark:bg-zinc-900/15" : "bg-zinc-200 dark:bg-zinc-800"
                }`}
              >
                {count}
              </span>
            )}
          </Link>
          <span className="mx-1 hidden h-5 w-px bg-zinc-200 sm:block dark:bg-zinc-800" />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
