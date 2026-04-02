# Oh My Lawd Orchestration Specification

Status: Active
Layer: Orchestration (evolvable, runtime-dependent)

## 1. Scope
Defines:
- task graph model
- task state semantics
- scheduler behavior
- team and delegation semantics
- synthesis semantics
- taxonomy for task outputs

Does not define runtime approval binding, runtime persistence semantics, or product UX.

## 2. Canonical Operations
- `run_tasks(team, tasks)`
- `run_team(team, goal)`

## 3. Task Contract
Required fields:
- `id`
- `title`
- `description`
- `status`
- `createdAt`
- `updatedAt`

Optional fields:
- `assignee`
- `dependsOn`
- `result`

### 3.1 Task result contract
For `status=completed`, `result` MUST be present and MUST include:
1. `outcome_type` (`success | partial_success`)
2. `summary` (non-empty)
3. `artifacts[]` (field required, may be empty)
4. `evidence[]` (field required, may be empty)
5. `handoff_notes` (string, may be empty)
6. `verification` (object conforming to section 3.3)

For `status=failed`, `result` MUST include:
1. `failure_code`
2. `failure_summary`
3. `remediation_steps[]`
4. `artifacts[]` (field required, may be empty)
5. `evidence[]` (field required, may be empty)
6. `handoff_notes` (string, may be empty)

### 3.2 Artifact and evidence typing
Each artifact entry MUST include:
1. `artifact_id`
2. `artifact_kind` (`file | patch | log | other`)
3. `locator` (path, URL, or resource pointer)
4. `producer_task_id`

Each evidence entry MUST include:
1. `evidence_id`
2. `evidence_kind` (`test_result | trace | reference | other`)
3. `content` (structured or text)
4. `producer_task_id`

Non-normative subtype detail MAY be carried as implementation metadata.

### 3.3 Verification model
Verification data for completed tasks MUST include:
1. `verification_status` (`unverified | verified`)
2. `verification_method` (`automated | human_review | other`)
3. `verification_evidence_refs[]` (references to `evidence_id`, may be empty only when `verification_status=unverified`)

## 4. DAG Validation
Before execution, orchestration MUST reject graphs with:
- unknown dependencies
- self dependencies
- cycles

Failure code: `TASK_DAG_INVALID` with full violation list.

## 5. Task State Machine
Allowed transitions only:
- `pending -> blocked`
- `blocked -> pending`
- `blocked -> failed`
- `pending -> in_progress`
- `in_progress -> completed`
- `in_progress -> failed`

Illegal transitions MUST fail with `TASK_INVALID_TRANSITION`.

### 5.1 Blocked task semantics
A task is `blocked` when it is not runnable due to a concrete precondition, such as:
- unmet dependency
- write-scope conflict
- required approval
- external prerequisite

Task-level blocking reasons MUST be represented in orchestration blocking metadata.

## 6. Assignment and Ownership Boundaries

### 6.1 Ownership
Each `in_progress` task MUST have a single owner (`assignee`).

### 6.2 Shared state rules
1. Tasks MUST declare write scope for mutable artifacts.
2. Parallel tasks with overlapping write scope MUST NOT run concurrently unless explicit lock mode is enabled.
3. Conflict violations MUST fail with `TASK_WRITE_CONFLICT`.

### 6.3 Write scope model
Write scope MUST be represented as normalized entries of one of:
1. `fs_root:<absolute_path_prefix>`
2. `resource_key:<namespace>/<key>`
3. `namespace:<logical_namespace>`

Normalization requirements:
1. `fs_root` paths MUST be absolute and canonicalized before overlap checks.
2. `resource_key` comparisons MUST be exact match on normalized namespace and key.
3. `namespace` overlap is exact namespace equality unless configured hierarchical namespace policy is enabled.

Overlap rules:
1. Any identical `resource_key` overlaps.
2. Any identical `namespace` overlaps.
3. `fs_root` overlaps when one path prefix contains the other.

## 7. Scheduling
Required v1 baseline policy:
- `dependency_first`

Optional policy extensions:
- `capability_match`
- `round_robin`
- `least_busy`

Scheduler contract:
1. Scheduler MUST only select `pending` tasks whose dependencies are satisfied.
2. Scheduler MUST NOT dispatch tasks with conflicting write scopes unless explicit lock policy permits it.
3. Scheduler MUST respect single-owner semantics for `in_progress` tasks.
4. Scheduler decisions MUST be deterministic under the configured policy.
5. Configured scheduling policy MUST be recorded in orchestration metadata.

## 8. Delegation Semantics
Delegation is an orchestration primitive, not a runtime capability-class action.

### 8.1 Delegation operations
- `spawn_subagent`
- `assign_task`
- `join_subagent`
- `close_subagent`

These MUST have explicit lineage tracking:
- `parent_run_id`
- `subagent_id`
- `task_id`

### 8.2 Recursion control
Sub-agent depth MUST be bounded by configurable `max_delegation_depth`.

## 9. `run_team` Decomposition and Synthesis
1. Decomposition output MUST parse into valid task specs.
2. Parse failure default policy: `strict_fail` (`TASK_DAG_INVALID`).
3. Final synthesis MUST report:
- completed work
- partial successes
- failed items
- unresolved gaps

### 9.1 Decomposition policy extension point
Decomposition failure policy is an orchestration extension point with:
1. `strict_fail` (default, REQUIRED)
2. `review_required_fallback` (OPTIONAL)
3. `partial_materialization` (OPTIONAL)

If non-default policy is enabled, orchestration MUST emit active policy metadata into orchestration metadata and audit metadata.

## 10. Orchestration Metadata
When orchestration is active, `orchestration_state` MUST include:
1. `tasks[]`
2. `assignment_metadata`
3. `delegation_lineage`
4. `decomposition_policy_metadata`
5. `write_scopes`
6. `blocking_metadata`
7. `scheduling_policy`

## 11. Orchestration Errors
Required additional codes:
- `TASK_DAG_INVALID`
- `TASK_INVALID_TRANSITION`
- `TASK_ASSIGNEE_NOT_FOUND`
- `TASK_WRITE_CONFLICT`
- `DELEGATION_DEPTH_EXCEEDED`

## 12. Orchestration Acceptance Gates
- `OR-01`: invalid DAGs are always rejected pre-execution.
- `OR-02`: ownership uniqueness for `in_progress` tasks is enforced.
- `OR-03`: conflicting write scopes are blocked.
- `OR-04`: delegation lineage is complete and queryable.
- `OR-05`: synthesis contains explicit unresolved gaps when failures exist.
- `OR-06`: completed and failed tasks both include required `artifacts[]`, `evidence[]`, and `handoff_notes`.
- `OR-07`: write-scope normalization yields deterministic overlap decisions.
- `OR-08`: task blocking is reachable only through legal task transitions and carries concrete blocking metadata.
- `OR-09`: `dependency_first` is the required v1 baseline scheduling policy.
- `OR-10`: configured scheduling policy is persisted in orchestration metadata.
- `OR-11`: optional scheduling policies do not weaken dependency, write-scope, or ownership guarantees.
