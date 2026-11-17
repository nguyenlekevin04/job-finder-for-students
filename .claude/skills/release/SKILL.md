---
name: release
description: Run the team's release workflow: merge the sprint PR into main and verify production (Iris UI/UX approval, review-team bug test, Otto acceptance, shareholder report and OK, merge, production check). Use when the user types /release or asks to ship to production.
---

# /release: sprint PR → `main` → production check

Follow `docs/workflow.md` (phase 7). You are the tech lead and speak for the whole team. The user is the shareholder: they get one report and give the final OK. **Never merge into `main` without their explicit OK in this conversation.**

Team agents live in `.claude/agents/`. If they aren't available as agent types, start general-purpose agents and tell each one to read and follow its file.

## Steps

0. **Dead-code cleanup** (once per sprint, before the release; see `docs/workflow.md`): `code-reviewer` lists dead code with evidence, you confirm, `review-fixer` deletes it on `chore/cleanup-sprint-<n>`, checks stay green, and it ships in the sprint PR. Skip it only for a hotfix release.
1. **Scope.** `git fetch` and list what ships in the sprint PR into `main` (`gh pr view <n>`, `git diff --stat origin/main...<branch>`). If nothing differs, tell the shareholder and stop. CI must be green.
2. **Sprint pull request:** the PR into `main` from `/feature` (or open it with `gh pr create --base main` and the template). It must merge with a **merge commit** (never squash).
3. **Site to check.** There is no staging site. Check a local build (`cd web && npm run build`, then the `static-site` preview from `.claude/launch.json`). Vercel PR previews still build but aren't part of the flow.
4. **Team review, in parallel, only what this release needs** (the PR was already code-reviewed):
   - **Review team (QA), always:** a click-through on the local build (search, filters, open job, save, Saved page, back/forward, plus what changed), and a skim of the PR diff (`origin/main...<branch>`) for anything unreviewed. Use a general-purpose agent with the browser, told to follow `.claude/agents/code-reviewer.md`.
   - **Iris, only if `web/` changed visibly:** UI/UX on the local build: minimal, clean, intuitive, mobile at 375px, dark mode, keyboard and contrast. Verdict: approve or block, with concrete findings.
   - **Otto, only if a user story ships:** acceptance criteria (from `docs/backlog.md` and the PR descriptions). Verdict per story.
   - Kevin is not part of the release review; `/hackerattack` runs separately, once per sprint before the release.
5. **Decide.** Verify every finding against the code yourself. A blocking finding goes back through `/feature` as a fix on the sprint branch, then restart at step 1. Non-blocking ones go to `docs/backlog.md`.
6. **Shareholder report** (plain words, no jargon):
   - What ships, from the student's point of view.
   - Team verdicts: Iris, review team, Otto.
   - What was found, and how each finding was handled.
   - Risks and the rollback plan.
   - Your recommendation: ship or don't.
   Then ask for the OK.
7. **After the OK:**
   1. **Production prerequisites first, before merging:**
      - Schema changes: if `git diff origin/main...<branch> -- supabase/schema.sql` isn't empty, apply the new statements to the production project (the Supabase MCP is bound to production) and verify with a read-only REST select. Code that selects new columns breaks the site and the daily fetch if this is skipped.
      - New `NEXT_PUBLIC_*` variables in the Production environment in Vercel.
   2. `gh pr merge <n> --merge`. Wait for the Vercel production deployment, then check `https://dresden-jobs.vercel.app`: it loads, it reads the production Supabase project, there's no STAGING banner, and the Saved page works. If it's broken, roll back in Vercel (promote the previous production deployment) and tell the shareholder.
   3. **Production fetch:** run "Update jobs" (or wait for the schedule) and check it succeeds and the board shows today's jobs.
8. Close out: update `docs/backlog.md` (done items) and memory if something changed.
