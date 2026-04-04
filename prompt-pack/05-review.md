# 05-review

You are performing the slice review pass after build execution is complete.

## Mission

Review the current slice for implementation quality before spec-check runs. This phase is about code quality, correctness, edge cases, and evidence strength, not final source-spec closure.

## Required reads

Read:
- `/spec`
- `/plan/<slice-id>-metaplan.md`
- `/plan/<slice-id>-detailed-plan.md`
- `/tasks/queue-state.json`
- the completed slice task files
- the changed code and tests

## Required output

Write `/tasks/review-<slice-id>.md`.

That file must contain:
- `Result: pass|fail`
- reviewed scope
- findings or explicit statement that no findings were discovered
- weak tests, edge cases, or unsafe assumptions that still need work
- recommended next step if the result is `fail`

## Non-negotiable rules

1. Keep review separate from spec-check.
2. Review implementation quality, not just task completion.
3. If the slice is internally consistent but misses the spec, leave that for 06.
