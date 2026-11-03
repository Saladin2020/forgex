---
name: forgex-close
description: Close a FORGEX task by filling the contract, validating, and rendering the closeout
---
Set the check and AC statuses (only for checks that were run), the final `touchedPaths`, and `status`. Run `validate.mjs <file>`, then `scaffold.py render <file>`, and use its output as the reply or PR body. If you set a one-line `pattern`, run `scaffold.py pattern <file>`. Before the chat ends, save the plan: `context.py close --now "<status>" --next "<step>" …` and make sure `context.py check` passes (QUICK: skip).
