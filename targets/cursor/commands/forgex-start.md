---
name: forgex-start
description: Start a FORGEX task by picking a mode and generating the JSON contract stub
---
Follow the `forgex` skill. First run `ctxpack.py "<task>" --path …`, read only `forgex/context-pack.md` and state `context: pack <id> · <MODE> · <used>/<cap>` (no Python: manual fallback from the skill). Use that mode (never lower), QUICK: just make the change, no contract. STANDARD/GUARDED: run `scaffold.py standard|guarded <taskId> "<goal>" --path … --check …`, fill in values only, plan seed-first blocks, and make the first slice walk the real user path. The task is permission; stop only before deleting data, real machines/hardware, or secrets.
