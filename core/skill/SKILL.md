---
name: forgex
description: Use for a software change done FORGEX-style (fast, correct, few tokens). Covers picking QUICK/STANDARD/GUARDED, generating and filling the per-mode JSON contract, Lego blocks built seed-first, seam checks, validating, closing with a rendered report and one pattern line, starting a new web app from a house kit (profile, design, block cards, golden examples), and keeping STATE, DECISIONS and CODEMAP context files.
---
# FORGEX v2.8

`F` = `references/tools`. The spec is `references/FORGEX.md`; read only the section you need. STANDARD and GUARDED use a JSON contract at `forgex/tasks/<taskId>.json`. Generate it with the scaffold, **fill in values only**, and validate it with `python3 F/validate.py <file>` (pure Python) or `node F/validate.mjs <file>` (needs ajv). If neither runs, write one line, `validate: skipped (no python/node)`, and move on; no NOT_RUN ceremony. Never add a check that cannot pass in this environment.
**Permission:** the task message is permission to build, in every mode including GUARDED. Stop and ask only before deleting data, touching real machines or hardware, or touching secret values.
**Files:** every tool reads and writes text as UTF-8 (`encoding="utf-8"`); do the same in any script you write (Windows cp874 breaks Thai otherwise).

## CONTEXT (every session)
`K` = `references/kit` if it exists, else `references/house` (blank template).
- **New chat / "ทำต่อ" (resume):** run `python3 F/context.py resume` FIRST and continue Plan step 1; do not start other work until the plan is done or the user changes it. No Python: read `forgex/STATE.md` `## Plan` first.
- **Start (before any code, lean by default):** `python3 F/ctxpack.py "<task>" --path <file> …` and read **only** `forgex/context-pack.md` (STATE + matching DECISIONS, cards, CODEMAP sections, golden files, capped per mode; est. tokens). Use the mode it prints (shared risk classifier; it never lowers an explicit mode). **Say once:** `context: pack <id> · <MODE> · <used>/<cap> est. tokens`. Open more only if the pack lacks something, and say why. Exit 2 = fix the policy or path, don't guess.
- **No Python?** Fallback by hand and say `context: manual (no python) · <MODE>`: read STATE, `rg` DECISIONS and blocks/INDEX for the task's area tags, only touched CODEMAP dirs, ≤ the mode cap in `F/../config/context-policy.json`. Mode: GUARDED only if the task **really touches** auth/session/authz decisions (verify, hash, session, role check, 2FA) or writes the ledger/balances (post, debit, update balance, maker-checker), changes schema/migrations, or a path matches a guarded glob in `F/../risk/rules.json` (secrets, env, migrations, auth code). Mentioning login or money in UI/display/copy (login page styling, login button, show balance on dashboard) is STANDARD. Unsure → higher. Missing files? `python3 F/context.py init` and `python3 F/codemap.py`.
- **Before ending any STANDARD/GUARDED chat (mandatory):** save the plan: `python3 F/context.py close --now "<status>" --next "<step 1: file + what + check>" --next "<step 2>" --task <id> --mode <M>` (rewrites Updated/Now/Plan in `forgex/STATE.md`), then `python3 F/context.py check` must pass. A plan that lives only in chat is lost. Each settled choice: `python3 F/context.py decide "<d>" --why "<w>" --alt "<x>" --tag <area>` (`--tag` required; cards need `- **Tags:**` too). Never reverse a D-entry without a new superseding one. After adding/moving files, rerun `codemap.py` (sharded JSON + import graph + symbol index in `forgex/codemap/`; `codemap.py related <file>` / `codemap.py symbol <name>`).
- **Measure (optional, A/B):** `python3 F/tokens.py log --task <id> --classifier-mode <pack mode> --actual-mode <what it really needed> [--tokens-in N --tokens-out N --source cursor-usage]`; `tokens.py report` shows real tokens and the false-GUARDED rate.

## NEW WEB APP (read these first, nothing else)
1. Copy the block in `K/PROFILE.md` into the repo's `AGENTS.md`; pick a look from `K/DESIGN.md` into `DESIGN.md`. Run `context.py init` and `codemap.py`.
2. `rg -i "<feature>" K/blocks/INDEX.md`, open only matching cards, copy from the cited source. Before writing a page, route, action or test, open the one matching `K/golden/<kind>.md` and mimic its shape.
3. At project end, harvest per FORGEX.md §7.

## QUICK (one file, low risk, reversible)
1. A short pack read is enough. **No JSON contract, no STATE update.**
2. Make the change and run one real check if one exists. If the file matches a guarded glob, switch to GUARDED.
3. Close in ≤3 lines: what changed, the check and its result.

## STANDARD (several files, API or data shape, medium risk)
1. Run `python3 F/scaffold.py standard <taskId> "<goal>" --path … --blocks seed,b2,b3 --check "<cmd>" --ac "<criterion>"`.
2. Give each block an interface. Build seed-first, one block at a time, on `forgex/<taskId>`. Give each check an id like `C1`.
3. Integrate by adding one `kind: "seam"` check per pair of connected blocks, such as `tsc --noEmit`, a call or a test. Add a Vercel preview check when the change touches UI or API.
4. **Walkable first slice:** before closing, trace the user's real path end to end through the touched files (e.g. maker creates → checker approves → ledger posts) and confirm each step exists. Never silently move a decision step (approve, reject, post) into `nonGoals`; if it truly must wait, say so to the user.
5. Map the evidence: every AC marked PASS lists its check ids in `checks`. Completed means every AC is PASS or NOT_APPLICABLE and no check has FAILED.
6. Validate, then run `render` to produce the PR body.

## GUARDED (writes money, schema/migrations, login/authz decisions, secrets/env, prod)
1. Run `python3 F/scaffold.py guarded <taskId> "<goal>" --path …`. Fill in `nonGoals`, `constraints` and `deployment.rollbackRunbook`; the runbooks are in `references/guides/runbooks.md` and the stack guide is `references/guides/adapter-nextjs-vercel-neon.md`. Then build; the task is the permission (stop only for data deletion, real machines/hardware, secret values).
2. Build and verify as in STANDARD. Completed requires `budget` as well. Validate, then open the PR per `references/guides/git-pr-ci.md`, where CI and gitleaks must be green and a human reviews it.

## Always
- **Tests are evidence only if they import and call the real code.** A test that reimplements the function under test proves nothing; do not count it.
- Read only the files you need. Do not rerun unchanged checks or repeat summaries, and never claim a check you did not run.
- For patterns, run `rg -i "<keyword>" forgex/patterns.md` before designing and apply any `[rule]` lines it finds. At close, set the contract's `pattern` (one line, optional) and run `python3 F/scaffold.py pattern <file>`. Each time a candidate helps another task, raise its count (`1/2` → `2/2`). At 2/2 or more, promote it to `[rule]`.
- Use one agent. Read `references/extras/multi-agent.md` only when the user asks for a team.
