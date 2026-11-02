# Multi-agent: lead/worker protocol

**Optional module (extras/).** It is not loaded by default and is not part of the always-on rule. Use it only when the user explicitly asks for a team. Single-agent is the default.

## Roles
- **Lead:** owns the parent contract, G0, G1, G4 and G5, the final evidence and the merge. It is the only role that can set `status: completed` (schema R4).
- **Worker:** receives a child contract (`parentTaskId`, `handoff.role: "worker"`), works on its own branch `forgex/<parentTaskId>/<worker>` within `handoff.fileLocks`, and returns `status: "submitted"` with its evidence.

## Handoff
1. **Lead → worker:** a child contract that validates. It carries a narrowed scope, the AC that are copied or split, the `fileLocks`, the risk and mode (never lower than the parent's), and a `budget.limitTokens`.
2. **Worker:** builds and verifies within its scope, records evidence (`recordedBy`) and discoveries, and never widens scope. A REQUIRED discovery outside the locks goes back to the lead as `blocked`.
3. **Worker → lead:** the contract with status `submitted` (or `blocked`/`failed`) plus the branch name. Leave out G4 and G5.
4. **Lead verification:** the lead re-runs or inspects the worker's key evidence. It does not trust a reported PASS blindly. It merges the worker branches, runs the integration checks (G3) and the final verification (G4), and adds the token budgets of all children to the parent.
5. **Close:** the lead sets the parent to `completed` (R3) and opens one PR.

## Conflicts
- No two workers may hold overlapping `fileLocks`.
- If the lock sets overlap, run the work in sequence.
- If two pieces of evidence disagree, the lead re-runs the check, and the observed result wins.
