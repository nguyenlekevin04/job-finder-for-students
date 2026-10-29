---
name: release
description: Run the team's release workflow from staging to production (release PR, Iris UI/UX approval, review-team bug test, Otto acceptance, shareholder report and OK, merge, production check). Use when the user types /release or asks to ship staging to production.
---

# /release: `staging` → `main`

Follow `docs/workflow.md` (phase 7). You are the tech lead and speak for the whole team. The user is the shareholder: they get one report and give the final OK. **Never merge into `main` without their explicit OK in this conversation.**

Team agents live in `.claude/agents/`. If they aren't available as agent types, start general-purpose agents and tell each one to read and follow its file.

## Steps

0. **Dead-code cleanup** (once per sprint, before the release; see `docs/workflow.md`): `code-reviewer` lists dead code with evidence, you confirm, `review-fixer` deletes it on `chore/cleanup-sprint-<n>`, checks stay green, and the PR merges into `staging`. Skip it only for a hotfix release.
1. **Scope.** `git fetch` and list what ships: `git log --oneline origin/main..origin/staging` and `git diff --stat origin/main...origin/staging`. If nothing differs, tell the shareholder and stop.
2. **Release pull request:** `gh pr create --base main --head staging --title "Release: <summary>"` with the template. It must merge with a **merge commit** (never squash), so `staging` and `main` stay in sync.
3. **Staging site.** It's the Vercel preview of the `staging` branch (needs a Vercel login). Get a link the agents' browser can open with the Vercel MCP (`get_access_to_vercel_url` or a share link), and check that it shows the STAGING banner and staging data.
4. **Team review, in parallel, only what this release needs** (each PR into `staging` was already code-reviewed):
   - **Review team (QA), always:** a click-through on the staging link (search, filters, open job, save, Saved page, back/forward, plus what changed), and a skim of the release diff (`origin/main...origin/staging`) for anything unreviewed. Use a general-purpose agent with the browser, told to follow `.claude/agents/code-reviewer.md`.
   - **Iris, only if `web/` changed visibly:** UI/UX on the staging link: minimal, clean, intuitive, mobile at 375px, dark mode, keyboard and contrast. Verdict: approve or block, with concrete findings.
   - **Otto, only if a user story ships:** acceptance criteria (from `docs/backlog.md` and the PR descriptions). Verdict per story.
   - Kevin is not part of the release review; `/hackerattack` runs separately, once per sprint before the release.
5. **Decide.** Verify every finding against the code yourself. A blocking finding goes back through `/feature` as a fix into `staging`, then restart at step 1. Non-blocking ones go to `docs/backlog.md`.
6. **Shareholder report** (plain words, no jargon):
   - What ships, from the student's point of view.
   - Team verdicts: Iris, review team, Otto.
   - What was found, and how each finding was handled.
   - Risks and the rollback plan.
   - Your recommendation: ship or don't.
   Then ask for the OK.
7. **After the OK:** `gh pr merge <n> --merge`. Wait for the Vercel production deployment, then check `https://dresden-jobs.vercel.app`: it loads, it reads the production Supabase project, there's no STAGING banner, and the Saved page works. If it's broken, roll back in Vercel (promote the previous production deployment) and tell the shareholder.
8. Close out: update `docs/backlog.md` (done items) and memory if something changed.
