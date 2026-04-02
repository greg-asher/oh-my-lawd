# plan2tasks.md

You are operating inside a repository that already contains a `/plan` folder derived from the active spec set.

Your job is to convert `/plan` into an executable `/tasks` workspace.

You are not implementing app code. You are not redesigning the architecture. You are materializing the planned task graph into durable, agent-operable task files that can be executed iteratively.

## Mission

Read the planning artifacts in `/plan`, decompose the implementation work into concrete task files, and create a `/tasks` folder that becomes the operational work queue for execution.

The `/tasks` workspace must be:
- dependency-aware
- resumable
- explicit about evidence and acceptance impact
- aligned with the spec-derived plan
- suitable for iterative execution by another agent

## Non-negotiable rules

1. `/plan` is the authoritative planning layer.
2. The spec remains authoritative over `/plan` if a contradiction is discovered, but do not reread raw specs unless needed to resolve a real issue.
3. Do not implement app code.
4. Do not invent new architecture.
5. Do not collapse multiple major work units into one vague task.
6. Do not produce trivial micro-tasks with no coherent completion value.
7. Every task must be dependency-aware, execution-ready, and honest about what counts as done.
8. Every task must identify what evidence or artifacts are required before it can be marked complete.
9. If `/plan/task-graph.md` contains tasks that are too large, split them.
10. Preserve the layer boundaries from the plan.
11. The markdown task files are the human-readable source of truth.
12. `task-index.json` and `queue-state.json` must be lossless projections of task truth, not competing sources of truth.

## Required inputs to read

Read at minimum:
- `/plan/README.md`
- `/plan/system-summary.md`
- `/plan/spec-map.md`
- `/plan/invariants.md`
- `/plan/acceptance-matrix.md`
- `/plan/build-order.md`
- `/plan/task-graph.md`
- `/plan/open-questions.md`
- `/plan/forbidden-shortcuts.md`
- `/plan/walkthroughs.md`
- `/plan/implementation-brief.json`

## Required outcome

Create a `/tasks` folder with at minimum:

### 1. `/tasks/README.md`
Explain:
- what `/tasks` is for
- how to use it
- how it relates to `/plan`
- how task execution should update task files and selected plan files

### 2. `/tasks/index.md`
Create a task index showing for every task:
- task id
- title
- status
- owning layer
- prerequisite task ids
- acceptance gates advanced
- current recommended next task(s)

This should be the main queue surface.

### 3. One markdown file per task
Create files like:
- `/tasks/TASK-001.md`
- `/tasks/TASK-002.md`
- etc.

Each task file MUST use the canonical template exactly.

## Canonical task file template

All task files MUST follow this structure exactly. Sections MUST NOT be omitted or reordered.

```markdown
# Task

## ID
TASK-001

## Title
<task title>

## Status
not_started

## Owning Layer
runtime

## Objective
<concrete objective>

## Why This Exists
<why this task exists>

## Prerequisites
- none

## Acceptance Gates Advanced
- RT-01

## Relevant Plan References
- /plan/task-graph.md
- /plan/acceptance-matrix.md

## Scope
<likely files, modules, or system areas>

## Constraints
- <task-specific constraint>

## Implementation Notes
<what must be true when this task is done>

## Expected Evidence
- <tests, checks, or walkthrough evidence>

## Expected Artifacts
- <files, logs, reports, or other outputs>

## Open Questions
- none

## Handoff Notes
<what the next executing agent should know>

## Iteration Log
- [init] Task created from /plan.
```

## Required task file semantics

Each task file must contain these sections in this order:

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

Allowed `## Status` values:
- `not_started`
- `ready`
- `in_progress`
- `blocked`
- `partial_success`
- `completed`
- `failed`

Allowed `## Owning Layer` values:
- `runtime`
- `orchestration`
- `product`
- `cross_layer` only if truly necessary

## Task decomposition rules

When creating task files:

1. Each task must be a coherent implementation unit, not a vague epic.
2. A task should usually advance one or a small number of closely related acceptance gates.
3. If a task from `/plan/task-graph.md` is too large, split it into smaller tasks now.
4. Keep foundational tasks early:
   - canonical types
   - persisted truth
   - runtime core
   - approval enforcement
   - orchestration state semantics
   - scheduler/write-scope blocking
   - product state projection
   - operator IA and first-run usability
   - provider schema compatibility and loop containment
   - walkthrough verification
5. Keep UI and UX tasks downstream of the persisted/runtime/orchestration truths they depend on.
6. Do not produce placeholder tasks like “do cleanup later” unless they correspond to a real acceptance or verification need.
7. Do not bury operator-validation work inside generic CLI or UX tasks when the plan identifies it as a distinct contract surface.

## Status initialization rules

Initialize task statuses honestly:

- `ready` if all prerequisites are satisfied by already-existing plan assumptions and the task can be started now
- `not_started` if it is a future task with unmet prerequisites
- do not mark anything `in_progress`, `partial_success`, `completed`, `blocked`, or `failed` at creation time unless the plan explicitly requires it

There should usually be one or a very small number of `ready` tasks at the front of the queue.

## Required indexing behavior

`/tasks/index.md` must include:
- a short description of queue semantics
- tasks grouped or ordered by implementation sequence
- status summary counts
- dependency-ready tasks
- blocked tasks if any
- the single recommended next task if one clearly exists

## Required machine-readable output

Also create:

### `/tasks/task-index.json`
This file must be a machine-usable, lossless projection of the markdown task files.

Use this exact top-level shape:

```json
{
  "tasks": [
    {
      "task_id": "TASK-001",
      "title": "string",
      "status": "not_started",
      "owning_layer": "runtime",
      "prerequisites": [],
      "acceptance_gates": ["RT-01"],
      "file_path": "/tasks/TASK-001.md",
      "recommended_order": 1
    }
  ]
}
```

Rules:
- every markdown task file must appear exactly once in `task-index.json`
- every JSON task entry must correspond to exactly one markdown task file
- status must match the markdown file
- prerequisites must reference valid task ids
- acceptance gates must match the markdown file

### `/tasks/queue-state.json`
A compact queue snapshot containing:

```json
{
  "ready_tasks": ["TASK-001"],
  "blocked_tasks": [],
  "in_progress_tasks": [],
  "completed_tasks": [],
  "recommended_next_task": "TASK-001",
  "last_generated_at": "ISO-8601 timestamp"
}
```

## Validation requirements

After generating `/tasks`, you MUST verify:

1. every task in `task-index.json` has a corresponding `.md` file
2. every `.md` task file appears in `task-index.json`
3. statuses match between markdown and JSON
4. prerequisites reference valid task IDs
5. acceptance gates referenced by tasks exist in `/plan/acceptance-matrix.md`
6. `/tasks/index.md`, `task-index.json`, and `queue-state.json` agree on recommended next task
7. every task file contains all required sections in the required order

If validation fails, fix the `/tasks` workspace before finishing.

## Planning quality bar

The `/tasks` workspace must make execution easier than rereading `/plan/task-graph.md`.

Another agent should be able to:
- open `/tasks/index.md`
- select the next ready task
- open a single task file
- execute it honestly
- update task state and evidence without re-planning the whole system

The generated task set MUST include explicit tasks, when present in `/plan`, for:
- operator information architecture and command taxonomy
- assistant-response visibility
- cold-start guided success
- provider schema compatibility hardening
- repeated tool-use loop containment
- live operator walkthrough validation

## Forbidden mistakes

Do not:
- flatten the plan into giant task blobs
- create hyper-granular tasks that produce no meaningful checkpoint
- ignore acceptance gates
- ignore evidence requirements
- lose dependency order
- mix runtime/orchestration/product concerns carelessly
- let product tasks get ahead of runtime truth
- omit handoff-oriented structure
- treat JSON as a second independent source of truth

## Final behavior

At the end:
1. create the full `/tasks` folder
2. create all required task files using the canonical template
3. create `/tasks/index.md`
4. create `/tasks/task-index.json`
5. create `/tasks/queue-state.json`
6. validate consistency between markdown and JSON outputs
7. initialize iteration logs in each task file with a creation entry

Do not implement code. Only create the operational task workspace.
