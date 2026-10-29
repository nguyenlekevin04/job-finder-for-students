import type { Metadata } from "next";
import { SavedJobs } from "@/components/SavedJobs";

export const metadata: Metadata = {
  title: "Saved jobs · dresden/jobs",
};

export default function SavedPage() {
  return <SavedJobs />;
}
