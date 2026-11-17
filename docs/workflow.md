# Team workflow

How a feature goes from idea to production. The user is the **shareholder**: they decide what matters and give the final OK for every production release. Everything else is run by the tech lead (the main Claude session) with the team agents in `.claude/agents/`.

Run it with the skills in `.claude/skills/`:
- `/feature <idea>`: phases 1–6, ending in a pull request into `main`.
- `/release`: phase 7, merge the sprint PR into `main` and verify production.
- `/hackerattack [focus]`: a security attack by Kevin with triage and fixes. Run it after features that touch data, secrets or the workflows, and before anything with logins.

## Roles

| Role | Who | Owns | Never does |
|---|---|---|---|
| Shareholder | the user | priorities, the final production OK | — |
| Tech lead | main session | technical design, building, decisions on findings, merging | approve production without the shareholder |
| Full-stack dev | `mia` | `web/`, `fetcher/`, `supabase/`, workflows: builds the tech lead's tasks on her own branch | design product or UX alone, decide scope, push, merge, touch production |
| Product owner | `otto` | user stories, acceptance criteria, priority, acceptance at the end | write code |
| UI/UX | `iris` | look, flow, copy and accessibility; keeps the site minimal, clean and intuitive | write code |
| Ethical hacker | `kevin` | attacks our own system and proves holes (`/hackerattack`) | touch production data, attack third parties, use real secrets |
| Review team | `code-reviewer` (read-only), `review-fixer` | bugs, security and quality; browser bug test on a local build | review its own fixes, add features |

**Separation of duties:** whoever writes a change doesn't approve it. The tech lead and Mia build; the review team reviews. Fixes from `review-fixer` are checked again by `code-reviewer` before they count.

## Development: idea → pull request into `main`

Production only since 2026-11-17 (solo devs): there is no staging environment. Vercel still builds a preview per pull request (STAGING banner via `NEXT_PUBLIC_DEPLOY_ENV`, reading whatever Supabase project the Preview environment points at), but previews aren't part of the flow.

1. **Priority** (Otto + tech lead): Otto writes the user story with acceptance criteria and ranks it in `docs/backlog.md`. The tech lead checks feasibility and cost (free tiers only; anything that costs money goes to the shareholder).
2. **Technical design** (tech lead): a short plan with files, data and schema changes (applied to production via the Supabase MCP before merge), risks, tests and the rollback path.
3. **UX design** (Iris + tech lead): Iris says how it should look and behave; the tech lead says what's feasible. They agree before building.
4. **Build** (tech lead with Mia):
   - Mia builds the task in an isolated git worktree on its own branch, with tests for new logic. Small changes the tech lead does alone.
   - The tech lead checks the result and runs all checks.
5. **Code review** (review team + tech lead), scaled to the risk of the change:
   - **Small** (docs, copy, config, or about 50 lines without data, security or workflow impact): one `code-reviewer` pass. The tech lead fixes confirmed findings directly. A second pass happens only when a fix isn't trivial.
   - **Normal** (fetcher logic, data, security, workflows, anything students see): `code-reviewer` lists findings, the tech lead decides which are valid, `review-fixer` applies them, and `code-reviewer` checks the fixes.
   - The author never approves their own change: the reviewer always has the last word on a fix.
6. **Pull request into `main`** (tech lead), using the template checklist. It merges in phase 7, when CI is green and every box is checked.

## End of sprint: dead-code cleanup

Before every release, the review team removes dead code:
- **`code-reviewer`** lists dead code with evidence: unused functions, files, components, exports, CSS classes, dependencies (`package.json`, `requirements.txt`), test fixtures, feature flags, and leftovers of removed features. Evidence means no references found with `grep`, plus `npx knip` / `vulture` where they help.
- **`review-fixer`** deletes what the tech lead confirms, on `chore/cleanup-sprint-<n>`. All tests, lint, type-check and the build stay green.
- The cleanup ships in the sprint PR into `main`, so the release review covers it.
- **Kept on purpose:** documented hooks (e.g. `is_enabled()`), temporary code with a dated removal note (e.g. the Render forward), and anything a doc names as an extension point.

## Release: pull request → `main` → production

7. **Release** (`/release`):
   1. The sprint pull request into `main` has CI green. It merges with a merge commit, never squash.
   2. On a local build, only the checks the release needs. Code was already reviewed in the pull request, so there is no second code review here:
      - **Review team (QA):** always. Clicks through the local build in the browser (search, filters, open job, save, Saved page, back/forward, plus what the release changed), and skims the diff for anything unreviewed.
      - **Iris:** only when something visible changed (`web/`). She approves the UI/UX: minimal, clean, intuitive, mobile, dark mode, accessibility.
      - **Otto:** only when a user story ships. He checks every acceptance criterion.
   3. The tech lead weighs the findings and writes the **shareholder report**: what ships, what was found and fixed, open risks, and a recommendation.
   4. The **shareholder** gives the OK, or says no.
   5. The tech lead applies production prerequisites first (schema changes from `supabase/schema.sql` via the Supabase MCP, new Vercel production variables), then merges, then checks production: the site loads, it reads the production database, there's no banner, and the next production fetch succeeds. If anything is wrong, it's rolled back in Vercel (instant rollback to the previous deployment).

A finding that blocks the release sends the work back to phase 4 on a fix branch; that fix goes into the sprint branch or its own pull request into `main`.

**Cadence:** one release per sprint, at the end, so the shareholder approves once. Exception: a **hotfix** for a production bug goes fix PR → `main` right away, still with the shareholder's OK.

**Security:** `/hackerattack` runs once per sprint before the release, and before any feature with logins, personal data or new secrets. Kevin attacks production read-only (anonymous write attempts must be refused; he never writes real data) and reports; he isn't part of code review or release review. The review team fixes his confirmed findings and checks the fixes against his proof.

## Guarantees that don't rely on the process

- Branch protection on `main`: a pull request with "Fetcher tests" and "Website checks" green, admins included, with no force-push and no deletion.
- Only the scheduled GitHub Action writes to the production database (`ALLOW_PRODUCTION_WRITE`); local runs can't. The staging Supabase project and `STAGING_*` secrets are no longer used by the daily job.
- Vercel PR previews are noindex, carry the STAGING banner and need a Vercel login.
