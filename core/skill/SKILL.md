---
name: forgex
description: Use for a software change done FORGEX-style (fast, correct, few tokens). Covers picking QUICK/STANDARD/GUARDED, generating and filling the per-mode JSON contract, Lego blocks built seed-first, seam checks, validating, closing with a rendered report and one pattern line, starting a new web app from a house kit (profile, design, block cards, golden examples), and keeping STATE, DECISIONS and CODEMAP context files.
---
# FORGEX v2.6

`F` = `references/tools`. The spec is `references/FORGEX.md`; read only the section you need. Every mode uses a JSON contract at `forgex/tasks/<taskId>.json`. Generate it with the scaffold, **fill in values only**, and validate it with `node F/validate.mjs <file>`, which needs `ajv`. If Node or ajv is missing, report the validation as NOT_RUN.

## CONTEXT (every session)
`K` = `references/kit` if it exists, else `references/house` (blank template).
- **Start (before any code, lean by default):** `python3 F/ctxpack.py "<task>" --path <file> …` and read **only** `forgex/context-pack.md` (STATE + matching DECISIONS, cards, CODEMAP sections, golden files, capped per mode; est. tokens). Use the mode it prints (shared risk classifier; it never lowers an explicit mode). **Say once:** `context: pack <id> · <MODE> · <used>/<cap> est. tokens`. Open more only if the pack lacks something, and say why. Exit 2 = fix the policy or path, don't guess.
- **No Python?** Fallback by hand and say `context: manual (no python) · <MODE>`: read STATE, `rg` DECISIONS and blocks/INDEX for the task's area tags, only touched CODEMAP dirs, ≤ the mode cap in `F/../config/context-policy.json`. Mode: guarded glob in `F/../risk/rules.json` or auth/money/db → GUARDED; when unsure pick the higher mode. Missing files? `python3 F/context.py init` and `python3 F/codemap.py`.
- **End or handoff:** rewrite `forgex/STATE.md` (≤30 lines). Each settled choice: `python3 F/context.py decide "<d>" --why "<w>" --alt "<x>" --tag <area>`. Never reverse a D-entry without a new superseding one. After adding/moving files, rerun `codemap.py`.

## NEW WEB APP (read these first, nothing else)
1. Copy the block in `K/PROFILE.md` into the repo's `AGENTS.md`; pick a look from `K/DESIGN.md` into `DESIGN.md`. Run `context.py init` and `codemap.py`.
2. `rg -i "<feature>" K/blocks/INDEX.md`, open only matching cards, copy from the cited source. Before writing a page, route, action or test, open the one matching `K/golden/<kind>.md` and mimic its shape.
3. At project end, harvest per FORGEX.md §7.

## QUICK (low risk, local, reversible)
1. Run `python3 F/scaffold.py quick <taskId> "<goal>" --path <file> --check "<cmd>"`.
2. Make the change and run the check. Set its `status`; NOT_RUN needs a `reason`. Add the final `touchedPaths`, set `status: completed` and write a one-line `result`.
3. Validate. If the validator says a path matches a guarded glob, the risk was rated too low, so switch to GUARDED.
4. Close by running `python3 F/scaffold.py render <file>`, which prints 3 lines. Do not write a separate closeout.

## STANDARD (several files, API or data shape, medium risk)
1. Run `python3 F/scaffold.py standard <taskId> "<goal>" --path … --blocks seed,b2,b3 --check "<cmd>" --ac "<criterion>"`.
2. Give each block an interface. Build seed-first, one block at a time, on `forgex/<taskId>`. Give each check an id like `C1`.
3. Integrate by adding one `kind: "seam"` check per pair of connected blocks, such as `tsc --noEmit`, a call or a test. Add a Vercel preview check when the change touches UI or API.
4. Map the evidence: every AC marked PASS lists its check ids in `checks`. Completed means every AC is PASS or NOT_APPLICABLE and no check has FAILED.
5. Validate, then run `render` to produce the PR body.

## GUARDED (high/critical, migrations, auth, .env*, prod, money, secrets)
1. Run `python3 F/scaffold.py guarded <taskId> "<goal>" --path …`. Fill in `nonGoals`, `constraints` and `deployment.rollbackRunbook`; the runbooks are in `references/guides/runbooks.md` and the stack guide is `references/guides/adapter-nextjs-vercel-neon.md`. **Get explicit permission before you build.**
2. Build and verify as in STANDARD. Completed requires `budget` as well. Validate, then open the PR per `references/guides/git-pr-ci.md`, where CI and gitleaks must be green and a human reviews it.

## Always
- Read only the files you need. Do not rerun unchanged checks or repeat summaries, and never claim a check you did not run.
- For patterns, run `rg -i "<keyword>" forgex/patterns.md` before designing and apply any `[rule]` lines it finds. At close, set the contract's `pattern` (one line, optional) and run `python3 F/scaffold.py pattern <file>`. Each time a candidate helps another task, raise its count (`1/2` → `2/2`). At 2/2 or more, promote it to `[rule]`.
- Use one agent. Read `references/extras/multi-agent.md` only when the user asks for a team.
