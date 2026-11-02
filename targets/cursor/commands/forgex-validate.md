---
name: forgex-validate
description: Validate every FORGEX task contract in forgex/tasks
---
Run `node <forgex>/tools/validate.mjs forgex/tasks/*.json`. Report each file as PASS or FAIL with the first error. If a guarded-glob error appears, switch the task to GUARDED. If Node or ajv is missing, report NOT_RUN.
