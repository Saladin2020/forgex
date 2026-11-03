# Changelog

## v2.9.0 (2026-11-03): light planning, harvest, style capture
- Planning: `core/templates/ROADMAP.md` + `tools/roadmap.py` via `tools/forgex.py`. `forgex.py plan "<goal>"` writes `forgex/roadmap.json` + `forgex/ROADMAP.md` (3-5 milestones with outcomes; slices of 1-3 files, own test, `dependsOn`, mode from the risk classifier, never lower). `plan --check` rejects placeholders, cycles, >3 files, missing deps/tests, ≤3 slices, wrong milestone count, a non-walkable first slice. `forgex.py next` writes the ready slice into STATE Plan; `slice done <id> --check-cmd` marks done only if the test passes. Only for >3 slices; QUICK/single tasks skip it.
- ctxpack: new `roadmap` kind loads only the current + next slice (skipped in QUICK; policy priority + schema updated).
- Harvest: `forgex.py harvest <id>` drafts kit cards from a done slice's exports into `forgex/harvest/`; `--confirm <draft> --kit <personal kit>` copies one into `blocks/` + INDEX. Never automatic, refuses core/house or any folder without kit.json/private-terms.txt.
- Style capture: `forgex.py style capture <image-or-url...>` → `forgex/style/style.draft.json` (color, spacing, radius, shadow, type, motion: shimmer, stagger, reduced motion), `DESIGN.draft.md`, `CHECKLIST.md`, cards `ui-skeleton-list`, `ui-empty-state`, `ui-data-table` (runnable tsx + rules). URLs: declared CSS variables from the page + up to 5 same-origin stylesheets (no browser, no computed styles). Images: template + agent fill steps. Principles only, never logos/assets/code.
- Tests: new `tools/test_plan.py` (real tools on a temp repo, run by `release.py`).

## v2.8.0 (2026-11-03): real-touch risk, saved plans, tags, graph CODEMAP, real tokens
Credit: owner's priority list after the v2.7 bench (fix false GUARDED → plan into STATE → tags + CODEMAP/graph → real tokens).
- Risk: `writeSignals` replaced by `touchSignals` (per kind: `strong` phrases, or `nouns` AND `verbs`; nouns alone never escalate). Display/UI words (`displaySignals`, `uiSignals`: show, dashboard, button, styling, css, label, แสดง, ปุ่ม…) cancel noun+verb hits, never strong ones or schema-change. New real-touch globs: `**/ledger/**`, `**/*ledger*.*`, `**/session/**`, `**/*session*.ts`. "login page styling", "members page with login button", "show balance on dashboard", "fix login" on a page → STANDARD; TOTP/2FA, hash password, verify session, role enforce, maker-checker, post to ledger, debit, update balance → GUARDED. 67 py/js parity cases (35 new, EN+TH).
- Cross-chat plan: STATE template has `## Plan` (numbered, file paths). `context.py close --now … --next …` rewrites Updated/Now/Plan; `context.py resume` prints Plan first for a new chat ("continue Plan step 1, no other work"); `context.py check` and `validate.py --context` fail on a missing/placeholder plan. Skill, always-on rule and /forgex-start, /forgex-close wired to it (QUICK unchanged: no STATE).
- Tags mandatory: `context.py decide --tag` required; `validate.py --context` fails on untagged D-entries/cards, `--self-test` checks every shipped/kit card. ctxpack selects D-entries by tag (tag in areas or tag word in task); legacy untagged entries fall back to title words, flagged UNTAGGED.
- CODEMAP: `codemap.py` writes `forgex/codemap/index.json` + per-dir `shards/*.json` + `symbols.json` + `graph.json` (TS/JS import/export-from/require/dynamic import with relative and `@/`/`~/` aliases; Python absolute + relative imports). No 200-line truncation; `CODEMAP.md` is a short summary with kept Notes. `codemap.py related <file> [--hops N]`, `codemap.py symbol <name>`. ctxpack loads touched files, 1–2 hop neighbours (`graphHops`, `maxRelated` in policy) and the defining file of symbols named in the task; legacy CODEMAP.md used only without the JSON index. Money area keywords add balance/ledger/satang/ยอด/เงิน.
- Measurement: new `tools/tokens.py` (tiktoken o200k/cl100k if installed, else chars/4 flagged `estimate`), `log` to `forgex/log.jsonl` (tokensIn/tokensOut, tokenSource incl. manual `cursor-usage`, classifierMode vs actualMode) and `report` (real vs estimated tokens, false-GUARDED rate). ctxpack `--json` adds `classifierMode`, `explicitMode`, `tokensIn`, `tokenMethod`, `tokenEstimate`. Bench `results-template.csv` adds those columns; `score.py` adds a "Real tokens + false GUARDED" table per arm.
- Tests: new `tools/test_context.py` (30 checks, real tools on a temp repo), run by `release.py`.
- Not added on purpose: vector DB/embeddings, heavy Spec-Kit-style ceremony. QUICK path unchanged.

## v2.7.0 (2026-11-03): findings from A/B bench run
Credit: findings from A/B bench run (v2.6.1 bench, 8 findings).
- Risk: GUARDED only when the task **writes** money/balances, changes schema/migrations, or changes login/authz decisions (`writeSignals` EN+TH in `rules.json`), a secret/key/env/migration/auth-code glob matches, or mode is explicit GUARDED. Read/display work (members list page, 125.75 display fix, payment history) stays STANDARD; read-only words never cancel schema-change. Money/payment/billing globs and `guardedAreas` removed. 31 py/js parity cases.
- ctxpack: page/UI tasks always reserve one ui/design/style/token card ("UI style slot") and load the kit `DESIGN.md` (new `design` kind, STANDARD/GUARDED); page tasks with a page path reach the golden minimum.
- Closing rule: the first slice must be walkable end to end on the user's real path (maker creates → checker approves → ledger posts); never silently move a decision step to non-goals.
- Encoding: every tool reads/writes text as UTF-8, stdout/stderr reconfigured, argv repaired on non-UTF-8 locales (Windows cp874 crash). Test runs ctxpack + context.py under `LC_ALL=C`.
- Validation: new pure-Python `tools/validate.py` (schema subset + classifier cross-checks, `--self-test`, run by `release.py`). If no validator can run: one line `validate: skipped`, no NOT_RUN ceremony, no ritual checks that cannot pass.
- QUICK: no JSON contract and no STATE update; short pack read, ≤3 closing lines. QUICK skips `design`.
- Tests: only tests that import and call the real code count as evidence.
- Permission: the task message is permission in every mode, GUARDED included. Stop only before deleting data, real machines/hardware, or secrets. Removed "get permission before you build" in GUARDED.
- Bench: T4 checks an approve route exists and the approve path posts to the ledger; T2/T5 stay STANDARD.

## v2.6.1 (2026-11-02): A/B bench
- New `bench/`: A/B kit to test FORGEX vs no FORGEX in Cursor (same starter, model and prompts). Thai README, 6 tasks (QUICK ×1, STANDARD ×2, GUARDED ×3 incl. a new-chat "ทำต่อ" memory test), `tasks/checks.json` objective checks, generic `starter/` (Next.js 16, Tailwind v4, Drizzle/Neon, Auth.js v5, planted money bug), `style.json`, `score.py` (stdlib; grep/exists/style/cmd checks + results.csv metrics → markdown table with a winner per metric), `results-template.csv`.
- Personal kits may add `bench/style.json` with their own tokens (`score.py --style`).

## v2.6.0 (2026-11-02): reliability first
- One risk classifier: `core/risk/rules.json` + `classifier.py` + `classifier.mjs` (shipped as `references/risk/`), used by both `ctxpack.py` and `validate.mjs`. Explicit mode is a floor (never downgraded); guarded globs/areas always escalate to GUARDED; unknown mode/riskLevel → GUARDED; no paths → STANDARD. Guarded globs add payments/billing/money/secrets/keys; project `forgex/policy.json` globs are added. `tools/test_risk.py` checks py/js parity (18 cases).
- Workflow wiring: always-on rule, SKILL.md and `/forgex-start` run ctxpack before coding, state `context: pack <id> · MODE · used/cap`, and give a manual no-Python fallback.
- ctxpack: YAML metadata header (pack id, forgex/policy versions, mode reasons, budget + estimator chars/4, selected/skipped with reasons, warnings; outside the cap); golden examples need `goldenMinScore` (default 2); card allocation rule (guarded areas first, one core card per area, extra core cards skipped with a reason); clear exit 2 on invalid policy or a path outside the project root; warnings for missing files, no matched area, no paths.
- Edge-case tests in `test_ctxpack.py`: auth path, guarded glob, explicit STANDARD/GUARDED, multi-area, over budget, core cards > maxCards, no tags, no paths, missing file, invalid policy (2 kinds), path outside root (2 kinds), golden min score, metadata header + deterministic id. `release.py` runs both test files.
- Deferred (roadmap in FORGEX.md §11): v2.7 dependency graph + relevance scoring; v2.8 tokenizer adapter + feedback JSONL. Contract schema unchanged.

## v2.5.0 (2026-11-02): context orchestration, lean by default
- `config/context-policy.json` + `schemas/context-policy.schema.json`: task signals (keywords, path globs, mode) → areas → what to load; per-mode caps in est. tokens (QUICK 1200 / STANDARD 3500 / GUARDED 7000), priority order, `maxCards`, skip list, `skipKinds`. Project override `forgex/context-policy.json`.
- `tools/ctxpack.py`: builds `forgex/context-pack.md` (STATE + matching DECISIONS, cards, CODEMAP sections, golden files), never over the cap, prints loaded/skipped with reasons, `--json` report.
- Optional `Tags` on kit cards and DECISIONS entries (`context.py decide --tag`); old untagged files still work.
- `tools/test_ctxpack.py` scenario tests (login → auth only; tiny CSS under QUICK cap; money API picks its core card money-math; cap trimming). Each matched area reserves one card slot for its core card (first tag); `release.py` runs them and tags the local public commit. Validator checks the context policy and budget order.
- SKILL.md start step uses the pack; FORGEX.md §9; QUICKSTART. Contract schema unchanged.

## v2.4.0 (2026-11-02): context engineering + shareable kits
- Context files per project (`forgex/`): `STATE.md` (read at start, rewrite at end/handoff), `DECISIONS.md` (append-only D-n log), `CODEMAP.md` (generated). New `tools/context.py` (`init`, `decide`) and `tools/codemap.py` (git-aware tree + exported symbols, 200-line cap, keeps `## Notes`). Templates in `core/templates/`. Spec §8, SKILL.md CONTEXT section.
- Golden examples: `golden/` per kit (form-page, api-route, server-action, test) with template.
- Shareability: `core/house/` is now a blank template; filled kits live in `kits/<name>/`, picked by `config/kit.json` (see `kit.example.json`). The author's own kit moved to a private `kits/<name>/` and gained 4 golden examples; cards thai-pdf, password-auth, staff-totp and maker-checker were verified against source.
- `build.py` makes `dist/public/` (no kit, privacy-scanned against `kits/*/private-terms.txt`, emails and secret patterns; fails on a hit) and `dist/personal-<kit>/` (kit at `references/kit/`). `validate.mjs --dist` checks both and kit presence.
- English README rewrite, new QUICKSTART.md; plugin author is now generic. License: MIT, © FORGEX contributors (personal build may name its kit author).
- `tools/release.py`: one command rebuilds public + personal, scans, validates, syncs the bot copy (with backup) and stages `dist/public-repo/` as a local git commit. Rule: every change goes to both packages; nothing is published automatically.

## v2.3.0 (2026-11-02): house kit, reuse the owner's past apps
- New `core/house/` (shipped as `references/house/`), loaded only when starting a new web app:
  - `PROFILE.md`: AGENTS.md template filled from the author's own apps (stack, layout, scripts, rules, don'ts).
  - `DESIGN.md`: two observed looks (warm terracotta, navy), with real tokens and fonts.
  - `blocks/INDEX.md` + 16 cards: thai-pdf, audit-log, idempotency, rate-limit, web-push, blob-backup, password-auth, staff-totp, maker-checker, promptpay-qr, money-math, drizzle-neon-migrate, daily-cron, thai-address, image-compress, async-button.
- SKILL.md gains a 3-step NEW WEB APP section; FORGEX.md gains §7 (start and harvest). `build.py` copies `house/`.
- Contract schema, validator and modes are unchanged (`contractVersion` stays "2.2").

## v2.2.0 (2026-10-17): machine-checked JSON for all modes, still lean
- Tiered contract in one schema (`contractVersion: "2.2"`):
  - QUICK requires `taskId, mode, riskLevel, goal, touchedPaths, checks[{cmd,status}], status`.
  - STANDARD adds `acceptanceCriteria`, where each PASS AC must list its check ids (`checks: ["C1"]`).
  - GUARDED adds `nonGoals, constraints, git`, a rollback runbook and `budget`.
- R1/R2 risk-to-mode rules apply in every tier. A check marked NOT_RUN or BLOCKED needs a `reason`.
- The validator now cross-checks:
  - QUICK and STANDARD `touchedPaths` against `policy.guardedGlobs`, using a built-in glob matcher with a self-test, so risk rated too low is rejected.
  - Check-id references from ACs and blocks, which must exist.
  - Duplicate check ids.
  - A project policy override at `forgex/policy.json` is used when present.
- `scaffold.py` emits JSON stubs for every mode (the agent fills values only):
  - `render` produces the closeout from the JSON, so nothing is written twice.
  - `pattern` appends the contract's one-line pattern to `forgex/patterns.md`, without duplicates.
- New optional `tools/hooks/pre-commit` validates staged `forgex/tasks/*.json`.
- CI validates every `forgex/tasks/*.json` in all tiers, and gitleaks still runs.
- **Breaking:**
  - `objective`, `scope`, `changedFiles` and `evidence` are replaced by `goal`, `touchedPaths`, `nonGoals` and `checks`.
  - Templates `quick.md`, `standard.md`, `task-closeout.md` and `task-contract.json` are removed; the stubs and `render` replace them.
- 5 valid and 18 invalid examples, including a QUICK that touches `migrations/**` and a STANDARD that touches `auth/**`, plus 3 generated stubs.

## v2.1.0 (2026-10-17): lean refocus (fast, correct, few tokens)
- Mode tiers: QUICK uses a 3-line `Goal/Check/Result` checklist and a 2–3 line closeout with no JSON. STANDARD uses a Markdown mini-contract (`templates/standard.md`), with JSON optional. GUARDED uses the JSON contract, validator, CI and a runbook. The schema rules R0–R6 still apply whenever JSON is used.
- Lego and seed-first: the Blueprint splits work into blocks, each with an interface and its own check, ordered seed-first. The Integrate gate checks each seam once.
- Evolution: one-line patterns go in `forgex/patterns.md` as `[candidate n/2]`. A candidate becomes a `[rule]` after 2 or more successful uses. Retrieve patterns with `rg`, and never load the whole file. The template `pattern-record.md` was removed, while the JSON pattern schema remains as an optional tool.
- The always-on rule was cut to 7 bullet lines, under 15 (the validator enforces ≤15). Everything else loads on demand, and the glob-scoped `forgex-guarded.mdc` is unchanged.
- Token rules: read only the relevant files, never rerun unchanged checks, summarize once, and re-plan a block after 3 failed attempts.
- Multi-agent moved to the optional `extras/multi-agent.md`. It is no longer in the always-on rule or the default skill path.
- New `tools/scaffold.py` generates the quick, standard, guarded and pattern skeletons. It never overwrites a file and it validates `taskId`.
- New `tools/measure_tokens.py` reports tiktoken cl100k_base counts for v2 versus v2.1.
- Removed `mini-blueprint.md`, which `standard.md` replaces.

## v2.0.0 (2026-10-17)
### Enforcement
- The task contract schema enforces these rules with `if/then`:
  - R0: a non-blank, whitespace-free `taskId`, and no blank text fields.
  - R1: high or critical risk requires GUARDED.
  - R2: medium risk cannot use QUICK.
  - R3: success definition. `completed` requires every AC to be PASS or NOT_APPLICABLE, at least one PASS, evidence, `changedFiles` and `budget`.
  - R4: a worker cannot complete the task or set G4/G5.
  - R5: GUARDED work in progress needs a rollback runbook.
  - R6: NOT_APPLICABLE requires a rationale.
- New schemas: `policy.schema.json` and `pattern-record.schema.json` (a validated pattern needs ≥2 evidence entries; a deprecated one needs a replacement).
- New `tools/validate.mjs` (ajv) with 4 valid and 9 invalid contract examples and 2 pattern examples. It also cross-checks the policy against the task schema.
### Fixes from the v1 review
- Added the missing incident template (`templates/incident-report.md`).
- Fixed the v1 inconsistencies: `mode` is in the handoff contract, NOT_APPLICABLE is everywhere, pattern metadata matches the schema, and `defaultMode` was replaced by `fallbackMode`, which applies only before risk is assessed and is never QUICK.
- Merged README, the spec, ARCHITECTURE, DECISION-ENGINE, PHASE-GATES, RECOVERY, SECURITY, OBSERVABILITY and EVOLUTION into one canonical `core/FORGEX.md`. The 8 docs became 1 spec and 4 focused guides.
- Added a git/PR flow (branch per task, commit and PR conventions, contracts in `forgex/tasks/`).
- Added CI: a GitHub Actions workflow that validates contracts and runs gitleaks.
- Added concrete rollback runbooks RB-1 to RB-5 (git, Neon restore and down migrations, Vercel instant rollback/promote, secret rotation, local revert).
- Added a Next.js, Vercel and Neon adapter (Vercel preview as evidence, Neon branch per migration, guarded globs).
- Added the glob-scoped rule `forgex-guarded.mdc` for migrations, auth, `.env*`, middleware, vercel.json and ORM schemas.
- Added a measurable `budget` (source measured, estimated or unavailable; tokens; attempts; limits) and defined the `tokens_per_successful_task` metric.
- Added the multi-agent lead/worker protocol (child contracts, `fileLocks`, the `submitted` status, and the lead owning the final gate and evidence).
### Packaging
- Cursor Plugin (`.cursor-plugin/plugin.json`, with rules, skills and commands) and a Grok Bot skill folder, both built by `tools/build.py` from `core/`.
- Thai installation guide `INSTALL-TH.md`.
### Breaking
- `contractVersion: "2.0"` is now required, and the `status` field adds `submitted`. v1 contracts must add these fields.

## v1.0.0
- The initial specification package.
