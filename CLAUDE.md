# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A job board for student roles (Werkstudent, internship, thesis) in AI/ML/CS around Dresden plus remote-in-Germany:

```
GitHub Action (daily) ─▶ fetcher/ (Python) ─writes─▶ Supabase Postgres (jobs, fetch_runs)
                                                            ▲ read-only REST (anon key)
                              Vercel (static): web/ (Next.js export) ─fetch() in browser
```

- **Environments:** dev (local) and staging both use the **staging** Supabase project. Production (`main`) uses the production project. Branch flow: feature → PR into `staging` → PR `staging` → `main`; both are protected and need CI.
- `.github/workflows/ci.yml`: fetcher tests, plus website lint / tsc / vitest / build, on every PR and on pushes to `main` / `staging`.
- `.github/workflows/update-jobs.yml`: the daily schedule fetches into both databases (matrix); manual dispatch picks one. Production uses `SUPABASE_*` secrets plus `ALLOW_PRODUCTION_WRITE=1`; staging uses `STAGING_SUPABASE_*`, with no fallback. `main.py` refuses to write to `PRODUCTION_PROJECT_REF` without that flag, so local runs can never touch production.
- Hosting is **Vercel** (project root `web/`, config `web/vercel.json`). Production deploys from `main`; previews (the `staging` branch and every PR) use the staging project plus `NEXT_PUBLIC_DEPLOY_ENV=staging`, which adds a STAGING banner and noindex. `NEXT_PUBLIC_*` values are inlined at **build time**, so redeploy after changing them. `render.yaml` is the legacy Render site, kept only to forward its old address.
- `docs/capacity.md` covers free-tier limits for 5,000 users and the switch point: at 100 jobs, or above 2.5 GB/month of Supabase egress, serve the job list from the CDN.
- `supabase/schema.sql` is the source of truth for tables and RLS (anon = select only; the fetcher uses the service_role / secret key, which bypasses RLS). Re-runnable.
- **Local fallback:** with no Supabase env vars, the fetcher writes `web/public/jobs.json` (git-ignored) and the site reads it. Both paths must keep working.

## Commands

All Python commands run from the repo root (the fetcher imports itself as the `fetcher` package).

```bash
pip install -r fetcher/requirements.txt
python fetcher/main.py                       # fetch all sources (~2 min, live network) → Supabase if SUPABASE_* set, else web/public/jobs.json
python fetcher/main.py --require-db          # fail instead of falling back to jobs.json (used in CI)
python -m pytest fetcher/tests -q            # all tests (offline, use saved fixtures)
python -m pytest fetcher/tests/test_classify.py::test_drops_other_jobs -q   # single test
```

```bash
cd web
npm run dev        # dev server on :3000
npm run build      # static export to web/out/
npm run lint       # eslint
npx tsc --noEmit   # type-check (on a fresh checkout run `npx next typegen` first, as CI does)
npm test           # vitest unit tests (lib/*.test.ts)
```

`web/.env.local` (from `web/.env.example`) makes `dev`/`build` read from Supabase; without it the site reads `web/public/jobs.json`.

`.claude/launch.json` has a `static-site` config that serves `web/out` on :4173 for browser checks of the real build.

Root `.env` (read by a minimal loader in `main.py`; real env vars win) holds `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (staging values locally); production and staging values are GitHub secrets.

## Fetcher architecture

- **Sources** (`fetcher/sources/*.py`): each module exposes `NAME` and `fetch() -> list[Job]`, with parsing split into pure `parse*()` functions that take raw text/JSON so tests can run against `fetcher/tests/fixtures/`. Optional `is_enabled()` lets a source be skipped. Register new sources in `SOURCES` in `fetcher/main.py`.
- **`Job.tags` vs `Job.description`** (`fetcher/models.py`) matters for classification: `tags` is short, reliable context (BA occupation names, HZDR's category heading like "Master theses / Compulsory internship") and is treated like the title; `description` is long free text with stricter rules.
- **Classifier** (`fetcher/classify.py`) returns tag dict or `None` (drop):
  - Type comes from title+tags; description is only a fallback for werkstudent/internship (never thesis). HiWi / "Studentische Hilfskraft", Ausbildung, PhD, senior, school-pupil posts are excluded **on purpose** (user requirement) — this is why TU Dresden yields ~0 jobs and many Fraunhofer posts drop.
  - Field from title+tags; description-only evidence needs `MIN_DESC_HITS` distinct terms and is blocked by `NON_TECH_TITLE`. `IT` and `BI` are matched case-sensitively (`IT_WORD`, `BI_WORD`) to avoid false hits like "Co-Bi".
  - When tuning keywords, re-check with the parametrized cases in `test_classify.py`.
- **`main.py`** pipeline: run sources (one failing source never stops the others; per-source status is saved) → strip "Company: " title prefixes → classify → dedupe by `job_id()` = sha1 of normalized title|company → `store.save()`. If every source fails, nothing is written.
  - `SOURCES` order matters: direct employer/institute sources come before aggregators, because a merged job's first link is its "Apply now" button.
  - **Links and merges are hardened** (security attack #1): `safe_link()` accepts only `https://` URLs on the hosts in `LINK_HOSTS` (per source; add the host when you add a source, or all its postings are skipped). When duplicates merge, the first (highest-priority) posting keeps its snippet, dates and language; later copies only fill empty fields.
  - **Source health alarm:** after saving, `health_problems()` flags sources that failed or returned 0 postings (unless the module sets `MAY_BE_EMPTY = True`). `main()` then returns 3, so the Action fails and GitHub emails the owner.
  - Errors and tracebacks go through `redact()`, which strips URL query strings. They may carry API keys, and the status is stored in the publicly readable `fetch_runs` table.
- **Employer career feeds** (Infineon/Eightfold, GlobalFoundries/Workday, Bosch/SmartRecruiters, Amazon) list every role without descriptions. Their sources fetch the full posting only when `classify.is_student_title()` matches, which keeps it to a handful of requests per run. Each strips the company's boilerplate intro so the snippet starts with the role. Workday search needs POST (`net.post_json`). The session asks for gzip only, because amazon.jobs answers the default zstd offer with a body urllib3 can't decode.
- **`store.py`** has two backends behind `get_store()`: `SupabaseStore` (plain `requests` against PostgREST: `previous()` pages through every row, `save(jobs, removed, …)` upserts with `on_conflict=id` + `resolution=merge-duplicates`, deletes `removed` by id and inserts a `fetch_runs` row) and `JsonFileStore` (same on the file). `COLUMNS` maps the camelCase job dict to snake_case columns — keep it, `schema.sql`, `web/lib/types.ts` and `JOB_SELECT` in `web/lib/useJobs.ts` in sync. Legacy JWT keys (`eyJ…`) also go in `Authorization`; new `sb_secret_`/`sb_publishable_` keys only in `apikey`.
- **Open jobs only** (`fetcher/availability.py`, pure, tested offline): `decide()` gives every link open/closed/unknown and every job a verdict. Sources default to a complete feed (listed = open, not listed while the source worked = closed); aggregators set `FEED = "partial"` and may define `check(url)`. A posting the source still lists (`raw_urls`) but that didn't become a job today (detail page timed out, reclassified) is unknown, not closed. `lastSeen` means "last confirmed open"; unconfirmed jobs stay `UNCONFIRMED_DAYS` (2), and closed links are dropped from every job that stays. A guard keeps a source's jobs and raises the alarm when the source's own closed links would remove at least `GUARD_MIN_REMOVALS` (3) and more than half of its jobs in one run; removals after the grace period are never blocked. To approve a real mass closure, run "Update jobs" with `accept_removals=<Source>` (env `ACCEPT_REMOVALS`). Per-source link counts go into `fetch_runs.sources[name].links`. New sources: set `FEED = "partial"` if the feed is capped or search-ranked.
- **Changing `norm_title` / `norm_company` changes job IDs**, which resets `firstSeen` ("New" badges) and orphans users' browser bookmarks.
- The HTTP helper module is `fetcher/net.py`, deliberately not `http.py`: running `python fetcher/main.py` puts `fetcher/` on `sys.path`, and a local `http.py` shadows the stdlib and breaks `requests`.

## Web architecture

- **Next.js 16** — read `web/AGENTS.md`: APIs differ from older versions; check `web/node_modules/next/dist/docs/` before using framework features.
- `output: "export"` (static only). `cacheComponents` / `partialPrefetching` (PPR) **cannot** be enabled with export — the build fails. No server features (route handlers, server actions, rewrites, image optimization).
- Optional `basePath` from `NEXT_BASE_PATH` (unused on Vercel) is re-exposed as `NEXT_PUBLIC_BASE_PATH` for the `jobs.json` fallback URL. `trailingSlash: true` so `/saved/` exports as `saved/index.html`.
- `lib/useJobs.ts` loads data client-side once and caches it module-wide: from Supabase REST (jobs + latest `fetch_runs` row, aliased to camelCase in `JOB_SELECT`) when the `NEXT_PUBLIC_SUPABASE_*` vars are set, else `jobs.json`. All job rendering is client-only, so there are no SSR date/locale mismatches.
- **Filters** (`lib/filters.ts` + `components/JobBoard.tsx`): component state is the source of truth and is mirrored to the URL after 250 ms via `router.replace`; external URL changes (back/forward) flow back through the `seenParams`/`pushed` render-time check. Don't derive filters directly from `useSearchParams` on each click — fast consecutive clicks lose updates. `JobBoard` uses `useSearchParams`, so it must stay inside the `<Suspense>` in `app/page.tsx` or the export build fails.
- **Bookmarks** (`lib/useBookmarks.ts`): `useSyncExternalStore` over localStorage (all access in try/catch), storing whole `Job` objects so the Saved page can show jobs that vanished from the data ("No longer listed").
- **Dark mode**: Tailwind v4 `@custom-variant dark` on the `.dark` class; an inline script in `app/layout.tsx` sets it before paint (`suppressHydrationWarning` on `<html>`), and `ThemeToggle` stores the choice under `dsj:theme`.
- **Design tokens**: colors are CSS variables in `app/globals.css` (`--c-*`, overridden under `.dark`) exposed as Tailwind colors (`bg-canvas`, `text-ink`, `text-muted`, `border-rule`, `bg-btn`, `text-orange-text`, …). Use those instead of raw palette classes. `orange` is decoration only (it fails text contrast); use `orange-text` for orange text. Fonts: Schibsted Grotesk (`font-sans`) and Instrument Serif italic (`font-serif`, accent words only).
- The open job on the board is `Filters.job` (`?job=` in the URL); it isn't a filter, so `applyFilters` and `activeFilterCount` ignore it.
- The footer links to arbeitnow.com because Arbeitnow's API terms ask for a backlink — keep it.

## Team (project agents in `.claude/agents/`)

The user calls these by name; start them only when asked or when `/feature` or `/release` runs.

- **Tech lead and project manager: the main Claude session.**
  - Acts as an architect and tech lead with 10+ years of big-tech experience.
  - Decides what is technically necessary and how and when things get built.
  - Briefs the agents, checks their output against the code, implements, and commits.
- **Devs, managed entirely by the tech lead:**
  - **Mia (`mia`): senior frontend engineer.** `web/`.
  - **Jonas (`jonas`): senior backend and data engineer.** `fetcher/`, `supabase/`, workflows.
  - The tech lead splits a design into tasks that don't share files and runs them in parallel, each in its own git worktree on its own branch.
  - Devs commit only on their branch. They never push, merge, change settings or touch production. The tech lead integrates, pushes and opens the PR.
- **Otto (`otto`): senior product owner.**
  - Says what he wants for students and why, as user stories with acceptance criteria.
  - May only edit `docs/backlog.md`.
- **Iris (`iris`): UI/UX expert** (master's in design, 15 years).
  - Analyses the real page when asked and discusses proposals with the tech lead, who decides what gets implemented.
  - Doesn't edit code.
- **Kevin (`kevin`): ethical hacker (red team).**
  - Attacks our own system (staging for anything that writes, production read-only) and reports findings with proof.
  - Run with `/hackerattack [focus]` once per sprint before the release, and before logins or new secrets: Kevin attacks → the tech lead triages → the review team fixes and verifies against his proof. Kevin isn't part of code or release review. Results go to `docs/security.md`.
- **Review team: staff engineers.**
  - `code-reviewer` is read-only and covers bugs, security and code quality in existing code, never missing features.
  - `review-fixer` applies confirmed findings.

**End of every sprint:** the review team removes dead code before the release (`docs/workflow.md`).

**Flow:** `docs/workflow.md` is the source of truth (run it with `/feature <idea>` and `/release`). In short: Otto states the want → the tech lead designs → Iris and the tech lead agree on UX → the tech lead builds → the review team reviews (the author never approves their own change) → PR into `staging` → Iris, the review team and Otto test staging → the shareholder (the user) gives the OK → release PR `staging` → `main` with a merge commit, never squash.

New agent files only load as agent types after a session restart. Until then, run them as general-purpose agents told to follow their file.
