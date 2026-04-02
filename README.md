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
This repository also includes a prompt pack for turning the spec set into an executable implementation workflow:

- [prompt-pack/00-sample-starter-plan.md](prompt-pack/00-sample-starter-plan.md)
- [prompt-pack/01-spec2plan.md](prompt-pack/01-spec2plan.md)
- [prompt-pack/02-plan2tasks.md](prompt-pack/02-plan2tasks.md)
- [prompt-pack/03-tasks2build.md](prompt-pack/03-tasks2build.md)

Recommended starting point:
1. use `00-sample-starter-plan.md` as a reusable high-level brief for cloning the repo and running the full workflow

Recommended usage order:
1. run `01-spec2plan.md` against the `spec/` folder to produce a `/plan` workspace
2. validate `/plan` before moving on
3. run `02-plan2tasks.md` against `/plan` to produce a `/tasks` workspace
4. run `03-tasks2build.md` against `/tasks` and `/plan` to execute the next ready implementation task honestly

The intended pipeline is:
- `spec/` -> `/plan` -> `/tasks` -> implementation

The prompt pack is designed to preserve the same boundaries as the spec set:
- `spec/` remains the normative contract
- `/plan` becomes the strategic implementation layer
- `/tasks` becomes the operational execution queue

Workflow rules:
- keep `spec/` read-only during plan, task, and implementation generation
- do not skip directly from `spec/` to code
- prefer fresh agent sessions for each major phase and each implementation task
- treat repo state, not chat history, as the durable source of truth

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
- `prompt-pack/01-spec2plan.md`: derives a buildable `/plan` package from the spec set
- `prompt-pack/02-plan2tasks.md`: derives an executable `/tasks` queue from `/plan`
- `prompt-pack/03-tasks2build.md`: executes the next ready task and updates `/tasks` and selected `/plan` truth
- `CONTRIBUTING.md`: contributor rules for boundary discipline and spec-safe changes
- `SECURITY.md`: security and sensitive-reporting guidance
- `RELEASING.md`: release cadence, versioning guidance, and release checklist
- `.github/`: CODEOWNERS, PR template, and issue templates for repo governance
