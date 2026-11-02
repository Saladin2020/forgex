# Git, PR and CI flow

## Branch per task
```bash
git status --porcelain            # must be understood before touching anything
git switch -c forgex/<taskId>     # from an up-to-date main
git rev-parse --short HEAD        # record as contract.git.baseCommit
```
- Workers branch from the lead's branch: `forgex/<parentTaskId>/<worker>`.
- Never commit unrelated user changes. If the working tree is dirty with someone else's work, stash it only with permission, or work in a `git worktree`.

## Commits
- Keep commits small and focused. Use the message `<type>(<taskId>): <what>`, for example `feat(date-label-001): compact date label`.
- Never commit `.env*`, keys or dumps. gitleaks and `.gitignore` back this up, but you remain the first line of defence.

## Pull request
- Use the title `[<MODE>] <taskId>: <objective>`.
- The body is the output of `scaffold.py render forgex/tasks/<taskId>.json`. It covers the AC table with statuses, the evidence (commands and the preview URL), the discoveries, the budget and the rollback runbook (GUARDED only).
- Keep the PR to one task. If it grows past about 400 changed lines, split it or go back to G1.
- GUARDED PRs need human review and must not be auto-merged.
- Merge only after CI is green, and use a squash merge. Never force-push a shared branch.

## CI (`.github/workflows/forgex.yml`)
CI runs these jobs:
1. `validate`: `npm ci && node tools/validate.mjs` runs the schemas, the policy, the examples and every `forgex/tasks/*.json` contract committed in the project.
2. `gitleaks`: a full-history secret scan (`gitleaks/gitleaks-action@v2`).
3. Projects add their own lint, typecheck, test and build jobs. Vercel builds the preview through its Git integration.

Every mode stores `forgex/tasks/<taskId>.json`. CI validates every file there, in all tiers, and gitleaks always runs. The PR body is the output of `scaffold.py render`. The optional pre-commit hook `tools/hooks/pre-commit` validates staged contracts locally; enable it with `git config core.hooksPath <forgex>/tools/hooks`.
