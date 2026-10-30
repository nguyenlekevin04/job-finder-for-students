# Backlog

Owner: Otto (product owner). Ranked by value to students against effort. Free tiers only; anything that costs money goes to the shareholder.

## Now

**Sprint 4 (lean): usage analytics and fixes.**

- **Privacy-friendly usage analytics** (Next #1): built, off until the shareholder creates the Umami Cloud account and sets `NEXT_PUBLIC_UMAMI_WEBSITE_ID` in Vercel Production. Counts page views, filter use and "Apply now" clicks; the privacy page gets a "Usage statistics" section once it's on.
- **Moved links** (Fixes 0b): done, see below.
- **Employer closure memory** (Fixes 0): done, needs the `closed_jobs` table in each database before it's active.
- **Supply chain:** `pip-audit` in CI (rest of Fixes 3 already done or still open, see below).

## Next

1. **More cities** (L): As a student in Leipzig or Chemnitz, I want the same board for my city, so that I find local student jobs as easily.
   - Acceptance: choose a city with the location filter in the URL. Dresden stays the default. Classifier accuracy stays at or above 90% for every city.
   - Blocked by: serving the job list from the CDN first (docs/capacity.md: do it before a second city).
2. **AI feature** (M, open): As a student, I want help judging fit quickly (for example a plain-English summary of hours, language and deadline), so that I can skip reading long German postings.
   - Open question: which outcome exactly? It must run at no cost, e.g. once a day in the fetcher. No per-visit calls to a paid API.
3. **Custom domain** (S, **shareholder decision: ~€10/year**): As a student, I want a short, trustworthy address, so that I remember it and can share it with classmates.
   - Acceptance: the domain serves production, the vercel.app address redirects to it, and saved jobs and the theme carry over.

## Fixes (from the release reviews)

Non-blocking findings; the tech lead decides the order. Most are small.

1. **Duplicate jobs from GlobalFoundries** (should-fix, M): the same posting appears under two company names and with cut-off titles. Changes job IDs, which resets "New" badges, so it ships in its own release.
2. **HiWi + thesis posting gets through** (Otto decides, S): "Studentische Hilfskraft mit anschließender Abschlussarbeit" shows as a thesis.
3. **Supply chain hardening** (security, S): left from attack #1 (`docs/security.md`): restrict allowed actions in the repository settings (shareholder, one click), and a full `script-src` CSP with hashes for the two inline scripts plus `https://cloud.umami.is`.

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

## Monetization (to validate)

Nothing here gets built until step 0 shows demand. Guiding rule: students never pay, are never tracked, and every paid placement is labelled. **Taking any money is a shareholder decision**: register a Gewerbe, register with the Finanzamt (Kleinunternehmer §19 UStG up to €25k/year), write B2B terms (AGB), and leave Vercel Hobby, which is non-commercial only (Vercel Pro is $20/month; the tech lead may look at a host that allows commercial use for free). A non-EU student needs the Ausländerbehörde to allow self-employment first.

0. **Validate demand by hand** (S, no code): As the shareholder, I want 5 to 8 Dresden employers (small and mid-size tech firms, startups, institute groups that post student roles) to tell me whether they would pay for a featured student job, so that we build only what someone buys.
   - Acceptance: a one-page offer (what "featured" means, a price of €39 to €49 for 30 days, our audience numbers) goes out by email or in person. The result is written down: who said yes at which price, and why the others said no. **Go** = at least 2 written "yes, we'd buy" at ≥ €39. **No-go** = fewer, and we stop here.
   - Needs: about 4 weeks of visitor numbers from the privacy-friendly analytics (built in sprint 4; on once the Umami account exists), or the offer has nothing to sell.
   - Benchmarks: TU Dresden's Stellenticket charges about €50 per student ad; stellenwerk €79 / €149 per 30 days.
1. **Featured job, sold by hand** (S, after Go): As an employer, I want my student job pinned at the top for 30 days, so that more of the right students see it. As a student, I want sponsored jobs clearly marked, so that I still trust the order of the board.
   - Acceptance: at most 2 featured jobs at a time, each with a visible "Sponsored" label (the "Anzeige" rule, §6 DDG / §5a UWG). It must be a real student role that passes our classifier (no HiWi, no full-time roles). It ends by itself after 30 days. The "Show only new" and filter results stay honest: a featured job appears only if it matches the active filters. Payment by a Stripe Payment Link with an invoice; no payment code on our site. The privacy page and a short "How ranking works" note say that paid placement exists.
2. **Paid post for employers we don't collect** (M): As a small Dresden employer that isn't in our sources, I want to get my student job onto the board, so that local students find it.
   - Acceptance: the employer sends the posting by email; the operator checks it (real company, student role, closing date, non-discriminatory wording per AGG) and adds it by hand. It shows as "Sponsored", has a link that passes `safe_link`, and leaves the board at its deadline or after 30 days. No employer accounts, no self-serve form.
3. **One board sponsor** (S): As a local employer, I want a "Supported by …" line, so that students see us as student-friendly. The board stays free.
   - Acceptance: one sponsor at a time, a text logo or line in the footer, no tracking pixel, labelled as sponsorship. Price to test: €100 to €250 for a semester.
4. **Free support and grants** (S, no revenue risk): ask dresden|exists (TU Dresden founder support) and the student councils (Fachschaftsräte) to share the board, and check whether a public-interest open-source grant would cover hosting. This adds students, which is what makes items 1 to 3 sellable.

**Not doing:** display ads (AdSense etc.: they need a cookie banner under §25 TDDDG and break "no tracking", and earn a few euros a month at our size); a paid tier or paid alerts for students; selling or sharing usage data; employer branding pages (they need far more traffic first; TU Dresden sells profiles for €975+ with the university's name behind it). **Later, only on request:** affiliate links for international students (blocked account, health insurance), each labelled.

## Done (sprint 4)

- **Moved links aren't closures:** a link that now belongs to another of today's jobs (renamed title, copy merged into its employer posting) is `moved`. It still removes its old job, but no longer trips the guard or counts as closed in `fetch_runs` (new `moved` count).
- **Employer closures are remembered** (security, attack #2 re-check): a job its employer closed can't come back for 30 days through a job-board copy with the same title (`closed_jobs` table).
- `pip-audit` checks the hashed Python lock in CI. Already done earlier and now off the list: SHA-pinned actions, the hashed lock, the four small items (Saved title on staging, `.env.example`, clear-search focus, "Update jobs" defaults to staging).

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
