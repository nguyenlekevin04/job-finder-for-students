"use client";

import { useEffect, useState } from "react";
import type { Job, JobsFile, SourceStatus } from "./types";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: JobsFile };

// Set at build time (Render env vars / web/.env.local). Without them the site
// falls back to the local web/public/jobs.json written by the fetcher.
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "");
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Database columns -> the camelCase Job shape (PostgREST renames with "alias:column").
const JOB_SELECT = [
  "id", "title", "company", "location", "remote", "type", "types", "fields",
  "englishFriendly:english_friendly", "postedAt:posted_at", "deadline",
  "firstSeen:first_seen", "lastSeen:last_seen", "links", "snippet",
].join(",");

async function getJson<T>(url: string, headers?: Record<string, string>): Promise<T> {
  const res = await fetch(url, { headers, cache: "no-cache" });
  if (!res.ok) throw new Error(`Could not load jobs (HTTP ${res.status})`);
  return res.json() as Promise<T>;
}

async function loadFromSupabase(url: string, key: string): Promise<JobsFile> {
  const headers: Record<string, string> = { apikey: key };
  // Legacy anon keys are JWTs and also go in Authorization; new publishable keys don't.
  if (key.startsWith("eyJ")) headers.Authorization = `Bearer ${key}`;
  const rest = `${url}/rest/v1`;
  const [jobs, runs] = await Promise.all([
    getJson<Job[]>(`${rest}/jobs?select=${JOB_SELECT}&limit=5000`, headers),
    getJson<{ generatedAt: string; sources: Record<string, SourceStatus> }[]>(
      `${rest}/fetch_runs?select=generatedAt:generated_at,sources&order=generated_at.desc&limit=1`,
      headers,
    ),
  ]);
  const run = runs[0];
  return {
    generatedAt: run?.generatedAt ?? new Date().toISOString(),
    sources: run?.sources ?? {},
    count: jobs.length,
    jobs,
  };
}

function loadFromFile(): Promise<JobsFile> {
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return getJson<JobsFile>(`${base}/jobs.json`);
}

// Shared across pages so navigating Jobs <-> Saved doesn't refetch.
let cache: Promise<JobsFile> | null = null;

function load(): Promise<JobsFile> {
  if (!cache) {
    cache = SUPABASE_URL && SUPABASE_KEY ? loadFromSupabase(SUPABASE_URL, SUPABASE_KEY) : loadFromFile();
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
