# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A job board for student roles (Werkstudent, internship, thesis) in AI/ML/CS around Dresden plus remote-in-Germany:

```
GitHub Action (daily) ─▶ fetcher/ (Python) ─writes─▶ Supabase Postgres (jobs, fetch_runs)
                                                            ▲ read-only REST (anon key)
                              Render Static Site: web/ (Next.js export) ─fetch() in browser
```

- `.github/workflows/update-jobs.yml`: on push to `fetcher/**` it only runs pytest; on the daily schedule / manual dispatch it runs `python fetcher/main.py --require-db` with Supabase secrets. It no longer commits data or deploys.
- `render.yaml` (Blueprint) builds `web/` into `web/out` as a Render Static Site. `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` are inlined at **build time**, so changing them needs a Render redeploy.
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
npx tsc --noEmit   # type-check
```

`web/.env.local` (from `web/.env.example`) makes `dev`/`build` read from Supabase; without it the site reads `web/public/jobs.json`.

`.claude/launch.json` has a `static-site` config that serves `web/out` on :4173 for browser checks of the real build.

Root `.env` (read by a minimal loader in `main.py`; real env vars win) holds `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` and optional `ADZUNA_APP_ID` / `ADZUNA_APP_KEY`; the same names are GitHub secrets. Without Adzuna keys that source is reported as skipped.

## Fetcher architecture

- **Sources** (`fetcher/sources/*.py`): each module exposes `NAME` and `fetch() -> list[Job]`, with parsing split into pure `parse*()` functions that take raw text/JSON so tests can run against `fetcher/tests/fixtures/`. Optional `is_enabled()` lets a source be skipped. Register new sources in `SOURCES` in `fetcher/main.py`.
- **`Job.tags` vs `Job.description`** (`fetcher/models.py`) matters for classification: `tags` is short, reliable context (BA occupation names, HZDR's category heading like "Master theses / Compulsory internship") and is treated like the title; `description` is long free text with stricter rules.
- **Classifier** (`fetcher/classify.py`) returns tag dict or `None` (drop):
  - Type comes from title+tags; description is only a fallback for werkstudent/internship (never thesis). HiWi / "Studentische Hilfskraft", Ausbildung, PhD, senior, school-pupil posts are excluded **on purpose** (user requirement) — this is why TU Dresden yields ~0 jobs and many Fraunhofer posts drop.
  - Field from title+tags; description-only evidence needs `MIN_DESC_HITS` distinct terms and is blocked by `NON_TECH_TITLE`. `IT` and `BI` are matched case-sensitively (`IT_WORD`, `BI_WORD`) to avoid false hits like "Co-Bi".
  - When tuning keywords, re-check with the parametrized cases in `test_classify.py`.
- **`main.py`** pipeline: run sources (one failing source never stops the others; per-source status is saved) → strip "Company: " title prefixes → classify → dedupe by `job_id()` = sha1 of normalized title|company → `store.save()`. If every source fails, nothing is written.
- **`store.py`** has two backends behind `get_store()`: `SupabaseStore` (plain `requests` against PostgREST: page through `id,first_seen`, upsert with `on_conflict=id` + `resolution=merge-duplicates`, delete rows with `last_seen` older than `KEEP_MISSING_DAYS`, insert a `fetch_runs` row) and `JsonFileStore` (same history rules on the file). `COLUMNS` maps the camelCase job dict to snake_case columns — keep it, `schema.sql`, `web/lib/types.ts` and `JOB_SELECT` in `web/lib/useJobs.ts` in sync. Legacy JWT keys (`eyJ…`) also go in `Authorization`; new `sb_secret_`/`sb_publishable_` keys only in `apikey`.
- **Changing `norm_title` / `norm_company` changes job IDs**, which resets `firstSeen` ("New" badges) and orphans users' browser bookmarks.
- The HTTP helper module is `fetcher/net.py`, deliberately not `http.py`: running `python fetcher/main.py` puts `fetcher/` on `sys.path`, and a local `http.py` shadows the stdlib and breaks `requests`.

## Web architecture

- **Next.js 16** — read `web/AGENTS.md`: APIs differ from older versions; check `web/node_modules/next/dist/docs/` before using framework features.
- `output: "export"` (static only). `cacheComponents` / `partialPrefetching` (PPR) **cannot** be enabled with export — the build fails. No server features (route handlers, server actions, rewrites, image optimization).
- Optional `basePath` from `NEXT_BASE_PATH` (unused on Render) is re-exposed as `NEXT_PUBLIC_BASE_PATH` for the `jobs.json` fallback URL. `trailingSlash: true` so `/saved/` exports as `saved/index.html`.
- `lib/useJobs.ts` loads data client-side once and caches it module-wide: from Supabase REST (jobs + latest `fetch_runs` row, aliased to camelCase in `JOB_SELECT`) when the `NEXT_PUBLIC_SUPABASE_*` vars are set, else `jobs.json`. All job rendering is client-only, so there are no SSR date/locale mismatches.
- **Filters** (`lib/filters.ts` + `components/JobBoard.tsx`): component state is the source of truth and is mirrored to the URL after 250 ms via `router.replace`; external URL changes (back/forward) flow back through the `seenParams`/`pushed` render-time check. Don't derive filters directly from `useSearchParams` on each click — fast consecutive clicks lose updates. `JobBoard` uses `useSearchParams`, so it must stay inside the `<Suspense>` in `app/page.tsx` or the export build fails.
- **Bookmarks** (`lib/useBookmarks.ts`): `useSyncExternalStore` over localStorage (all access in try/catch), storing whole `Job` objects so the Saved page can show jobs that vanished from the data ("No longer listed").
- **Dark mode**: Tailwind v4 `@custom-variant dark` on the `.dark` class; an inline script in `app/layout.tsx` sets it before paint (`suppressHydrationWarning` on `<html>`), and `ThemeToggle` stores the choice under `dsj:theme`.
- **Design tokens**: colors are CSS variables in `app/globals.css` (`--c-*`, overridden under `.dark`) exposed as Tailwind colors (`bg-canvas`, `text-ink`, `text-muted`, `border-rule`, `bg-btn`, `text-orange-text`, …). Use those instead of raw palette classes. `orange` is decoration only (it fails text contrast); use `orange-text` for orange text. Fonts: Schibsted Grotesk (`font-sans`) and Instrument Serif italic (`font-serif`, accent words only).
- The open job on the board is `Filters.job` (`?job=` in the URL); it isn't a filter, so `applyFilters` and `activeFilterCount` ignore it.
- The footer links to arbeitnow.com because Arbeitnow's API terms ask for a backlink — keep it.

## Team (project agents in `.claude/agents/`)

The user calls these by name; start them only when asked.

- **Tech lead and project manager: the main Claude session.**
  - Acts as an architect and tech lead with 10+ years of big-tech experience.
  - Decides what is technically necessary and how and when things get built.
  - Briefs the agents, checks their output against the code, implements, and commits.
- **Otto (`otto`): senior product owner.**
  - Says what he wants for students and why, as user stories with acceptance criteria.
  - May only edit `docs/backlog.md`.
- **Iris (`iris`): UI/UX expert** (master's in design, 15 years).
  - Analyses the real page when asked and discusses proposals with the tech lead, who decides what gets implemented.
  - Doesn't edit code.
- **Review team: staff engineers.**
  - `code-reviewer` is read-only and covers bugs, security and code quality in existing code, never missing features.
  - `review-fixer` applies confirmed findings.

**Flow:** Otto states the want → the tech lead decides scope, technical needs and order → Iris and the tech lead agree on UX changes → the tech lead builds → the review team reviews and fixes → the tech lead verifies and commits.

New agent files only load as agent types after a session restart. Until then, run them as general-purpose agents told to follow their file.
