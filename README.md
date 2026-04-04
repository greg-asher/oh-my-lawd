# Oh My Lawd

Oh My Lawd is an independent open-source specification project for an agent harness: a runtime, orchestration, and product control system that turns a language model from a text generator into a controlled, repeatable execution engine.

This project is not affiliated with or endorsed by Anthropic.

## License
This repository is licensed under [Apache-2.0](LICENSE).

Using this repository as a specification reference does not automatically require downstream implementations to be licensed under Apache-2.0. License obligations attach to material copied from this repository, not merely to ideas, requirements, or architectural patterns implemented independently.

## What Is An Agent Harness?
An agent harness is not the model. It is the system around the model that governs how decisions are made, actions are executed, and state evolves over time.

At a minimum, a serious harness defines:
- an execution model with explicit steps, validation, and transitions
- a durable state model for tasks, intermediate outputs, tool results, and prior decisions
- a strict tool interface layer with typed inputs, structured outputs, and explicit failures
- transition logic for continue, branch, wait-for-human, and terminate paths
- a clear boundary between decision and mutation
- reconstructable execution records and inspectable state

Harness engineering is the discipline of designing those runtimes so agents behave like systems, not demos.

In practical terms, the harness is a deterministic shell around a non-deterministic core.

This repository treats harness design as infrastructure work. The model is a component. The real product is the runtime system that enforces control, repeatability, replayability, and operator visibility.

## Background
This specification was created agentically.

It emerged from analysis of the rapid wave of Claude Code clones that appeared on GitHub in the 48 hours leading up to April 2, 2026, after Anthropic's Claude Code source leak became public. For broader context, see the Wall Street Journal article: [Anthropic Races to Contain Leak of Code Behind Claude AI Agent](https://www.wsj.com/tech/ai/anthropic-races-to-contain-leak-of-code-behind-claude-ai-agent-4bc5acc7?gaa_at=eafs&gaa_n=AWEtsqcUPuZoCO1ciJb8rRUZZy1kFHfazh0-AztaQO5XmVMgce0WSD6Kzm_t&gaa_ts=69ce65f5&gaa_sig=FwVmHcmH8vuU6zt6lIhJI9n1vKDiS6-IaFfKzitSBJIO5UgsUIVYoWOZ_AL5gXM_sZUgRpW9J1eEtsYWhuk0Ig%3D%3D).

Our agents identify Claude Code clones emerging on GitHub, analyze the implementations that remain publicly accessible, and continuously update a uniform best-practices specification distilled from the repos that survive DMCA takedowns.

The goal of this repository is not to mirror any leaked code. The goal is to capture the durable architectural patterns, execution semantics, orchestration boundaries, and product behaviors that emerged across the clone ecosystem and turn them into a coherent public specification for agent harnesses.

## Why Harness Engineering Matters
Raw LLM usage fails in predictable ways:
- non-deterministic outputs
- silent failure modes
- weak memory discipline
- no execution guarantees
- poor debuggability

Agent harnesses exist to impose systems-level constraints on probabilistic components.

Strong harness engineering emphasizes:
- determinism boundaries around model invocation and output validation
- state as a first-class primitive rather than chat history
- separation of decision, execution, and orchestration
- replayability and auditability
- failure handling, retry logic, and human intervention points
- operator control surfaces for inspection, recovery, and guided intervention

The architectural direction is toward agents as systems of action, not conversation:
- fewer chat-loop abstractions
- more task-oriented runtimes
- stronger execution guarantees
- closer alignment with workflow engines, event-driven systems, and durable orchestration runtimes

## Roadmap
This repository is intended to become a continuously maintained public specification rather than a static snapshot.

Near-term roadmap:
- expand the harness analysis net beyond Claude Code clones to include existing open-source harnesses such as Codex and OpenCoder
- compare those systems against the current specification and fold durable patterns back into the spec set
- automate weekly releases of the specification so changes are published on a regular cadence
- proactively monitor new and emerging agent harnesses as they appear
- evaluate new harnesses against the specification and use those comparisons to refine the contract over time

The long-term goal is to maintain a public, implementation-grounded specification that tracks the agent-harness ecosystem as it evolves while preserving a stable core runtime, orchestration, and product model.

## Spec Set
- [Specification Index](spec/oh-my-lawd.md)
- [Runtime Specification](spec/runtime-spec.md)
- [Orchestration Specification](spec/orchestration-spec.md)
- [Product Contract](spec/product-contract.md)
- [System Coherence Review](spec/system-coherence-review.md)

## Prompt Pack
This repository also includes a prompt pack for turning the spec set into a spec-validated implementation workflow:

- [prompt-pack/00-sample-starter-plan.md](prompt-pack/00-sample-starter-plan.md)
- [prompt-pack/00-spec2slices.md](prompt-pack/00-spec2slices.md)
- [prompt-pack/01-slice2metaplan.md](prompt-pack/01-slice2metaplan.md)
- [prompt-pack/02-metaplan2detailedplan.md](prompt-pack/02-metaplan2detailedplan.md)
- [prompt-pack/03-detailedplan2tasks.md](prompt-pack/03-detailedplan2tasks.md)
- [prompt-pack/04-tasks2build.md](prompt-pack/04-tasks2build.md)
- [prompt-pack/05-review.md](prompt-pack/05-review.md)
- [prompt-pack/06-spec-check.md](prompt-pack/06-spec-check.md)
- [prompt-pack/07-whole-spec-audit.md](prompt-pack/07-whole-spec-audit.md)

Recommended starting point:
1. use `00-sample-starter-plan.md` as a reusable high-level brief for cloning the repo and running the full workflow

Recommended usage order:
1. run `00-spec2slices.md` against the `spec/` folder to produce the root `/plan` package plus `plan/slice-manifest.json`
2. for each slice, run `01-slice2metaplan.md`, `02-metaplan2detailedplan.md`, and `03-detailedplan2tasks.md`
3. loop `04-tasks2build.md` until the current slice queue is exhausted
4. run `05-review.md` and `06-spec-check.md` before committing the slice
5. after all slices pass, run `07-whole-spec-audit.md` before final completion

The intended pipeline is:
- `spec/` -> `00-spec2slices` -> slice `01..06` loops -> `07-whole-spec-audit`

The prompt pack is designed to preserve the same boundaries as the spec set:
- `spec/` remains the normative contract
- `/plan` remains the strategic implementation layer and slice index
- `/tasks` remains the operational execution queue and review/spec-check evidence surface

Workflow rules:
- keep `spec/` read-only during plan, task, and implementation generation
- do not skip directly from `spec/` to code
- prefer fresh agent sessions for each major phase and each implementation task
- require each slice to pass both review and direct spec-check before it is committed
- treat repo state, not chat history, as the durable source of truth

## Autonomous Runner
This repository includes a repo-local helper that runs the prompt-pack pipeline through the `codex` CLI.

Requirements:
- `codex` installed and available on `PATH`
- Python 3 available locally

Usage:

```bash
./bin/oh-my-lawd-build pipeline run
```

`pipeline run` requires a clean git worktree because the runner creates one commit per passing slice and a final commit after the whole-spec audit passes.

Cold-start path to a first useful result:

```bash
./bin/oh-my-lawd-build --help
./bin/oh-my-lawd-build pipeline preview --max-build-iterations 10
./bin/oh-my-lawd-build pipeline run
```

Command groups:
- `pipeline`
  - `./bin/oh-my-lawd-build pipeline run`
  - `./bin/oh-my-lawd-build pipeline resume`
  - `./bin/oh-my-lawd-build pipeline preview --max-build-iterations 10`
- `state`
  - `./bin/oh-my-lawd-build state show --run-state-path docs/release-evidence/inputs/w7-provider-rejection-run-state.json`
- `extension`
  - `./bin/oh-my-lawd-build extension onboard --extension-id demo-extension --manifest-path extensions/demo-extension/manifest.json --config-path extensions/demo-extension/config.json`
  - `./bin/oh-my-lawd-build extension status --extension-id demo-extension`

Pipeline flags:
- `--max-build-iterations 10`
- `--max-slice-retries 3`
- `--model <model>`
- `--profile <profile>`
- `--codex-bin <path>`
- `--verbose`

Legacy compatibility:
- `./bin/oh-my-lawd-build` maps to `pipeline run`
- `./bin/oh-my-lawd-build --dry-run` maps to `pipeline run --dry-run`
- `./bin/oh-my-lawd-build --resume` maps to `pipeline run --resume`

Runner state and logs are written to `.ohmylawd/`.

Runner state now tracks the active slice, per-slice review/spec-check results, retry counts, and slice commit SHAs.

`state show` expects a persisted runtime `run_state` JSON, not the runner metadata file at `.ohmylawd/run-state.json`.

## Contributing And Governance
This repository is governed as a specification project, not an implementation repo.

Before opening a PR or issue:
- read [CONTRIBUTING.md](CONTRIBUTING.md)
- use the issue templates under [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE)
- use [SECURITY.md](SECURITY.md) for sensitive reports instead of public issues
- review [RELEASING.md](RELEASING.md) if the change affects release process or release-worthy repo state

Use GitHub Discussions for:
- open-ended questions about the spec set
- architecture discussion that is still exploratory
- comparisons to other harnesses
- reports on emerging agent harnesses worth evaluating

Use Issues for:
- spec bugs
- ambiguities that block planning or implementation
- scoped proposals
- prompt-pack drift

Contribution standards:
- preserve layer boundaries
- avoid redefining the same requirement in multiple documents
- keep normative changes small and justified
- keep `prompt-pack/` aligned with the spec set
- prefer tightening and removal over speculative expansion

The review model for this repo is:
- `spec/` defines the contract
- `prompt-pack/` must remain aligned with that contract
- governance files protect against drift, unsafe prompts, and unreviewed normative changes

## Structure
- `spec/oh-my-lawd.md`: index and document ownership boundaries
- `spec/runtime-spec.md`: runtime execution, persistence, restore, and approval enforcement
- `spec/orchestration-spec.md`: task state, blocking, scheduling, delegation, and task-output taxonomy
- `spec/product-contract.md`: product UX, approval UX, explainability UX, and operational visibility
- `spec/system-coherence-review.md`: non-normative coherence, scope, and complexity guardrails
- `prompt-pack/00-sample-starter-plan.md`: reusable high-level brief for bootstrapping the full workflow
- `prompt-pack/00-spec2slices.md`: derives the root `/plan` package plus the slice manifest from the spec set
- `prompt-pack/01-slice2metaplan.md` through `prompt-pack/06-spec-check.md`: plan, task, build, review, and spec-check one slice at a time
- `prompt-pack/07-whole-spec-audit.md`: closes the pipeline with a repository-wide spec audit
- `CONTRIBUTING.md`: contributor rules for boundary discipline and spec-safe changes
- `SECURITY.md`: security and sensitive-reporting guidance
- `RELEASING.md`: release cadence, versioning guidance, and release checklist
- `.github/`: CODEOWNERS, PR template, and issue templates for repo governance
