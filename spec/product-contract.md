# Oh My Lawd Product Contract

Status: Active
Layer: Product, UX, and governance flows (evolvable)

## 1. Scope
Defines user journeys, UX obligations, approval workflow UX, explainability UX, and extensibility onboarding UX.

This document MUST NOT redefine runtime execution semantics, approval binding semantics, task-state semantics, scheduler semantics, or delegation semantics.

## 2. Core Product Journeys

### J1 Guided First Task
Outcome:
- user reaches a first successful result from cold start

### J2 Interactive Iteration
Outcome:
- user can iterate with continuity and safe tooling

### J3 Structured Multi-Agent Delivery
Outcome:
- user can execute decomposed work with traceable progress

### J4 Recover and Resume
Outcome:
- user can recover interrupted work predictably

### J5 Governed Execution
Outcome:
- user can trust policy enforcement and auditability

### J6 Extensible Workspace
Outcome:
- user can safely use plugins and MCP integrations

### J7 Explainability for Non-Expert Users
Outcome:
- user can understand intent, actions, and outcomes without technical internals

### J8 Human Approval Workflow
Outcome:
- user controls high-impact execution with explicit approvals

### J9 Onboarding to Extensibility
Outcome:
- user can onboard extensions through guided steps with actionable remediation

## 3. Explainability Contract
System explanations MUST communicate three semantics:
1. intent: what the system interpreted the user wanted
2. action: what was done and why those actions were chosen
3. outcome: what changed or did not change, plus what the user can do next

For failures and denials, explanations MUST include:
- root cause category
- user-actionable remediation

The display schema MAY evolve as long as semantic coverage remains complete.

## 4. Human Approval UX Contract

### 4.1 User controls
Before gated execution, the user MUST be shown:
1. proposed actions
2. risk summary
3. runtime-defined approval scope and any expiry limit
4. revocation path

### 4.2 Audit UX
User MUST be able to view:
- what was approved
- by whom
- when
- what executed under that approval

## 5. Operator Information Architecture Contract
Operator interaction surfaces MUST be action-oriented, self-describing, and recoverable without prior repository-specific knowledge.

Required operator IA behavior:
1. commands MUST be action-oriented and self-describing
2. commands MUST be logically grouped; flat command sprawl is non-compliant
3. the default path for a first operator action MUST be obvious without external documentation
4. contextual help text MUST be available at the point of use
5. every non-terminal state transition MUST expose what the operator can do next
6. help text, onboarding text, remediation guidance, and next-command suggestions MUST only show commands executable exactly as rendered

### 5.1 Primary Operator Surface Reality
The documented primary operator surface MUST be the real release surface, not a demo substitute.

Required behavior:
1. the primary operator surface MUST accept real user input and route through real runtime and orchestration behavior as applicable
2. demo commands and fixture-backed scenario flows do NOT satisfy the primary operator surface unless the documented release scope explicitly defines them as the real surface
3. if a preserved or canonical operator seam is renamed, the rename MUST be documented before implementation completion

## 6. Assistant Response Visibility Contract
The assistant's actual latest response content MUST always be visible in operator surfaces.

Required behavior:
1. final assistant answer MUST be visible in CLI and equivalent operator surfaces
2. projection, state, or metadata views MUST NOT replace user-facing assistant output
3. this requirement applies to new runs, resumed runs, and interactive operator surfaces
4. if no assistant response exists yet, the system MUST explicitly state why, such as `blocked` or `approval_pending`

## 7. Guided First-Run Usability Contract
Cold-start usage MUST guide the operator to a meaningful first result without dead-end flows.

Required behavior:
1. cold start MUST produce one useful answer in a single guided flow
2. dead-end prompts are prohibited
3. the system MUST guide the operator to the next valid action when a required precondition is missing
4. default flows MUST succeed without prior repository-specific knowledge

## 8. Recovery UX Contract
Recovery states MUST be actionable, not descriptive only.

Every recovery or failure surface MUST include:
1. what failed
2. why it failed
3. the exact next command or commands needed to resolve it

Generic error-only output is non-compliant.
## 9. Extensibility Onboarding UX Contract
Onboarding MUST provide the guided flow:
- discover -> select -> install -> configure -> validate -> activate

At each step, UX MUST provide:
1. current state
2. blocking checks
3. actionable next step

Validation failures MUST show:
- check ID
- reason
- remediation instructions

## 10. Privacy and Trust UX
In `private-hardened` mode, UI MUST clearly indicate:
1. active policy profile
2. blocked egress behavior
3. telemetry and export suppression status

## 11. Live Operational State Visibility
Product surfaces MUST show current execution truth, not only post-hoc explanations.

Minimum visible states:
1. `running`
2. `waiting_for_input`
3. `blocked`
4. `approval_pending`
5. `failed_unresolved`
6. `completed`

State visibility requirements:
1. User MUST be able to identify current state at all times during active runs.
2. For `blocked`, UI MUST show the persisted blocking reason and unblock condition.
3. For `approval_pending`, UI MUST show pending approval scope and required decision.
4. For `failed_unresolved`, UI MUST show unresolved failure summary and next remediation action.

### 11.1 State freshness requirement
State display freshness MUST be testable:
1. default freshness SLO: displayed state transitions MUST reflect backend state changes within 2 seconds in standard operating conditions
2. deployments MAY configure a stricter SLO
3. if deployment conditions cannot meet the default SLO, product MUST disclose the configured freshness target in operator settings

## 12. Product-Level Acceptance Gates
- `PX-01`: non-expert users can explain system behavior from explanation UI artifacts.
- `PX-02`: approval prompts expose runtime-defined approval scope and enforce scope boundaries.
- `PX-03`: extension onboarding failure surfaces deterministic check IDs and remediations.
- `PX-04`: privacy profile status is visible and understandable in product surfaces.
- `PX-05`: active run state is visible and transition freshness meets the configured SLO (default <= 2 seconds).
- `PX-06`: blocked and approval-pending states expose explicit unblock actions.
- `PX-07`: guided-first operator information architecture is discoverable and self-describing.
- `PX-08`: latest assistant response content is always visible in operator surfaces.
- `PX-09`: every non-terminal operator state exposes explicit next action command(s).
- `PX-10`: cold-start setup reaches a first useful answer without dead-end prompts.
- `PX-11`: command naming is consistent, action-oriented, and self-describing.
- `PX-12`: recovery states (`blocked`, `approval_pending`, `failed_unresolved`) provide concrete command-level remediation.
- `PX-13`: the documented primary operator surface accepts real inputs and routes through real runtime/orchestration behavior rather than demo-only scenarios.
- `PX-14`: every command shown in help, onboarding, remediation, and next-action guidance is executable exactly as rendered.
