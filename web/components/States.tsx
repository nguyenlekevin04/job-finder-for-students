import type { ReactNode } from "react";
import { JobRowSkeleton } from "./JobRow";

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="border-t-[1.5px] border-rule py-12">
      <h3 className="text-2xl font-semibold tracking-[-0.04em]">{title}</h3>
      {children && <div className="mt-2 max-w-md text-[15px] leading-relaxed text-muted">{children}</div>}
    </div>
  );
}

export function LoadingList({ count = 5 }: { count?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading jobs">
      {Array.from({ length: count }, (_, i) => (
        <JobRowSkeleton key={i} />
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
        className="focus-ring mt-4 rounded-[10px] bg-btn px-4 py-2.5 text-[15px] font-semibold text-btn-ink hover:opacity-90"
      >
        Try again
      </button>
    </EmptyState>
  );
}
