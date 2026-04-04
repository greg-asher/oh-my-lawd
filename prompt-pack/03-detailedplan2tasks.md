# 03-detailedplan2tasks

You are operating on one slice that already has a detailed plan.

## Mission

Create the slice-scoped `/tasks` workspace used for execution, review, and spec-check. The queue must represent only the current slice.

## Required reads

Read:
- `/plan/<slice-id>-detailed-plan.md`
- `/plan/acceptance-matrix.md`
- `/plan/open-questions.md`
- `/plan/forbidden-shortcuts.md`
- `/plan/slice-manifest.json`

## Required outputs

Create or update:
- `/tasks/README.md`
- `/tasks/index.md`
- `/tasks/task-index.json`
- `/tasks/queue-state.json`
- one canonical `/tasks/TASK-XXX.md` file per slice task

## Task requirements

Every task file must include:
- `## Slice ID`
- `## Relevant Spec References`
- honest completion criteria
- expected evidence
- expected artifacts

`/tasks/task-index.json` must include:
- `slice_id`
- `source_spec_refs`
- slice-scoped status data

`/tasks/queue-state.json` must include:
- `current_slice`
- `slice_status`
- `slice_retry_count`
- `review_status`
- `spec_check_status`

## Non-negotiable rules

1. Scope the queue to the current slice only.
2. Keep markdown as the human-readable source of truth.
3. Do not implement code here.
4. Do not bury review or spec-check work inside generic implementation tasks.
