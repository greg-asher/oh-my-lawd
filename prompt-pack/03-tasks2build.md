# tasks2build.md

You are operating inside a repository that contains both `/plan` and `/tasks`.

Your job is to execute the next dependency-ready task from `/tasks`, verify the work honestly, and update both `/tasks` and any impacted `/plan` artifacts to reflect the new truth.

This is an execution loop, not a redesign pass.

## Mission

Select the next valid task from `/tasks`, implement the smallest coherent slice that satisfies it honestly, produce evidence, and update the repository’s execution records.

Your work must stay aligned with:
- the authoritative spec-derived plan in `/plan`
- the operational task contract in `/tasks`
- the system invariants and forbidden shortcuts

## Non-negotiable rules

1. `/tasks` is the operational queue. Start there.
2. `/plan` remains the strategic source for acceptance, invariants, and architecture boundaries.
3. The markdown task files are the human-readable source of truth. JSON task files are machine-readable projections and must stay aligned.
4. If `/tasks` and `/plan` conflict, check whether execution revealed a real inconsistency. If not, do not improvise.
5. Do not skip foundational truths to make visible feature progress.
6. Do not mark a task complete without evidence.
7. Do not silently widen scope.
8. Do not rewrite architecture unless required by a real contradiction.
9. If a task is too large, split it before or during execution and update `/tasks`.
10. Keep status reporting honest.
11. Prefer durable progress over broad speculative changes.
12. A task cannot be marked `completed` unless both automated verification and live operator evidence are recorded when the task advances product-facing or provider-reliability acceptance gates.
13. Demo, walkthrough, and scenario surfaces do not close preserved seams unless `/plan` explicitly defines them as the real release surface.

## Required files to read before acting

Read at minimum:
- `/tasks/README.md`
- `/tasks/index.md`
- `/tasks/task-index.json`
- `/tasks/queue-state.json`

Then read:
- the selected task file
- any directly relevant `/plan` files referenced by that task
- any existing code/files needed to execute the task

Before claiming implementation completion or release closure, also read:
- `/plan/spec-map.md`
- `/plan/domain-glossary.md`
- `/plan/invariants.md`
- `/plan/implementation-brief.json`
- `/plan/preserved-seams.md`

## Task selection rules

Choose the next task using this order:
1. tasks marked `ready`
2. among ready tasks, prefer the one recommended in `/tasks/index.md` or `/tasks/queue-state.json`
3. if multiple are ready, prefer the one that best advances foundational contracts or acceptance gates

If no task is ready:
- do not invent new work
- identify the blocking reason from `/tasks`
- update queue state honestly if needed

## Task file contract

Every task file must follow the canonical section order established by `plan2tasks.md`. Do not reorder sections. Do not remove sections. Update values within the existing structure.

Required sections:
1. `# Task`
2. `## ID`
3. `## Title`
4. `## Status`
5. `## Owning Layer`
6. `## Objective`
7. `## Why This Exists`
8. `## Prerequisites`
9. `## Acceptance Gates Advanced`
10. `## Relevant Plan References`
11. `## Scope`
12. `## Constraints`
13. `## Implementation Notes`
14. `## Expected Evidence`
15. `## Expected Artifacts`
16. `## Open Questions`
17. `## Handoff Notes`
18. `## Iteration Log`

## Execution procedure

### Step 1: Load task truth
From the selected task file, extract:
- objective
- owning layer
- prerequisites
- acceptance gates advanced
- scope
- constraints
- expected evidence
- expected artifacts
- open questions
- handoff notes

### Step 2: Validate readiness
Before coding, confirm:
- prerequisites are actually satisfied
- no blocking condition remains
- the task scope is coherent for one iteration

If not, update `/tasks` honestly before proceeding.

### Step 3: Move task into execution
Update the task file status to `in_progress`.
Update `/tasks/index.md`, `/tasks/task-index.json`, and `/tasks/queue-state.json` to reflect that.

### Step 4: Implement the smallest coherent slice
Implement only what is necessary to advance this task honestly.

Prefer this order when relevant:
- canonical contracts and types
- persisted truth
- runtime behavior
- orchestration behavior
- product state projection
- UX surfaces
- walkthrough or end-to-end verification hooks

Do not build adjacent features unless the task requires them.

### Step 5: Verify
Run the strongest available verification for the work completed:
- targeted tests
- integration checks
- schema checks
- walkthrough-aligned tests
- static analysis
- verification notes only where automation is not yet possible

When the task advances product-facing or provider-reliability acceptance gates, verification MUST include:
- automated checks, and
- live operator walkthrough evidence

Be explicit about what was and was not verified.

When the task advances a preserved seam or primary operator surface:
- verification MUST exercise the real delivered surface, not only a demo or fixture-backed substitute
- any shown help, onboarding, remediation, or next-command guidance MUST be checked for executable honesty
- when persisted runtime truth is part of the task scope, verification MUST create, load, or resume real persisted state through the intended operator surface

### Step 6: Determine honest task status
After implementation and verification, set the task to one of:
- `completed`
- `partial_success`
- `blocked`
- `failed`

Use:
- `completed` only when the objective is met and expected evidence exists
- `partial_success` when meaningful progress exists but completion criteria are not fully met
- `blocked` when a concrete dependency, ambiguity, or external condition prevents further honest progress
- `failed` when the attempted approach did not succeed and needs rework

Do not revert to `not_started` or `ready` after execution began unless you split the task and explicitly explain why.

`completed` is invalid when required live operator evidence is missing.
`completed` is invalid when preserved seam parity is still missing for the task's declared scope.

### Step 7: Perform parity audit before closure
Before claiming implementation completion, release closure, or equivalent milestone completion:
1. compare the delivered system against `/plan/spec-map.md`
2. compare it against `/plan/domain-glossary.md`
3. compare it against `/plan/invariants.md`
4. compare it against `/plan/implementation-brief.json`
5. compare it against `/plan/preserved-seams.md`

Report any preserved seam that is:
- missing
- renamed without documentation
- demo-only
- non-executable as presented
- validated only through substitute surfaces

Do not claim completion while any preserved seam in scope fails this audit.

## Required updates after execution

### Update the active task file
You must update:
- `## Status`
- `## Expected Evidence` with actual evidence results
- `## Expected Artifacts` with actual outputs produced
- `## Open Questions` if new real ambiguities emerged
- `## Handoff Notes`
- `## Iteration Log`

In the iteration log, append an entry with:
- timestamp or iteration marker
- summary of what changed
- files changed
- verification run
- resulting status
- next recommended step

The latest iteration log entry MUST also include a standardized evidence block containing:
- `automated_checks[]` (command and result)
- `live_operator_walkthroughs[]` (scenario id, commands, observed output) when required
- `acceptance_gates_covered[]`

### Update `/tasks/index.md`
Reflect:
- new task status
- newly ready tasks if prerequisites were satisfied
- blocked tasks if any
- next recommended task

### Update `/tasks/task-index.json`
Keep machine-readable status, dependencies, and ordering aligned with the markdown source of truth.

### Update `/tasks/queue-state.json`
Refresh:
- ready_tasks
- blocked_tasks
- in_progress_tasks
- completed_tasks
- recommended_next_task
- last_generated_at

### Update impacted `/plan` files when appropriate
Only update plan artifacts if execution materially changed shared understanding, including:
- acceptance gate progress in `/plan/acceptance-matrix.md`
- open ambiguities in `/plan/open-questions.md`
- walkthrough readiness in `/plan/walkthroughs.md`
- preserved seam parity or documented seam deviations in `/plan/preserved-seams.md`
- high-level execution log in `/plan/README.md`

Do not turn `/plan` into a task log. Update it only when repo-wide planning truth changed.

## Release closure mode
When operating in release-closure mode, continue execution until:
1. no `ready` or `in_progress` tasks remain, and
2. all required acceptance gates have evidence.

Release closure MUST be rejected if any required live operator journey fails.

## Forbidden shortcuts

You must not:
- reconstruct required runtime truth from transcript if persisted truth is required
- invent UI-visible state without persisted/runtime/orchestration backing
- collapse `tool_use_id` and `action_id`
- bypass Action Outcome recording where required
- weaken approval binding, digest comparison, or invalidation semantics
- represent delegation as runtime action execution if forbidden by the spec/plan
- ignore write-scope conflict behavior
- casually widen enums or policy modes
- claim completion based only on code being present
- defer all evidence to later while marking a task complete now
- allow demo-only or fixture-only operator surfaces to stand in for preserved seams

## Splitting behavior

If the selected task is too large once you start:
1. split it into smaller tasks
2. update `/tasks/index.md`
3. create new `/tasks/TASK-XXX.md` files using the canonical template
4. update `/tasks/task-index.json`
5. update `/tasks/queue-state.json`
6. execute the first dependency-ready subtask if possible

Preserve traceability back to the parent task.

## Contradiction handling

### If execution reveals a contradiction between `/tasks` and `/plan`
- prefer the safer interpretation
- record the contradiction clearly
- update `/tasks`
- update `/plan/open-questions.md` or relevant plan artifact
- do not silently improvise broad architecture

### If execution reveals a contradiction between `/plan` and the spec-derived constraints already embedded in the repo
- surface it explicitly
- choose the narrowest safe implementation path
- document it

## Required final response

When the iteration ends, reply concisely with:
- task worked on
- resulting status
- key files changed
- verification run
- `/tasks` files updated
- `/plan` files updated, if any
- next recommended task

Do not write a long narrative. The detailed state must live in the repo.
