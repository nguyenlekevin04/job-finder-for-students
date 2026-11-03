import type { Metadata } from "next";
import { Suspense } from "react";
import { JobBoard } from "@/components/JobBoard";
import { LoadingList } from "@/components/States";
import { BOARD_LABELS, BOARDS, type Board } from "@/lib/types";

// One static page per board besides Dresden (the home page): /leipzig/, /chemnitz/, /berlin/, /remote/.
// Short links to share in a city's student groups, each with its own title and link preview.
const OTHER_BOARDS = BOARDS.filter((b) => b !== "dresden");
const OG_IMAGE = { url: "/og.png", width: 1200, height: 630, alt: "dresden/jobs: student tech jobs, updated daily" };
export const dynamicParams = false;

export function generateStaticParams() {
  return OTHER_BOARDS.map((board) => ({ board }));
}

function headline(board: Board): string {
  return board === "remote" ? "Remote student tech jobs" : `Student tech jobs in ${BOARD_LABELS[board]}`;
}

export async function generateMetadata({ params }: PageProps<"/[board]">): Promise<Metadata> {
  const board = (await params).board as Board;
  const title = headline(board);
  const description =
    board === "remote"
      ? "Remote Werkstudent jobs, internships and theses in AI, data and software in Germany. Updated daily, no account needed."
      : `Werkstudent jobs, internships and theses in AI, data and software in ${BOARD_LABELS[board]}. Updated daily, no account needed.`;
  return {
    title, // the layout's template adds " · dresden/jobs" (and "[STAGING] ")
    description,
    // Next replaces (not merges) the layout's openGraph, so the image is repeated here.
    openGraph: { type: "website", siteName: "dresden/jobs", title, description, url: `/${board}/`, images: [OG_IMAGE] },
    twitter: { card: "summary_large_image", title, description, images: [OG_IMAGE.url] },
  };
}

export default async function BoardPage({ params }: PageProps<"/[board]">) {
  const board = (await params).board as Board;
  return (
    <Suspense fallback={<div className="pt-40"><LoadingList /></div>}>
      <JobBoard home={board} />
    </Suspense>
  );
}
