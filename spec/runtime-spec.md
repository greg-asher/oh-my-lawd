# Oh My Lawd Runtime Specification

Status: Active
Layer: Runtime Core (stable)

## 1. Scope
This document defines the stable runtime contract only:
- turn engine
- tool engine
- policy engine
- persisted run state
- adapter normalization
- error semantics
- approval binding and enforcement

This document MUST NOT define product UX, onboarding flows, task-state semantics, scheduler semantics, or delegation semantics.

## 2. Canonical Runtime Operations
- `run_agent(config, prompt)`

Orchestration operations are defined in the Orchestration Specification.

## 3. Canonical Runtime Types

### 3.1 Roles
`system | user | assistant | tool`

### 3.2 Content blocks
- `text { text }`
- `tool_use { id, capability_class, operation, input }`
- `tool_result { tool_use_id, action_id, capability_class, operation, output, is_error }`
- optional `image { source }`

### 3.3 Permission modes
`read-only | workspace-write | danger-full-access | prompt | allow`

### 3.4 Persisted `run_state`
Every run MUST persist a common `run_state` envelope with:
1. `run_id`
2. `session_id`
3. `version`
4. `run_mode` (`agent | tasks | team`)
5. `execution_status`
6. `created_at`
7. `updated_at`
8. `transcript`
9. `runtime_cursor`
10. `ledger`
11. `frontier`
12. `approval_state`
13. optional `orchestration_state` (structure defined by Orchestration Specification)

`run_state` substructures:
1. `transcript.messages[]`
2. `runtime_cursor.current_turn_id`
3. `runtime_cursor.current_step_type`
4. `runtime_cursor.iteration_count`
5. `runtime_cursor.max_iteration_limit`
6. `ledger.action_outcomes[]`
7. `frontier.open_action_batch | null`
8. `frontier.blocking_reason | null`
9. `approval_state.approval_records[]`

`execution_status` is the canonical persisted run-status vocabulary. Product-visible states are derived from persisted execution truth and MUST NOT redefine runtime execution semantics.

`frontier.open_action_batch`, when present, MUST include:
1. `batch_id`
2. `action_envelopes[]`

### 3.5 Action Envelope (first-class runtime object)
Every executable model-issued action MUST be normalized into a single Action Envelope before authorization and execution.

Required Action Envelope fields:
1. `action_id` (stable within turn)
2. `tool_use_id` (original model reference)
3. `capability_class`
4. `operation`
5. `input`
6. `required_permission_mode`
7. `target_scopes[]` (normalized resource scopes used by policy engine)
8. `correlation` (`session_id`, `turn_id`, optional `task_id`)

`tool_use.capability_class` MUST normalize to `Action Envelope.capability_class`.

All runtime subsystems (policy, execution, audit, explainability emitters) MUST reference this same Action Envelope identity.

Normalized scope grammar for `target_scopes[]` MUST be:
1. `fs_root:<absolute_path_prefix>`
2. `resource_key:<namespace>/<key>`
3. `namespace:<logical_namespace>`
4. `network_host:<host_or_domain>`

`target_scopes[]` MUST use this grammar exactly.

### 3.6 Action Outcome (first-class runtime ledger object)
Every Action Envelope MUST produce one Action Outcome record.

Required Action Outcome fields:
1. `action_id`
2. `outcome_type` (`denied | succeeded | failed | aborted`)
3. `error_code` (required when `outcome_type` is `denied | failed | aborted`)
4. `output` (string or structured payload)
5. `started_at` (timestamp)
6. `completed_at` (timestamp)
7. `correlation` (`session_id`, `turn_id`, optional `task_id`)

`tool_result.tool_use_id` references model-issued action lineage.
`tool_result.action_id` references runtime-issued execution lineage.
`tool_result` blocks are the conversational representation; Action Outcome is the runtime and audit representation. Every `tool_result` representing an executable action MUST carry the matching `action_id`, and that `action_id` MUST match exactly one Action Outcome.

## 4. Capability-Class Tool Model
The runtime MUST classify executable actions by capability class.

### 4.1 Capability classes
- `io`: file and structured reads and writes
- `execution`: shell, repl, or process execution
- `network`: fetch, search, or HTTP operations
- `coordination`: messaging, planning, and meta operations that do not create delegation lineage

A concrete tool operation MUST declare:
1. `capability_class`
2. `operation`
3. `input_schema`
4. `required_permission_mode`

The runtime MAY expose named operations (`read_file`, `grep_search`), but authorization and auditing MUST be based on capability metadata, not name matching.

## 5. Formal Turn Step Model
A turn MUST execute the following stateful step machine.

### 5.1 Step types
- `STEP_RECEIVE_INPUT`
- `STEP_MODEL_INFER`
- `STEP_PARSE_ASSISTANT_OUTPUT`
- `STEP_AUTHORIZE_ACTIONS`
- `STEP_EXECUTE_ACTIONS`
- `STEP_APPEND_ACTION_RESULTS`
- `STEP_FINALIZE`
- `STEP_FAIL`

### 5.2 Transition rules
1. `STEP_RECEIVE_INPUT -> STEP_MODEL_INFER`
2. `STEP_MODEL_INFER -> STEP_PARSE_ASSISTANT_OUTPUT`
3. `STEP_PARSE_ASSISTANT_OUTPUT -> STEP_FINALIZE` only when interpretation is `terminal_final_answer`
4. `STEP_PARSE_ASSISTANT_OUTPUT -> STEP_AUTHORIZE_ACTIONS` only when interpretation is `non_terminal_with_actions`
5. `STEP_AUTHORIZE_ACTIONS -> STEP_EXECUTE_ACTIONS` with the authorized subset of the same action batch
6. Denied actions MUST be retained as synthetic outcomes and MUST join the same batch append phase
7. `STEP_EXECUTE_ACTIONS -> STEP_APPEND_ACTION_RESULTS` for the full batch (denied plus executed outcomes)
8. `STEP_APPEND_ACTION_RESULTS -> STEP_MODEL_INFER`
9. `STEP_PARSE_ASSISTANT_OUTPUT -> STEP_FAIL` when interpretation is `non_terminal_non_actionable` or `parse_invalid`
10. Any other unrecoverable error -> `STEP_FAIL`

### 5.3 Termination conditions
Turn terminates only on:
1. `STEP_FINALIZE` (success)
2. `STEP_FAIL` (failure)
3. max-iteration guard hit (`TURN_MAX_ITERATIONS_EXCEEDED`)

### 5.4 Multi-action behavior
- Multiple actions per model step are allowed.
- Runtime MUST preserve model-issued action order for appended outcomes.
- Denied, success, and failed execution outcomes from the same batch MUST be appended in one append phase in original action order.
- Partial action failure MUST NOT abort sibling actions unless configured fail-fast policy explicitly requires it.

### 5.5 Assistant output interpretation seams
After `STEP_PARSE_ASSISTANT_OUTPUT`, runtime MUST classify parsed output into exactly one interpretation:
1. `terminal_final_answer`: actionable final response, no further actions required
2. `non_terminal_with_actions`: one or more valid actions present
3. `non_terminal_non_actionable`: response is not final and contains no executable actions
4. `parse_invalid`: response cannot be normalized to canonical assistant state

Required handling:
- `terminal_final_answer` -> `STEP_FINALIZE`
- `non_terminal_with_actions` -> `STEP_AUTHORIZE_ACTIONS`
- `non_terminal_non_actionable` -> `STEP_FAIL` with `ASSISTANT_OUTPUT_NON_ACTIONABLE`
- `parse_invalid` -> `STEP_FAIL` with `ASSISTANT_OUTPUT_PARSE_FAILED`

## 6. Policy and Approval Hooks
1. Every action MUST be authorized before execution.
2. Denied actions MUST produce `tool_result.is_error=true` and MUST NOT execute.
3. Pre and post hooks MAY mutate metadata and MAY deny; deny is terminal for that action.
4. Approval binding and enforcement are runtime responsibilities.

### 6.1 Approval binding
Approvals MUST bind to runtime-issued Action Envelopes, not to raw model text or UI display text.

Every persisted approval record in `approval_state.approval_records[]` MUST include:
1. `approval_id`
2. `approval_scope` (`single_action | task_batch | session_window`)
3. `approval_status` (`pending | granted | denied | invalidated | expired`)
4. `covered_action_ids[]` or `approval_window_binding`
5. `approval_digest`
6. `created_at`
7. `resolved_at | null`

Approval scope semantics:
1. `single_action` binds to exactly one `action_id`.
2. `task_batch` binds to a finite covered `action_id` set.
3. `session_window` binds to future Action Envelopes only when they match the persisted `approval_window_binding`.

`approval_window_binding` MAY constrain future Action Envelopes by:
1. permission mode ceiling
2. allowed target-scope subset
3. optional capability-class subset
4. optional expiry

### 6.2 Approval digest and invalidation
`approval_digest` MUST be computed over the approval-relevant normalized execution surface, not over display text.

Minimum digest inputs:
1. `action_id`
2. `capability_class`
3. `operation`
4. `required_permission_mode`
5. `target_scopes[]`

Normalized `input` MUST be included whenever it materially affects side effects.

An approval record MUST be invalidated if the covered execution surface changes such that the persisted `approval_digest` no longer matches the pending execution candidate.

At minimum, approval MUST invalidate when:
1. covered action set changes
2. operation changes
3. permission mode escalates
4. target scope changes or broadens
5. input changes in a side-effect-relevant way
6. a `session_window` candidate falls outside the approved binding constraints

### 6.3 Approval enforcement
Approval-gated execution MUST remain blocked unless a valid persisted approval record covers the pending execution candidate.
Digest comparison MUST occur at the execution boundary before any covered action executes.

Approval-gate UX is defined in the Product Contract; runtime defines only approval binding and enforcement semantics.

## 7. Persistence and Compatibility
1. `run_state` saves MUST be atomic.
2. Loader MUST validate schema version.
3. Incompatible versions MUST return `SESSION_LOAD_FAILED` with version detail.
4. On restore, the system MUST resume from persisted `runtime_cursor`, `frontier`, `approval_state`, and committed `ledger` state.
5. The system MUST NOT reconstruct prior committed execution from transcript history.

## 8. Provider Adapter Contract
1. Adapters MUST normalize provider outputs into canonical runtime types.
2. Stream MUST emit exactly one terminal event (`done` or `error`).
3. Stop reason and token usage MUST be normalized.

### 8.1 Structured output compatibility contract
Provider adapters MUST tolerate provider-side structured output variation within deterministic runtime handling.

Required behavior:
1. adapters MUST normalize provider responses into provider-supported schema subsets before exposing them to runtime consumers
2. adapters MUST coerce partial provider structures when deterministic coercion is possible
3. provider schema rejection MUST map to deterministic runtime error semantics with actionable details
4. hard provider failures without a deterministic fallback path are non-compliant

### 8.2 Model loop containment contract
The runtime MUST detect repeated equivalent tool-use behavior within a turn.

Required behavior:
1. repeated equivalent tool-use signatures within a turn MUST be detected
2. repeated equivalent tool-use behavior MUST trigger deterministic containment
3. deterministic containment MUST either:
   - abort with an explicit loop-related runtime error, or
   - transition to a deterministic fallback path
4. infinite or redundant tool-use loops are prohibited

### 8.3 Dead-end access-request prevention
If the transcript already contains sufficient tool results for response synthesis, the assistant MUST NOT finalize with a dead-end access request.

Required behavior:
1. if sufficient `tool_result` content already exists for synthesis, the assistant MUST produce a response or fail deterministically for another explicit reason
2. finalization with generic `need access` or equivalent dead-end language is prohibited when sufficient tool results already exist

## 9. Error Contract
All errors MUST include `code`, `message`, optional `details`.

Required runtime error codes:
- `TURN_MAX_ITERATIONS_EXCEEDED`
- `PROVIDER_REQUEST_FAILED`
- `PROVIDER_STREAM_PROTOCOL_ERROR`
- `ASSISTANT_OUTPUT_PARSE_FAILED`
- `ASSISTANT_OUTPUT_NON_ACTIONABLE`
- `TOOL_NOT_FOUND`
- `TOOL_INPUT_VALIDATION_FAILED`
- `TOOL_EXECUTION_FAILED`
- `TOOL_ABORTED`
- `PERMISSION_DENIED`
- `HOOK_DENIED`
- `HOOK_EXECUTION_WARNING`
- `SESSION_LOAD_FAILED`
- `SESSION_SAVE_FAILED`
- `CONFIG_PARSE_FAILED`
- `PROVIDER_SCHEMA_INCOMPATIBLE`
- `MODEL_TOOL_LOOP_DETECTED`
- `MODEL_DEAD_END_ACCESS_REQUEST`

## 10. Runtime Acceptance Gates
- `RT-01`: step machine follows legal transitions only.
- `RT-02`: max-iteration guard is enforced.
- `RT-03`: multi-action turn supports partial failures deterministically.
- `RT-03A`: mixed batches (denied plus executed) append exactly once in original action order.
- `RT-03B`: every Action Envelope yields exactly one Action Outcome with matching `action_id`.
- `RT-03C`: every `tool_result` representing an executable action carries the matching `action_id`, and that `action_id` matches exactly one Action Outcome.
- `RT-04`: denied actions never execute.
- `RT-05`: stream terminal event uniqueness holds.
- `RT-05A`: parse-invalid assistant output fails with `ASSISTANT_OUTPUT_PARSE_FAILED`.
- `RT-05B`: non-terminal non-actionable assistant output fails with `ASSISTANT_OUTPUT_NON_ACTIONABLE`.
- `RT-05C`: provider schema compatibility is validated at the execution boundary.
- `RT-05D`: provider rejection and normalization failures map to deterministic runtime errors.
- `RT-05E`: repeated equivalent tool-use loops are contained deterministically.
- `RT-05F`: dead-end access-request finalization is prevented when sufficient tool results already exist.
- `RT-06`: `run_state` save and load atomicity and compatibility checks pass.
- `RT-06A`: restore resumes from persisted `runtime_cursor`, `frontier`, `approval_state`, and `ledger` without transcript reconstruction.
- `RT-07`: approval-gated execution remains blocked without a valid persisted approval record.
- `RT-07A`: granted approval binds to covered actions via `approval_digest`.
- `RT-07B`: digest mismatch invalidates approval before execution.
- `RT-07C`: restored runs preserve approval records without transcript inference.
