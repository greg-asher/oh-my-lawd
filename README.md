# Oh My Lawd

Oh My Lawd is an independent open-source specification project for an agent runtime, orchestration layer, and product contract.

This project is not affiliated with or endorsed by Anthropic.

## Background
This specification was created agentically.

It emerged from analysis of the rapid wave of Claude Code clones that appeared on GitHub in the 48 hours leading up to April 2, 2026, after Anthropic's Claude Code source leak became public. For broader context, see the Wall Street Journal article: [Anthropic Races to Contain Leak of Code Behind Claude AI Agent](https://www.wsj.com/tech/ai/anthropic-races-to-contain-leak-of-code-behind-claude-ai-agent-4bc5acc7?gaa_at=eafs&gaa_n=AWEtsqcUPuZoCO1ciJb8rRUZZy1kFHfazh0-AztaQO5XmVMgce0WSD6Kzm_t&gaa_ts=69ce65f5&gaa_sig=FwVmHcmH8vuU6zt6lIhJI9n1vKDiS6-IaFfKzitSBJIO5UgsUIVYoWOZ_AL5gXM_sZUgRpW9J1eEtsYWhuk0Ig%3D%3D).

Our agents identify Claude Code clones emerging on GitHub, analyze the implementations that remain publicly accessible, and continuously update a uniform best-practices specification distilled from the repos that survive DMCA takedowns.

The goal of this repository is not to mirror any leaked code. The goal is to capture the durable architectural patterns, execution semantics, orchestration boundaries, and product behaviors that emerged across the clone ecosystem and turn them into a coherent public specification.

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
