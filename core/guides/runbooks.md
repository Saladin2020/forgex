# Rollback runbooks

Every GUARDED contract names one of these anchors in `deployment.rollbackRunbook`. Before running any step marked ⚠, get explicit authorization. Record each step you run as evidence.

## RB-1: Code-only change, not merged yet
1. `git switch main`. The task branch stays as a record.
2. Close the PR. If the user agrees, delete the remote branch with `git push origin --delete forgex/<taskId>`.
3. Nothing reached production, so there is nothing more to do.

## RB-2: Neon migration
**Before the change (required):**
1. Create a rehearsal branch, either `neonctl branches create --name forgex-<taskId> --parent main` or through the Neon console or MCP `create_branch`.
2. Run the migration against the branch's connection string and run the app's tests against it.
3. Record a restore point by noting the UTC timestamp or LSN just before you apply it to production. Neon instant restore (point-in-time) depends on the project's history retention, so confirm retention ≥ the expected rollback window.
4. Write a **down migration** and test it on the branch.

**To roll back:**
1. Preferred: run the tested down migration.
2. ⚠ Otherwise: restore with `neonctl branches restore main ^self@<RFC3339-timestamp> --preserve-under-name main_before_<taskId>`. The `--preserve-under-name` flag is required and keeps the current state as a backup branch. You can also use Console → Restore. This works only on root branches, and it rewinds **all** writes after that timestamp, so confirm data-loss acceptance first. To undo the restore, restore again from the preserved branch.
3. Verify the row counts and the app's health check, and record the results as evidence.

## RB-3: Vercel production deploy
1. ⚠ Roll back instantly to the last good deployment with `vercel rollback <deployment-url-or-id>` (or Dashboard → Deployments → Instant Rollback). Use `vercel rollback status` to check its state. On the Hobby plan you can only roll back to the immediately previous production deployment. Production then stops auto-assigning new deploys until you promote one again.
2. Fix forward on `forgex/<taskId>-fix`. Once the new preview is verified, return with `vercel promote <url>` (or by promoting it in the Dashboard).
3. If the bad deploy depended on a migration, run RB-2 **after** the code rollback only if the old code cannot run on the new schema. Prefer expand/contract migrations so it can.

## RB-4: Environment variable or secret exposure
1. ⚠ Rotate the secret at the provider first.
2. Update the Vercel env vars (`vercel env rm` / `vercel env add`) and redeploy.
3. Purge the secret from history only with explicit authorization, because this means a force-push. Rotating the secret is the real fix.
4. Record it in `templates/incident-report.md (GUARDED only)`.

## RB-5: Agent-made local changes
- Revert only the files listed in this task's `changedFiles` with `git restore --source=<baseCommit> -- <files>`.
- Never use `reset --hard` or `clean -fd` without authorization.
