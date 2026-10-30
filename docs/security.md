# Security log

Results of `/hackerattack` runs (Kevin, `.claude/agents/kevin.md`). Newest first. Each entry: scope, findings with severity and status, and what held.

## 2026-10-29: attack #2, sprint 3 changes

**Scope:** everything since attack #1 (21 commits): share, "new since your last visit", imprint and privacy pages, hours and pay extraction, GlobalFoundries twin merging, page caps, the e2e test server, CI supply chain.

**Verdict:** the database, secrets, the e2e server and the new regexes held. One release blocker (availability, not an attack) and one medium data-poisoning chain.

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | High | The production database lacks the new hours/pay columns; merging the release would break the board and the daily fetch | Fixed in the process: `/release` now applies schema changes to production before merging |
| 2 | Medium | A job-board copy of an employer job could add fake pay or hours to it, and take over "Apply now" once the employer closed the job | Fixed: hours and pay come only from the highest-priority posting; twin matching only for Arbeitsagentur copies; a job closes when its employer link closes |
| 3 | Low | An empty or short page before the reported total cut a feed short silently | Fixed: the source fails ("feed ended early") instead |
| 4 | Info | pytest and requests advisories (local temp files); `actions/cache` and `upload-artifact` tag-pinned; `?since=` with a future date shows an odd ticket | Fixed (lock refreshed, SHA-pinned); `?since=` handled in the sprint cleanup |

**Tried and held:** anonymous writes to the new columns (401), ReDoS on 50 KB adversarial inputs (worst 0.08 s), path traversal on the e2e server (404), no operator data in git history or bundles, `?job=`/share/localStorage tampering has no sink, CSP/XFO/HSTS on production, CI without secrets for PRs, `npm audit` 0.

**Not tested:** the staging site in a browser (Vercel login), posting on third-party job boards, production writes, DoS.

## 2026-10-29: attack #1, whole system

**Scope:**
- repo and git history
- staging and production Supabase (production read-only)
- production site, staging preview and the Render forward
- GitHub workflows and dependencies

**Verdict:** nothing critical or high. The database, secrets and CI held.

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | Medium | A posting on an aggregator with the same title and company as a real employer job merged into it: its longer description replaced the employer's text, its earlier date won, and its link (any scheme or host) was added | Fixed: the highest-priority source keeps description and dates; links must be `https://` on the source's known host |
| 2 | Low | No Content-Security-Policy and no frame protection (clickjacking) | Fixed: `frame-ancestors 'none'`, `base-uri`, `object-src`, `form-action`, `X-Frame-Options: DENY`. A full `script-src` needs hashes for the inline scripts (backlog) |
| 3 | Low | A small source (1–2 jobs) that breaks but answers OK lost all its jobs without an alarm | Fixed: alarm when a source's jobs all close in one run |
| 4 | Low | Email sign-up is enabled on both Supabase projects, though the app has no login: anyone can trigger confirmation emails from our project | Open, shareholder step: Supabase → Authentication → Sign In / Providers → disable sign-ups (both projects) |
| 5 | Info | GitHub Actions pinned by tag, not commit SHA; Python dependencies unpinned | Python pinned; actions SHA pinning in backlog |

**Tried and held:**
- **Database:** anonymous insert, update and delete on `jobs` and `fetch_runs` were all refused (401). No RPC functions, no exposed `auth`/`storage` schemas, GraphQL off.
- **Secrets:** no service-role key in git history, the built site or `fetch_runs`. The site bundles contain only the publishable key. Source maps are blocked.
- **XSS through job data:** text is rendered by React, which neutralises `javascript:` hrefs. The `?job=` parameter has no sink. The Render bookmark import requires the old origin as referrer and https links.
- **CI:** fork PRs get no secrets (`pull_request`, read-only token). The `accept_removals` input goes through `env:`, so no shell injection.
- **Staging preview:** locked behind the Vercel login, including its static files.
- `npm audit`: 0 vulnerabilities.

**Not tested:** creating auth users (Kevin's rules), anything that writes to production, load or egress exhaustion (DoS), `pip-audit`.
