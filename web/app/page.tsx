import { Suspense } from "react";
import { JobBoard } from "@/components/JobBoard";
import { LoadingList } from "@/components/States";

// JobBoard reads filters from the URL (useSearchParams), so it needs a
// Suspense boundary for the static export.
export default function Home() {
  return (
    <Suspense fallback={<div className="pt-40"><LoadingList /></div>}>
      <JobBoard />
    </Suspense>
  );
}
