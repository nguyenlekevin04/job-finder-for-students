# Backlog

Owner: Otto (product owner). Ranked by value to students against effort. Free tiers only; anything that costs money goes to the shareholder.

## Now

**Sprint 2 goal: only show jobs that are still open.**

1. **Closed jobs leave the board by the next daily update** (M): As a student checking the board between lectures, I want every job I see to still accept applications, so that I don't waste my few free minutes on dead postings.
   - Acceptance (fetcher, each daily run):
     - Every listed job's own posting page is checked once per run (~1 request per job, free).
     - A job is **closed** when its page returns 404/410, redirects away from the posting (to a search, list or home page), or shows a "no longer available" / "nicht mehr verfügbar" message. A closed job is removed in that run, even if its source feed still lists it.
     - A job missing from a source that **succeeded** this run is removed unless its page check confirms it is open. This replaces the 7-day grace period.
     - A **failed source** removes nothing on feed absence; its jobs stay unless their own page check says closed.
     - An **inconclusive** check (timeout, 5xx, 403/429, captcha, unknown page) keeps the job if its feed still lists it. If the feed also dropped it, it stays for at most 2 runs, then goes.
     - Guard: if one run would remove more than half of a source's jobs, no removals for that source happen, and the health alarm fires (exit 3).
     - The run log and `fetch_runs` show per source how many jobs were checked, open, closed or inconclusive.
     - Offline tests with saved fixtures cover each case: 404, 410, redirect, "no longer available" text, open page, timeout, failed source, and the half-removal guard.
   - Acceptance (site):
     - A saved job that is no longer on the board shows **"No longer available"** on the Saved page. "Apply now" is replaced by a plain link labelled "View original posting". The job stays saved until the student removes it.
     - A shared link `?job=<id>` to a removed job shows "This job is no longer available" and the board below, not an empty panel.
   - Out of scope: deadlines (0 of 40 jobs have one), checks more than once a day or live in the browser, a "report closed job" button, changes to job IDs.
   - Open question for the tech lead: per-source rules for "closed" pages (Arbeitsagentur, Arbeitnow, Adzuna redirects, Workday, Eightfold). Size may grow if a source needs special handling.

## Next

1. **Browser smoke tests in CI** (S): As a student, I want the board to never ship broken, so that it works when I check it between lectures.
   - Acceptance: CI loads the built site in a headless browser and checks that the job list renders, a filter narrows it, a job opens, and a bookmark survives a reload. A failure blocks the PR.
2. **Privacy-friendly usage analytics** (S): As a student, I want the team to know which filters and jobs people use, so that the board improves where it matters, without being tracked.
   - Acceptance: cookieless and free, no personal data and no consent banner needed. It counts visits, filter use, and "Apply now" clicks. The privacy note on the site says what is counted.
3. **More cities** (L): As a student in Leipzig or Chemnitz, I want the same board for my city, so that I find local student jobs as easily.
   - Acceptance: choose a city with the location filter in the URL. Dresden stays the default. Classifier accuracy stays at or above 90% for every city.
   - Blocked by: serving the job list from the CDN first (docs/capacity.md: do it before a second city).
4. **AI feature** (M, open): As a student, I want help judging fit quickly (for example a plain-English summary of hours, language and deadline), so that I can skip reading long German postings.
   - Open question: which outcome exactly? It must run at no cost, e.g. once a day in the fetcher. No per-visit calls to a paid API.
5. **Custom domain** (S, **shareholder decision: ~€10/year**): As a student, I want a short, trustworthy address, so that I remember it and can share it with classmates.
   - Acceptance: the domain serves production, the vercel.app address redirects to it, and saved jobs and the theme carry over.

## Fixes (from the release reviews)

Non-blocking findings; the tech lead decides the order. Most are small.

1. **Duplicate jobs from GlobalFoundries** (should-fix, M): the same posting appears under two company names and with cut-off titles. Changes job IDs, which resets "New" badges, so it ships in its own release.
2. **HiWi + thesis posting gets through** (Otto decides, S): "Studentische Hilfskraft mit anschließender Abschlussarbeit" shows as a thesis.
3. **Employer feeds can be cut off silently** (should-fix, S): Infineon, GlobalFoundries, Bosch, Fraunhofer and Amazon stop at a page cap (150–500 postings; today's counts are 6–60). If a site grows past it, the missing postings count as closed. Make `fetch()` fail when it hits the cap, so the source counts as failed and nothing is removed.
4. **Small items** (nice-to-have, S):
   - the Saved page title lacks "[STAGING]" on staging
   - an outdated comment in `web/.env.example`
   - the clear-search button drops keyboard focus
   - the manual "Run workflow" button defaults to production; switch the default to staging

## Later

- **Login / accounts** (L): As a student, I want my saved jobs on my phone and my laptop, so that I don't lose them. Waits: bookmarks in the browser cover the need today. Accounts bring privacy, security and support costs. Look at it again only if students ask for sync.

## Done (sprint 1: safe shipping)

- Production moved from Render to Vercel (dresden-jobs.vercel.app). The old address forwards before first paint and carries the path, saved jobs and the theme over.
- Separate staging: its own Supabase project, a STAGING banner and title, noindex, and a Vercel login.
- Only the GitHub Action writes production (`ALLOW_PRODUCTION_WRITE`). Local runs and previews use staging.
- More accurate job list: frontend academies, maintenance/repair and consulting roles are dropped (~94% of kept jobs are real tech roles).
- Capacity note with a switch point: serve the job list from the CDN at 100 jobs or above 2.5 GB/month of Supabase egress.
- Team workflow (docs/workflow.md) with branch protection and CI on every PR.
