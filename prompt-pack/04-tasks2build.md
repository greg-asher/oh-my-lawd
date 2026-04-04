# 04-tasks2build

You are operating on one slice that already has `/tasks` and `/plan`.

## Mission

Execute the next ready task for the current slice, update the task queue honestly, and produce only the smallest coherent slice of implementation progress.

## Required reads

Read:
- `/tasks/README.md`
- `/tasks/index.md`
- `/tasks/task-index.json`
- `/tasks/queue-state.json`
- the selected task file
- directly relevant slice planning files
- relevant source spec references for the selected task
- `/tasks/review-<slice-id>.md` when present
- `/tasks/spec-check-<slice-id>.json` when present

## Required behavior

1. Execute only the current slice's queue.
2. Update the selected task file first, then the queue mirrors.
3. Keep `current_slice`, `slice_status`, `review_status`, and `spec_check_status` accurate in `/tasks/queue-state.json`.
4. Stop the 04 loop only when the current slice queue is exhausted.

## Verification rules

- Run the strongest available automated checks for the task.
- When the task advances an operator-facing seam, verify the real command or operator surface.
- Do not mark work complete based only on generated evidence or fixture-backed substitutes.

## Non-negotiable rules

1. `/spec` remains authoritative if the slice plan drifts.
2. Do not silently widen scope.
3. Do not claim slice completion here. Review and spec-check still remain.
4. If this build pass follows a failed review or spec-check, treat the recorded findings as required input and address them before advancing the slice again.
