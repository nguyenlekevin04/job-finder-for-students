"use client";

import { useEffect, useState } from "react";
import type { JobsFile } from "./types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: JobsFile };

// Shared across pages so navigating Jobs <-> Saved doesn't refetch.
let cache: Promise<JobsFile> | null = null;

function load(): Promise<JobsFile> {
  if (!cache) {
    const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
    cache = fetch(`${base}/jobs.json`, { cache: "no-cache" }).then((res) => {
      if (!res.ok) throw new Error(`Could not load jobs (HTTP ${res.status})`);
      return res.json() as Promise<JobsFile>;
    });
    cache.catch(() => {
      cache = null; // allow a retry
    });
  }
  return cache;
}

export function useJobsFile() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    load()
      .then((data) => alive && setState({ status: "ready", data }))
      .catch((err: Error) => alive && setState({ status: "error", message: err.message }));
    return () => {
      alive = false;
    };
  }, [attempt]);

  const retry = () => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  return { state, retry };
}
