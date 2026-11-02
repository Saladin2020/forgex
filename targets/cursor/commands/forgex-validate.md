---
name: forgex-validate
description: Validate every FORGEX task contract in forgex/tasks
---
Run `python3 <forgex>/tools/validate.py forgex/tasks/*.json` (or `node <forgex>/tools/validate.mjs …` if ajv is installed). Report each file as PASS or FAIL with the first error. If a guarded-glob error appears, switch the task to GUARDED. If neither Python nor Node runs, say `validate: skipped` in one line.
