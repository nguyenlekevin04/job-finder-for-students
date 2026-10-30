# Backlog

Owner: Otto (product owner). Ranked by value to students against effort. Free tiers only; anything that costs money goes to the shareholder.

## Now

_Empty: sprint 3 is being released._

**Release gate (shareholder):** the production release waits until `NEXT_PUBLIC_OPERATOR_STREET` and `_CITY` are set in Vercel production and the site is redeployed, so the imprint and privacy pages show no "Draft" note. Don't hide the legal pages instead.

## Next

1. **Privacy-friendly usage analytics** (S): As a student, I want the team to know which filters and jobs people use, so that the board improves where it matters, without being tracked.
   - Acceptance: cookieless and free, no personal data and no consent banner needed. It counts visits, filter use, and "Apply now" clicks. The privacy note on the site says what is counted.
2. **More cities** (L): As a student in Leipzig or Chemnitz, I want the same board for my city, so that I find local student jobs as easily.
   - Acceptance: choose a city with the location filter in the URL. Dresden stays the default. Classifier accuracy stays at or above 90% for every city.
   - Blocked by: serving the job list from the CDN first (docs/capacity.md: do it before a second city).
3. **AI feature** (M, open): As a student, I want help judging fit quickly (for example a plain-English summary of hours, language and deadline), so that I can skip reading long German postings.
   - Open question: which outcome exactly? It must run at no cost, e.g. once a day in the fetcher. No per-visit calls to a paid API.
4. **Custom domain** (S, **shareholder decision: ~€10/year**): As a student, I want a short, trustworthy address, so that I remember it and can share it with classmates.
   - Acceptance: the domain serves production, the vercel.app address redirects to it, and saved jobs and the theme carry over.

## Fixes (from the release reviews)

Non-blocking findings; the tech lead decides the order. Most are small.

0. **Employer closure isn't remembered** (security, M; attack #2 re-check): when an employer closes a job, an exact-title copy on a job board can reappear the next day as its own job ("New", the copy's link and pay). Store tombstones (`closed_jobs(id, closed_on)`, schema change) and reject partial-only jobs with those ids for 30 days.

1. **Duplicate jobs from GlobalFoundries** (should-fix, M): the same posting appears under two company names and with cut-off titles. Changes job IDs, which resets "New" badges, so it ships in its own release.
2. **HiWi + thesis posting gets through** (Otto decides, S): "Studentische Hilfskraft mit anschließender Abschlussarbeit" shows as a thesis.
3. **Supply chain hardening** (security, S): pin GitHub Actions to commit SHAs and restrict allowed actions; add `pip-audit` to CI; a full `script-src` CSP with hashes for the two inline scripts; a lock file with hashes (`pip-compile --generate-hashes`) for transitive Python dependencies (`docs/security.md`, attack #1).
4. **Small items** (nice-to-have, S):
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

## Done (sprint 3: launch to students)

- **Imprint and privacy pages** (`/imprint/`, `/privacy/`), linked from the footer. Privacy covers Vercel logs, Supabase requests, the three localStorage keys, no cookies and no tracking. Accepted on staging; **production only once the postal address is filled** (see the release gate under Now).
- **Hours and pay**: shown only when the posting states them, in the row and the open job; "Up to 20 h/week" filter (`?hours=20`) keeps only jobs with stated hours ≤ 20. Hand check: 0 wrong values in 110 postings.
- **New since your last visit**: "Welcome back, N new jobs, Since Tuesday" with "Show only new" (`?since=`, shareable) and "New" badges. The mark is local only, moves after a 30-minute break, and with storage blocked the board falls back to "Fresh this week".
- **Share a job**: native share sheet on phones (title, company, `?job=` link), "Copy link" plus "Link copied" elsewhere. No tracking parameters.
- Reliability: browser smoke tests in CI (24 Playwright tests block the PR); employer feeds fail loudly at their page cap instead of dropping postings; security fixes.

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
