---
name: forgex-start
description: Start a FORGEX task by picking a mode and generating the JSON contract stub
---
Follow the `forgex` skill. First run `ctxpack.py "<task>" --path …`, read only `forgex/context-pack.md` and state `context: pack <id> · <MODE> · <used>/<cap>` (no Python: manual fallback from the skill). Use that mode (never lower), then run `scaffold.py quick|standard|guarded <taskId> "<goal>" --path … --check …`. Fill in values only. For STANDARD and GUARDED, plan seed-first blocks. For GUARDED, stop for permission before editing.
