# FORGEX Quickstart (10 minutes)

## 1. Install
- **Cursor:** unzip `forgex-cursor-plugin.zip` and add it as a local plugin, or copy `rules/*.mdc` to `.cursor/rules/` and `skills/forgex/` to `.cursor/skills/forgex/` in your repo.
- **Grok Bot / other agents:** give the agent `forgex-grokbot-skill.zip` and ask it to save the `forgex` skill.
- Validation needs nothing extra: `python3 <forgex>/tools/validate.py forgex/tasks/*.json` (pure Python). `npm i -D ajv ajv-formats` is optional for `validate.mjs`. QUICK tasks (one reversible file) need no contract.

## 2. Make your kit (once)
```bash
cp -r core/house kits/<you>          # blank template
# fill PROFILE.md, DESIGN.md, blocks/*.md, golden/*.md from YOUR real code; cite repo:path; mark unsure items "?"
echo '{ "kit": "<you>" }' > config/kit.json
echo 'MyPrivateRepo' > kits/<you>/private-terms.txt   # words that must never leak into the public build
python3 tools/build.py                                 # -> dist/personal-<you>/
```
No kit yet? Skip this; the agent falls back to the blank template and asks.

## 3. Start a new app
Tell the agent: "start a new web app with FORGEX". It copies the kit profile into `AGENTS.md`, picks a look into `DESIGN.md`, runs `context.py init` + `codemap.py`, then opens only the block cards and golden examples it needs.

## 4. Every session
- Start (before coding): agent runs `ctxpack.py "<task>" --path <file>`, reads only `forgex/context-pack.md` (capped: QUICK ~1.2k, STANDARD ~3.5k, GUARDED ~7k est. tokens) and tells you `context: pack cp-… · MODE · used/cap`. Tune with `forgex/context-policy.json`; add risky paths to `forgex/policy.json` `guardedGlobs`.
- Mode: one shared risk classifier (`references/risk/`) for ctxpack and the validator. Your explicit mode is never lowered; auth/money/db or guarded paths always mean GUARDED; unknown → higher.
- No Python on the machine? The agent follows the manual fallback in the skill and says `context: manual`.
- Check it: `python3 tools/test_risk.py && python3 tools/test_ctxpack.py` (source repo).
- End or handoff: agent rewrites `STATE.md`, logs choices with `context.py decide`, refreshes `codemap.py`.

## 5. Harvest patterns (end of each project)
Each feature worth reusing becomes a ≤6-line card in `kits/<you>/blocks/` plus one line in `blocks/INDEX.md`; a better code shape replaces a golden example. Rebuild.

## 6. Teams
Put FORGEX (or just `kits/<team>/`) in a shared private repo. Everyone sets `config/kit.json` to the team kit and builds; changes to cards go through PRs like code. Share `dist/public/` with outsiders only.
