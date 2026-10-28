import type { Metadata } from "next";
import { SavedJobs } from "@/components/SavedJobs";

export const metadata: Metadata = {
  title: "Saved jobs · Dresden Student Tech Jobs",
};

export default function SavedPage() {
  return <SavedJobs />;
}
