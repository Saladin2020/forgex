# House kit (template)
A kit teaches FORGEX one person's or team's way of building apps. This folder is the **blank template**; a filled kit lives in `kits/<name>/` with the same files and is selected by `config/kit.json`.

| File | Becomes in a new project | Fill with |
|---|---|---|
| `PROFILE.md` | `AGENTS.md` | stack, layout, scripts, rules, don'ts |
| `DESIGN.md` | `DESIGN.md` | colors, fonts, shape, component kit |
| `blocks/INDEX.md` + `blocks/<card>.md` | (read on demand) | one card per reusable feature |
| `golden/<kind>.md` | (read on demand) | 1–2 short exemplary excerpts per kind |

Rules: write only what exists in your real code; cite `repo:path`; mark single-source or unread items `?`. Make your own: `cp -r core/house kits/<you>`, fill it, set `{"kit": "<you>"}` in `config/kit.json`, run `python3 tools/build.py`.
