# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A job board for student roles (Werkstudent, internship, thesis) in AI/ML/CS around Dresden plus remote-in-Germany. Two halves joined by one JSON file:

```
fetcher/ (Python)  ──writes──▶  web/public/jobs.json  ◀──fetch()──  web/ (Next.js static site)
```

A GitHub Action (`.github/workflows/update-jobs.yml`) runs daily: pytest → `python fetcher/main.py` → commits `jobs.json` as `github-actions[bot]` → `next build` with `NEXT_BASE_PATH` from `configure-pages` → deploys `web/out` to GitHub Pages (https://nguyenlekevin04.github.io/job-finder-for-students/). Because the bot commits data to `main` daily, **pull before pushing**.

## Commands

All Python commands run from the repo root (the fetcher imports itself as the `fetcher` package).

```bash
pip install -r fetcher/requirements.txt
python fetcher/main.py                       # fetch all sources, rewrite web/public/jobs.json (~2 min, live network)
python -m pytest fetcher/tests -q            # all tests (offline, use saved fixtures)
python -m pytest fetcher/tests/test_classify.py::test_drops_other_jobs -q   # single test
```

```bash
cd web
npm run dev        # dev server on :3000
npm run build      # static export to web/out/
npm run lint       # eslint
npx tsc --noEmit   # type-check
NEXT_BASE_PATH=/job-finder-for-students npm run build   # reproduce the GitHub Pages sub-path build
```

`.claude/launch.json` has a `static-site` config that serves `web/out` on :4173 for browser checks of the real build.

Adzuna is optional: keys come from `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` in `.env` (read by a minimal loader in `main.py`) or GitHub secrets; without them the source is reported as skipped.

## Fetcher architecture

- **Sources** (`fetcher/sources/*.py`): each module exposes `NAME` and `fetch() -> list[Job]`, with parsing split into pure `parse*()` functions that take raw text/JSON so tests can run against `fetcher/tests/fixtures/`. Optional `is_enabled()` lets a source be skipped. Register new sources in `SOURCES` in `fetcher/main.py`.
- **`Job.tags` vs `Job.description`** (`fetcher/models.py`) matters for classification: `tags` is short, reliable context (BA occupation names, HZDR's category heading like "Master theses / Compulsory internship") and is treated like the title; `description` is long free text with stricter rules.
- **Classifier** (`fetcher/classify.py`) returns tag dict or `None` (drop):
  - Type comes from title+tags; description is only a fallback for werkstudent/internship (never thesis). HiWi / "Studentische Hilfskraft", Ausbildung, PhD, senior, school-pupil posts are excluded **on purpose** (user requirement) — this is why TU Dresden yields ~0 jobs and many Fraunhofer posts drop.
  - Field from title+tags; description-only evidence needs `MIN_DESC_HITS` distinct terms and is blocked by `NON_TECH_TITLE`. `IT` and `BI` are matched case-sensitively (`IT_WORD`, `BI_WORD`) to avoid false hits like "Co-Bi".
  - When tuning keywords, re-check with the parametrized cases in `test_classify.py`.
- **`main.py`** pipeline: run sources (one failing source never stops the others; status per source goes into the JSON) → strip "Company: " title prefixes → classify → dedupe by `job_id()` = sha1 of normalized title|company → merge with the previous `jobs.json` to keep `firstSeen`; jobs missing from today's run are kept up to `KEEP_MISSING_DAYS`. If every source fails, the old file is left untouched.
- **Changing `norm_title` / `norm_company` changes job IDs**, which resets `firstSeen` ("New" badges) and orphans users' browser bookmarks.
- The HTTP helper module is `fetcher/net.py`, deliberately not `http.py`: running `python fetcher/main.py` puts `fetcher/` on `sys.path`, and a local `http.py` shadows the stdlib and breaks `requests`.

## Web architecture

- **Next.js 16** — read `web/AGENTS.md`: APIs differ from older versions; check `web/node_modules/next/dist/docs/` before using framework features.
- `output: "export"` (static only). `cacheComponents` / `partialPrefetching` (PPR) **cannot** be enabled with export — the build fails. No server features (route handlers, server actions, rewrites, image optimization).
- `basePath` comes from `NEXT_BASE_PATH` at build time and is re-exposed as `NEXT_PUBLIC_BASE_PATH`; anything fetched by raw URL (e.g. `jobs.json` in `lib/useJobs.ts`) must prefix it manually. `next/link` handles it automatically. `trailingSlash: true` so `/saved/` exports as `saved/index.html`.
- `jobs.json` is loaded client-side once and cached module-wide (`lib/useJobs.ts`); all job rendering is client-only, so there are no SSR date/locale mismatches.
- The JSON schema is defined twice: the dict built in `fetcher/main.py` (`build_jobs` / `main`) and `web/lib/types.ts`. Keep them in sync.
- **Filters** (`lib/filters.ts` + `components/JobBoard.tsx`): component state is the source of truth and is mirrored to the URL after 250 ms via `router.replace`; external URL changes (back/forward) flow back through the `seenParams`/`pushed` render-time check. Don't derive filters directly from `useSearchParams` on each click — fast consecutive clicks lose updates. `JobBoard` uses `useSearchParams`, so it must stay inside the `<Suspense>` in `app/page.tsx` or the export build fails.
- **Bookmarks** (`lib/useBookmarks.ts`): `useSyncExternalStore` over localStorage (all access in try/catch), storing whole `Job` objects so the Saved page can show jobs that vanished from the data ("No longer listed").
- **Dark mode**: Tailwind v4 `@custom-variant dark` on the `.dark` class; an inline script in `app/layout.tsx` sets it before paint (`suppressHydrationWarning` on `<html>`), and `ThemeToggle` stores the choice under `dsj:theme`.
- The footer links to arbeitnow.com because Arbeitnow's API terms ask for a backlink — keep it.
