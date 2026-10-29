# Backlog

Owner: Otto (product owner). Ranked by value to students against effort. Free tiers only; anything that costs money goes to the shareholder.

## Now (sprint 3: launch to students)

Runs in parallel to the reliability work (browser tests, feed page caps, supply chain). Item 0 blocks the launch; items 1–3 are the visible features, in priority order.

0. **Imprint and privacy page** (S, frontend, **launch blocker**): As a student, I want to see who runs the board and what happens to my data, so that I can trust it.
   - Acceptance: `/imprint/` (Impressum, § 5 DDG) and `/privacy/` (Datenschutzerklärung, GDPR Art. 13) pages, linked from the footer on every page. Privacy covers Vercel hosting logs (IP), Supabase requests from the browser, localStorage (bookmarks, theme, last visit), and analytics if added. No cookies, no consent banner.
   - **Shareholder decision:** the imprint needs a real name and a postal address that can receive mail. Wording isn't legal advice; the shareholder signs off.
1. **Hours and pay in every job** (M, both: Jonas extracts, Mia shows): As a student, I want to see hours per week and pay at a glance, so that I know right away if a job fits around my lectures.
   - Acceptance: the daily fetcher extracts hours per week (e.g. "15–20 h/week") and hourly or monthly pay when the posting states them (German and English wording), saved in new fields (schema, `COLUMNS`, types and `JOB_SELECT` in sync). The job row and the open job show them; if not stated, nothing is shown (no guesses). A "Up to 20 h/week" filter keeps jobs with known hours ≤ 20. A hand check of 30 postings finds no wrong value; tests use saved fixtures.
   - Notes: job IDs don't change. Pay is shown only as stated, never estimated.
2. **New since your last visit** (S, frontend): As a student who checks between lectures, I want to see what's new since I last looked, so that I don't reread the whole list.
   - Acceptance: the browser stores the time of the last visit in localStorage (nothing leaves the device). On return, a line says "5 new since Tuesday" with a one-tap "Show only new" view (in the URL, so it can be shared); those jobs carry the "New" badge. The first visit shows no count. The mark moves forward only on the next visit (not while the page is open), and works with storage blocked (then nothing is shown).
3. **Share a job** (S, frontend): As a student, I want to send a job to a classmate on WhatsApp in one tap, so that we can apply together and the board spreads by word of mouth.
   - Acceptance: a Share button on the open job. On phones it opens the native share sheet (Web Share API) with title, company and the `?job=` link; elsewhere it copies the link and confirms "Link copied". The link opens that job (or the "no longer available" notice). No tracking parameters, no third-party scripts.
   - Out of scope: a per-job preview image (needs per-job pages; see SEO in Later).

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

0. **Employer closure isn't remembered** (security, M; attack #2 re-check): when an employer closes a job, an exact-title copy on a job board can reappear the next day as its own job ("New", the copy's link and pay). Store tombstones (`closed_jobs(id, closed_on)`, schema change) and reject partial-only jobs with those ids for 30 days.

1. **Duplicate jobs from GlobalFoundries** (should-fix, M): the same posting appears under two company names and with cut-off titles. Changes job IDs, which resets "New" badges, so it ships in its own release.
2. **HiWi + thesis posting gets through** (Otto decides, S): "Studentische Hilfskraft mit anschließender Abschlussarbeit" shows as a thesis.
3. **Employer feeds can be cut off silently** (should-fix, S): Infineon, GlobalFoundries, Bosch, Fraunhofer and Amazon stop at a page cap (150–500 postings; today's counts are 6–60). If a site grows past it, the missing postings count as closed. Make `fetch()` fail when it hits the cap, so the source counts as failed and nothing is removed.
4. **Supply chain hardening** (security, S): pin GitHub Actions to commit SHAs and restrict allowed actions; add `pip-audit` to CI; a full `script-src` CSP with hashes for the two inline scripts; a lock file with hashes (`pip-compile --generate-hashes`) for transitive Python dependencies (`docs/security.md`, attack #1).
5. **Small items** (nice-to-have, S):
   - the Saved page title lacks "[STAGING]" on staging
   - an outdated comment in `web/.env.example`
   - the clear-search button drops keyboard focus
   - the manual "Run workflow" button defaults to production; switch the default to staging

## Later

- **Pages search engines can read** (M): per-job and per-company pages built at deploy time, so students find jobs on Google. Waits for serving the job list from the CDN (docs/capacity.md); today all jobs render in the browser only.
- **RSS / calendar feed of deadlines** (S–M): few students use RSS; a static feed needs a rebuild or public storage after each fetch. After the CDN switch.
- **Company pages** (M): little value at today's ~100 jobs from a few dozen employers; the company filter/search covers it.

- **Login / accounts** (L): As a student, I want my saved jobs on my phone and my laptop, so that I don't lose them. Waits: bookmarks in the browser cover the need today. Accounts bring privacy, security and support costs. Look at it again only if students ask for sync.
  - **Technical preconditions (tech lead, fixed before any build):**
    - **Sign-in without passwords:** magic link or OAuth with PKCE (Supabase Auth, free tier). We never store passwords.
    - **Sessions in cookies, not localStorage:** HttpOnly, Secure, SameSite=Lax, `__Host-` prefix, set by the server (Next.js on Vercel with `@supabase/ssr`). This means leaving `output: "export"` for the auth routes, which is an architecture change. A token in localStorage can be stolen by any XSS.
    - **Short-lived tokens:** access token about 1 h, refresh tokens rotated with reuse detection. Logout revokes all sessions (`signOut({ scope: "global" })`). Account deletion removes everything.
    - **CSRF:** SameSite=Lax plus an Origin check on every write.
    - **XSS:** a strict Content-Security-Policy first, because job data comes from third-party feeds.
    - **Data access:** new tables (e.g. `bookmarks`) only with RLS `user_id = auth.uid()`. The existing tables stay read-only for the public.
    - **Law:** privacy policy and imprint, data export and deletion (GDPR). Session cookies are strictly necessary, so no consent banner (TTDSG §25(2)). No tracking cookies.
    - **Before release:** `/hackerattack login` (Kevin) covers session theft, fixation, CSRF, IDOR on bookmarks, open redirects in the login flow, and rate limits on magic links.

## Done (sprint 2: only open jobs)

- **Closed jobs leave the board by the next daily update.** Employer and institute feeds are complete, so a posting they stop listing is removed in that run. Arbeitsagentur and Arbeitnow postings are checked one by one (404/410 = closed). A failed source removes nothing. A job nobody can confirm stays at most 2 days. A guard (≥3 and >50% of a source) blocks mass removals and raises the alarm; the owner can approve once with `accept_removals`. Per-source open/closed/unconfirmed counts are in `fetch_runs`. On the site, a closed saved job shows "Closed", the notice "This job is no longer available." and "View original posting"; a shared link to a removed job shows the notice.
- Adzuna source removed; security fixes from the attack review (docs/security.md).

## Done (sprint 1: safe shipping)

- Production moved from Render to Vercel (dresden-jobs.vercel.app). The old address forwards before first paint and carries the path, saved jobs and the theme over.
- Separate staging: its own Supabase project, a STAGING banner and title, noindex, and a Vercel login.
- Only the GitHub Action writes production (`ALLOW_PRODUCTION_WRITE`). Local runs and previews use staging.
- More accurate job list: frontend academies, maintenance/repair and consulting roles are dropped (~94% of kept jobs are real tech roles).
- Capacity note with a switch point: serve the job list from the CDN at 100 jobs or above 2.5 GB/month of Supabase egress.
- Team workflow (docs/workflow.md) with branch protection and CI on every PR.
