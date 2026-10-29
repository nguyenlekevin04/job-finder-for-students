---
name: feature
description: Run the team's development workflow for a new feature, from idea to a pull request into staging (Otto → tech design → Iris → build → review team). Use when the user types /feature <idea> or asks the team to build a feature.
---

# /feature: idea → pull request into `staging`

Follow `docs/workflow.md` (phases 1–6). You are the tech lead. The user is the shareholder: report to them in plain words and ask them only for decisions that are theirs (priority conflicts, anything that costs money, scope cuts).

Team agents live in `.claude/agents/`. If `otto`, `iris`, `code-reviewer` or `review-fixer` aren't available as agent types, start a general-purpose agent and tell it to read and follow its file.

## Steps

1. **Priority.** Brief Otto with the idea (`$ARGUMENTS`) and current state. He returns a user story, acceptance criteria and its place in `docs/backlog.md`. Check feasibility and free-tier cost. If the idea isn't worth it now, say so to the shareholder and stop.
2. **Technical design.** Write a short plan: files, data/schema changes (staging first), risks, tests, rollback. Keep it in the pull request description later.
3. **UX design** (skip only for changes with no visible effect). Brief Iris with the story and your plan; she returns the design. Settle disagreements yourself, and give the reason.
4. **Build** on `feature/<short-name>` from `staging`. Tests for new logic. Run locally: `python -m pytest fetcher/tests -q`; in `web/`: `npm run lint`, `npx next typegen && npx tsc --noEmit`, `npm test`, `npm run build`. Check visible changes in the browser.
5. **Code review, scaled to risk** (see `docs/workflow.md` phase 5). Run `code-reviewer` on the branch diff (`git diff staging...HEAD`) and verify each finding yourself. Small change: fix confirmed findings directly; re-review only non-trivial fixes. Normal change: pass confirmed findings to `review-fixer`, then run `code-reviewer` once more on the fixes. Brief agents with the files that matter, not the whole repo. Commit.
6. **Pull request into `staging`** with `gh pr create --base staging`, filling `.github/pull_request_template.md`. Don't merge with red checks.

## Report to the shareholder

Short: what was built, how it was checked, what the review found and how each finding was handled, open risks, and the pull request link. Then offer `/release` if the shareholder wants it live.
