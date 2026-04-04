# 06-spec-check

You are performing the slice spec-check pass.

## Mission

Compare the current slice directly against `/spec`, real code paths, real commands, runtime behavior, and operator-visible outputs. This phase decides whether the slice actually satisfies the source specification.

## Required reads

Read `/spec` directly, especially the slice's `source_spec_refs`. Also read:
- `/plan/slice-manifest.json`
- `/plan/<slice-id>-metaplan.md`
- `/plan/<slice-id>-detailed-plan.md`
- `/tasks/review-<slice-id>.md`
- `/tasks/queue-state.json`
- the implemented code, tests, commands, and operator outputs for the slice

## Required output

Write `/tasks/spec-check-<slice-id>.json` with:
- `slice_id`
- `result`
- `summary`
- `missing_requirements`
- `verified_code_paths`
- `verified_commands`
- `verified_outputs`
- `requires_replan`

## Non-negotiable rules

1. Read `/spec` directly. Do not rely only on `/plan`, `/tasks`, generated evidence, or unit tests.
2. Compare the slice against real code paths, real CLI commands, real runtime behavior, and real outputs shown to the operator.
3. A passing review does not imply a passing spec-check.
4. Evidence validates implemented behavior and must not stand in for missing functionality.
5. If the slice misses source requirements, return `result = fail` and set `requires_replan = true`.
