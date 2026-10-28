import type { ReactNode } from "react";
import { JobCardSkeleton } from "./JobCard";

export function EmptyState({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-zinc-300 bg-white/50 px-6 py-14 text-center dark:border-zinc-700 dark:bg-zinc-900/40">
      {icon && <div className="mb-3 grid size-11 place-items-center rounded-full bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">{icon}</div>}
      <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">{title}</h3>
      {children && <div className="mt-1.5 max-w-sm text-sm text-zinc-500 dark:text-zinc-400">{children}</div>}
    </div>
  );
}

export function LoadingList({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading jobs">
      {Array.from({ length: count }, (_, i) => (
        <JobCardSkeleton key={i} />
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <EmptyState title="Couldn't load jobs">
      <p>{message}. Check your connection and try again.</p>
      <button
        type="button"
        onClick={onRetry}
        className="focus-ring mt-4 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-600 dark:bg-white dark:text-zinc-900"
      >
        Try again
      </button>
    </EmptyState>
  );
}
