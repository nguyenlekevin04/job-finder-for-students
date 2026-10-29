# Backlog

Owner: Otto (product owner). Ranked by value to students against effort. Free tiers only; anything that costs money goes to the shareholder.

## Now

_Empty: sprint 1 is being released._

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

## Fixes (from the sprint 1 release review)

Non-blocking findings; the tech lead decides the order. Most are small.

1. **Predictive-maintenance jobs are dropped** (should-fix, S): the hands-on title rule removes ML roles like "Masterarbeit Predictive Maintenance". Exclude "predictive maintenance" / "vorausschauende Wartung" from `HANDS_ON_TITLE` and add test cases.
2. **Vercel can skip a needed build** (should-fix, S): `ignoreCommand` in `web/vercel.json` only compares the last commit. Compare against `VERCEL_GIT_PREVIOUS_SHA` and build when it's missing.
3. **Duplicate jobs from GlobalFoundries** (should-fix, M): the same posting appears under two company names and with cut-off titles. Changes job IDs, which resets "New" badges, so it ships in its own release.
4. **HiWi + thesis posting gets through** (Otto decides, S): "Studentische Hilfskraft mit anschließender Abschlussarbeit" shows as a thesis.
5. **Small items** (nice-to-have, S):
   - the Saved page title lacks "[STAGING]" on staging
   - the production guard should compare the database URL in lowercase
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
