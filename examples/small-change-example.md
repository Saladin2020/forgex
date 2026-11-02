# Example — Add an optional compact date label

This example illustrates workflow behavior, not a claim that code was implemented or tested.

## Intake
Objective: Display a compact date label in an existing list.
Scope: One UI component and its focused test.
Non-goals: Redesign the page, change API shape, refactor unrelated components.

## Decision
- Conventional option: use the project's existing date formatter.
- Simpler option: use a new inline formatter.
- Chosen: existing formatter, if inspection confirms it meets the requirement.
- Excluded: global date-format refactor.
- Mode: QUICK if localized and reversible.

## Acceptance criteria
- [ ] Label displays the expected date.
- [ ] Missing/invalid date behavior matches project conventions.
- [ ] Existing list behavior is unchanged.

## Verification
Inspect existing formatter and component tests. Run focused test(s) if available. If no test runner is available, report NOT_RUN and state what was inspected.

## Scope discoveries
- REQUIRED: a demonstrated bug in the current date path that prevents the new behavior.
- OPPORTUNITY: date-format inconsistency elsewhere.
- FUTURE: localization framework for all dates.

Only REQUIRED work enters the current change automatically.
