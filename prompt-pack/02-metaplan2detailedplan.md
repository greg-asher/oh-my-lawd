# 02-metaplan2detailedplan

You are operating on one slice that already has a metaplan.

## Mission

Convert the slice metaplan into a detailed, execution-ready slice plan that another agent can decompose into tasks without making new product or architecture decisions.

## Required reads

Read:
- `/spec`
- `/plan/<slice-id>-metaplan.md`
- `/plan/acceptance-matrix.md`
- `/plan/build-order.md`
- `/plan/open-questions.md`
- `/plan/forbidden-shortcuts.md`
- `/tasks/review-<slice-id>.md` when present
- `/tasks/spec-check-<slice-id>.json` when present

## Required output

Write `/plan/<slice-id>-detailed-plan.md`.

That file must include:
- implementation approach
- ordered work breakdown for this slice
- required interfaces and data flow
- failure modes and edge cases
- review criteria
- spec-check criteria
- exact artifacts that later phases must produce

## Non-negotiable rules

1. Keep decisions local to the slice.
2. Preserve direct traceability from the slice back to `/spec`.
3. Do not create `/tasks` yet.
4. Do not treat generated evidence as proof of missing behavior.
5. When this phase is a replan after a failed review or spec-check, explicitly incorporate the failure feedback into the updated detailed plan instead of regenerating the prior plan shape.
