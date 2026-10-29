---
name: hackerattack
description: Run a security attack on our own system with Kevin (ethical hacker), triage his findings as tech lead, have the review team fix the confirmed ones, and let Kevin re-attack to verify. Use when the user types /hackerattack (optionally with a focus, e.g. "/hackerattack auth") or asks Kevin to attack the system.
---

# /hackerattack: Kevin attacks, the team fixes

You are the tech lead. Kevin (`.claude/agents/kevin.md`) is the team's ethical hacker. The user is the shareholder: they get one short security report at the end.

If `kevin`, `code-reviewer` or `review-fixer` aren't available as agent types, start a general-purpose agent and tell it to read and follow its file. Kevin's rules of engagement in his file are hard limits: own system only, staging for anything that writes, read-only on production, no denial of service, never use real secrets.

## Steps

1. **Scope.** Focus: `$ARGUMENTS` if given; otherwise the whole system. Tell Kevin:
   - what changed since the last attack (`git log` since the last "Security:" commit or entry in `docs/security.md`)
   - the current staging and production URLs.
2. **Attack.** Run Kevin. He returns findings with severity, proof, "tried and held", "not tested" and "cleanup".
3. **Triage (you).** Reproduce or verify every finding yourself, against the code or with a safe request on staging. For each one, decide:
   - **fix now:** critical, high, or cheap medium
   - **backlog:** the rest
   - **no action:** with the reason
   Production-affecting critical findings are reported to the shareholder immediately, before fixing.
4. **Fix.** Give the confirmed "fix now" findings to `review-fixer` (with Kevin's proof). Then `code-reviewer` checks the fixes.
5. **Verify.** Run Kevin again, only on the fixed findings, to confirm they're closed.
6. **Ship.** Commit on `security/<short-name>`, open a PR into `staging` with the template, and merge it when green. Fixes reach production with the next `/release`, which needs the shareholder's OK.
7. **Record.** Append a dated entry to `docs/security.md`:
   - scope
   - findings with severity and status (fixed, backlog, accepted)
   - what held
   Backlog items also go into `docs/backlog.md` under Fixes.

## Report to the shareholder

Plain words, short:
- the overall verdict
- each finding in one line: what an attacker could do, and its status
- what's still open
- the PR link

Never include secrets or working exploit payloads against production.
