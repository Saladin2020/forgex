# Adapter: Next.js + Vercel + Neon

| FORGEX concept | This stack |
|---|---|
| Task isolation | git branch `forgex/<taskId>`, with a Vercel preview per push (Git integration) |
| Evidence for UI/API AC | the Vercel preview URL in `deployment.previewUrl`, recorded as `evidence.kind: "preview-deploy"` after you actually open it or curl it |
| Data changes | a Neon branch `forgex-<taskId>` in `deployment.neonBranch`, with the migration rehearsed there first |
| Preview DB | the Neon–Vercel integration (or a manual preview `DATABASE_URL`) points each preview at its Neon branch, so it never writes to the prod DB |
| Rollback | Vercel Instant Rollback (RB-3) and Neon restore or a down migration (RB-2) |
| Secrets | Vercel Environment Variables per environment and `.env.local` (git-ignored); never `NEXT_PUBLIC_` for secrets |
| GUARDED paths | `**/migrations/**`, `**/auth/**`, `**/.env*`, `middleware.ts`, `vercel.json`, the ORM schema (from `guardedGlobs`, enforced by the rule `forgex-guarded.mdc`) |

## Checks per mode
- **QUICK:** `npm run lint` plus a focused test.
- **STANDARD:** add `tsc --noEmit`, `next build` and the relevant tests, and check the preview URL.
- **GUARDED:** add the migration on the Neon branch, the down migration tested, an auth negative test (an unauthenticated request gets 401/403), a written rollback runbook and human review.

## Migration rules
- Use expand/contract: add nullable columns or new tables first, deploy the code, backfill, then tighten. Never drop or rename in the same deploy as the code that stops using the old name.
- One migration per PR.
- Never run a migration against production from an agent session without explicit authorization.
