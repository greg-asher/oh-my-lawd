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

## Structure
- `spec/oh-my-lawd.md`: index and document ownership boundaries
- `spec/runtime-spec.md`: runtime execution, persistence, restore, and approval enforcement
- `spec/orchestration-spec.md`: task state, blocking, scheduling, delegation, and task-output taxonomy
- `spec/product-contract.md`: product UX, approval UX, explainability UX, and operational visibility
- `spec/system-coherence-review.md`: non-normative coherence, scope, and complexity guardrails
