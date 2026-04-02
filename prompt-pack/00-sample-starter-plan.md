# Oh My Lawd App-Generation Plan

## Summary
- Clone [greg-asher/oh-my-lawd](https://github.com/greg-asher/oh-my-lawd) into `<LOCAL_WORKSPACE_ROOT>/oh-my-lawd` and treat that repo as the implementation workspace.
- Follow the repo’s intended pipeline exactly: `spec/` -> `/plan` -> `/tasks` -> iterative implementation.
- Use the spec as the normative contract, `/plan` as the strategic build layer, and `/tasks` as the operational queue. Do not skip directly from spec to code.
- Target the repo’s `core_v1` center of gravity first: durable execution, controlled action, inspectability, resumability, and safe delegation.

## Workflow
1. **Bootstrap the repo**
- Clone the repo into `<LOCAL_WORKSPACE_ROOT>/oh-my-lawd`.
- Create a working branch before any generated artifacts or code work, using `<WORKING_BRANCH_NAME>`.
- Read [README.md](https://github.com/greg-asher/oh-my-lawd/blob/main/README.md), all files under `spec/`, and all three prompt packs under `prompt-pack/`.
- Keep `spec/` read-only for the entire workflow.

2. **Generate `/plan` from the spec**
- In a fresh agent session rooted at the cloned repo, run the contents of [`prompt-pack/01-spec2plan.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/01-spec2plan.md) against `spec/`.
- Require the full planning package the prompt specifies, including `README.md`, `system-summary.md`, `spec-map.md`, `domain-glossary.md`, `invariants.md`, `acceptance-matrix.md`, `build-order.md`, `task-graph.md`, `open-questions.md`, `forbidden-shortcuts.md`, `walkthroughs.md`, and `implementation-brief.json`.
- Do not proceed to `/tasks` until `/plan` explicitly captures the canonical contracts that will anchor implementation:
  `run_agent(config, prompt)`, `run_tasks(team, tasks)`, `run_team(team, goal)`, `run_state`, Action Envelope, Action Outcome, task/result schema, approval records, orchestration metadata, and product-visible run states.

3. **Validate `/plan` before task generation**
- Confirm `/plan` preserves layer boundaries:
  runtime owns execution, persistence, approval binding, and error semantics;
  orchestration owns DAGs, task states, write scopes, scheduling, and delegation lineage;
  product owns journeys, explainability, approval UX, onboarding UX, and live state visibility.
- Confirm `/plan/open-questions.md` contains only real ambiguities. If it contains stack-blocking or architecture-blocking gaps, resolve those before moving on.
- Confirm `/plan/build-order.md` starts with persisted truth and execution core before orchestration polish or product UX.

4. **Generate `/tasks` from `/plan`**
- In a new agent session rooted at the same repo, run [`prompt-pack/02-plan2tasks.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/02-plan2tasks.md) against `/plan`.
- Require `/tasks/README.md`, `/tasks/index.md`, one canonical `TASK-XXX.md` per task, `/tasks/task-index.json`, and `/tasks/queue-state.json`.
- Do not accept the queue unless it has a very small ready set and a single recommended next task, with foundational work first.

5. **Execute the build iteratively from `/tasks`**
- For implementation, use a fresh agent session per task iteration and start each time from [`prompt-pack/03-tasks2build.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/03-tasks2build.md).
- Always execute the current recommended `ready` task from `/tasks/index.md` and `/tasks/queue-state.json`.
- Preserve the required dependency order:
  canonical types and contracts ->
  persisted `run_state`/ledger/approval truth ->
  deterministic runtime step machine ->
  authorization and approval digest enforcement ->
  action outcome and `tool_result` lineage ->
  atomic save/load and restore ->
  orchestration DAG/state/write-scope rules ->
  delegation lineage and synthesis ->
  product state projection, explainability, approval UX, onboarding UX ->
  walkthrough verification.
- After every task, update the task markdown file first, then `index.md`, `task-index.json`, `queue-state.json`, and only the `/plan` files whose shared truth changed.

## Acceptance and Verification
- `/plan` must be complete, internally consistent, and directly traceable to the spec set before `/tasks` is created.
- `/tasks` must pass the prompt’s own consistency checks: markdown/JSON parity, valid prerequisites, valid acceptance gates, and a coherent recommended next task.
- The implementation phase must drive the repo toward the spec acceptance gates, especially the `core_v1` baseline from the coherence review:
  Action Envelope, Action Outcome, deterministic turn engine, authorization before execution, deterministic mixed-batch append ordering, atomic `run_state` save/load, DAG validation, write-scope conflict blocking, visible `blocked`, visible `approval_pending`, and resumable restore without transcript reconstruction.
- Final release validation must cover the canonical walkthroughs W1-W5 and the runtime (`RT-*`), orchestration (`OR-*`), and product (`PX-*`) gates with honest evidence.

## Assumptions and Defaults
- The cloned repo itself is the app-generation workspace; this is not a reference-only repo.
- The stopping point is a runnable first release, not just generated `/plan` and `/tasks` artifacts.
- Stack-specific choices should not be invented ahead of the spec-derived plan; if a concrete stack is still unresolved after `/plan`, resolve it there before the first code task.
- Fresh agent sessions are preferred for each major phase and each build task so repo state, not chat history, remains the durable source of truth.
