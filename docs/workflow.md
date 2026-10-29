# Team workflow

How a feature goes from idea to production. The user is the **shareholder**: they decide what matters and give the final OK for every production release. Everything else is run by the tech lead (the main Claude session) with the team agents in `.claude/agents/`.

Run it with the skills in `.claude/skills/`:
- `/feature <idea>`: phases 1–6, ending in a pull request into `staging`.
- `/release`: phase 7, `staging` → `main`.
- `/hackerattack [focus]`: a security attack by Kevin with triage and fixes. Run it after features that touch data, secrets or the workflows, and before anything with logins.

## Roles

| Role | Who | Owns | Never does |
|---|---|---|---|
| Shareholder | the user | priorities, the final production OK | — |
| Tech lead | main session | technical design, building, decisions on findings, merging | approve production without the shareholder |
| Product owner | `otto` | user stories, acceptance criteria, priority, acceptance at the end | write code |
| UI/UX | `iris` | look, flow, copy and accessibility; keeps the site minimal, clean and intuitive | write code |
| Ethical hacker | `kevin` | attacks our own system and proves holes (`/hackerattack`) | touch production data, attack third parties, use real secrets |
| Review team | `code-reviewer` (read-only), `review-fixer` | bugs, security and quality; browser bug test on staging | review its own fixes, add features |

**Separation of duties:** whoever writes a change doesn't approve it. The tech lead builds; the review team reviews. Fixes from `review-fixer` are checked again by `code-reviewer` before they count.

## Development: idea → pull request into `staging`

1. **Priority** (Otto + tech lead): Otto writes the user story with acceptance criteria and ranks it in `docs/backlog.md`. The tech lead checks feasibility and cost (free tiers only; anything that costs money goes to the shareholder).
2. **Technical design** (tech lead): a short plan with files, data and schema changes, risks, tests and the rollback path.
3. **UX design** (Iris + tech lead): Iris says how it should look and behave; the tech lead says what's feasible. They agree before building.
4. **Build** (tech lead): a feature branch (`feature/<name>`), small commits, tests for new logic, CI green.
5. **Code review** (review team + tech lead): `code-reviewer` lists findings. The tech lead decides which are valid. `review-fixer` applies those, then `code-reviewer` checks the fixes.
6. **Pull request into `staging`** (tech lead), using the template checklist. It merges when CI is green and every box is checked.

## Testing → production: `staging` → `main`

7. **Release** (`/release`):
   1. The tech lead opens the release pull request `staging` → `main` (merge commit, never squash, so the branches stay in sync).
   2. On the staging site:
      - **Iris** approves the UI/UX: minimal, clean, intuitive, mobile, dark mode, accessibility.
      - The **review team** reviews the release diff for bugs and security, and clicks through the staging site in the browser.
      - **Otto** checks every acceptance criterion.
   3. The tech lead weighs the findings and writes the **shareholder report**: what ships, what was found and fixed, open risks, and a recommendation.
   4. The **shareholder** gives the OK, or says no.
   5. The tech lead merges, then checks production: the site loads, it reads the production database, and there's no banner. If anything is wrong, it's rolled back in Vercel (instant rollback to the previous deployment).

A finding that blocks the release sends the work back to phase 4 on a fix branch; that fix goes into `staging` through its own pull request.

## Guarantees that don't rely on the process

- Branch protection on `main` and `staging`: a pull request with "Fetcher tests" and "Website checks" green, admins included, with no force-push and no deletion.
- Only the scheduled GitHub Action writes to the production database (`ALLOW_PRODUCTION_WRITE`); local runs and previews use staging.
- Vercel previews are noindex, carry the STAGING banner and need a Vercel login.
