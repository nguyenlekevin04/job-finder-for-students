import type { Metadata } from "next";
import { SavedJobs } from "@/components/SavedJobs";

export const metadata: Metadata = {
  title: "Saved jobs", // layout template adds " · dresden/jobs" (and "[STAGING] ")
};

export default function SavedPage() {
  return <SavedJobs />;
}
