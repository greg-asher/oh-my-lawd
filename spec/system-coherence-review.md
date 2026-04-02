# Oh My Lawd System Coherence Review

Status: Active
Layer: Cross-layer review and scope control

## 1. Purpose
This document is not a behavioral specification.

It exists to keep the active spec set coherent, implementable, and resistant to unnecessary complexity. It defines:
- the system center of gravity
- cross-layer invariants used for review
- canonical end-to-end walkthroughs used to test coherence
- release classification guidance
- complexity-budget rules for future additions

No runtime, orchestration, or product behavior is normative unless it is defined in its owning document.

## 2. Center of Gravity
Tie-breaker question for new requirements:

Does this requirement make execution safer, more legible, or more resumable in production?

Interpretation:
1. If no, it is probably optional and should not be core.
2. If partly, it is probably product sugar and should not be normative.
3. If yes only in rare cases, it should usually be an extension point, not a core requirement.

The intended center of gravity for this system is:
1. durable execution
2. controlled action
3. inspectability
4. resumability
5. safe delegation

## 3. Release Classification
Every major requirement SHOULD be classified before implementation planning.

Allowed classifications:
1. `core_v1`: required for first release
2. `pre_enterprise`: required before multi-tenant or enterprise hardening
3. `extension_point`: defined as a supported extension seam, not required in first release
4. `aspirational`: useful direction, not release-blocking

### 3.1 Baseline `core_v1` set
The following items are the default `core_v1` baseline unless later removed by explicit design review:
1. Action Envelope
2. Action Outcome
3. deterministic runtime step machine
4. authorization before execution
5. deterministic mixed-batch append ordering
6. atomic `run_state` save and load
7. DAG validation
8. write-scope conflict blocking
9. visible `blocked` state
10. visible `approval_pending` state
11. resumable state restoration without hidden reinterpretation

### 3.2 Likely `extension_point` or later items
The following items are not presumed `core_v1` unless a release plan explicitly upgrades them:
1. multiple scheduler strategies beyond the baseline policy
2. multiple decomposition fallback modes beyond the default
3. broad artifact or evidence subtype expansion
4. advanced policy-profile variations beyond the default supported mode set
5. approval UX beyond the minimum scope needed for safe launch

## 4. Complexity Budget Rule
Before adding a new normative requirement, review it against these questions:
1. What concrete failure does it prevent?
2. Can that failure occur in normal usage, or only at scale or edge cases?
3. Can the problem be detected without formalizing it in the core contract?
4. What implementation burden does it impose across runtime, orchestration, and product surfaces?
5. If omitted, does the system become unsafe, nondeterministic, or materially harder to debug or resume?

If a requirement cannot justify itself through this review, it should not enter the core contract.

## 5. Anti-Bloat Rules
1. Prefer extensibility through shared object models and metadata, not new control-flow branches.
2. Treat every new enum value as suspect until a concrete scenario and implementation difference require it.
3. A normative concept should usually earn its keep in at least two places.
4. Avoid introducing a concept only to make a single section feel complete.
5. Operator cost is part of the design cost.

## 6. Cross-Layer Invariants
### I1. Every attempted action is explainable
If a model issues an action:
1. runtime can normalize it into a stable action identity
2. policy can authorize or deny it
3. execution can produce a stable outcome record
4. product can surface what happened in user terms

### I2. No hidden mutation
If any action mutates state:
1. it has normalized scope
2. permission is checked before mutation
3. orchestration can reason about ownership or conflict where applicable
4. audit can reference the mutation
5. product can present the mutation at the right level of explanation

### I3. Interrupted work is resumable without reinterpretation
If a run is paused or crashes:
1. persisted state survives
2. action and outcome history survives
3. orchestration metadata survives when present
4. product can restore visible state
5. continuation does not require hidden or best-guess reasoning reconstruction

### I4. Delegation never destroys accountability
If a parent run delegates:
1. lineage remains visible
2. ownership remains attributable
3. scope remains bounded
4. failures remain attributable
5. synthesis can explain unresolved gaps and remaining responsibility

### I5. User-visible state reflects execution truth
If the product shows `blocked`, `approval_pending`, `failed_unresolved`, or `completed`:
1. the underlying runtime or orchestration layer supports that state
2. there is a concrete cause or condition behind it
3. freshness and transitions are measurable
4. operator and user-facing views do not rely on guesswork

## 7. Canonical End-to-End Walkthroughs
### W1. Simple successful edit
Scenario:
1. user asks for a code change
2. model emits a read action and a write action
3. both actions are authorized
4. both execute successfully
5. outcomes append in order
6. assistant finalizes
7. product shows completion and explanation

### W2. Mixed batch with denial
Scenario:
1. model emits three actions
2. one action is denied
3. two actions execute
4. one executed action succeeds
5. one executed action fails
6. all outcomes append once in original action order
7. assistant continues from that combined result stream

### W3. Parallel task conflict
Scenario:
1. two tasks become runnable
2. their write scopes overlap
3. scheduler blocks concurrent execution
4. orchestration records the conflict
5. product shows blocked state and remediation

### W4. Approval pending then invalidated
Scenario:
1. a gated action batch is proposed
2. user reviews the proposal
3. user grants approval for an allowed scope
4. the action digest changes before execution
5. prior approval invalidates
6. execution remains blocked until new approval is obtained or actions are revised

### W5. Resume after crash mid-run
Scenario:
1. run crashes after some action outcomes are recorded but before final synthesis
2. persisted state reloads
3. product restores visible state
4. unresolved work remains attributable and resumable

## 8. System Compression Test
The spec set should remain compressible into one mental model:

A run accepts user input, models actions through a deterministic turn engine, normalizes each attempted action into a shared runtime identity, authorizes and records every outcome, persists enough state to resume safely, optionally coordinates tasks and delegated subagents under explicit ownership and scope boundaries, and presents users with live state, approvals, and plain-language explanations grounded in that execution truth.

If future changes make this model materially harder to state or defend, the spec set should be reviewed for unnecessary complexity.
