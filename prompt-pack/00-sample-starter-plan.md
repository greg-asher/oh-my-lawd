# Oh My Lawd App-Generation Plan

## Summary
- Clone [greg-asher/oh-my-lawd](https://github.com/greg-asher/oh-my-lawd) into `<LOCAL_WORKSPACE_ROOT>/oh-my-lawd` and treat that repo as the implementation workspace.
- Follow the repo’s intended slice pipeline exactly: `00-spec2slices` -> per-slice `01..06` loops -> `07-whole-spec-audit`.
- Use the spec as the normative contract, `/plan` as the strategic slice-planning layer, and `/tasks` as the operational slice queue plus review/spec-check evidence surface. Do not skip directly from spec to code.
- Target the repo’s `core_v1` center of gravity first: durable execution, controlled action, inspectability, resumability, and safe delegation.

## Workflow
1. **Bootstrap the repo**
- Clone the repo into `<LOCAL_WORKSPACE_ROOT>/oh-my-lawd`.
- Create a working branch before any generated artifacts or code work, using `<WORKING_BRANCH_NAME>`.
- Read [README.md](https://github.com/greg-asher/oh-my-lawd/blob/main/README.md), all files under `spec/`, and the full `00` through `07` prompt pack under `prompt-pack/`.
- Keep `spec/` read-only for the entire workflow.

2. **Generate the slice manifest from the spec**
- In a fresh agent session rooted at the cloned repo, run [`prompt-pack/00-spec2slices.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/00-spec2slices.md) against `spec/`.
- Require the full planning package plus `plan/slices.md` and `plan/slice-manifest.json`.
- Do not proceed until the slice manifest breaks the spec into small, testable capability slices with `slice_id`, `source_spec_refs`, `acceptance_gates`, and inter-slice dependencies.

3. **Validate root planning artifacts before slice execution**
- Confirm `/plan` preserves layer boundaries:
  runtime owns execution, persistence, approval binding, and error semantics;
  orchestration owns DAGs, task states, write scopes, scheduling, and delegation lineage;
  product owns journeys, explainability, approval UX, onboarding UX, and live state visibility.
- Confirm `/plan/open-questions.md` contains only real ambiguities. If it contains stack-blocking or architecture-blocking gaps, resolve those before moving on.
- Confirm `/plan/build-order.md` starts with persisted truth and execution core before orchestration polish or product UX.
- Confirm `plan/slice-manifest.json` uses small slices that map to one primary capability or journey.

4. **Run the per-slice planning and tasking loop**
- For each slice in `plan/slice-manifest.json`, run [`prompt-pack/01-slice2metaplan.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/01-slice2metaplan.md), then [`prompt-pack/02-metaplan2detailedplan.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/02-metaplan2detailedplan.md), then [`prompt-pack/03-detailedplan2tasks.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/03-detailedplan2tasks.md).
- Require each task file to include `## Slice ID` and `## Relevant Spec References`.
- Do not accept the queue unless it is scoped to the current slice and has a single honest recommended next task.

5. **Execute, review, and spec-check each slice**
- For implementation, use a fresh agent session per task iteration and start each time from [`prompt-pack/04-tasks2build.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/04-tasks2build.md).
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
- After the slice queue is exhausted, run [`prompt-pack/05-review.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/05-review.md) and [`prompt-pack/06-spec-check.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/06-spec-check.md).
- If review fails, route back to slice build execution. If spec-check fails, route back to detailed planning for the same slice.
- Commit only slices that pass both review and direct spec-check.

6. **Close with the whole-spec audit**
- After all slices pass, run [`prompt-pack/07-whole-spec-audit.md`](https://github.com/greg-asher/oh-my-lawd/blob/main/prompt-pack/07-whole-spec-audit.md).
- If the whole-spec audit fails, create one synthetic fix slice, run it through `01..06`, then rerun the whole-spec audit.
- Do not declare completion until the whole-spec audit passes.

## Acceptance and Verification
- `/plan` must be complete, internally consistent, and directly traceable to the spec set before `/tasks` is created.
- `/tasks` must pass the prompt’s own consistency checks: markdown/JSON parity, valid prerequisites, valid acceptance gates, slice ownership metadata, and a coherent recommended next task.
- The implementation phase must drive the repo toward the spec acceptance gates, especially the `core_v1` baseline from the coherence review:
  Action Envelope, Action Outcome, deterministic turn engine, authorization before execution, deterministic mixed-batch append ordering, atomic `run_state` save/load, DAG validation, write-scope conflict blocking, visible `blocked`, visible `approval_pending`, and resumable restore without transcript reconstruction.
- Release evidence must attach to the real operator surface and preserved seams, not only to demo flows or fixture-backed walkthroughs.
- Every slice must produce review output and a spec-check result that compares `/spec` directly against code, commands, runtime behavior, and operator-visible outputs.
- When persisted runtime truth is in scope, the main operator path must create, load, or resume real persisted state.
- Final release validation must cover the canonical walkthroughs W1-W5 and the runtime (`RT-*`), orchestration (`OR-*`), and product (`PX-*`) gates with honest evidence plus a passing whole-spec audit.

## Assumptions and Defaults
- The cloned repo itself is the app-generation workspace; this is not a reference-only repo.
- The stopping point is a runnable first release, not just generated `/plan` and `/tasks` artifacts.
- Stack-specific choices should not be invented ahead of the spec-derived plan; if a concrete stack is still unresolved after `/plan`, resolve it there before the first code task.
- Fresh agent sessions are preferred for each major phase and each build task so repo state, not chat history, remains the durable source of truth.
