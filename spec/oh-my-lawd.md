# Oh My Lawd

This is the product specification index.

Oh My Lawd is an independent open-source specification project and is not affiliated with or endorsed by Anthropic.

## Active Spec Set
1. [Runtime Specification](./runtime-spec.md)
2. [Orchestration Specification](./orchestration-spec.md)
3. [Product Contract](./product-contract.md)
4. [System Coherence Review](./system-coherence-review.md)

## Governance
1. Runtime Specification is stability-first and changes least frequently.
2. Orchestration Specification evolves with planning and delegation strategy.
3. Product Contract evolves with UX and onboarding requirements.
4. System Coherence Review constrains scope, release burden, and cross-layer consistency.

## Change Rule
No requirement may be defined in more than one document.
- Runtime behavior belongs in Runtime Specification.
- Task graph, task state, scheduler, delegation, and output taxonomy behavior belong in Orchestration Specification.
- Journey, explainability UX, approval UX, and onboarding UX belong in Product Contract.
- System Coherence Review is non-normative and exists to review cross-layer fit, release scope, and complexity cost.
