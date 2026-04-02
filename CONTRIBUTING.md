# Contributing

## Project Model
This repository is a specification project, not an implementation repository.

The main contribution standards are:
- preserve layer boundaries
- avoid duplicating requirements across documents
- keep normative changes small and justified
- prefer tightening and removal over speculative expansion

## Document Ownership
- `spec/runtime-spec.md`: runtime execution, persistence, restore, approval binding and enforcement
- `spec/orchestration-spec.md`: task state, blocking, scheduling, delegation, taxonomy
- `spec/product-contract.md`: UX, visibility, explainability, approval UX, onboarding UX
- `spec/system-coherence-review.md`: non-normative coherence and complexity guardrails
- `prompt-pack/`: workflows that must remain aligned with the spec set

## Before Opening a PR
Be explicit about:
- which layer changed
- whether the change is normative or non-normative
- what failure or ambiguity the change addresses
- whether any acceptance gates are affected
- whether any prompt-pack file must be updated to stay aligned

## Change Rules
1. Do not redefine the same requirement in multiple documents.
2. Do not move backend truth into the product contract.
3. Do not move orchestration semantics into runtime.
4. Do not widen enums, policies, or state vocabularies without a concrete behavioral reason.
5. Do not weaken persisted-truth, approval-binding, or blocking semantics for convenience.

## Prompt-Pack Contributions
Prompt-pack changes must:
- preserve the `spec -> plan -> tasks -> execution` flow
- preserve the distinction between normative truth and operational projections
- avoid inventing architecture outside the spec set
- avoid turning planning artifacts into execution-state stores

## Preferred PR Shape
Small PRs are preferred.

Good:
- tighten one document boundary
- fix one contradiction
- align one prompt with the current spec
- improve one governance artifact

Bad:
- broad rewrites across all documents without a single governing reason
- speculative expansion of runtime or orchestration surfaces
- mixing naming cleanup with behavioral changes and prompt-pack redesign in one PR
