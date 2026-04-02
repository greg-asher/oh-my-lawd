# Oh My Lawd

Oh My Lawd is an independent open-source specification project for an agent harness: a runtime, orchestration, and product control system that turns a language model from a text generator into a controlled, repeatable execution engine.

This project is not affiliated with or endorsed by Anthropic.

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

- [prompt-pack/01-spec2plan.md](prompt-pack/01-spec2plan.md)
- [prompt-pack/02-plan2tasks.md](prompt-pack/02-plan2tasks.md)
- [prompt-pack/03-tasks2build.md](prompt-pack/03-tasks2build.md)

Recommended usage order:
1. run `01-spec2plan.md` against the `spec/` folder to produce a `/plan` workspace
2. run `02-plan2tasks.md` against `/plan` to produce a `/tasks` workspace
3. run `03-tasks2build.md` against `/tasks` and `/plan` to execute the next ready implementation task honestly

The intended pipeline is:
- `spec/` -> `/plan` -> `/tasks` -> implementation

The prompt pack is designed to preserve the same boundaries as the spec set:
- `spec/` remains the normative contract
- `/plan` becomes the strategic implementation layer
- `/tasks` becomes the operational execution queue

## Structure
- `spec/oh-my-lawd.md`: index and document ownership boundaries
- `spec/runtime-spec.md`: runtime execution, persistence, restore, and approval enforcement
- `spec/orchestration-spec.md`: task state, blocking, scheduling, delegation, and task-output taxonomy
- `spec/product-contract.md`: product UX, approval UX, explainability UX, and operational visibility
- `spec/system-coherence-review.md`: non-normative coherence, scope, and complexity guardrails
- `prompt-pack/01-spec2plan.md`: derives a buildable `/plan` package from the spec set
- `prompt-pack/02-plan2tasks.md`: derives an executable `/tasks` queue from `/plan`
- `prompt-pack/03-tasks2build.md`: executes the next ready task and updates `/tasks` and selected `/plan` truth
