# FORGEX v2.4: Lean AI Engineering System

**Engineer the Plan. Execute with Precision.** · Small seeds, proven growth.

FORGEX helps AI coding agents (Cursor, Grok Bot, any agent that reads Markdown) work **fast, correctly and with few tokens**:
- **Risk modes:** QUICK / STANDARD / GUARDED, each with a small machine-checked JSON contract (`tools/scaffold.py`, `tools/validate.mjs`).
- **Lego blocks:** work is split into blocks with interfaces and built seed-first; seams are checked once.
- **Context files:** `STATE.md`, `DECISIONS.md`, `CODEMAP.md` per project, so a new chat or bot picks up where the last stopped without re-reading the repo.
- **House kits:** your stack, design, reusable feature cards and golden code examples, so new apps follow your style without retyping it.

New here? Read **[QUICKSTART.md](QUICKSTART.md)**. Thai install guide: [INSTALL-TH.md](INSTALL-TH.md). The spec: [core/FORGEX.md](core/FORGEX.md).

## Layout
```
core/           single source: FORGEX.md (spec), rules/, skill/SKILL.md, guides/, templates/ (STATE, DECISIONS, patterns…)
core/house/     blank kit template (PROFILE, DESIGN, blocks/, golden/)
kits/<name>/    filled kits (personal or team); never shipped in the public package
config/         default-policy.json, kit.example.json (copy to kit.json to pick your kit)
schemas/ examples/ targets/cursor/ extras/
tools/          scaffold.py, context.py, codemap.py, validate.mjs, build.py, hooks/
```

## Commands
```bash
npm install && npm run build     # builds dist/public and dist/personal-<kit>, privacy-scans public, validates both
python3 tools/build.py --public-only
python3 tools/context.py init | decide "<d>" --why "<w>" --alt "<x>"
python3 tools/codemap.py [root] --max-lines 200
```

## Outputs
- `dist/public/`: generic Cursor plugin + Grok Bot skill (+ source zip). Contains only the blank kit template. The build fails if any term from any `kits/*/private-terms.txt`, an email address or a secret-looking string appears in it.
- `dist/personal-<kit>/`: the same plus your kit at `references/kit/`. Keep it private.

## License
MIT, © FORGEX contributors. See [LICENSE](LICENSE).

## Two places, one change (rule)
Every change updates **both** packages: the public one and every personal kit build. Run `python3 tools/release.py` after any edit; it rebuilds both, privacy-scans, validates, syncs the local bot copy and stages the public repo in `dist/public-repo/` with a local commit. Publishing (push + release) is always a separate, manual step.
