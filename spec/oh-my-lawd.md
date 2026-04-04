# Oh My Lawd

This is the product specification index.

Oh My Lawd is an independent open-source specification project and is not affiliated with or endorsed by Anthropic.

## Active Spec Set
1. [Runtime Specification](./runtime-spec.md)
2. [Orchestration Specification](./orchestration-spec.md)
3. [Product Contract](./product-contract.md)
4. [Scope and Simplicity Guide](./scope-and-simplicity-guide.md)

## Governance
1. Runtime Specification is stability-first and changes least frequently.
2. Orchestration Specification evolves with planning and delegation strategy.
3. Product Contract evolves with UX and onboarding requirements.
4. Scope and Simplicity Guide keeps the spec lean, clear, and consistent across layers.

## Implementation Fidelity Rule
Preserved, canonical, and release-blocking seams are binding from spec to plan to tasks to implementation.

Required behavior:
1. any preserved, canonical, or release-blocking seam MUST remain concretely represented through planning, tasking, implementation, and release validation
2. a seam MAY be renamed or reduced only if the plan records the change explicitly, with rationale and impact
3. demo flows, aliases, and fixture-backed substitutes do NOT satisfy a preserved seam unless the owning document explicitly defines them as the real release surface
4. validation checks confirm implemented behavior and MUST NOT stand in for missing functionality

## Implementation Fidelity Rule
Preserved, canonical, and release-blocking seams are binding from spec to plan to tasks to implementation.

Required behavior:
1. any preserved, canonical, or release-blocking seam MUST remain concretely represented through planning, tasking, implementation, and release evidence
2. a seam MAY be renamed or reduced only if the plan records the change explicitly, with rationale and impact
3. demo flows, walkthrough harnesses, aliases, and fixture-backed substitutes do NOT satisfy a preserved seam unless the owning document explicitly defines them as the real release surface
4. evidence validates implemented behavior and MUST NOT stand in for missing functionality

## Change Rule
No requirement may be defined in more than one document.
- Runtime behavior belongs in Runtime Specification.
- Task graph, task state, scheduler, delegation, and output taxonomy behavior belong in Orchestration Specification.
- Journey, explainability UX, approval UX, and onboarding UX belong in Product Contract.
- Scope and Simplicity Guide is non-normative and exists to keep scope clear, reduce complexity, and maintain cross-layer consistency.
