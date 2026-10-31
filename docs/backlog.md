# Backlog

Owner: Otto (product owner). Ranked by value to students against effort. Free tiers only; anything that costs money goes to the shareholder.

## Now

### MVP (from Lena's interview, 2026-10-31)

Goal: a board a busy international student trusts and comes back to, as fast as possible. Each story ships to production on its own, in this order. Students never pay. **No account in the MVP**: everything stays in the browser, and alerts work by email with double opt-in.

1. ✅ **AI/ML list without noise** (S, shipped 2026-10-31): As a CS/AI student, I want the AI/ML filter to show only AI/ML roles and no HiWi posts, so that I trust the list and don't waste time.
   - Acceptance: the five postings Lena named (climate consulting, "Digital Functional Verification", Backoffice, Kalibrierlabor, Elektrotechnik) are not tagged AI/ML, each as a test case in `test_classify.py`. "Studentische Hilfskraft" / HiWi is dropped even when combined with a thesis ("… mit anschließender Abschlussarbeit"). A hand check of the AI/ML filter on production finds ≤ 1 wrong job in 20. Every row shows its age ("3 days ago"); the tech lead checks which jobs looked "old" to Lena and fixes the cause if it is a bug.
2. ✅ **Search that understands AI words** (S, shipped 2026-10-31): As a student, I want "machine learning", "ML", "KI", "AI", "LLM" and "deep learning" to find each other, so that one search finds everything relevant.
   - Acceptance: searching any word of a synonym group gives the same results as its strongest term; "machine learning" returns at least as many jobs as the AI/ML filter. Groups also cover German/English pairs (Informatik/computer science, Datenanalyse/data analysis) and umlauts (ä/ae). Search text is still never sent to analytics.
3. **Scan on the phone** (S): As a student on my phone between lectures, I want to see jobs on the first screen and snippets that start with the role, so that I can judge a job in seconds.
   - Acceptance: on a 390×844 viewport the first job row is visible without scrolling (filters fold away, Playwright check). Snippets of the top 5 employers by job count start with the role, not company boilerplate. After a reload the active filters are still there (URL), checked in a smoke test.
4. **The facts I decide on** (M): As an international student, I want the required German level, the deadline, the pay and where "Apply" leads, so that I only open jobs I can actually get.
   - Acceptance: each job shows German level as "English OK", "German B1–B2" or "German C1+" when the posting says so (else nothing, never a guess), and a "German level" filter. Deadline and pay show when stated; a hand check of 50 postings finds 0 wrong values. Jobs past their deadline leave the board. The Apply button names its target ("Apply at Fraunhofer", "View on arbeitnow.com") and uses the employer link when we have one.
   - Notes: new column → schema, `COLUMNS`, types and `JOB_SELECT` in sync.
5. **Track my applications** (S): As a student applying to several jobs, I want to mark saved jobs as applied / interview / offer / rejected with a date, so that I keep track without a spreadsheet.
   - Acceptance: status and date are set from the Saved page and the open job, stored in localStorage only, survive a reload, and the Saved page can filter by status. Works with storage blocked (no crash, a short notice). No account.
6. **Weekly email alert for a search** (M–L, **shareholder action: create a Resend account and buy the custom domain, ~€10/year**, needed to send mail to students): As a student, I want one email a week with new jobs for my saved search, so that I don't have to check the board.
   - Acceptance: "Email me new jobs for this search" takes an email address only (no account, no password). Double opt-in: nothing is sent until the student clicks the confirm link. At most one email a week, only when there are new matches, each with a one-click unsubscribe (and `List-Unsubscribe` header). At most 3 alerts per address; unconfirmed sign-ups are deleted after 48 h. The privacy page names the email provider and the stored data; "delete my data" works from any email. Rate limit on sign-ups.
   - Gate: `/hackerattack alerts` (Kevin) before production: email bombing, enumeration, unsubscribe/confirm token guessing, injection into email content.
   - Notes: needs a small server part (e.g. a Supabase Edge Function for sign-up/confirm) and a weekly GitHub Action to send; the tech lead decides. No login needed for this.

**Open step (shareholder):** the `closed_jobs` table still has to be created in the **staging** project (URL contains `dszz`). Production has it. Until then staging runs without the closure memory and logs a warning.

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
2. ~~HiWi + thesis posting gets through~~: moved into MVP story 1 (Otto: drop it).
3. **Restrict allowed GitHub Actions** (security, S, shareholder): one click in the repository settings.
5. **Check the Umami volume after a week** (S): the free plan is capped by monthly events; filter events fire on every change.

## Later

- **Pages search engines can read** (M): per-job and per-company pages built at deploy time, so students find jobs on Google. Waits for serving the job list from the CDN (docs/capacity.md); today all jobs render in the browser only.
- **RSS / calendar feed of deadlines** (S–M): few students use RSS; a static feed needs a rebuild or public storage after each fetch. After the CDN switch.
- **Instant thesis alerts / push notifications** (M): weekly email first; instant only if students ask after MVP 6 (push needs a service worker and more security work).
- **Thesis group, supervisor and contact email** (M): HZDR/Fraunhofer pages state them inconsistently, and publishing personal emails needs care; revisit after MVP 4 shows how reliable extraction is.
- **Sync of saved jobs and status across devices** (L): needs login (see below); MVP keeps everything in the browser and alerts work without an account.
- **Make the imprint easier to find** (S): it is in the footer and legally fine; not a student need.
- **Company pages** (M): little value at today's ~100 jobs from a few dozen employers; the company filter/search covers it.

- **Login / accounts** (L): As a student, I want my saved jobs on my phone and my laptop, so that I don't lose them. Waits: bookmarks in the browser cover the need today. Accounts bring privacy, security and support costs. Look at it again only if students ask for sync. Lena (2026-10-31) wants it only for alerts and sync, via magic link or Google, never a password/CV/profile, and saving must never need an account; MVP 6 covers alerts without it.
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
   - Needs: about 4 weeks of visitor numbers from the privacy-friendly analytics (built in sprint 4; counting starts with the sprint 4 release), or the offer has nothing to sell.
   - Benchmarks: TU Dresden's Stellenticket charges about €50 per student ad; stellenwerk €79 / €149 per 30 days.
1. **Featured job, sold by hand** (S, after Go): As an employer, I want my student job pinned at the top for 30 days, so that more of the right students see it. As a student, I want sponsored jobs clearly marked, so that I still trust the order of the board.
   - Acceptance: at most 2 featured jobs at a time, each with a visible "Sponsored" label (the "Anzeige" rule, §6 DDG / §5a UWG). It must be a real student role that passes our classifier (no HiWi, no full-time roles). It ends by itself after 30 days. The "Show only new" and filter results stay honest: a featured job appears only if it matches the active filters. Payment by a Stripe Payment Link with an invoice; no payment code on our site. The privacy page and a short "How ranking works" note say that paid placement exists.
2. **Paid post for employers we don't collect** (M): As a small Dresden employer that isn't in our sources, I want to get my student job onto the board, so that local students find it.
   - Acceptance: the employer sends the posting by email; the operator checks it (real company, student role, closing date, non-discriminatory wording per AGG) and adds it by hand. It shows as "Sponsored", has a link that passes `safe_link`, and leaves the board at its deadline or after 30 days. No employer accounts, no self-serve form.
3. **One board sponsor** (S): As a local employer, I want a "Supported by …" line, so that students see us as student-friendly. The board stays free.
   - Acceptance: one sponsor at a time, a text logo or line in the footer, no tracking pixel, labelled as sponsorship. Price to test: €100 to €250 for a semester.
4. **Free support and grants** (S, no revenue risk): ask dresden|exists (TU Dresden founder support) and the student councils (Fachschaftsräte) to share the board, and check whether a public-interest open-source grant would cover hosting. This adds students, which is what makes items 1 to 3 sellable.

**Not doing:** display ads (AdSense etc.: they need a cookie banner under §25 TDDDG and break "no tracking", and earn a few euros a month at our size); a paid tier or paid alerts for students; selling or sharing usage data; employer branding pages (they need far more traffic first; TU Dresden sells profiles for €975+ with the university's name behind it). **Later, only on request:** affiliate links for international students (blocked account, health insurance), each labelled.

## Done (sprint 5)

- **No third-party code on the site:** the Umami tracker is a pinned copy served from our own origin.
- **Strict Content-Security-Policy per page:** only our scripts (hashed inline ones included) run, and the browser only talks to us, Supabase and Umami. An injected script is blocked.
- Tombstones are read in pages, so the list can't be cut off.

## Done (sprint 4, released 2026-10-30)

- **Moved links aren't closures:** a link that now belongs to another of today's jobs (renamed title, copy merged into its employer posting) is `moved`. It still removes its old job, but no longer trips the guard or counts as closed in `fetch_runs` (new `moved` count).
- **Usage counts** (Umami Cloud, cookieless): page views without query strings, filters turned on (never search text) and "Apply now" clicks by source; Do Not Track respected. Live in production; the privacy page has a "Usage statistics" section.
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
